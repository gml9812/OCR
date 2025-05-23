# Document Processing API

## Description

This project provides a **Document Processing API** built with FastAPI, designed to extract structured information from various document types, with a primary focus on **Business Licenses**. It leverages Google's Gemini multimodal AI models via the `google-genai` SDK for OCR and information extraction.

**Purpose:** To automate the extraction of key information from business license documents from different countries, providing a standardized JSON output. The system is designed to be configurable for various country-specific document formats and fields.

**Key functionalities include:**
-   FastAPI endpoint (`/process-business-license`) for uploading business license documents (PDF, PNG, JPG, TIFF).
-   Automatic conversion of PDFs (first page) and various image formats to a processable image format (JPEG/PNG).
-   Integration with Google Gemini for OCR and structured data extraction based on dynamic, country-specific prompts and schemas.
-   Configuration-driven approach using `country_config.json` to define fields and prompts for different countries (e.g., Korea, USA).
-   Environment variable-based setup for Google Cloud Project ID, Region, and Gemini Model Name.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoint](#api-endpoint)
- [Project Structure](#project-structure)
- [Key Features Detailed](#key-features-detailed)
- [Technologies Used](#technologies-used)
- [Development Notes](#development-notes)

## Installation

### Prerequisites

-   Python 3.11 (as per Dockerfile)
-   pip (Python package installer)
-   Docker (Recommended for deployment, and for a consistent environment)
-   Access to a Google Cloud Project with the AI Platform API enabled and appropriate credentials configured for Application Default Credentials (ADC).

### Steps

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd <your-project-directory-name>
    ```

2.  **Set up Environment Variables:**
    Create a `.env` file in the project root or set the following environment variables in your system:
    ```env
    GCP_PROJECT_ID="your-gcp-project-id"
    GCP_REGION="your-gcp-region" # e.g., us-central1
    MODEL_NAME="your-gemini-model-name" # e.g., gemini-1.0-pro-vision-001 or gemini-2.0-flash-001
    # PORT=8080 # Optional, defaults to 8080 for local Uvicorn and is set by Cloud Run
    ```
    Replace placeholders with your actual GCP project details and desired Gemini model.

3.  **Create and activate a virtual environment (recommended for local development):**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Docker Setup (Recommended for Deployment)

1.  **Build the Docker image:**
    ```bash
    docker build -t document-processing-api .
    ```

2.  **Run the Docker container:**
    ```bash
    docker run -p 8080:8080 \
      -e GCP_PROJECT_ID="your-gcp-project-id" \
      -e GCP_REGION="your-gcp-region" \
      -e MODEL_NAME="your-gemini-model-name" \
      document-processing-api
    ```
    Ensure the environment variables are correctly passed to the container.

## Configuration

### `country_config.json`

This file is crucial for defining how business licenses from different countries are processed. It's a JSON object where each key is a lowercase country code (e.g., "korea", "usa"). Each country object should contain:

-   `unique_id_field_name`: (String) The primary identifier field in that country's business license (e.g., "사업자등록번호" for Korea).
-   `common_fields`: (List of Strings) A list of common field names found on the document.
-   `gemini_ocr_schema`: (Object) This is the schema provided to the Gemini model in the prompt.
    -   Keys are standardized `OCR_FIELD_NAME` (e.g., `OCR_TAX_ID_NUM`, `OCR_BP_NAME_LOCAL`).
    -   Values are descriptive strings that guide the Gemini model in extracting the correct information, often including the original field name in the local language.

**Example for a new country:**
```json
{
  "korea": { ... },
  "usa": { ... },
  "newcountry": {
    "unique_id_field_name": "Local Unique ID Field Name",
    "common_fields": ["Field1", "Field2", "Address"],
    "gemini_ocr_schema": {
      "OCR_TAX_ID_NUM": "Local Unique ID Field Name (e.g., NNN-NN-NNNNN). This is the unique tax ID.",
      "OCR_BP_NAME_LOCAL": "Official Business Name in local language.",
      "OCR_FULL_ADDR_LOCAL": "Full business address as it appears on the document."
    }
  }
}
```
The application loads this configuration at startup. Changes require a restart.

### `config.py`

This file loads `country_config.json` and sets up global configuration from environment variables:
-   `GCP_PROJECT_ID`: Your Google Cloud Project ID.
-   `GCP_REGION`: The GCP region for AI Platform services (defaults to "us-central1").
-   `MODEL_NAME`: The Gemini model to use (defaults to "gemini-2.0-flash-001").
-   `CONFIG_FILE`: Path to the country configuration JSON (defaults to "country_config.json").

## Usage

### Running Locally

1.  Ensure all prerequisites, environment variables, and dependencies are set up.
2.  Ensure `country_config.json` is present and correctly configured.
3.  Run the FastAPI application using Uvicorn (as done by the run scripts or Docker):
    ```bash
    uvicorn app:app --host 0.0.0.0 --port 8080 --reload
    ```
    The `--reload` flag is useful for development.
    Alternatively, use the provided run scripts:
    -   Windows (PowerShell): `.\run_local.ps1`
    -   Windows (Batch): `run_local.bat`
    -   macOS/Linux: `./run_local.sh` (ensure it's executable: `chmod +x ./run_local.sh`)

The API will be accessible at `http://localhost:8080`.

## API Endpoint

### Process Business License

-   **Endpoint:** `POST /process-business-license`
-   **Description:** Extracts key fields from an uploaded business license document.
-   **Request:** `multipart/form-data`
    -   `file`: The document file (PDF, PNG, JPG, JPEG, TIFF, TIF).
    -   `country`: (Optional Form data) The lowercase country code (e.g., "korea", "usa") to use specific field mappings and prompts from `country_config.json`. If not provided, or if the country code is invalid, an error will occur.
-   **Response:** `application/json`
    -   On success (200 OK): A JSON object containing the extracted fields based on the `gemini_ocr_schema` for the specified country.
        ```json
        {
          "OCR_TAX_ID_NUM": "123-45-67890",
          "OCR_BP_NAME_LOCAL": "Example Corp",
          "OCR_REPRE_NAME": "John Doe",
          // ... other fields from the schema
        }
        ```
    -   On error (4xx/5xx): A JSON object with a "detail" field describing the error.
        ```json
        {
          "detail": "Error message"
        }
        ```

**Example `curl` request:**
```bash
curl -X POST "http://localhost:8080/process-business-license" \
  -F "file=@/path/to/your/business_license.pdf" \
  -F "country=korea"
```

## Project Structure

```
.
├── .git/                     # Git version control files
├── .gitignore                # Specifies intentionally untracked files
├── app.py                    # FastAPI application entry point, defines endpoints and startup logic
├── config.py                 # Loads environment variables and country_config.json
├── country_config.json       # JSON configuration for country-specific OCR fields and prompts
├── Dockerfile                # Defines the Docker image for the application
├── models.py                 # Pydantic models for API request/response validation (e.g., StandardBusinessLicenseResponse)
├── requirements.txt          # Python dependencies
├── run_local.bat             # Batch script to run locally (Windows)
├── run_local.ps1             # PowerShell script to run locally (Windows)
├── run_local.sh              # Shell script to run locally (macOS/Linux)
├── services/                 # Core service logic
│   ├── __init__.py
│   ├── business_license_processor.py # Orchestrates business license processing using FileProcessor and GeminiService
│   ├── document_processor.py # Abstract base class for generic document processing (currently not directly used by BusinessLicenseProcessor)
│   ├── file_processor.py     # Handles file validation, image/PDF preprocessing
│   └── gemini_service.py     # Interacts with the Google Gemini API
└── utils/                    # Utility modules
    ├── __init__.py
    ├── error_handlers.py     # FastAPI custom error handlers
    └── response_parser.py    # Utility for parsing JSON responses (used by DocumentProcessor)
```

-   `app.py`: Initializes the FastAPI app, sets up CORS, error handlers, and the `/process-business-license` endpoint. Loads configuration on startup.
-   `config.py`: Manages loading of `country_config.json` and environment variables.
-   `country_config.json`: Defines country-specific schemas and field names for OCR. **This is a key file to modify when adding support for new countries or fields.**
-   `services/business_license_processor.py`: The core logic for handling a business license. It uses `FileProcessor` to prepare the document and `GeminiService` to perform OCR and data extraction based on the prompt generated from `country_config.json`.
-   `services/file_processor.py`: Validates file types (PDF, various images) and converts them into a usable format (PNG bytes for PDFs, original bytes for images) for the OCR service.
-   `services/gemini_service.py`: Encapsulates all interactions with the Google Gemini API, including authentication (via ADC), request formatting, and response handling. Configures safety settings and generation parameters.
-   `models.py`: Contains Pydantic models like `StandardBusinessLicenseResponse` to define the expected structure of API responses.
-   `Dockerfile`: Specifies how to build the production Docker image, using `python:3.11-slim` and running Uvicorn.
-   `utils/error_handlers.py`: Defines custom exception handlers for API errors.

## Key Features Detailed

-   **Dynamic Country Configuration:** Supports different business license formats and required fields per country through `country_config.json`. New countries can be added by defining their specific `gemini_ocr_schema` and field names.
-   **Multimodal Input:** Accepts PDF documents (first page is processed) and common image formats (PNG, JPEG, TIFF).
-   **Gemini Integration:** Leverages Google's Gemini models for advanced OCR and structured data extraction. The prompt sent to Gemini is dynamically constructed based on the `gemini_ocr_schema` for the target country.
-   **Standardized Output:** Aims to provide a consistent JSON output structure (`OCR_FIELD_NAME` keys) for extracted data, regardless of the input document's country of origin (as defined in the schema).
-   **Error Handling:** Includes custom error handlers for API exceptions and logs errors during processing.
-   **Dockerized Deployment:** Comes with a `Dockerfile` for easy containerization and deployment, suitable for environments like Google Cloud Run (port 8080 is used by default).
-   **Environment-Driven Setup:** Critical parameters like GCP Project ID, Region, and Model Name are configured via environment variables, promoting secure and flexible deployments.

## Technologies Used

-   **Programming Language:** Python 3.11
-   **Web Framework:** FastAPI
-   **ASGI Server:** Uvicorn
-   **Containerization:** Docker
-   **Cloud Services:**
    -   Google Cloud AI Platform (Vertex AI) for Gemini models.
    -   Google Cloud Secret Manager (implied by `google-cloud-secret-manager` in requirements, though not explicitly used in the provided code snippets for configuration loading - ensure it's used if secrets are involved).
-   **Key Python Libraries:**
    -   `google-genai`: SDK for interacting with Google's generative AI models (Gemini).
    -   `fastapi`: For building the API.
    -   `uvicorn`: For running the FastAPI application.
    -   `pydantic`: For data validation and settings management (API request/response models).
    -   `Pillow`: For image manipulation (part of file processing).
    -   `PyMuPDF (fitz)`: For PDF processing (extracting pages as images).
    -   `google-cloud-aiplatform`: (Potentially older or alternative SDK for Vertex AI, `google-genai` seems to be the primary one in use for Gemini calls in `gemini_service.py`).
    -   `google-cloud-secret-manager`: For securely managing secrets (e.g., API keys if not using ADC for Gemini).
-   **Logging:** Standard Python `logging` module.

## Development Notes

-   **Abstract `DocumentProcessor`:** The `services/document_processor.py` contains an abstract base class `DocumentProcessor`. While `BusinessLicenseProcessor` implements similar functionality, it does not currently inherit from this base class. This could be a point for future refactoring if more document types are added, to promote code reuse.
-   **Gemini Safety Settings:** The `GeminiService` is configured to `BLOCK_NONE` for several harm categories. Review these settings based on your application's requirements and Google's acceptable use policy.
-   **Error Propagation:** The API generally returns detailed error messages, which is useful for debugging but might need to be managed for production environments to avoid exposing internal details.
-   **Confidence Scores:** The `DocumentProcessor` base class includes a placeholder for a confidence score. Implementing actual confidence scoring for OCR results could be a valuable future enhancement.

---

_This README has been generated based on an analysis of the project files. Please review and update it further with any specific details, examples, or deployment instructions relevant to your project._

</rewritten_file>




- country_config 완성할것(DB 데이터 확인)
- 