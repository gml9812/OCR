from typing import Dict, Any, Optional
from fastapi import UploadFile, HTTPException
from services.file_processor import FileProcessor
from services.gemini_service import GeminiService
from utils.error_handlers import APIError
import json
import logging

logger = logging.getLogger(__name__)

class ReceiptProcessor:
    """Processor for receipt documents."""
    
    def __init__(self, file_processor: FileProcessor, gemini_service: GeminiService):
        self.file_processor = file_processor
        self.gemini_service = gemini_service
    
    def get_prompt_template(self) -> str:
        """
        Get the prompt template for receipt documents.
        
        Returns:
            str containing the prompt template
        """
        return """
        Analyze this receipt document and extract ALL relevant information into a well-structured JSON object.

        Please create the most appropriate JSON structure based on what you can see in the receipt. Include:
        - Merchant/store information (name, address, phone, etc.)
        - Transaction details (date, time, receipt number, etc.)
        - All purchased items with their details (name, quantity, price, etc.)
        - Financial information (subtotal, tax, total, discounts, etc.)
        - Payment information (method, card details if visible, etc.)
        - Any other relevant information you can extract

        Guidelines:
        1. Use clear, descriptive field names that make sense for the data
        2. Group related information logically (e.g., merchant info, items, totals)
        3. For multiple items, use an array/list structure
        4. Include confidence indicators if you're uncertain about any values
        5. Use appropriate data types (numbers for amounts, arrays for lists, etc.)
        6. Extract monetary values as numbers without currency symbols
        7. If you can't read something clearly, indicate uncertainty

        Return ONLY the JSON object with the extracted data. Do not include any explanations or additional text outside the JSON.
        Make the JSON structure as comprehensive and useful as possible based on what's actually visible in the receipt.
        """
    
    async def process(
        self,
        file: UploadFile
    ) -> Dict[str, Any]:
        """
        Process a receipt document.
        
        Args:
            file: The uploaded document file
            
        Returns:
            Dict containing the extracted data in a dynamic format
            
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
            
            # Get prompt
            prompt = self.get_prompt_template()
            
            # Process with Gemini
            response_text, error = await self.gemini_service.process_document(
                processed_image_bytes,
                processed_mime_type,
                prompt
            )
            
            if error:
                raise HTTPException(status_code=500, detail=error)
                
            # Parse response
            try:
                # Strip Markdown code block markers if present
                cleaned_response_text = response_text.strip()
                if cleaned_response_text.startswith("```json"):
                    # Find the start and end of the JSON block
                    start_idx = cleaned_response_text.find("{")
                    end_idx = cleaned_response_text.rfind("}")
                    if start_idx != -1 and end_idx != -1:
                        cleaned_response_text = cleaned_response_text[start_idx:end_idx+1]
                elif cleaned_response_text.startswith("```"):
                    # Handle other code block formats
                    lines = cleaned_response_text.split('\n')
                    if len(lines) > 1:
                        # Remove first and last lines if they're code block markers
                        if lines[0].startswith("```") and lines[-1].strip() == "```":
                            cleaned_response_text = '\n'.join(lines[1:-1])
                
                extracted_data = json.loads(cleaned_response_text)
                
                # Validate that we got a dictionary
                if not isinstance(extracted_data, dict):
                    raise ValueError("Response is not a JSON object")
                    
                return extracted_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response: {response_text}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse Gemini response as JSON: {str(e)}"
                )
            except ValueError as e:
                logger.error(f"Invalid response format: {response_text}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid response format: {str(e)}"
                )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Unexpected error in ReceiptProcessor.process", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) 