from typing import Dict, Any, Optional
import json
import logging
from .error_handlers import APIError, ExternalServiceError

logger = logging.getLogger(__name__)

class ResponseParser:
    """Utility class for parsing and validating API responses."""
    
    @staticmethod
    def parse_json_response(response_text: str) -> Dict[str, Any]:
        """
        Parse a JSON response from an external service.
        
        Args:
            response_text (str): The response text to parse
            
        Returns:
            Dict[str, Any]: The parsed JSON response
            
        Raises:
            ExternalServiceError: If the response cannot be parsed
        """
        try:
            cleaned_response = ResponseParser._clean_response_text(response_text)
            parsed_json = json.loads(cleaned_response)
            
            if not isinstance(parsed_json, dict):
                raise ExternalServiceError(
                    message="Response is not a JSON object",
                    raw_response=response_text
                )
                
            return parsed_json
            
        except json.JSONDecodeError as e:
            raise ExternalServiceError(
                message=f"Invalid JSON response: {str(e)}",
                raw_response=response_text
            )
        except Exception as e:
            raise ExternalServiceError(
                message=f"Error parsing response: {str(e)}",
                raw_response=response_text
            )
    
    @staticmethod
    def _clean_response_text(response_text: str) -> str:
        """
        Clean and prepare response text for JSON parsing.
        
        Args:
            response_text (str): The raw response text
            
        Returns:
            str: Cleaned response text
            
        Raises:
            ExternalServiceError: If no valid JSON object can be found
        """
        if not response_text:
            raise ExternalServiceError(message="Empty response received")
            
        text = response_text.strip()
        
        # Handle markdown code blocks
        if text.startswith('```json'):
            text = text[7:]
        if text.endswith('```'):
            text = text[:-3]
            
        text = text.strip()
        
        # If response starts with a JSON object, use it
        if text.startswith('{'):
            return text
            
        # Try to find JSON object in the text
        json_start = text.find('{')
        json_end = text.rfind('}')
        
        if json_start != -1 and json_end != -1:
            return text[json_start:json_end+1]
            
        raise ExternalServiceError(
            message="No valid JSON object found in response",
            raw_response=response_text
        )
    
    @staticmethod
    def extract_field(
        data: Dict[str, Any],
        field_path: str,
        default: Any = None
    ) -> Any:
        """
        Safely extract a field from a nested dictionary using dot notation.
        
        Args:
            data (Dict[str, Any]): The dictionary to extract from
            field_path (str): The path to the field (e.g., "user.address.city")
            default (Any): Default value if field is not found
            
        Returns:
            Any: The extracted value or default
        """
        try:
            current = data
            for key in field_path.split('.'):
                if isinstance(current, dict):
                    current = current.get(key, default)
                else:
                    return default
            return current
        except Exception:
            return default 