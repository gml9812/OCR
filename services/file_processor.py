from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException
import logging
from PIL import Image
import fitz  # PyMuPDF
import io

logger = logging.getLogger(__name__)

class FileProcessor:
    SUPPORTED_IMAGE_TYPES = ('.png', '.jpg', '.jpeg', '.tiff', '.tif')
    SUPPORTED_PDF_TYPES = ('.pdf',)

    @staticmethod
    async def process_file(file: UploadFile) -> Tuple[bytes, str]:
        """
        Process an uploaded file and return its bytes and MIME type.
        
        Args:
            file (UploadFile): The uploaded file to process
            
        Returns:
            Tuple[bytes, str]: A tuple containing the file bytes and MIME type
            
        Raises:
            HTTPException: If file is invalid or unsupported
        """
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file uploaded.")
            
        filename = file.filename.lower()
        try:
            if filename.endswith(FileProcessor.SUPPORTED_IMAGE_TYPES):
                return await FileProcessor._process_image(file)
            elif filename.endswith(FileProcessor.SUPPORTED_PDF_TYPES):
                return await FileProcessor._process_pdf(file)
            else:
                raise HTTPException(
                    status_code=400, 
                    detail="Unsupported file type. Use PNG, JPG, TIFF, or PDF."
                )
        except Exception as e:
            logger.error(f"Error processing file {filename}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process file: {str(e)}"
            )

    @staticmethod
    async def _process_image(file: UploadFile) -> Tuple[bytes, str]:
        """Process an image file."""
        try:
            contents = await file.read()
            # Validate image by opening it
            Image.open(io.BytesIO(contents))
            mime_type = file.content_type or 'image/jpeg'
            return contents, mime_type
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image file: {str(e)}"
            )

    @staticmethod
    async def _process_pdf(file: UploadFile) -> Tuple[bytes, str]:
        """Process a PDF file, converting first page to image."""
        try:
            contents = await file.read()
            pdf_document = fitz.open(stream=contents, filetype="pdf")
            if pdf_document.page_count == 0:
                raise HTTPException(
                    status_code=400,
                    detail="PDF file is empty"
                )
            
            # Get first page
            first_page = pdf_document[0]
            pix = first_page.get_pixmap()
            
            # Convert to bytes
            img_data = pix.tobytes("png")
            return img_data, "image/png"
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid PDF file: {str(e)}"
            )
        finally:
            if 'pdf_document' in locals():
                pdf_document.close() 