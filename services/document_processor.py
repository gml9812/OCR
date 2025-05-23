from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
import json
import logging
import time

from fastapi import UploadFile, HTTPException
from .file_processor import FileProcessor
from .gemini_service import GeminiService
from utils.response_parser import ResponseParser

logger = logging.getLogger(__name__)

class DocumentProcessor(ABC):
    """Base class for document processors."""
    
    def __init__(self, file_processor: FileProcessor, gemini_service: GeminiService):
        self.file_processor = file_processor
        self.gemini_service = gemini_service
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return the schema for the document type."""
        pass
    
    @abstractmethod
    def get_prompt_template(self) -> str:
        """Return the prompt template for the document type."""
        pass
    
    async def process(self, file: UploadFile, **kwargs) -> Dict[str, Any]:
        """
        Process a document and extract information according to the schema.
        
        Args:
            file: The uploaded document file
            **kwargs: Additional parameters specific to the document type
            
        Returns:
            Dict containing extracted data and processing metadata
        """
        start_time = time.time()
        
        try:
            # Process the file
            image_bytes, mime_type = await self.file_processor.process_file(file)
            
            # Get schema and construct prompt
            schema = self.get_schema()
            prompt = self.get_prompt_template().format(
                schema=json.dumps(schema, indent=2),
                **kwargs
            )
            
            # Process with Gemini API
            response_text, error = await self.gemini_service.process_document(
                image_bytes=image_bytes,
                mime_type=mime_type,
                prompt=prompt
            )
            
            if error:
                raise HTTPException(status_code=500, detail=error)
            
            # Parse response
            try:
                extracted_data = ResponseParser.parse_json_response(response_text)
            except Exception as e:
                logger.error(f"Failed to parse response: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to parse API response"
                )
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            return {
                "extracted_data": extracted_data,
                "processing_metadata": {
                    "processing_time": processing_time,
                    "document_type": self.__class__.__name__,
                    "confidence_score": 0.95  # Placeholder for actual confidence score
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error processing document: {str(e)}"
            ) 