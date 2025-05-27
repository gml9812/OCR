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
        if not self.country_config:
            logger.warning("BusinessLicenseProcessor initialized with empty country_config. Country identification will fail if no country is provided by the user.")
        else:
            logger.info(f"BusinessLicenseProcessor initialized with country_config containing: {list(self.country_config.keys())}")
    
    def get_schema(self, country_code: str) -> Dict[str, Any]:
        """
        Get the schema for business license documents to be used in the prompt for Gemini.
        This schema consists of OCR_XXX keys and their descriptions (which include original field names).
        
        Args:
            country_code: Country code to get country-specific schema.
            
        Returns:
            Dict containing the prompt-specific schema (the gemini_ocr_schema from config)
            
        Raises:
            HTTPException: If country code is not supported.
        """
        logger.info(f"BusinessLicenseProcessor.get_schema: Requested country: {country_code}")

        country_code_lower = country_code.lower()
        if country_code_lower not in self.country_config:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported country code: {country_code}. Supported countries: {list(self.country_config.keys())}"
            )
            
        # Directly return the gemini_ocr_schema for the country
        country_specific_config = self.country_config[country_code_lower]
        prompt_schema = country_specific_config.get("gemini_ocr_schema", {})

        if not prompt_schema:
             logger.warning(f"No gemini_ocr_schema found for country '{country_code}' or it was empty. Prompt schema will be empty.")

        return prompt_schema
    
    async def _identify_document_country(
        self,
        image_bytes: bytes,
        mime_type: str
    ) -> str:
        """
        Identifies the country of the document using Gemini.

        Args:
            image_bytes: The image bytes of the document.
            mime_type: The MIME type of the image.

        Returns:
            The identified country code (lowercase).

        Raises:
            HTTPException: If country identification fails or the country is not supported.
        """
        if not self.country_config:
            logger.error("_identify_document_country: country_config is empty. Cannot identify country.")
            raise HTTPException(status_code=500, detail="Country configuration is missing, cannot identify document country.")

        available_countries = list(self.country_config.keys())
        prompt = f"""
        Analyze this document image and identify its country of origin.
        The possible countries are: {', '.join(available_countries)}.
        Return ONLY the identified country code from the provided list (e.g., 'korea', 'usa').
        If the country cannot be reliably determined from the list, return 'unknown'.
        """

        logger.info(f"Attempting to identify document country. Available countries: {available_countries}")

        response_text, error = await self.gemini_service.process_document(
            image_bytes=image_bytes,
            mime_type=mime_type,
            prompt=prompt
        )

        if error:
            logger.error(f"Gemini error during country identification: {error}")
            raise HTTPException(status_code=500, detail=f"Error identifying document country: {error}")

        if not response_text:
            logger.error("Gemini returned an empty response for country identification.")
            raise HTTPException(status_code=500, detail="Failed to identify document country: No response from AI.")

        identified_country = response_text.strip().lower()
        logger.info(f"Gemini identified country as: '{identified_country}'")

        if identified_country == 'unknown':
            logger.warning("Gemini could not reliably determine the country.")
            raise HTTPException(status_code=400, detail=f"Could not identify document country. Please specify one of the supported countries: {available_countries}")

        if identified_country not in available_countries:
            logger.warning(f"Gemini identified an unsupported country: {identified_country}. Supported: {available_countries}")
            raise HTTPException(
                status_code=400,
                detail=f"Identified country '{identified_country}' is not supported. Supported countries: {available_countries}"
            )

        return identified_country

    def get_prompt_template(self, country_code: str) -> str:
        """
        Get the prompt template for business license documents.
        
        Args:
            country_code: Country code to get country-specific prompt
            
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
            country: Optional country code for the document. If None, country will be identified by LLM.
            
        Returns:
            Dict containing the extracted data
            
        Raises:
            HTTPException: If processing fails
        """
        try:
            # Process the uploaded file
            file_data = await self.file_processor.process_file(file)
            
            if not file_data:
                raise HTTPException(status_code=400, detail="Failed to process file: No data returned.")

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
            
            
            # Determine the country code
            effective_country_code: str
            if country:
                logger.info(f"User provided country: {country}")
                country_lower = country.lower()
                if country_lower not in self.country_config:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported country code: {country}. Supported countries: {list(self.country_config.keys())}"
                    )
                effective_country_code = country_lower
            else:
                logger.info("Country not provided by user, attempting LLM-based identification.")
                if not self.country_config:
                     logger.error("Cannot identify country: country_config is empty.")
                     raise HTTPException(status_code=500, detail="Country configuration is missing, cannot identify document country automatically.")
                effective_country_code = await self._identify_document_country(processed_image_bytes, processed_mime_type)
                logger.info(f"LLM identified country: {effective_country_code}")

            # Get schema and prompt using the determined country code
            schema = self.get_schema(effective_country_code)
            prompt = self.get_prompt_template(effective_country_code)
            
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