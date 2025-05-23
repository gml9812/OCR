from typing import Dict, Any, Optional
from fastapi import UploadFile, HTTPException
from services.file_processor import FileProcessor
from services.gemini_service import GeminiService
from utils.error_handlers import APIError
from config import COUNTRY_CONFIG
import json
import logging

logger = logging.getLogger(__name__)

class BusinessLicenseProcessor:
    """Processor for business license documents."""
    
    def __init__(self, file_processor: FileProcessor, gemini_service: GeminiService, country_config: Dict[str, Any]):
        self.file_processor = file_processor
        self.gemini_service = gemini_service
        self.country_config = country_config
    
    def get_schema(self, country_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the schema for business license documents to be used in the prompt for Gemini.
        This schema consists of OCR_XXX keys and their descriptions (which include original field names).
        
        Args:
            country_code: Optional country code to get country-specific schema
            
        Returns:
            Dict containing the prompt-specific schema (the gemini_ocr_schema from config)
            
        Raises:
            HTTPException: If country code is not supported
        """
        logger.info(f"BusinessLicenseProcessor.get_schema: Received country_code: {country_code}")

        if not country_code:
            raise HTTPException(status_code=400, detail="Country code is required")
            
        country_code_lower = country_code.lower() # Use a different variable name
        if country_code_lower not in self.country_config:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported country code: {country_code}. Supported countries: {list(self.country_config.keys())}"
            )
            
        # Directly return the gemini_ocr_schema for the country
        country_specific_config = self.country_config[country_code_lower]
        prompt_schema = country_specific_config.get("gemini_ocr_schema", {})

        if not prompt_schema:
             logger.warning(f"No gemini_ocr_schema found for country '{country_code_lower}' or it was empty. Prompt schema will be empty.")

        return prompt_schema
    
    def get_prompt_template(self, country_code: Optional[str] = None) -> str:
        """
        Get the prompt template for business license documents.
        
        Args:
            country_code: Optional country code to get country-specific prompt
            
        Returns:
            str containing the prompt template
        """
        # This will now get the prompt-specific schema with OCR_XXX keys
        schema_for_prompt = self.get_schema(country_code) 
        
        # Ensure ensure_ascii=False for languages like Korean if descriptions contain non-ASCII
        schema_json_string = json.dumps(schema_for_prompt, indent=2, ensure_ascii=False)
        
        return f"""
        Analyze this business license document and extract the following information as a JSON object:
        {schema_json_string}
        
        Return ONLY the JSON object with the extracted data. Use null for any missing fields.
        Some fields in the document might list multiple values or span multiple lines (e.g., types of business, multiple addresses, lists of items).
        For such fields, ensure you extract ALL listed values.
        Combine these multiple values into a single string for the corresponding JSON field, preferably separating distinct items with a comma or semicolon if applicable.
        Do not include any explanations or additional text.
        """
    
    async def process(
        self,
        file: UploadFile,
        country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a business license document.
        
        Args:
            file: The uploaded document file
            country: Optional country code for the document
            
        Returns:
            Dict containing the extracted data
            
        Raises:
            HTTPException: If processing fails
        """
        try:
            # Process the uploaded file
            file_data = await self.file_processor.process_file(file)
            
            # Check if file_data is valid and unpack if it's a tuple
            if not file_data:
                raise HTTPException(status_code=400, detail="Failed to process file: No data returned.")

            # Assuming process_file returns a tuple (image_bytes, mime_type)
            # If it might return a dict, more robust checking would be needed.
            if isinstance(file_data, tuple) and len(file_data) == 2:
                processed_image_bytes, processed_mime_type = file_data
            elif isinstance(file_data, dict) and "image_bytes" in file_data and "mime_type" in file_data:
                processed_image_bytes = file_data["image_bytes"]
                processed_mime_type = file_data["mime_type"]
            else:
                logger.error(f"Unexpected data structure from file_processor: {type(file_data)}, content: {str(file_data)[:200]}")
                raise HTTPException(status_code=500, detail="Unexpected data structure from file processor.")

            if not processed_image_bytes or not processed_mime_type:
                 raise HTTPException(status_code=400, detail="Failed to process file: Missing image bytes or mime type.")
                
            # Get schema and prompt
            # schema will now be the prompt_schema with OCR_XXX keys
            schema = self.get_schema(country) 
            prompt = self.get_prompt_template(country)
            
            # Process with Gemini
            response_text, error = await self.gemini_service.process_document(
                processed_image_bytes, # Use unpacked variable
                processed_mime_type,   # Use unpacked variable
                prompt
            )
            
            if error:
                raise HTTPException(status_code=500, detail=error)
                
            # Parse response
            try:
                # Strip Markdown code block markers if present
                cleaned_response_text = response_text
                if cleaned_response_text.startswith("```json\n"):
                    cleaned_response_text = cleaned_response_text[len("```json\n"):]
                if cleaned_response_text.endswith("\n```"):
                    cleaned_response_text = cleaned_response_text[:-len("\n```")]
                
                extracted_data = json.loads(cleaned_response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response: {response_text}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse Gemini response: {str(e)}"
                )
            
            # Validate extracted data against schema
            # This loop will now correctly use the OCR_XXX keys from the new schema
            validated_data = {}
            for field_key in schema.keys(): # field_key will be OCR_XXX
                validated_data[field_key] = extracted_data.get(field_key) 
            
            return validated_data # Return the validated data that conforms to the schema
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Unexpected error in BusinessLicenseProcessor.process", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) 