import os
import logging
from typing import Tuple, Optional, Dict, Any, List

# Import for the new SDK - updated to match documentation
from google import genai # Changed from import google.generativeai as genai
from google.genai import types # Changed from from google.generativeai import types as genai_types
from google.genai.types import HarmCategory, HarmBlockThreshold # Updated path

from utils.error_handlers import ExternalServiceError
# ResponseParser might not be needed if the new SDK gives structured output directly
# from utils.response_parser import ResponseParser 

logger = logging.getLogger(__name__)

class GeminiService:
    """Service for interacting with Google's Gemini API using the google-genai SDK."""
    
    # self.client will now be an instance of google.genai.Client
    client: Optional[genai.Client] = None 
    model_name_str: str # To store the short model name like 'gemini-2.0-flash-001'

    def __init__(
        self,
        project_id: Optional[str] = None,
        region: Optional[str] = None, 
        model_name: Optional[str] = None
    ):
        """
        Initialize the Gemini service using google-genai SDK for Vertex AI.
        
        Args:
            project_id: GCP project ID.
            region: GCP location (e.g., 'us-central1').
            model_name: Model name to use (e.g., 'gemini-2.0-flash-001').
        """
        used_project_id = project_id or os.environ.get("GCP_PROJECT_ID")
        if not used_project_id:
            raise ValueError("GCP_PROJECT_ID must be set either as an argument or environment variable.")
            
        used_location = region or os.environ.get("GCP_REGION", "us-central1")
        
        self.model_name_str = model_name or os.environ.get("MODEL_NAME", "gemini-2.0-flash-001")
        
        try:
            logger.info(f"Initializing google-genai Client for Vertex AI. Project: {used_project_id}, Location: {used_location}")
            
            # Initialize the main client for Vertex AI as per PyPI documentation
            self.client = genai.Client(
                vertexai=True, 
                project=used_project_id, 
                location=used_location
            )
            
            logger.info(f"Successfully initialized google-genai Client for Vertex AI. Default model for calls: {self.model_name_str}")

        except Exception as e:
            logger.error(f"Failed to initialize google-genai Client for Vertex AI: {str(e)}", exc_info=True)
            raise ExternalServiceError(f"Failed to initialize google-genai Client for Vertex AI: {str(e)}")
    
    async def process_document(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str
    ) -> Tuple[str, Optional[str]]:
        """
        Process a document using the Gemini API (google-genai SDK).
        
        Args:
            image_bytes (bytes): The image data.
            mime_type (str): The MIME type of the image.
            prompt (str): The prompt to send to the API.
            
        Returns:
            Tuple[str, Optional[str]]: The response text and any error message.
            
        Raises:
            ExternalServiceError: If the API call fails.
        """
        if not self.client:
            logger.error("Gemini client (google-genai) not initialized.")
            return "", "Gemini client not initialized."

        try:
            # Use types directly instead of genai_types
            image_part = types.Part(inline_data=types.Blob(mime_type=mime_type, data=image_bytes))
            content_parts = [prompt, image_part]
            
            logger.debug(f"Sending request with google-genai client using model: {self.model_name_str} with prompt and image.")

            # Original GenerationConfig object
            current_generation_config_obj = types.GenerationConfig(
                temperature=0.0,  
                top_p=1,       
                top_k=1          
            )
            
            # Original safety_settings dictionary
            current_safety_settings_dict = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            # Convert safety_settings dict to a list of types.SafetySetting objects
            safety_settings_list_of_objs = [
                types.SafetySetting(category=category, threshold=threshold)
                for category, threshold in current_safety_settings_dict.items()
            ]

            # Prepare the payload for types.GenerateContentConfig
            # Start with parameters from the GenerationConfig object
            generate_content_config_payload = current_generation_config_obj.model_dump(exclude_none=True)
            # Add the list of SafetySetting objects
            generate_content_config_payload["safety_settings"] = safety_settings_list_of_objs

            # Corrected async call, passing the prepared payload to the 'config' argument
            response = await self.client.aio.models.generate_content(
                model=self.model_name_str, 
                contents=content_parts,
                config=generate_content_config_payload 
            )
            
            logger.debug(f"Received response from google-genai model: {response}")

            if not response.candidates or not response.candidates[0].content.parts:
                 logger.warning("Empty or unexpected response structure from Gemini API (google-genai).")
                 if response.prompt_feedback and response.prompt_feedback.block_reason:
                     block_reason_message = response.prompt_feedback.block_reason_message or str(response.prompt_feedback.block_reason)
                     raise ExternalServiceError(f"Gemini API request blocked: {block_reason_message}")
                 raise ExternalServiceError("Empty response from Gemini API (google-genai)")

            response_text = response.text
            
            if not response_text:
                logger.warning("No text in Gemini API response (google-genai) despite valid candidates/parts.")
                raise ExternalServiceError("No text in Gemini API response (google-genai)")
                
            return response_text, None
            
        except Exception as e:
            error_msg = f"Error calling Gemini API (google-genai): {str(e)}"
            logger.error(error_msg, exc_info=True)
            return "", error_msg 