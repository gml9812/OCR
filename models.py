from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class CountryFieldMapping(BaseModel):
    pass

class CountryConfig(BaseModel):
    unique_id_field_name: str
    common_fields: List[str]
    field_mapping: Dict[str, Optional[str]]

class ExtractedData(BaseModel):
    structured_fields: Dict[str, Any] = Field(..., description="Descriptive key-value pairs for all relevant extracted text segments (values, sentences, paragraphs).")

class ProcessingMetadata(BaseModel):
    input_filename: str
    page_processed: Optional[int] = None
    processing_duration_ms: int

class OCRResponse(BaseModel):
    document_type: str = Field(..., description="Classification of the document type (e.g., invoice, receipt).")
    classification_reasoning: str = Field(..., description="LLM reasoning for the classification.")
    extracted_data: ExtractedData
    processing_metadata: ProcessingMetadata

class ErrorResponse(BaseModel):
    error: str
    raw_response: Optional[str] = None

class KeywordExtractionResponse(BaseModel):
    extracted_keywords: Dict[str, Optional[str]] = Field(..., description="Dictionary containing the requested keywords and their extracted values. Value is null if keyword was not found.")

class StandardBusinessLicenseResponse(BaseModel):
    OCR_TAX_ID_NUM: Optional[str] = None
    OCR_BP_NAME_LOCAL: Optional[str] = None
    OCR_REPRE_NAME: Optional[str] = None
    OCR_COMP_REG_NUM: Optional[str] = None
    OCR_FULL_ADDR_LOCAL: Optional[str] = None
    OCR_BIZ_TYPE: Optional[str] = None
    OCR_INDUSTRY_TYPE: Optional[str] = None

class DynamicReceiptResponse(BaseModel):
    """
    Dynamic response model for receipt processing.
    The LLM determines the optimal JSON structure based on the receipt content.
    """
    class Config:
        # Allow any additional fields that the LLM might return
        extra = "allow"
    
    # We can define some common fields that might be present, but they're all optional
    # since the LLM will determine the actual structure
    def __init__(self, **data):
        super().__init__(**data) 