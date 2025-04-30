import os
import base64
import io
import time
import json
import logging
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError # Use BaseModel from pydantic and add ValidationError

from google.cloud import aiplatform
# Secret Manager client is not needed if using ADC for Vertex AI
# from google.cloud import secretmanager
from google.protobuf import struct_pb2
import fitz  # PyMuPDF
from PIL import Image

# --- Configuration ---
# These will be set in Cloud Run environment variables
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GCP_REGION = os.environ.get("GCP_REGION", "us-central1")
# SECRET_NAME = os.environ.get("GEMINI_API_KEY_SECRET_NAME") # Not needed if using ADC
# SECRET_VERSION = os.environ.get("GEMINI_API_KEY_SECRET_VERSION", "latest") # Not needed if using ADC
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-2.0-flash-001") # Updated default model
CONFIG_FILE = "country_config.json"
COUNTRY_CONFIG = {} # Global variable to hold loaded config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Pydantic Models for Configuration Validation ---
class CountryFieldMapping(BaseModel):
    # Use extra='allow' or define all possible country-specific fields if you want strict validation
    # For now, let's assume the keys are dynamic country fields, mapping to standard OCR fields or null
    # We'll validate the target values are Optional[str]
    # This is a bit loose but flexible. A stricter approach might define all possible source fields.
    # A better validation might be done within the CountryConfig model below.
    pass # We'll validate specific known mappings later if needed

class CountryConfig(BaseModel):
    unique_id_field_name: str
    common_fields: List[str]
    field_mapping: Dict[str, Optional[str]] # Values must be string or null

    # Add custom validation if needed, e.g., ensure unique_id_field_name exists in field_mapping
    # from pydantic import validator
    # @validator('field_mapping')
    # def check_unique_id_in_mapping(cls, v, values):
    #     if 'unique_id_field_name' in values and values['unique_id_field_name'] not in v:
    #         raise ValueError(f"unique_id_field_name '{values['unique_id_field_name']}' must be present as a key in field_mapping")
    #     return v

# --- Pydantic Models for API Response Structure ---
class ExtractedData(BaseModel):
    structured_fields: Dict[str, Any] = Field(..., description="Descriptive key-value pairs for all relevant extracted text segments (values, sentences, paragraphs).")

class ProcessingMetadata(BaseModel):
    input_filename: str
    page_processed: Optional[int] = None
    processing_duration_ms: int

class OCRResponse(BaseModel):
    document_type: str = Field(..., description="Classification of the document type (e.g., invoice, receipt).")
    classification_reasoning: str = Field(..., description="LLM reasoning for the classification.")
    extracted_data: ExtractedData
    processing_metadata: ProcessingMetadata

class ErrorResponse(BaseModel):
    error: str
    raw_response: Optional[str] = None

# Pydantic model for the keyword extraction response
class KeywordExtractionResponse(BaseModel):
    extracted_keywords: Dict[str, Optional[str]] = Field(..., description="Dictionary containing the requested keywords and their extracted values. Value is null if keyword was not found.")

# --- New Pydantic Model for Standard Business License Output ---
class StandardBusinessLicenseResponse(BaseModel):
    OCR_TAX_ID_NUM: Optional[str] = None
    OCR_BP_NAME_LOCAL: Optional[str] = None
    OCR_REPRE_NAME: Optional[str] = None
    OCR_COMP_REG_NUM: Optional[str] = None
    OCR_FULL_ADDR_LOCAL: Optional[str] = None
    OCR_BIZ_TYPE: Optional[str] = None
    OCR_INDUSTRY_TYPE: Optional[str] = None
    # Add any other standard fields if needed

# --- Initialization ---
app = FastAPI(title="Gemini OCR API", version="1.0.0")

@app.on_event("startup")
def load_config():
    """Load and validate country configuration from JSON file on startup."""
    global COUNTRY_CONFIG
    COUNTRY_CONFIG = {} # Ensure it's clear if loading fails
    try:
        logger.info(f"Attempting to load configuration from {CONFIG_FILE}...")
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            raw_config_data = json.load(f)
        
        validated_config = {} 
        if not isinstance(raw_config_data, dict):
            raise TypeError("Configuration file root must be a JSON object (dictionary).")

        for country_code, config_data in raw_config_data.items():
            try:
                # Ensure country_code is string and config_data is dict before passing to model
                if not isinstance(country_code, str):
                     logger.warning(f"Skipping non-string country key in config: {country_code}")
                     continue
                if not isinstance(config_data, dict):
                     logger.warning(f"Skipping non-dictionary config data for country '{country_code}'")
                     continue
                
                validated_config[country_code.lower()] = CountryConfig(**config_data) # Store keys lowercase
            except ValidationError as country_error:
                logger.error(f"Validation error in config for country '{country_code}' in {CONFIG_FILE}: {country_error}")
                raise ValueError(f"Invalid configuration for country '{country_code}'") from country_error
            except TypeError as type_err:
                 logger.error(f"Type error processing config for country '{country_code}': {type_err}")
                 raise ValueError(f"Invalid data structure for country '{country_code}'") from type_err

        # Store validated config as plain dicts for consistency with later access
        COUNTRY_CONFIG = {k: v.dict() for k, v in validated_config.items()}

        if not COUNTRY_CONFIG:
             logger.warning(f"Configuration file {CONFIG_FILE} loaded but resulted in empty configuration after validation.")
        else:
            logger.info(f"Successfully loaded and validated country configuration from {CONFIG_FILE}")
            logger.info(f"Supported countries: {list(COUNTRY_CONFIG.keys())}")

    except FileNotFoundError:
        logger.error(f"CRITICAL: Configuration file {CONFIG_FILE} not found. Business license endpoint will NOT work.")
    except json.JSONDecodeError as e:
        logger.error(f"CRITICAL: Error decoding JSON from {CONFIG_FILE}: {e}. Business license endpoint will NOT work.")
    except TypeError as e:
        logger.error(f"CRITICAL: Configuration file {CONFIG_FILE} has invalid structure: {e}. Business license endpoint will NOT work.")
    except ValueError as e: 
         logger.error(f"CRITICAL: Configuration loading halted due to validation errors in {CONFIG_FILE}. Fix the errors and restart. Details: {e}")
         # Optional: exit application if config is absolutely essential
         # import sys; sys.exit(1)
    except Exception as e:
        logger.error(f"CRITICAL: An unexpected error occurred during config loading: {e}")

# Initialize Vertex AI *once* on startup if credentials are available
try:
    if GCP_PROJECT_ID and GCP_REGION:
        aiplatform.init(project=GCP_PROJECT_ID, location=GCP_REGION)
        logger.info(f"Vertex AI initialized for project {GCP_PROJECT_ID} in {GCP_REGION}")
    else:
        logger.warning("GCP_PROJECT_ID or GCP_REGION environment variables not set. Vertex AI may not function.")
except Exception as e:
    logger.error(f"Error initializing Vertex AI: {e}")

# --- Helper Functions (Modified for FastAPI and ADC) ---

async def process_image_input(file: UploadFile):
    """Processes image files (PNG, JPG, TIFF) into bytes."""
    try:
        contents = await file.read() # Read file contents async
        img = Image.open(io.BytesIO(contents))
        # Ensure conversion to RGB if needed
        if img.mode != 'RGB':
           img = img.convert('RGB')

        byte_arr = io.BytesIO()
        img.save(byte_arr, format='JPEG') # Save as JPEG for consistency
        return byte_arr.getvalue(), "image/jpeg"
    except Exception as e:
        logger.error(f"Error processing image file '{file.filename}': {e}")
        return None, None

async def process_pdf_input(file: UploadFile):
    """Processes the first page of a PDF file into image bytes."""
    try:
        contents = await file.read() # Read file contents async
        pdf_document = fitz.open(stream=contents, filetype="pdf")
        if not pdf_document.page_count:
            logger.warning(f"PDF file '{file.filename}' has no pages.")
            return None, None

        first_page = pdf_document.load_page(0)
        pix = first_page.get_pixmap(dpi=150)
        pdf_document.close()

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        byte_arr = io.BytesIO()
        img.save(byte_arr, format='JPEG')
        return byte_arr.getvalue(), "image/jpeg"
    except Exception as e:
        logger.error(f"Error processing PDF file '{file.filename}': {e}")
        return None, None

# Note: This remains synchronous as the SDK call itself is sync
# FastAPI will run this in a thread pool automatically
def call_gemini_api(image_bytes, mime_type, prompt_text):
    """Calls the Gemini Multimodal API using Application Default Credentials."""
    if not GCP_PROJECT_ID or not GCP_REGION:
        raise HTTPException(status_code=500, detail="Server configuration error: Missing GCP Project ID or Region.")

    try:
        # Initialize the prediction client (uses ADC implicitly)
        model_client = aiplatform.gapic.PredictionServiceClient()

        # Prepare the text part
        text_part = aiplatform.gapic.Part(text=prompt_text)

        # Prepare the image part
        image_part = aiplatform.gapic.Part(
            inline_data=aiplatform.gapic.Blob(
                mime_type=mime_type,
                data=base64.b64encode(image_bytes).decode('utf-8') # Decode bytes to string
            )
        )

        # Combine parts into a single user Content object
        user_content = aiplatform.gapic.Content(
            role="user", # Assign the user role
            parts=[text_part, image_part] # Include both text and image parts
        )

        # Construct the request payload
        # Using the more standard endpoint path structure
        endpoint_path = f"projects/{GCP_PROJECT_ID}/locations/{GCP_REGION}/publishers/google/models/{MODEL_NAME}"
        request_payload = aiplatform.gapic.GenerateContentRequest(
            model=endpoint_path,
            contents=[user_content] # Send the single user content object
        )

        # Make the synchronous API call
        response = model_client.generate_content(request=request_payload)

        # Extract the text response
        if response.candidates and response.candidates[0].content.parts:
            response_text = response.candidates[0].content.parts[0].text
            return response_text, None
        else:
            safety_ratings = response.candidates[0].safety_ratings if response.candidates else []
            block_reason = response.prompt_feedback.block_reason if response.prompt_feedback else "Unknown"
            logger.warning(f"Gemini response empty or blocked. Reason: {block_reason}, Safety: {safety_ratings}")
            return None, f"Gemini response empty or blocked. Reason: {block_reason}"

    except HTTPException as http_exc:
        raise http_exc # Re-raise FastAPI's HTTP exceptions
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        # Consider specific handling for common API errors (e.g., QuotaExceeded)
        return None, f"Gemini API call failed: {e}"

# --- API Endpoint ---
@app.post("/process",
          response_model=OCRResponse, # Use Pydantic model for response validation & docs
          responses={ # Define potential error responses for documentation
              400: {"model": ErrorResponse, "description": "Bad Request (e.g., no file, unsupported type)"},
              500: {"model": ErrorResponse, "description": "Internal Server Error (processing/API call failed)"}
          },
          summary="Process Document Image for OCR and Classification",
          tags=["OCR"])
async def process_document(file: UploadFile = File(..., description="Document file (PNG, JPG, TIFF, PDF)")):
    """
    Accepts a document file, processes it using Gemini for OCR, key-value extraction,
    unstructured text extraction, and document classification.

    - Processes PNG, JPG, TIFF images directly.
    - Processes the **first page** of PDF documents.
    - Requires Cloud Run service account to have **Vertex AI User** role.
    """
    start_time = time.time()

    if not file:
         raise HTTPException(status_code=400, detail="No file uploaded.")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided with upload.")

    filename = file.filename
    logger.info(f"Received file: {filename}")
    image_bytes = None
    mime_type = None

    # Determine file type and process (async)
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif')):
        image_bytes, mime_type = await process_image_input(file)
    elif filename.lower().endswith('.pdf'):
        image_bytes, mime_type = await process_pdf_input(file)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PNG, JPG, TIFF, or PDF.")

    if not image_bytes or not mime_type:
         logger.error(f"Failed to process input file '{filename}'")
         raise HTTPException(status_code=500, detail="Failed to process the input file.")

    # Construct the detailed prompt for Gemini (revised for literal keys)
    prompt = """Analyze the provided document image.
1.  Extract ALL visible text from the document.
2.  Identify text segments that represent key-value pairs (e.g., 'Label: Value', 'Label Value', fields in a form).
3.  Identify other distinct text blocks (like paragraphs, notes, headers, table data, list items, unlabeled values).
4.  Construct a JSON object under the key 'structured_fields'.
5.  For identified key-value pairs, use the **exact label text** found in the document (preserving case and spacing) as the JSON key, and the corresponding value text as the JSON value.
6.  For other text blocks (not clear key-value pairs), create a descriptive snake_case key representing the content or purpose (e.g., 'document_header', 'notes_section', 'unlabeled_total', 'table_row_1_col_2').
7.  If a descriptive key isn't obvious for non-key-value text, use a generic key like 'text_block_N' (where N is a sequential number) as a last resort.
8.  Ensure ALL extracted text is included in the 'structured_fields' object using one of these key generation methods. Do not omit any text.
9.  Classify the document type (e.g., invoice, receipt, letter, driver_license, form, other). Provide this as a string under 'document_type'.
10. Provide a brief (1-2 sentence) justification for the classification. Provide this as a string under 'classification_reasoning'.

Format the entire output as a single JSON object containing only the keys: 'document_type', 'classification_reasoning', and 'extracted_data' (which itself contains only the 'structured_fields' JSON object described above). Ensure the output is only the JSON object, without any other explanatory text before or after it.

Example for Key-Value preference:
Input segment: "Total Amount : $123.45"
Output in structured_fields: { "Total Amount :": "$123.45" }

Example for descriptive/generic fallback:
Input segment: "Important Notes Section..."
Output in structured_fields: { "notes_section": "Important Notes Section..." }
"""

    # Call Gemini (synchronous function run in thread pool by FastAPI)
    gemini_response_text, error = call_gemini_api(image_bytes, mime_type, prompt)

    if error:
        # Use HTTPException for FastAPI error handling
        raise HTTPException(status_code=500, detail=error)
    if not gemini_response_text:
         raise HTTPException(status_code=500, detail="Received empty response from LLM")

    # Attempt to parse the JSON response from Gemini
    try:
        # Clean potential markdown code blocks
        if gemini_response_text.strip().startswith('```json'):
            cleaned_response = gemini_response_text.strip()[7:-3].strip()
        elif gemini_response_text.strip().startswith('{'):
             cleaned_response = gemini_response_text.strip()
        else:
             json_start = gemini_response_text.find('{')
             json_end = gemini_response_text.rfind('}')
             if json_start != -1 and json_end != -1:
                 cleaned_response = gemini_response_text[json_start:json_end+1]
             else:
                 raise ValueError("Cannot find JSON object in response")

        result_data = json.loads(cleaned_response)

        # Validate structure using Pydantic (will raise validation error if mismatch)
        # We only need the core fields for validation here before adding metadata
        validated_core_data = OCRResponse(
            document_type=result_data.get('document_type', 'N/A'),
            classification_reasoning=result_data.get('classification_reasoning', 'N/A'),
            extracted_data=ExtractedData(
                structured_fields=result_data.get('extracted_data', {}).get('structured_fields', {})
            ),
            processing_metadata=ProcessingMetadata( # Dummy value, will be replaced
                input_filename='temp', processing_duration_ms=0
            )
        )

    except (json.JSONDecodeError, ValueError, ValidationError) as e: # Catch Pydantic validation error too
        logger.error(f"Failed to parse or validate JSON response from Gemini: {e}")
        logger.error(f"Raw Gemini response: {gemini_response_text}")
        # Return error using JSONResponse for custom structure
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(error="Failed to parse or validate LLM response.", raw_response=gemini_response_text).dict()
        )

    end_time = time.time()
    processing_duration = int((end_time - start_time) * 1000)

    # Create final response using validated data and add correct metadata
    final_response = OCRResponse(
        document_type=validated_core_data.document_type,
        classification_reasoning=validated_core_data.classification_reasoning,
        extracted_data=validated_core_data.extracted_data,
        processing_metadata=ProcessingMetadata(
            input_filename=filename,
            page_processed=1 if filename.lower().endswith('.pdf') else None,
            processing_duration_ms=processing_duration
        )
    )

    logger.info(f"Successfully processed file: {filename} in {processing_duration} ms")
    return final_response # FastAPI automatically converts Pydantic model to JSON

# --- New Keyword Extraction Endpoint ---
@app.post("/extract-keywords",
          response_model=KeywordExtractionResponse,
          responses={ # Define potential error responses
              400: {"model": ErrorResponse, "description": "Bad Request (e.g., no file, no keywords, unsupported type)"},
              500: {"model": ErrorResponse, "description": "Internal Server Error (processing/API call failed)"}
          },
          summary="Extract Specific Keywords from Document",
          tags=["Keyword Extraction"])
async def extract_specific_keywords(
    file: UploadFile = File(..., description="Document file (PNG, JPG, TIFF, PDF)"),
    keywords: str = Form(..., description="Comma-separated string of keywords to extract (e.g., 'Invoice Number,Total Amount')")
):
    """
    Accepts a document file and a comma-separated list of keywords.
    Uses Gemini to extract the values associated with those specific keywords.
    Returns a dictionary of found keyword-value pairs.
    """
    start_time = time.time()

    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded.")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided with upload.")
    if not keywords:
        raise HTTPException(status_code=400, detail="No keywords provided.")

    filename = file.filename
    logger.info(f"Received file for keyword extraction: {filename}")
    logger.info(f"Keywords to extract: {keywords}")

    keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
    if not keyword_list:
        raise HTTPException(status_code=400, detail="Keywords list is empty or invalid.")

    image_bytes = None
    mime_type = None

    # Determine file type and process (async)
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif')):
        image_bytes, mime_type = await process_image_input(file)
    elif filename.lower().endswith('.pdf'):
        image_bytes, mime_type = await process_pdf_input(file)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PNG, JPG, TIFF, or PDF.")

    if not image_bytes or not mime_type:
         logger.error(f"Failed to process input file '{filename}' for keyword extraction")
         raise HTTPException(status_code=500, detail="Failed to process the input file.")

    # Construct the keyword-specific prompt for Gemini (revised for multi-line values)
    keyword_string_for_prompt = ", ".join([f"'{k}'" for k in keyword_list]) # Format for clarity in prompt
    prompt = f"""Analyze the provided document image.
1.  Carefully locate the following keywords or fields in the document: {keyword_string_for_prompt}.
2.  For each keyword found, extract its **complete corresponding value**. This value might span multiple lines or be presented in a list or column format below or next to the keyword. Ensure you capture the *entire* text that logically belongs to that keyword.
3.  Return the results as a single JSON object where the keys are the exact keywords provided ({keyword_string_for_prompt}) and the values are the full extracted text strings (including newlines if they are part of the value).
4.  If a specific keyword is not found in the document, omit it from the final JSON object.
5.  Ensure the output is ONLY the JSON object, with no other text before or after it.

Example Input Keywords: 'Shipping Address', 'Items'
Example Output (Address might be multi-line, Items might be a list joined by newlines):
```json
{{
  "Shipping Address": "123 Main St\nAnytown, CA 91234",
  "Items": "Product A - Qty 2\nProduct B - Qty 5"
}}
```
"""

    logger.info(f"Calling Gemini for keywords: {keyword_list}")
    # Call Gemini
    gemini_response_text, error = call_gemini_api(image_bytes, mime_type, prompt)

    if error:
        raise HTTPException(status_code=500, detail=f"Gemini API error during keyword extraction: {error}")
    if not gemini_response_text:
         raise HTTPException(status_code=500, detail="Received empty response from LLM during keyword extraction")

    # Attempt to parse the JSON response from Gemini
    # Initialize with None for all requested keywords
    extracted_data: Dict[str, Optional[str]] = {key: None for key in keyword_list}
    try:
        # Basic cleaning for potential markdown
        if gemini_response_text.strip().startswith('```json'):
            cleaned_response = gemini_response_text.strip()[7:-3].strip()
        elif gemini_response_text.strip().startswith('{'):
            cleaned_response = gemini_response_text.strip()
        else:
             # Try finding the first '{' and last '}'
             json_start = gemini_response_text.find('{')
             json_end = gemini_response_text.rfind('}')
             if json_start != -1 and json_end != -1:
                 cleaned_response = gemini_response_text[json_start:json_end+1]
             else:
                 # If no JSON object found, assume it might be a direct value for a single keyword?
                 # Or raise error - let's raise for now, safer.
                 raise ValueError("Cannot find JSON object in response")

        parsed_json = json.loads(cleaned_response)

        # Ensure the response is a dictionary
        if not isinstance(parsed_json, dict):
            raise ValueError("LLM response is not a JSON object (dictionary)")

        # Update values for keys found by the LLM and requested by the user
        for key, value in parsed_json.items():
            if key in extracted_data: # Check if this key was actually requested
                if isinstance(value, (str, int, float)):
                    extracted_data[key] = str(value) # Update from None to the found string value
                elif value is None:
                    extracted_data[key] = None # Explicitly handle if LLM returns null
                # else: LLM returned a value type we don't expect (e.g., list, object) for a requested key, keep as None

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse or validate JSON response from Gemini for keywords: {e}")
        logger.error(f"Raw Gemini response for keywords: {gemini_response_text}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse LLM response for keywords. Raw response: {gemini_response_text}"
        )

    end_time = time.time()
    processing_duration = int((end_time - start_time) * 1000)

    logger.info(f"Successfully extracted keywords for file: {filename} in {processing_duration} ms. Found: {list(extracted_data.keys())}")

    # Return using the Pydantic model
    return KeywordExtractionResponse(extracted_keywords=extracted_data)

# --- Business License Processing Endpoint (Standardized Response with Auto-Detect) ---
@app.post("/process-business-license",
          response_model=StandardBusinessLicenseResponse,
          response_description="A standardized JSON object containing extracted fields from the business license.",
          responses={ # Define potential error responses
              400: {"model": ErrorResponse, "description": "Bad Request (e.g., no file, invalid country, auto-detect failed, unsupported file type)"},
              404: {"model": ErrorResponse, "description": "Country configuration not found (if specified and invalid)"},
              500: {"model": ErrorResponse, "description": "Internal Server Error (config loading, processing, API call failed)"}
          },
          summary="Extract Key Fields from Business License into Standard Format (with Country Auto-Detect)",
          tags=["Business License"])
async def process_business_license(
    file: UploadFile = File(..., description="Business license document file (PNG, JPG, TIFF, PDF)"),
    country: Optional[str] = Form(None, description="Optional: Country code (e.g., 'korea', 'usa'). If omitted or invalid, auto-detection will be attempted.")
) -> StandardBusinessLicenseResponse:
    """
    Accepts a business license document and an optional country code.
    If country is omitted or invalid, attempts to auto-detect the country.
    Uses country-specific configuration to guide extraction and then maps
    the results to a standard predefined JSON format.
    """
    start_time = time.time()
    detected_country = None
    user_provided_country = country.lower() if country else None

    # --- Input Validation ---
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="File and filename are required.")
    filename = file.filename # Get filename early

    # --- Configuration Check ---
    if not COUNTRY_CONFIG:
         logger.error("CRITICAL: Country configuration is not loaded. Cannot process business license.")
         raise HTTPException(status_code=500, detail="Server configuration error: Country config not loaded.")

    # --- Determine Country (Validate User Input or Auto-Detect) ---
    if user_provided_country:
        logger.info(f"User provided country: {user_provided_country}")
        if user_provided_country in COUNTRY_CONFIG:
            detected_country = user_provided_country
            logger.info(f"Using user-provided valid country: {detected_country}")
        else:
            logger.warning(f"User provided country '{user_provided_country}' is not valid/supported. Attempting auto-detection.")
            # Fall through to auto-detection
    else:
        logger.info("No country provided by user. Attempting auto-detection.")
        # Fall through to auto-detection

    # --- File Processing (Needed for detection and extraction) ---
    image_bytes, mime_type = None, None
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif')):
        image_bytes, mime_type = await process_image_input(file)
    elif filename.lower().endswith('.pdf'):
        image_bytes, mime_type = await process_pdf_input(file)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    if not image_bytes or not mime_type:
        raise HTTPException(status_code=500, detail="Failed to process the input file.")

    # --- Auto-Detection Logic (if needed) ---
    if not detected_country:
        logger.info("Performing country auto-detection call to Gemini...")
        supported_countries_str = ", ".join(list(COUNTRY_CONFIG.keys()))
        detection_prompt = f"""Analyze the provided document image.
Identify the country of origin for this business license or registration document.
Return ONLY the lowercase country code corresponding to the detected country.
The possible valid country codes are: {supported_countries_str}.
If you are unsure or cannot determine the country from the list, return the word 'unknown'.
Do not include any other explanation or text in your response.
"""
        # *** FIRST LLM CALL (for detection) ***
        detected_country_raw, detection_error = call_gemini_api(image_bytes, mime_type, detection_prompt)

        if detection_error:
            logger.error(f"Gemini API error during country detection: {detection_error}")
            raise HTTPException(status_code=500, detail=f"Error during country auto-detection: {detection_error}")
        if not detected_country_raw or detected_country_raw.strip().lower() == 'unknown':
            logger.error(f"Could not auto-detect country from the supported list. LLM response: {detected_country_raw}")
            raise HTTPException(status_code=400, detail="Could not automatically determine the document's country from the supported list.")

        potential_country = detected_country_raw.strip().lower()
        if potential_country in COUNTRY_CONFIG:
            detected_country = potential_country
            logger.info(f"Auto-detected country: {detected_country}")
        else:
            logger.error(f"Auto-detection returned an unsupported country code: '{potential_country}'. Supported: {supported_countries_str}")
            raise HTTPException(status_code=400, detail=f"Detected country '{potential_country}' is not supported by current configuration.")

    # --- Proceed with Extraction using the detected_country ---
    config = COUNTRY_CONFIG[detected_country]
    unique_id_field = config.get("unique_id_field_name")
    common_fields = config.get("common_fields", [])
    field_mapping = config.get("field_mapping")

    if not unique_id_field or not field_mapping: # Should be caught by startup validation, but good to check
        raise HTTPException(status_code=500, detail=f"Incomplete server configuration for detected country '{detected_country}'.")

    logger.info(f"Using config for {detected_country}: Unique ID Field='{unique_id_field}', Common Fields={common_fields}")

    # --- Construct Extraction Prompt ---
    all_fields_to_extract = [unique_id_field] + common_fields
    field_list_str = ", ".join([f"'{f}'" for f in all_fields_to_extract])
    extraction_prompt = f"""Analyze the provided business license document from {detected_country}.
1.  Locate and extract the values for **only** the following fields: {field_list_str}.
2.  Pay special attention to finding the '{unique_id_field}'.
3.  Return the results as a single JSON object. Keys MUST be exact field names provided ({field_list_str}). Do not include other keys.
4.  Values should be full extracted text strings (including newlines).
5.  If a field is not found, include its key in the JSON with a value of `null`.
6.  Ensure the output is ONLY the JSON object.
"""

    # --- Call Gemini API (for extraction) --- 
    # *** SECOND LLM CALL (if auto-detect was used) or FIRST (if country provided) ***
    logger.info(f"Calling Gemini for field extraction ({detected_country})...")
    gemini_response_text, error = call_gemini_api(image_bytes, mime_type, extraction_prompt)

    if error:
        raise HTTPException(status_code=500, detail=f"Gemini API error during field extraction: {error}")
    if not gemini_response_text:
         raise HTTPException(status_code=500, detail="Received empty response from LLM during field extraction")

    # --- Parse LLM Response (country-specific keys) --- 
    llm_extracted_data: Dict[str, Optional[str]] = {}
    try:
        # Basic cleaning
        if gemini_response_text.strip().startswith('```json'):
            cleaned_response = gemini_response_text.strip()[7:-3].strip()
        elif gemini_response_text.strip().startswith('{'):
            cleaned_response = gemini_response_text.strip()
        else:
            json_start = gemini_response_text.find('{')
            json_end = gemini_response_text.rfind('}')
            if json_start != -1 and json_end != -1:
                cleaned_response = gemini_response_text[json_start:json_end+1]
            else:
                raise ValueError("Cannot find JSON object in LLM response")

        parsed_json = json.loads(cleaned_response)
        if not isinstance(parsed_json, dict):
            raise ValueError("LLM response is not a JSON object")
        llm_extracted_data = parsed_json
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse LLM extraction response: {e}")
        logger.error(f"Raw Gemini response: {gemini_response_text}")
        raise HTTPException(status_code=500, detail=f"Failed to parse LLM extraction response. Raw: {gemini_response_text}")

    # --- Map to Standard Output Format --- 
    standard_response_data = StandardBusinessLicenseResponse().dict()
    for country_specific_key, extracted_value in llm_extracted_data.items():
        standard_key = field_mapping.get(country_specific_key)
        if standard_key and standard_key in standard_response_data:
            if isinstance(extracted_value, (str, int, float)): standard_response_data[standard_key] = str(extracted_value)
            elif extracted_value is None: standard_response_data[standard_key] = None
        elif standard_key is None and country_specific_key in field_mapping: pass
        else: logger.warning(f"LLM key '{country_specific_key}' not handled in mapping for {detected_country}.")

    # --- Prepare Final Response --- 
    end_time = time.time()
    processing_duration = int((end_time - start_time) * 1000)
    logger.info(f"Successfully processed/mapped ({detected_country}) license: {filename} in {processing_duration} ms.")
    return standard_response_data

# --- Adaptive Processing Endpoint ---
@app.post("/process-adaptive",
          # No response_model as structure is dynamic
          response_description="A dynamically structured JSON object representing the extracted document content.",
          responses={ # Define potential error responses
              400: {"model": ErrorResponse, "description": "Bad Request (e.g., no file, unsupported file type)"},
              500: {"model": ErrorResponse, "description": "Internal Server Error (processing, API call, response parsing failed)"}
          },
          summary="Process Document with AI-Determined Structure",
          tags=["Adaptive OCR"])
async def process_adaptive_document(
    file: UploadFile = File(..., description="Document file (PNG, JPG, TIFF, PDF)")
) -> Dict[str, Any]: # Return type is a generic dictionary
    """
    Accepts any document file.
    Instructs the AI to determine the document type, choose an appropriate
    JSON structure for its content, and extract the information into that structure.
    Returns the AI-generated JSON object.
    """
    start_time = time.time()

    # --- Input Validation ---
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="File and filename are required.")
    filename = file.filename
    logger.info(f"Received file for adaptive processing: {filename}")

    # --- File Processing ---
    image_bytes, mime_type = None, None
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif')):
        image_bytes, mime_type = await process_image_input(file)
    elif filename.lower().endswith('.pdf'):
        image_bytes, mime_type = await process_pdf_input(file)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    if not image_bytes or not mime_type:
        raise HTTPException(status_code=500, detail="Failed to process the input file.")

    # --- Construct Adaptive Prompt ---
    prompt = """Analyze the provided document image thoroughly.
1.  Determine the type of document (e.g., invoice, receipt, resume, form, letter, contract excerpt, etc.).
2.  Based on the document type and content, decide on the most logical and informative JSON structure to represent its key information. This structure might include nested objects, arrays of objects (for line items, experience, etc.), and key-value pairs.
3.  Extract **all relevant information** from the document and populate the JSON structure you designed.
4.  Use clear and descriptive keys within your JSON structure.
5.  Ensure the final output is **only** the complete JSON object representing the extracted information. Do not include any explanations, apologies, or surrounding text.

Example Goal (Conceptual - DO NOT just copy this structure):
- If it's an invoice: Structure might include keys like `invoice_id`, `vendor_info` (object), `customer_info` (object), `line_items` (array of objects), `totals` (object).
- If it's a resume: Structure might include `contact_info` (object), `summary` (string), `work_experience` (array of objects), `education` (array of objects), `skills` (array of strings).
- If it's a simple note: Structure might just be `{"note_content": "extracted text..."}`.

Your primary task is to return the best-structured JSON for the *specific document provided*.
"""

    # --- Call Gemini API --- 
    logger.info(f"Calling Gemini for adaptive processing of {filename}...")
    gemini_response_text, error = call_gemini_api(image_bytes, mime_type, prompt)

    if error:
        raise HTTPException(status_code=500, detail=f"Gemini API error during adaptive processing: {error}")
    if not gemini_response_text:
         raise HTTPException(status_code=500, detail="Received empty response from LLM during adaptive processing")

    # --- Parse LLM Response --- 
    try:
        # Attempt to clean and parse the response as JSON
        if gemini_response_text.strip().startswith('```json'):
            cleaned_response = gemini_response_text.strip()[7:-3].strip()
        elif gemini_response_text.strip().startswith('{'):
            cleaned_response = gemini_response_text.strip()
        else:
            # Broader search if no standard start
            json_start = gemini_response_text.find('{')
            json_end = gemini_response_text.rfind('}')
            if json_start != -1 and json_end != -1:
                cleaned_response = gemini_response_text[json_start:json_end+1]
            else:
                 # Maybe it's just a simple string response if JSON failed?
                 # For now, let's assume JSON is expected and raise error if not found.
                raise ValueError("Cannot find JSON object structure in LLM response")

        parsed_json = json.loads(cleaned_response)
        # We expect a dictionary, but the LLM might technically return other valid JSON types
        # Let's ensure it's a dict for consistency, though this could be relaxed to `Any`
        if not isinstance(parsed_json, dict):
             logger.warning(f"LLM response parsed but is not a dictionary: {type(parsed_json)}")
             # Option: wrap it in a dict? e.g., {"result": parsed_json}
             # Option: return as is? (Requires changing return type hint to Any)
             # Option: raise error? Let's raise for now.
             raise ValueError("LLM response must be a JSON object (dictionary)")

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse LLM response for adaptive processing: {e}")
        logger.error(f"Raw Gemini response: {gemini_response_text}")
        # Consider returning the raw text in an error response if parsing fails?
        raise HTTPException(status_code=500, detail=f"Failed to parse LLM response into expected JSON format. Raw: {gemini_response_text}")

    # --- Return Result --- 
    end_time = time.time()
    processing_duration = int((end_time - start_time) * 1000)

    logger.info(f"Successfully processed adaptive request for {filename} in {processing_duration} ms.")

    return parsed_json # Return the parsed dictionary

# Add root endpoint for basic check / documentation link
@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Gemini OCR API is running. See /docs for details."} 