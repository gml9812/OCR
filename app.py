from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import logging
import os

from models import StandardBusinessLicenseResponse
from services.file_processor import FileProcessor
from services.gemini_service import GeminiService
from services.business_license_processor import BusinessLicenseProcessor
from utils.error_handlers import APIError, handle_api_error, handle_http_exception
from config import load_config

# --- Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Module-level variable to store the loaded country configuration
LOADED_COUNTRY_CONFIG: Dict[str, Any] = {}

# Initialize FastAPI app
app = FastAPI(
    title="Document Processing API",
    description="API for processing various document types including business licenses",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add error handlers
app.add_exception_handler(APIError, handle_api_error)
app.add_exception_handler(Exception, handle_http_exception)

# --- Dependencies ---
def get_file_processor() -> FileProcessor:
    return FileProcessor()

def get_gemini_service() -> GeminiService:
    return GeminiService(
        project_id=os.environ.get("GCP_PROJECT_ID"),
        region=os.environ.get("GCP_REGION"),
        model_name=os.environ.get("MODEL_NAME")
    )

def get_business_license_processor(
    file_processor: FileProcessor = Depends(get_file_processor),
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> BusinessLicenseProcessor:
    # Use the module-level LOADED_COUNTRY_CONFIG from app.py
    global LOADED_COUNTRY_CONFIG
    if not LOADED_COUNTRY_CONFIG:
        logger.error("get_business_license_processor: LOADED_COUNTRY_CONFIG is empty! This should have been set at startup.")
        # Fallback or raise an error, for now, pass it as is but it will likely fail in the processor
    return BusinessLicenseProcessor(file_processor, gemini_service, LOADED_COUNTRY_CONFIG)

# --- Startup Event ---
@app.on_event("startup")
async def startup_event():
    """Load configuration on startup."""
    global LOADED_COUNTRY_CONFIG
    try:
        # Verify environment variables
        required_vars = ["GCP_PROJECT_ID"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
        # Load country configuration and store it in the module-level variable
        LOADED_COUNTRY_CONFIG = load_config()
        
        if not LOADED_COUNTRY_CONFIG:
            logger.error("CRITICAL: Country configuration (LOADED_COUNTRY_CONFIG) is empty after loading at startup.")
            # Consider raising an exception here to prevent app from starting with bad config
        else:
            logger.info(f"app.py: LOADED_COUNTRY_CONFIG set. ID: {id(LOADED_COUNTRY_CONFIG)}, Keys: {list(LOADED_COUNTRY_CONFIG.keys())}")
            logger.info("Configuration loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        raise

# --- Endpoints ---
@app.post("/process-business-license", response_model=StandardBusinessLicenseResponse)
async def process_business_license(
    file: UploadFile = File(...),
    country: Optional[str] = Form(None),
    processor: BusinessLicenseProcessor = Depends(get_business_license_processor)
) -> Dict[str, Any]:
    """
    Extract key fields from business license documents.
    
    Args:
        file: The uploaded document file (image or PDF)
        country: Optional country code to use specific field mappings
        processor: BusinessLicenseProcessor instance
    
    Returns:
        Dict containing extracted fields and processing metadata
    """
    return await processor.process(file, country=country) 