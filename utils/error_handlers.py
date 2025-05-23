from fastapi import Request, Response
from fastapi.responses import JSONResponse
from typing import Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base exception for API errors."""
    def __init__(self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR", raw_response: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.raw_response = raw_response
        super().__init__(message)

class ValidationError(APIError):
    """Exception for validation errors."""
    def __init__(self, message: str, raw_response: Optional[str] = None):
        super().__init__(message, status_code=400, error_code="VALIDATION_ERROR", raw_response=raw_response)

class ProcessingError(APIError):
    """Exception for document processing errors."""
    def __init__(self, message: str, raw_response: str = None):
        super().__init__(message, status_code=500, error_code="PROCESSING_ERROR", raw_response=raw_response)

class ExternalServiceError(APIError):
    """Exception for external service errors."""
    def __init__(self, message: str, raw_response: str = None):
        super().__init__(message, status_code=500, error_code="EXTERNAL_SERVICE_ERROR", raw_response=raw_response)

async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
    """Handle APIError exceptions."""
    logger.error(f"API Error: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "raw_response": exc.raw_response
            }
        }
    )

async def handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }
    ) 