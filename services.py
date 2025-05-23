import base64
import io
import time
import json
import logging
from typing import Tuple, Optional, Dict, Any
from PIL import Image
import fitz  # PyMuPDF
from google.cloud import aiplatform
from fastapi import HTTPException

from config import GCP_PROJECT_ID, GCP_REGION, MODEL_NAME, logger

async def process_image_input(file) -> Tuple[Optional[bytes], Optional[str]]:
    """Processes image files (PNG, JPG, TIFF) into bytes."""
    try:
        contents = await file.read()
        img = Image.open(io.BytesIO(contents))
        if img.mode != 'RGB':
            img = img.convert('RGB')

        byte_arr = io.BytesIO()
        img.save(byte_arr, format='JPEG')
        return byte_arr.getvalue(), "image/jpeg"
    except Exception as e:
        logger.error(f"Error processing image file '{file.filename}': {e}")
        return None, None

async def process_pdf_input(file) -> Tuple[Optional[bytes], Optional[str]]:
    """Processes the first page of a PDF file into image bytes."""
    try:
        contents = await file.read()
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

def call_gemini_api(image_bytes: bytes, mime_type: str, prompt_text: str) -> Tuple[Optional[str], Optional[str]]:
    """Calls the Gemini Multimodal API using Application Default Credentials."""
    if not GCP_PROJECT_ID or not GCP_REGION:
        raise HTTPException(status_code=500, detail="Server configuration error: Missing GCP Project ID or Region.")

    try:
        model_client = aiplatform.gapic.PredictionServiceClient()

        text_part = aiplatform.gapic.Part(text=prompt_text)
        image_part = aiplatform.gapic.Part(
            inline_data=aiplatform.gapic.Blob(
                mime_type=mime_type,
                data=base64.b64encode(image_bytes).decode('utf-8')
            )
        )

        user_content = aiplatform.gapic.Content(
            role="user",
            parts=[text_part, image_part]
        )

        endpoint_path = f"projects/{GCP_PROJECT_ID}/locations/{GCP_REGION}/publishers/google/models/{MODEL_NAME}"
        request_payload = aiplatform.gapic.GenerateContentRequest(
            model=endpoint_path,
            contents=[user_content]
        )

        response = model_client.generate_content(request=request_payload)

        if response.candidates and response.candidates[0].content.parts:
            response_text = response.candidates[0].content.parts[0].text
            return response_text, None
        else:
            safety_ratings = response.candidates[0].safety_ratings if response.candidates else []
            block_reason = response.prompt_feedback.block_reason if response.prompt_feedback else "Unknown"
            logger.warning(f"Gemini response empty or blocked. Reason: {block_reason}, Safety: {safety_ratings}")
            return None, f"Gemini response empty or blocked. Reason: {block_reason}"

    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return None, f"Gemini API call failed: {e}" 