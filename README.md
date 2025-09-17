# Document Processing API

## Description

This project provides a **Document Processing API** built with FastAPI, designed to extract structured information from various document types, with a primary focus on **Business Licenses** and **Receipts**. It leverages Google's Gemini multimodal AI models via the `google-genai` SDK for OCR and information extraction.

**Purpose:** To automate the extraction of key information from business license documents from different countries and receipt documents, providing a standardized JSON output. The system is designed to be configurable for various country-specific document formats and fields.

**Key functionalities include:**

- FastAPI endpoint (`/process-business-license`) for uploading business license documents (PDF, PNG, JPG, TIFF).
- FastAPI endpoint (`/process-receipt`) for uploading receipt documents (PDF, PNG, JPG, TIFF).
- Automatic conversion of PDFs (first page) and various image formats to a processable image format (JPEG/PNG).
- Integration with Google Gemini for OCR and structured data extraction based on dynamic, country-specific prompts and schemas.
- Configuration-driven approach using `country_config.json` to define fields and prompts for different countries (e.g., Korea, USA).
- Environment variable-based setup for Google Cloud Project ID, Region, and Gemini Model Name.

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

- Python 3.11 (as per Dockerfile)
- pip (Python package installer)
- Docker (Recommended for deployment, and for a consistent environment)
- Access to a Google Cloud Project with the AI Platform API enabled and appropriate credentials configured for Application Default Credentials (ADC).

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
    MODEL_NAME="your-gemini-model-name" # e.g., gemini-1.0-pro-vision-001 or gemini-2.5-flash
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

- `unique_id_field_name`: (String) The primary identifier field in that country's business license (e.g., "사업자등록번호" for Korea).
- `common_fields`: (List of Strings) A list of common field names found on the document.
- `gemini_ocr_schema`: (Object) This is the schema provided to the Gemini model in the prompt.
  - Keys are standardized `OCR_FIELD_NAME` (e.g., `OCR_TAX_ID_NUM`, `OCR_BP_NAME_LOCAL`).
  - Values are descriptive strings that guide the Gemini model in extracting the correct information, often including the original field name in the local language.

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

- `GCP_PROJECT_ID`: Your Google Cloud Project ID.
- `GCP_REGION`: The GCP region for AI Platform services (defaults to "us-central1").
- `MODEL_NAME`: The Gemini model to use (defaults to "gemini-2.5-flash").
- `CONFIG_FILE`: Path to the country configuration JSON (defaults to "country_config.json").

## Infrastructure Overview

### GKE Cluster Infrastructure

The development environment is hosted on a Google Kubernetes Engine (GKE) cluster in the `mdms-dev` project:

#### **Cluster Specifications**

- **Cluster Name**: `mdms-cluster-dev`
- **Location**: asia-northeast3
- **Kubernetes Version**: 1.32.4-gke.1415000
- **Node Configuration**: 3 nodes × e2-custom-12-24576 (12 vCPU, 24GB RAM each)

#### **Development Environments**

The cluster hosts multiple application environments for different business units:

| Environment | Namespace             | Services              | Purpose                        |
| ----------- | --------------------- | --------------------- | ------------------------------ |
| CNS         | `mdms-app-dev-cns`    | WAS, WEB, SVC         | CNS Development Environment    |
| G2R         | `mdms-app-dev-g2r`    | WAS, WEB, SVC         | G2R Development Environment    |
| GRP         | `mdms-app-dev-grp`    | WAS, WEB, Mobile      | GRP Development Environment    |
| LGE         | `mdms-app-dev-lge`    | WAS, WEB, SVC         | LGE Development Environment    |
| LGIT        | `mdms-app-dev-lgit`   | WAS, WEB, SVC         | LGIT Development Environment   |
| LXH         | `mdms-app-dev-lxh`    | WAS, WEB, SVC         | LXH Development Environment    |
| PANTOS      | `mdms-app-dev-pantos` | WAS, WEB, SVC, Mobile | PANTOS Development Environment |

#### **Service Architecture**

- **WAS** (Web Application Server) - Backend API services
- **WEB** - Frontend web applications
- **SVC** - Microservices and API endpoints
- **Mobile** - Mobile application backends

#### **Dedicated OCR Infrastructure**

In addition to the GKE cluster, dedicated VMs provide OCR services:

- `vm-an3-mdm-dev-ocr-was` - OCR Web Application Server
- `vm-an3-mdm-dev-ocr-web` - OCR Frontend Web Server

#### **Accessing the Cluster**

To interact with the development cluster:

```bash
# Configure kubectl access
gcloud container clusters get-credentials mdms-cluster-dev \
  --zone asia-northeast3 \
  --project mdms-dev

# View all services
kubectl get services --all-namespaces --insecure-skip-tls-verify

# Monitor deployments
kubectl get deployments --all-namespaces --insecure-skip-tls-verify
```

## Usage

### Running Locally

1.  Ensure all prerequisites, environment variables, and dependencies are set up.
2.  Ensure `country_config.json` is present and correctly configured.
3.  Run the FastAPI application using Uvicorn (as done by the run scripts or Docker):
    ```bash
    uvicorn app:app --host 0.0.0.0 --port 8080 --reload
    ```
    The `--reload` flag is useful for development.
    Alternatively, use the provided run script:
    - Windows (PowerShell): `.\run_local.ps1`

The API will be accessible at `http://localhost:8080`.

### Deploying to Google Cloud Run

This application is optimized for deployment on Google Cloud Run. Follow these steps:

#### Prerequisites

1. **Google Cloud SDK**: Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
2. **Authentication**: Run `gcloud auth login` to authenticate
3. **Project Setup**: Ensure you have a GCP project with billing enabled
4. **APIs**: The deployment script will enable required APIs automatically

#### Quick Deployment

**Option 1: Using the automated script (Recommended)**

For Windows (PowerShell):

```powershell
.\deploy_to_cloudrun.ps1
```

**Option 2: Manual deployment**

1. **Set your project ID**:

   ```bash
   export PROJECT_ID="your-gcp-project-id"
   gcloud config set project $PROJECT_ID
   ```

2. **Enable required APIs**:

   ```bash
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable aiplatform.googleapis.com
   ```

3. **Build and deploy**:

   ```bash
   # Build the container image
   gcloud builds submit --tag gcr.io/$PROJECT_ID/document-processing-api

   # Deploy to Cloud Run
   gcloud run deploy document-processing-api \
       --image gcr.io/$PROJECT_ID/document-processing-api \
       --platform managed \
       --region us-central1 \
       --no-allow-unauthenticated \
       --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=us-central1,MODEL_NAME=gemini-2.5-flash" \
       --memory=2Gi \
       --cpu=2 \
       --timeout=300 \
       --max-instances=10 \
       --min-instances=0
   ```

#### Configuration Options

The deployment includes these optimized settings for document processing:

- **Memory**: 2GB (sufficient for image processing and AI model calls)
- **CPU**: 2 vCPUs (good balance for concurrent requests)
- **Timeout**: 300 seconds (allows for longer AI processing times)
- **Scaling**: 0-10 instances (cost-effective auto-scaling)
- **Authentication**: Requires authentication (uses `--no-allow-unauthenticated` for security)

#### Environment Variables

The following environment variables are automatically set during deployment:

- `GCP_PROJECT_ID`: Your Google Cloud project ID
- `GCP_REGION`: The region where your service is deployed
- `MODEL_NAME`: The Gemini model to use (default: `gemini-2.5-flash`)

#### Post-Deployment

After successful deployment, you'll receive a service URL. Test your endpoints with authentication:

```bash
# Get authentication token
TOKEN=$(gcloud auth print-access-token)

# Health check
curl -H "Authorization: Bearer $TOKEN" https://your-service-url/health

# Process business license
curl -X POST "https://your-service-url/process-business-license" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@your-license.pdf" \
  -F "country=korea"

# Process receipt
curl -X POST "https://your-service-url/process-receipt" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@your-receipt.jpg"
```

#### Monitoring and Logs

- **View logs**: `gcloud run services logs tail document-processing-api --region us-central1`
- **Cloud Console**: Visit the [Cloud Run console](https://console.cloud.google.com/run) to monitor your service
- **Metrics**: Monitor request count, latency, and error rates in the console

#### Cost Optimization

Cloud Run charges only for actual usage. To optimize costs:

- Set `--min-instances=0` for automatic scaling to zero when not in use
- Adjust `--max-instances` based on expected traffic
- Monitor usage in the Cloud Console and adjust resources as needed

#### Security Considerations

The application is configured with authentication required by default:

1. **Authentication Required**: Uses `--no-allow-unauthenticated` for security
2. **IAM-based Access**: Set up proper IAM roles for service access using `roles/run.invoker`
3. **Service Accounts**: Use service accounts for programmatic access (recommended)
4. **Environment Variables**: Consider using Google Secret Manager for sensitive configuration
5. **VPC**: Deploy in a VPC for network isolation if additional security is needed

**Granting Access to Users:**

```bash
# Grant a user access to invoke the service
gcloud run services add-iam-policy-binding YOUR_SERVICE_NAME \
    --member="user:user@example.com" \
    --role="roles/run.invoker" \
    --region=YOUR_REGION

# Grant a service account access
gcloud run services add-iam-policy-binding YOUR_SERVICE_NAME \
    --member="serviceAccount:service-account@project.iam.gserviceaccount.com" \
    --role="roles/run.invoker" \
    --region=YOUR_REGION
```

## API Endpoint

### Process Business License

- **Endpoint:** `POST /process-business-license`
- **Description:** Extracts key fields from an uploaded business license document.
- **Request:** `multipart/form-data`
  - `file`: The document file (PDF, PNG, JPG, JPEG, TIFF, TIF).
  - `country`: (Optional Form data) The lowercase country code (e.g., "korea", "usa") to use specific field mappings and prompts from `country_config.json`. If not provided, or if the country code is invalid, an error will occur.
- **Response:** `application/json`
  - On success (200 OK): A JSON object containing the extracted fields based on the `gemini_ocr_schema` for the specified country.
    ```json
    {
      "OCR_TAX_ID_NUM": "123-45-67890",
      "OCR_BP_NAME_LOCAL": "Example Corp",
      "OCR_REPRE_NAME": "John Doe"
      // ... other fields from the schema
    }
    ```
  - On error (4xx/5xx): A JSON object with a "detail" field describing the error.
    ```json
    {
      "detail": "Error message"
    }
    ```

**Example `curl` request:**

**Local Development:**

```bash
curl -X POST "http://localhost:8080/process-business-license" \
  -F "file=@/path/to/your/business_license.pdf" \
  -F "country=korea"
```

**Cloud Run (with authentication):**

```bash
# Get access token
TOKEN=$(gcloud auth print-access-token)

# Make authenticated request
curl -X POST "https://your-service-url/process-business-license" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/your/business_license.pdf" \
  -F "country=korea"
```

## Authentication

### For Cloud Run Deployed Service

The deployed Cloud Run service requires authentication. You need to include an authorization header with a valid Google Cloud access token.

#### Getting an Access Token

```bash
# Get access token using gcloud CLI
gcloud auth print-access-token
```

#### Making Authenticated Requests

**Using curl (Linux/macOS):**

```bash
# Get access token
TOKEN=$(gcloud auth print-access-token)

# Make authenticated request
curl -X POST "https://your-service-url/process-business-license" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@your-license.pdf" \
  -F "country=korea"
```

**Using PowerShell:**

```powershell
# Get access token
$TOKEN = gcloud auth print-access-token

# Make authenticated request
$headers = @{ "Authorization" = "Bearer $TOKEN" }
$form = @{
    file = Get-Item "your-license.pdf"
    country = "korea"
}
Invoke-RestMethod -Uri "https://your-service-url/process-business-license" -Method Post -Headers $headers -Form $form
```

#### Service Account Authentication (Recommended for Production)

For production applications, use a service account instead of user credentials:

1. **Create a service account:**

```bash
gcloud iam service-accounts create ocr-api-client \
    --description="OCR API Client" \
    --display-name="OCR API Client"
```

2. **Grant necessary permissions:**

```bash
# Grant permission to invoke the Cloud Run service
gcloud run services add-iam-policy-binding YOUR_SERVICE_NAME \
    --member="serviceAccount:ocr-api-client@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.invoker" \
    --region=YOUR_REGION
```

3. **Create and download service account key:**

```bash
gcloud iam service-accounts keys create ocr-api-key.json \
    --iam-account=ocr-api-client@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

4. **Use service account for authentication:**

```bash
# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="path/to/ocr-api-key.json"

# Get token and make request
TOKEN=$(gcloud auth print-access-token)
curl -X POST "https://your-service-url/process-business-license" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@your-license.pdf" \
  -F "country=korea"
```

### For Local Development

When running locally (`http://localhost:8080`), no authentication is required:

```bash
curl -X POST "http://localhost:8080/process-business-license" \
  -F "file=@your-license.pdf" \
  -F "country=korea"
```

### Process Receipt

- **Endpoint:** `POST /process-receipt`
- **Description:** Extracts key fields from an uploaded receipt document using AI-determined optimal JSON structure.
- **Request:** `multipart/form-data`
  - `file`: The document file (PDF, PNG, JPG, JPEG, TIFF, TIF).
- **Response:** `application/json`
  - On success (200 OK): A JSON object containing the extracted receipt fields. The structure is dynamically determined by the AI based on the receipt content for optimal data organization.
    ```json
    {
      "merchant": {
        "name": "Example Store",
        "address": "123 Main St, City, State",
        "phone": "555-123-4567"
      },
      "transaction": {
        "date": "2024-01-15",
        "time": "14:30",
        "receipt_number": "REC-001234"
      },
      "items": [
        {
          "name": "Coffee",
          "quantity": 2,
          "unit_price": 2.25,
          "total": 4.5
        },
        {
          "name": "Sandwich",
          "quantity": 1,
          "unit_price": 8.99,
          "total": 8.99
        }
      ],
      "totals": {
        "subtotal": 23.69,
        "tax": 2.3,
        "total": 25.99,
        "currency": "USD"
      },
      "payment": {
        "method": "Credit Card"
      }
    }
    ```
    _Note: The actual JSON structure will vary based on the receipt content and what the AI determines is the most logical organization._
  - On error (4xx/5xx): A JSON object with a "detail" field describing the error.
    ```json
    {
      "detail": "Error message"
    }
    ```

**Example `curl` request:**

**Local Development:**

```bash
curl -X POST "http://localhost:8080/process-receipt" \
  -F "file=@/path/to/your/receipt.jpg"
```

**Cloud Run (with authentication):**

```bash
# Get access token
TOKEN=$(gcloud auth print-access-token)

# Make authenticated request
curl -X POST "https://your-service-url/process-receipt" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/your/receipt.jpg"
```

## Project Structure

```
.
├── .git/                     # Git version control files
├── .gitignore                # Specifies intentionally untracked files
├── .gcloudignore             # Specifies files to ignore when building with gcloud
├── app.py                    # FastAPI application entry point, defines endpoints and startup logic
├── config.py                 # Loads environment variables and country_config.json
├── country_config.json       # JSON configuration for country-specific OCR fields and prompts
├── deploy_to_cloudrun.ps1    # PowerShell script for deploying to Google Cloud Run
├── Dockerfile                # Defines the Docker image for the application
├── models.py                 # Pydantic models for API request/response validation
├── README.md                 # Project documentation
├── DEPLOYMENT_GUIDE.md       # Detailed deployment instructions
├── requirements.txt          # Python dependencies
├── run_local.ps1             # PowerShell script to run locally
├── services/                 # Core service logic
│   ├── __init__.py
│   ├── business_license_processor.py # Orchestrates business license processing
│   ├── file_processor.py     # Handles file validation, image/PDF preprocessing
│   ├── gemini_service.py     # Interacts with the Google Gemini API
│   └── receipt_processor.py  # Handles receipt document processing
├── utils/                    # Utility modules
│   ├── __init__.py
│   ├── error_handlers.py     # FastAPI custom error handlers
│   └── response_parser.py    # Utility for parsing JSON responses
└── __pycache__/              # Python bytecode cache (auto-generated)
```

- `app.py`: Initializes the FastAPI app, sets up CORS, error handlers, and the `/process-business-license` and `/process-receipt` endpoints. Loads configuration on startup.
- `config.py`: Manages loading of `country_config.json` and environment variables.
- `country_config.json`: Defines country-specific schemas and field names for OCR. **This is a key file to modify when adding support for new countries or fields.**
- `services/business_license_processor.py`: The core logic for handling a business license. It uses `FileProcessor` to prepare the document and `GeminiService` to perform OCR and data extraction based on the prompt generated from `country_config.json`.
- `services/receipt_processor.py`: The core logic for handling receipts. It uses `FileProcessor` to prepare the document and `GeminiService` to perform OCR and data extraction with a dynamic JSON structure determined by the AI.
- `services/file_processor.py`: Validates file types (PDF, various images) and converts them into a usable format (PNG bytes for PDFs, original bytes for images) for the OCR service.
- `services/gemini_service.py`: Encapsulates all interactions with the Google Gemini API, including authentication (via ADC), request formatting, and response handling. Configures safety settings and generation parameters.
- `models.py`: Contains Pydantic models like `StandardBusinessLicenseResponse` and `DynamicReceiptResponse` to define the expected structure of API responses.
- `Dockerfile`: Specifies how to build the production Docker image, using `python:3.11-slim` and running Uvicorn.
- `utils/error_handlers.py`: Defines custom exception handlers for API errors.

## Key Features Detailed

- **Dynamic Country Configuration:** Supports different business license formats and required fields per country through `country_config.json`. New countries can be added by defining their specific `gemini_ocr_schema` and field names.
- **Intelligent Receipt Processing:** The receipt endpoint uses AI to determine the optimal JSON structure based on the actual receipt content, providing more natural and useful data organization compared to fixed schemas.
- **Multimodal Input:** Accepts PDF documents (first page is processed) and common image formats (PNG, JPEG, TIFF).
- **Gemini Integration:** Leverages Google's Gemini models for advanced OCR and structured data extraction. The prompt sent to Gemini is dynamically constructed based on the `gemini_ocr_schema` for the target country.
- **Standardized Output:** Aims to provide a consistent JSON output structure (`OCR_FIELD_NAME` keys) for extracted data, regardless of the input document's country of origin (as defined in the schema).
- **Error Handling:** Includes custom error handlers for API exceptions and logs errors during processing.
- **Dockerized Deployment:** Comes with a `Dockerfile` for easy containerization and deployment, suitable for environments like Google Cloud Run (port 8080 is used by default).
- **Environment-Driven Setup:** Critical parameters like GCP Project ID, Region, and Model Name are configured via environment variables, promoting secure and flexible deployments.

## Technologies Used

- **Programming Language:** Python 3.11
- **Web Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **Containerization:** Docker
- **Cloud Services:**
  - Google Cloud AI Platform (Vertex AI) for Gemini models.
  - Google Cloud Secret Manager (implied by `google-cloud-secret-manager` in requirements, though not explicitly used in the provided code snippets for configuration loading - ensure it's used if secrets are involved).
- **Key Python Libraries:**
  - `google-genai`: SDK for interacting with Google's generative AI models (Gemini).
  - `fastapi`: For building the API.
  - `uvicorn`: For running the FastAPI application.
  - `pydantic`: For data validation and settings management (API request/response models).
  - `Pillow`: For image manipulation (part of file processing).
  - `PyMuPDF (fitz)`: For PDF processing (extracting pages as images).
  - `google-cloud-aiplatform`: (Potentially older or alternative SDK for Vertex AI, `google-genai` seems to be the primary one in use for Gemini calls in `gemini_service.py`).
  - `google-cloud-secret-manager`: For securely managing secrets (e.g., API keys if not using ADC for Gemini).
- **Logging:** Standard Python `logging` module.

## Development Notes

- **Abstract `DocumentProcessor`:** The `services/document_processor.py` contains an abstract base class `DocumentProcessor`. While `BusinessLicenseProcessor` implements similar functionality, it does not currently inherit from this base class. This could be a point for future refactoring if more document types are added, to promote code reuse.
- **Gemini Safety Settings:** The `GeminiService` is configured to `BLOCK_NONE` for several harm categories. Review these settings based on your application's requirements and Google's acceptable use policy.
- **Error Propagation:** The API generally returns detailed error messages, which is useful for debugging but might need to be managed for production environments to avoid exposing internal details.
- **Confidence Scores:** The `DocumentProcessor` base class includes a placeholder for a confidence score. Implementing actual confidence scoring for OCR results could be a valuable future enhancement.

---

_This README has been generated based on an analysis of the project files. Please review and update it further with any specific details, examples, or deployment instructions relevant to your project._

</rewritten_file>

## 메모

- country_config 완성할것(DB 데이터 확인)
- 대량의 테스트 준비할것
- 오류 발생시 자세한 설명 해주는 기능 추가할것(API 호출 시 무언가 잘못 넣었거나, OCR결과에서 확신 못하는 부분이 있거나)
