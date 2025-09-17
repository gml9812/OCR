# Technical Guide: OCR Document Processing API

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Overview](#architecture-overview)
3. [System Requirements](#system-requirements)
4. [Development Environment Setup](#development-environment-setup)
5. [Codebase Structure](#codebase-structure)
6. [Core Components](#core-components)
7. [API Endpoints](#api-endpoints)
8. [Configuration Management](#configuration-management)
9. [Error Handling](#error-handling)
10. [Development Workflow](#development-workflow)
11. [Testing Guide](#testing-guide)
12. [Deployment Guide](#deployment-guide)
13. [Monitoring and Maintenance](#monitoring-and-maintenance)
14. [Troubleshooting](#troubleshooting)
15. [Contributing Guidelines](#contributing-guidelines)

## Project Overview

### Purpose

The OCR Document Processing API is a FastAPI-based microservice designed to extract structured information from various document types using Google's Gemini AI models. It specializes in processing:

- **Business License Documents** (country-specific field extraction)
- **Receipt Documents** (dynamic field extraction)

### Key Features

- Multi-format support (PDF, PNG, JPG, TIFF)
- Country-specific business license processing
- AI-powered document classification and country identification
- Dynamic receipt parsing with flexible JSON output
- Cloud-native architecture optimized for Google Cloud Run
- Comprehensive error handling and logging
- Scalable dependency injection pattern

### Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **AI/ML**: Google Gemini AI (via google-genai SDK)
- **Image Processing**: Pillow, PyMuPDF
- **Cloud Platform**: Google Cloud (Cloud Run, Vertex AI)
- **Containerization**: Docker
- **Documentation**: Automatic OpenAPI/Swagger generation

## Architecture Overview

The application follows a clean architecture pattern with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   Processors    │    │  Gemini Service │
│   (app.py)      │───▶│  (business/     │───▶│  (AI Integration)│
│                 │    │   receipt)      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  File Processor │    │ Error Handlers  │    │   Config Mgmt   │
│ (File handling) │    │ (Exception Mgmt)│    │ (country_config)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Request Flow

1. **File Upload** → FastAPI endpoint receives file and parameters
2. **File Processing** → Convert PDF/images to processable format
3. **Document Classification** → Identify document type and country (if needed)
4. **Schema Selection** → Load country-specific configuration
5. **AI Processing** → Send to Gemini for OCR and extraction
6. **Response Parsing** → Clean and validate AI response
7. **Result Return** → Structured JSON response to client

## Infrastructure Overview

### GKE Cluster Infrastructure (`mdms-dev` Project)

The development environment includes a Google Kubernetes Engine (GKE) cluster that hosts multiple application environments:

#### **Cluster Details**

- **Cluster Name**: `mdms-cluster-dev`
- **Location**: asia-northeast3
- **Kubernetes Version**: 1.32.4-gke.1415000
- **Node Count**: 3 nodes
- **Machine Type**: e2-custom-12-24576 (12 vCPU, 24GB RAM each)

#### **Application Namespaces**

The cluster hosts multiple development environments for different business units:

| Namespace             | Purpose            | Services              |
| --------------------- | ------------------ | --------------------- |
| `mdms-app-dev-cns`    | CNS Development    | WAS, WEB, SVC         |
| `mdms-app-dev-g2r`    | G2R Development    | WAS, WEB, SVC         |
| `mdms-app-dev-grp`    | GRP Development    | WAS, WEB, Mobile      |
| `mdms-app-dev-lge`    | LGE Development    | WAS, WEB, SVC         |
| `mdms-app-dev-lgit`   | LGIT Development   | WAS, WEB, SVC         |
| `mdms-app-dev-lxh`    | LXH Development    | WAS, WEB, SVC         |
| `mdms-app-dev-pantos` | PANTOS Development | WAS, WEB, SVC, Mobile |

#### **Service Types**

- **WAS** (Web Application Server) - Backend API services
- **WEB** - Frontend web applications
- **SVC** - Microservices and APIs
- **Mobile** - Mobile application backends
- **Lena Manager** - Management and monitoring services

#### **Load Balancer Services**

Each namespace exposes services through LoadBalancer type services with internal IPs in the `10.1.119.x` range.

#### **Supporting Infrastructure VMs**

In addition to the GKE cluster, the development project includes dedicated VMs:

- `vm-an3-mdm-dev-ocr-was` - OCR Web Application Server
- `vm-an3-mdm-dev-ocr-web` - OCR Frontend Web Server
- `vm-an3-mdm-dev-db` - Database servers
- `vm-an3-mdm-dev-bastion` - Bastion host for secure access
- `vm-an3-mdm-dev-nexus` - Artifact repository
- `vm-an3-mdm-dev-sonar` - Code quality analysis

### Accessing GKE Services

To interact with the GKE cluster:

```bash
# Configure kubectl for the development cluster
gcloud container clusters get-credentials mdms-cluster-dev \
  --zone asia-northeast3 \
  --project mdms-dev

# List all services across namespaces
kubectl get services --all-namespaces --insecure-skip-tls-verify

# View pods in a specific namespace
kubectl get pods -n mdms-app-dev-pantos --insecure-skip-tls-verify

# Check deployment status
kubectl get deployments --all-namespaces --insecure-skip-tls-verify
```

**Note**: The `--insecure-skip-tls-verify` flag may be needed due to certificate configuration.

## System Requirements

### Development Environment

- **Python**: 3.11 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 2GB free space for dependencies and cache
- **Network**: Internet access for Google Cloud APIs

### Production Environment

- **Google Cloud Platform Account** with billing enabled
- **APIs**: AI Platform API, Cloud Run API, Cloud Build API
- **Authentication**: Service Account or Application Default Credentials
- **Resources**: 2GB RAM, 2 vCPUs (configurable)

### Required Environment Variables

```bash
GCP_PROJECT_ID="your-gcp-project-id"          # Required
GCP_REGION="us-central1"                       # Optional, defaults to us-central1
MODEL_NAME="gemini-2.5-flash"             # Optional, defaults to gemini-2.5-flash
```

## Development Environment Setup

### 1. Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd <project-directory>

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```env
GCP_PROJECT_ID="your-gcp-project-id"
GCP_REGION="us-central1"
MODEL_NAME="gemini-2.5-flash"
```

### 3. Google Cloud Authentication

```bash
# Install Google Cloud CLI
# Follow: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud auth application-default login

# Set project
gcloud config set project your-gcp-project-id
```

### 4. Local Development Server

```bash
# Using the provided PowerShell script
.\run_local.ps1

# Or directly with uvicorn
uvicorn app:app --host 0.0.0.0 --port 8080 --reload
```

The API will be available at `http://localhost:8080` with automatic documentation at `http://localhost:8080/docs`.

## Codebase Structure

```
├── app.py                          # Main FastAPI application
├── config.py                       # Configuration management
├── models.py                       # Pydantic data models
├── country_config.json             # Country-specific field schemas
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Container configuration
├── deploy_to_cloudrun.ps1         # Deployment script (PowerShell)
├── run_local.ps1                  # Local development script (PowerShell)
├── README.md                       # Project documentation
├── DEPLOYMENT_GUIDE.md             # Deployment documentation
├── .gitignore                      # Git ignore rules
├── .gcloudignore                   # Cloud Build ignore rules
├── services/                      # Core business logic
│   ├── __init__.py
│   ├── file_processor.py          # File handling and conversion
│   ├── gemini_service.py          # AI service integration
│   ├── business_license_processor.py  # Business license processing
│   └── receipt_processor.py       # Receipt processing
├── utils/                         # Utility modules
│   ├── __init__.py
│   ├── error_handlers.py          # Exception handling
│   └── response_parser.py         # Response parsing utilities
└── __pycache__/                   # Python bytecode cache
```

## Core Components

### 1. FastAPI Application (`app.py`)

**Purpose**: Main application entry point with endpoint definitions and dependency injection.

**Key Features**:

- CORS middleware configuration
- Global error handling
- Dependency injection for services
- Startup configuration loading
- Health check endpoint

**Dependencies Management**:

```python
def get_file_processor() -> FileProcessor:
    return FileProcessor()

def get_gemini_service() -> GeminiService:
    return GeminiService(
        project_id=os.environ.get("GCP_PROJECT_ID"),
        region=os.environ.get("GCP_REGION"),
        model_name=os.environ.get("MODEL_NAME")
    )
```

### 2. File Processor (`services/file_processor.py`)

**Purpose**: Handles file upload, validation, and format conversion.

**Supported Formats**:

- **Images**: PNG, JPG, JPEG, TIFF, TIF
- **Documents**: PDF (first page extracted as image)

**Key Methods**:

- `process_file()`: Main entry point for file processing
- `_process_image()`: Handle image files
- `_process_pdf()`: Convert PDF first page to image

**Error Handling**: Validates file types, checks image integrity, handles PDF corruption.

### 3. Gemini Service (`services/gemini_service.py`)

**Purpose**: Integrates with Google's Gemini AI for OCR and text extraction.

**Configuration**:

- **Temperature**: 0.0 (deterministic responses)
- **Top-p**: 1, Top-k: 1 (focused responses)
- **Safety Settings**: All categories set to BLOCK_NONE

**Key Method**:

```python
async def process_document(
    self,
    image_bytes: bytes,
    mime_type: str,
    prompt: str
) -> Tuple[str, Optional[str]]:
```

### 4. Business License Processor (`services/business_license_processor.py`)

**Purpose**: Specialized processing for business license documents with country-specific field extraction.

**Key Features**:

- Country identification using AI
- Dynamic schema loading based on country
- Standardized field mapping (OCR_XXX format)
- Support for user-specified or AI-detected country

**Processing Flow**:

1. File processing and validation
2. Country identification (if not provided)
3. Schema loading for detected country
4. AI-based field extraction
5. Response validation and standardization

### 5. Receipt Processor (`services/receipt_processor.py`)

**Purpose**: Dynamic processing for receipt documents with flexible field extraction.

**Key Features**:

- No predefined schema - AI determines optimal structure
- Comprehensive field extraction (merchant, items, totals, payment)
- Flexible JSON response format
- Built-in response cleaning and validation

### 6. Configuration Management (`config.py`)

**Purpose**: Centralized configuration loading and environment variable management.

**Key Functions**:

- `load_config()`: Loads and validates country configuration
- Environment variable defaults
- Global configuration state management

### 7. Country Configuration (`country_config.json`)

**Purpose**: Defines country-specific document schemas and field mappings.

**Structure**:

```json
{
  "country_code": {
    "unique_id_field_name": "Local field name",
    "common_fields": ["list", "of", "common", "fields"],
    "gemini_ocr_schema": {
      "OCR_FIELD_NAME": "Description for AI extraction"
    }
  }
}
```

**Current Support**: Korea, USA (extensible for additional countries)

### 8. Data Models (`models.py`)

**Purpose**: Pydantic models for request/response validation and documentation.

**Key Models**:

- `StandardBusinessLicenseResponse`: Fixed schema for business licenses
- `DynamicReceiptResponse`: Flexible schema for receipts
- `ProcessingMetadata`: Processing information
- `ErrorResponse`: Standardized error format

### 9. Error Handling (`utils/error_handlers.py`)

**Purpose**: Comprehensive exception management with custom error types.

**Error Types**:

- `APIError`: Base exception class
- `ValidationError`: Input validation failures
- `ProcessingError`: Document processing failures
- `ExternalServiceError`: External service integration failures

**Features**:

- HTTP status code mapping
- Structured error responses
- Raw response preservation for debugging
- Automatic logging

### 10. Response Parser (`utils/response_parser.py`)

**Purpose**: Utilities for cleaning and parsing AI responses.

**Key Features**:

- Markdown code block removal
- JSON extraction from mixed text
- Safe field extraction with dot notation
- Comprehensive error handling

## API Endpoints

### Health Check

```
GET /health
```

**Purpose**: Service health verification
**Response**: `{"status": "ok"}`

### Business License Processing

```
POST /process-business-license
Content-Type: multipart/form-data

Parameters:
- file: UploadFile (required) - Document file (PDF, PNG, JPG, TIFF)
- country: string (optional) - Country code ("korea", "usa")
```

**Response Format**:

```json
{
  "OCR_TAX_ID_NUM": "123-45-67890",
  "OCR_BP_NAME_LOCAL": "Company Name",
  "OCR_REPRE_NAME": "Representative Name",
  "OCR_COMP_REG_NUM": "110111-2309353",
  "OCR_FULL_ADDR_LOCAL": "Full Business Address",
  "OCR_BIZ_TYPE": "Business Category",
  "OCR_INDUSTRY_TYPE": "Specific Industry"
}
```

### Receipt Processing

```
POST /process-receipt
Content-Type: multipart/form-data

Parameters:
- file: UploadFile (required) - Receipt file (PDF, PNG, JPG, TIFF)
```

**Response Format** (Dynamic - AI-determined structure):

```json
{
  "merchant": {
    "name": "Store Name",
    "address": "Store Address",
    "phone": "Phone Number"
  },
  "transaction": {
    "date": "2024-01-15",
    "time": "14:30:00",
    "receipt_number": "12345"
  },
  "items": [
    {
      "name": "Product Name",
      "quantity": 2,
      "unit_price": 10.99,
      "total": 21.98
    }
  ],
  "totals": {
    "subtotal": 21.98,
    "tax": 1.76,
    "total": 23.74
  }
}
```

## Configuration Management

### Environment Variables

**Required**:

- `GCP_PROJECT_ID`: Google Cloud Project ID

**Optional**:

- `GCP_REGION`: GCP region (default: "us-central1")
- `MODEL_NAME`: Gemini model (default: "gemini-2.5-flash")

### Country Configuration

The `country_config.json` file defines how documents from different countries are processed.

**Adding a New Country**:

1. Add entry to `country_config.json`:

```json
{
  "newcountry": {
    "unique_id_field_name": "Local Unique ID Field",
    "common_fields": ["Field1", "Field2", "Address"],
    "gemini_ocr_schema": {
      "OCR_TAX_ID_NUM": "Tax ID description",
      "OCR_BP_NAME_LOCAL": "Business name description"
    }
  }
}
```

2. Test with sample documents from the new country
3. Restart the application to load new configuration

**Schema Field Guidelines**:

- Use `OCR_` prefix for all field names
- Include original language field names in descriptions
- Provide clear extraction guidance for AI
- Use consistent field naming across countries

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error description",
    "raw_response": "Raw AI response (if applicable)"
  }
}
```

### Common Error Scenarios

**File Upload Errors** (400):

- No file uploaded
- Unsupported file format
- Corrupted file
- File too large

**Processing Errors** (500):

- AI service unavailable
- Invalid AI response
- Configuration errors
- Internal processing failures

**Validation Errors** (400):

- Unsupported country code
- Invalid request parameters
- Country identification failure

### Error Debugging

1. **Check Logs**: All errors are logged with full stack traces
2. **Raw Response**: Error responses include raw AI output when available
3. **Status Codes**: Use HTTP status codes to identify error categories
4. **Structured Errors**: Error codes provide programmatic error handling

## Development Workflow

### 1. Setting Up New Features

**Branch Creation**:

```bash
git checkout -b feature/new-feature-name
```

### 2. Code Structure Guidelines

**Service Layer**:

- Keep business logic in service classes
- Use dependency injection for service instantiation
- Implement proper error handling and logging

**API Layer**:

- Keep endpoints thin - delegate to services
- Use Pydantic models for validation
- Implement proper HTTP status codes

**Utility Layer**:

- Create reusable utilities in `utils/`
- Keep utilities stateless and focused
- Implement comprehensive error handling

### 3. Testing Your Changes

**Manual Testing**:

```bash
# Health check
curl http://localhost:8080/health

# Business license test
curl -X POST "http://localhost:8080/process-business-license" \
  -F "file=@test-license.pdf" \
  -F "country=korea"

# Receipt test
curl -X POST "http://localhost:8080/process-receipt" \
  -F "file=@test-receipt.jpg"
```

**API Documentation**: Visit `http://localhost:8080/docs` for interactive testing

## Authentication Guide

### Overview

The OCR Document Processing API uses different authentication methods depending on the deployment environment:

- **Local Development**: No authentication required
- **Cloud Run Deployment**: Google Cloud authentication required

### Local Development Authentication

When running the API locally (port 8080), no authentication is required:

```bash
# Direct access to local API
curl -X POST "http://localhost:8080/process-business-license" \
  -F "file=@test-license.pdf" \
  -F "country=korea"
```

### Cloud Run Authentication

The deployed Cloud Run service requires authentication with Google Cloud credentials.

#### Method 1: User Account Authentication (Development/Testing)

**Step 1: Authenticate with Google Cloud**

```bash
# Login to Google Cloud
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

**Step 2: Get Access Token**

```bash
# Get access token
gcloud auth print-access-token
```

**Step 3: Make Authenticated Requests**

**Using curl (Linux/macOS):**

```bash
# Store token in variable
TOKEN=$(gcloud auth print-access-token)

# Make authenticated request
curl -X POST "https://your-service-url/process-business-license" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@your-license.pdf" \
  -F "country=korea"

# For receipt processing
curl -X POST "https://your-service-url/process-receipt" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@your-receipt.jpg"
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

$response = Invoke-RestMethod -Uri "https://your-service-url/process-business-license" -Method Post -Headers $headers -Form $form
$response | ConvertTo-Json -Depth 10
```

#### Method 2: Service Account Authentication (Production)

For production applications, use service account authentication:

**Step 1: Create Service Account**

```bash
# Create service account
gcloud iam service-accounts create ocr-api-client \
    --description="OCR API Client Service Account" \
    --display-name="OCR API Client"
```

**Step 2: Grant Permissions**

```bash
# Grant Cloud Run Invoker role
gcloud run services add-iam-policy-binding YOUR_SERVICE_NAME \
    --member="serviceAccount:ocr-api-client@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.invoker" \
    --region=YOUR_REGION
```

**Step 3: Create Service Account Key**

```bash
# Create and download key file
gcloud iam service-accounts keys create ocr-api-key.json \
    --iam-account=ocr-api-client@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

**Step 4: Use Service Account**

```bash
# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="path/to/ocr-api-key.json"

# Authenticate with service account
gcloud auth activate-service-account --key-file=ocr-api-key.json

# Get token and make requests
TOKEN=$(gcloud auth print-access-token)
curl -X POST "https://your-service-url/process-business-license" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@your-license.pdf" \
  -F "country=korea"
```

#### Method 3: Application Default Credentials (Recommended for Applications)

For applications running on Google Cloud or with ADC configured:

**Python Example:**

```python
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import requests

# Load service account credentials
credentials = service_account.Credentials.from_service_account_file(
    'path/to/ocr-api-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

# Refresh token
credentials.refresh(Request())

# Make authenticated request
headers = {
    'Authorization': f'Bearer {credentials.token}',
}

files = {'file': open('your-license.pdf', 'rb')}
data = {'country': 'korea'}

response = requests.post(
    'https://your-service-url/process-business-license',
    headers=headers,
    files=files,
    data=data
)

print(response.json())
```

**Node.js Example:**

```javascript
const { GoogleAuth } = require("google-auth-library");
const FormData = require("form-data");
const fs = require("fs");
const fetch = require("node-fetch");

async function callOCRAPI() {
  // Initialize Google Auth
  const auth = new GoogleAuth({
    keyFilename: "path/to/ocr-api-key.json",
    scopes: ["https://www.googleapis.com/auth/cloud-platform"],
  });

  // Get access token
  const client = await auth.getClient();
  const accessToken = await client.getAccessToken();

  // Prepare form data
  const form = new FormData();
  form.append("file", fs.createReadStream("your-license.pdf"));
  form.append("country", "korea");

  // Make authenticated request
  const response = await fetch(
    "https://your-service-url/process-business-license",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken.token}`,
        ...form.getHeaders(),
      },
      body: form,
    }
  );

  const result = await response.json();
  console.log(result);
}

callOCRAPI();
```

### Testing Authentication

**Test Health Endpoint:**

```bash
# Test without authentication (should fail)
curl https://your-service-url/health

# Test with authentication (should succeed)
TOKEN=$(gcloud auth print-access-token)
curl -H "Authorization: Bearer $TOKEN" https://your-service-url/health
```

**Expected Responses:**

**Without Authentication (401 Unauthorized):**

```json
{
  "error": {
    "code": 401,
    "message": "Request is missing required authentication credential."
  }
}
```

**With Valid Authentication (200 OK):**

```json
{
  "status": "ok"
}
```

### Troubleshooting Authentication

**Common Issues:**

1. **Token Expired:**

   - Tokens typically expire after 1 hour
   - Get a new token: `gcloud auth print-access-token`

2. **Insufficient Permissions:**

   - Ensure your account/service account has `roles/run.invoker` permission
   - Check IAM permissions: `gcloud projects get-iam-policy YOUR_PROJECT_ID`

3. **Wrong Project:**

   - Verify correct project: `gcloud config get-value project`
   - Switch project: `gcloud config set project YOUR_PROJECT_ID`

4. **Service Account Issues:**
   - Verify service account exists: `gcloud iam service-accounts list`
   - Check key file path and permissions

**Debug Commands:**

```bash
# Check current authentication
gcloud auth list

# Test token validity
TOKEN=$(gcloud auth print-access-token)
echo $TOKEN

# Check project configuration
gcloud config list

# Verify service permissions
gcloud run services get-iam-policy YOUR_SERVICE_NAME --region=YOUR_REGION
```

### 4. Adding New Country Support

1. **Update Configuration**:

```json
{
  "newcountry": {
    "unique_id_field_name": "Local Field Name",
    "common_fields": ["Common", "Fields", "List"],
    "gemini_ocr_schema": {
      "OCR_TAX_ID_NUM": "Tax ID description",
      "OCR_BP_NAME_LOCAL": "Business name description"
    }
  }
}
```

Add this to your `country_config.json` file.

2. **Test with Sample Documents**:

- Collect sample business licenses from the new country
- Test country identification accuracy
- Validate field extraction quality
- Adjust descriptions in schema as needed

3. **Update Documentation**:

- Add country to supported list in README
- Document any country-specific considerations
- Update API documentation examples

### 5. Modifying AI Prompts

**Business License Prompts** (`services/business_license_processor.py`):

- Located in `get_prompt_template()` method
- Include JSON schema in prompt
- Provide clear extraction instructions

**Receipt Prompts** (`services/receipt_processor.py`):

- Located in `get_prompt_template()` method
- Emphasize dynamic structure creation
- Include comprehensive field coverage

**Testing Prompt Changes**:

1. Test with diverse document samples
2. Validate JSON response format
3. Check field extraction accuracy
4. Monitor AI response consistency

## Testing Guide

### 1. Manual Testing

**Prepare Test Files**:

- Business licenses from supported countries
- Various receipt formats (retail, restaurant, service)
- Different file formats (PDF, PNG, JPG, TIFF)
- Edge cases (poor quality, partial documents)

**Test Scenarios**:

**Business License Testing**:

```bash
# Test with country specification
curl -X POST "http://localhost:8080/process-business-license" \
  -F "file=@korean-license.pdf" \
  -F "country=korea"

# Test automatic country detection
curl -X POST "http://localhost:8080/process-business-license" \
  -F "file=@korean-license.pdf"

# Test unsupported country
curl -X POST "http://localhost:8080/process-business-license" \
  -F "file=@license.pdf" \
  -F "country=unsupported"
```

**Receipt Testing**:

```bash
# Test various receipt types
curl -X POST "http://localhost:8080/process-receipt" \
  -F "file=@grocery-receipt.jpg"

curl -X POST "http://localhost:8080/process-receipt" \
  -F "file=@restaurant-receipt.pdf"
```

### 2. Error Testing

**File Format Errors**:

```bash
# Unsupported format
curl -X POST "http://localhost:8080/process-business-license" \
  -F "file=@document.docx" \
  -F "country=korea"

# Corrupted file
curl -X POST "http://localhost:8080/process-receipt" \
  -F "file=@corrupted.pdf"
```

**Configuration Errors**:

- Test with missing environment variables
- Test with invalid country configuration
- Test with malformed JSON in country_config.json

### 3. Performance Testing

**Load Testing**:

```bash
# Using Apache Bench (ab)
ab -n 100 -c 10 -p test-file.json -T multipart/form-data \
  http://localhost:8080/process-receipt

# Using curl in loop
for i in {1..10}; do
  curl -X POST "http://localhost:8080/process-receipt" \
    -F "file=@test-receipt.jpg" &
done
wait
```

**Memory Monitoring**:

```bash
# Monitor memory usage during processing
htop
# or
ps aux | grep python
```

### 4. Automated Testing Setup (Recommended)

**Note**: No automated tests currently exist in the codebase. Below is a recommended test structure.

**Unit Test Structure** (recommended setup):

```python
# tests/test_file_processor.py
import pytest
from services.file_processor import FileProcessor

class TestFileProcessor:
    async def test_process_valid_image(self):
        # Test valid image processing
        pass

    async def test_process_valid_pdf(self):
        # Test PDF processing
        pass

    async def test_invalid_file_format(self):
        # Test error handling
        pass

# tests/test_business_license_processor.py
class TestBusinessLicenseProcessor:
    async def test_korean_license_processing(self):
        # Test Korean license processing
        pass

    async def test_country_identification(self):
        # Test automatic country detection
        pass
```

**Running Tests** (once implemented):

```bash
# Install testing dependencies
pip install pytest pytest-asyncio httpx

# Create tests directory (does not exist yet)
mkdir tests

# Run tests (once test files are created)
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

## Deployment Guide

### 1. Google Cloud Run Deployment

**Automated Deployment** (Recommended):

```powershell
# PowerShell
.\deploy_to_cloudrun.ps1

# The script will:
# 1. Enable required APIs
# 2. Build container image
# 3. Deploy to Cloud Run
# 4. Set environment variables
# 5. Configure scaling and resources
```

**Manual Deployment**:

```bash
# Set project
export PROJECT_ID="your-gcp-project-id"
gcloud config set project $PROJECT_ID

# Enable APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable aiplatform.googleapis.com

# Build image
gcloud builds submit --tag gcr.io/$PROJECT_ID/document-processing-api

# Deploy
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

### 2. Docker Deployment

**Build Local Image**:

```bash
docker build -t document-processing-api .
```

**Run Locally with Docker**:

```bash
docker run -p 8080:8080 \
  -e GCP_PROJECT_ID="your-gcp-project-id" \
  -e GCP_REGION="us-central1" \
  -e MODEL_NAME="gemini-2.5-flash" \
  document-processing-api
```

**Push to Registry**:

```bash
# Tag for registry
docker tag document-processing-api gcr.io/$PROJECT_ID/document-processing-api

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/document-processing-api
```

### 3. Environment Configuration

**Production Environment Variables**:

```bash
# Required
GCP_PROJECT_ID="production-project-id"

# Optional (with production defaults)
GCP_REGION="us-central1"
MODEL_NAME="gemini-2.5-flash"
```

**Cloud Run Configuration**:

- **Memory**: 2GB (handles image processing)
- **CPU**: 2 vCPUs (parallel processing capability)
- **Timeout**: 300 seconds (long AI processing times)
- **Concurrency**: 10 requests per instance
- **Min Instances**: 0 (cost optimization)
- **Max Instances**: 10 (traffic handling)

### 4. Post-Deployment Verification

**Important**: The deployed Cloud Run service requires authentication. All requests must include an Authorization header.

**Health Check**:

```bash
# Get authentication token
TOKEN=$(gcloud auth print-access-token)

# Test health endpoint with authentication
curl -H "Authorization: Bearer $TOKEN" https://your-service-url/health
```

**Functional Testing**:

```bash
# Get authentication token
TOKEN=$(gcloud auth print-access-token)

# Test business license endpoint
curl -X POST "https://your-service-url/process-business-license" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test-license.pdf" \
  -F "country=korea"

# Test receipt endpoint
curl -X POST "https://your-service-url/process-receipt" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test-receipt.jpg"
```

**Performance Testing**:

```bash
# Note: Performance testing with authentication requires more complex setup
# For basic testing, you can use curl in a loop with authentication

TOKEN=$(gcloud auth print-access-token)

# Simple performance test with curl
for i in {1..10}; do
  curl -X POST "https://your-service-url/process-receipt" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@test-receipt.jpg" &
done
wait

# For comprehensive load testing, consider tools like:
# - Artillery.io with authentication headers
# - Apache Bench with custom headers (limited support for multipart)
# - Custom scripts using authenticated requests
```

### 5. CI/CD Pipeline Setup (Recommended)

**Note**: No CI/CD pipeline currently exists in the codebase. Below is a recommended GitHub Actions setup.

**GitHub Actions Example** (create `.github/workflows/deploy.yml`):

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - id: "auth"
        uses: "google-github-actions/auth@v0"
        with:
          credentials_json: "${{ secrets.GCP_SA_KEY }}"

      - name: "Set up Cloud SDK"
        uses: "google-github-actions/setup-gcloud@v0"

      - name: "Build and Deploy"
        run: |
          gcloud builds submit --tag gcr.io/${{ secrets.PROJECT_ID }}/document-processing-api
          gcloud run deploy document-processing-api \
            --image gcr.io/${{ secrets.PROJECT_ID }}/document-processing-api \
            --platform managed \
            --region us-central1 \
            --no-allow-unauthenticated
```

## Monitoring and Maintenance

### 1. Cloud Run Monitoring

**Built-in Metrics**:

- Request count and latency
- Error rates and status codes
- Memory and CPU utilization
- Instance scaling metrics

**Accessing Metrics**:

1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Select your service
3. Click "Metrics" tab
4. View real-time and historical data

### 2. Logging

**Application Logs**:

```bash
# View logs in Cloud Console
gcloud run services logs tail document-processing-api --region us-central1

# Or use Cloud Console
# https://console.cloud.google.com/logs
```

**Log Levels**:

- `INFO`: Normal operation events
- `WARNING`: Potential issues that don't break functionality
- `ERROR`: Errors that require attention
- `DEBUG`: Detailed debugging information (not used in production)

**Key Log Messages to Monitor**:

- Configuration loading errors
- AI service failures
- File processing errors
- Country identification issues

### 3. Error Monitoring

**Common Production Issues**:

**AI Service Errors**:

- Monitor Gemini API rate limits
- Track API quota usage
- Watch for model availability issues

**File Processing Errors**:

- Large file uploads
- Corrupted file uploads
- Unsupported formats

**Configuration Issues**:

- Missing environment variables
- Invalid country configuration
- Service account permission issues

### 4. Performance Optimization

**Response Time Optimization**:

- Monitor average response times
- Identify slow endpoints
- Optimize image processing pipeline
- Consider AI model response times

**Resource Optimization**:

- Monitor memory usage patterns
- Adjust Cloud Run memory allocation
- Optimize container startup time
- Review scaling configuration

**Cost Optimization**:

- Monitor Cloud Run billing
- Review Gemini API usage costs
- Optimize min/max instance settings
- Consider regional deployment costs

### 5. Backup and Recovery

**Configuration Backup**:

- Version control all configuration files
- Back up `country_config.json` changes
- Document environment variable requirements

**Service Recovery**:

- Cloud Run provides automatic health checks
- Failed instances are automatically restarted
- Multiple instances provide redundancy

**Data Recovery**:

- No persistent data storage required
- All processing is stateless
- Configuration can be restored from version control

### 6. Updates and Maintenance

**Regular Maintenance Tasks**:

**Weekly**:

- Review error logs for patterns
- Monitor resource utilization
- Check AI service performance

**Monthly**:

- Update dependencies if needed
- Review and optimize configurations
- Analyze usage patterns and costs

**Quarterly**:

- Performance optimization review
- Security updates
- Documentation updates

**Dependency Updates**:

```bash
# Check for updates
pip list --outdated

# Update requirements.txt
pip freeze > requirements.txt

# Test thoroughly before deploying
```

**Google Cloud Updates**:

- Monitor Google Cloud release notes
- Test new Gemini model versions
- Update SDK versions as needed

## Troubleshooting

### 1. Common Issues

**Application Won't Start**:

_Symptoms_: Service fails to start, health check fails
_Causes_:

- Missing environment variables
- Invalid configuration file
- Authentication issues

_Solutions_:

```bash
# Check environment variables
gcloud run services describe document-processing-api --region us-central1

# Check logs
gcloud run services logs tail document-processing-api --region us-central1

# Verify configuration
cat country_config.json | jq .
```

**AI Service Errors**:

_Symptoms_: 500 errors on processing endpoints, "External service error" messages
_Causes_:

- Invalid GCP project ID
- Insufficient permissions
- Gemini API quota exceeded
- Model unavailable

_Solutions_:

```bash
# Check project ID
echo $GCP_PROJECT_ID

# Verify authentication
gcloud auth list

# Check API enablement
gcloud services list --enabled | grep aiplatform

# Test API access
gcloud ai models list --region=us-central1
```

**File Processing Errors**:

_Symptoms_: 400 errors on file upload, "Failed to process file" messages
_Causes_:

- Unsupported file format
- Corrupted files
- File size too large
- Memory limitations

_Solutions_:

```bash
# Check file format support
file uploaded-document.pdf

# Verify file integrity
# For PDF: Try opening in PDF viewer
# For images: Try opening in image viewer

# Check file size
ls -lh uploaded-document.pdf
```

**Country Identification Issues**:

_Symptoms_: "Could not identify document country" errors
_Causes_:

- Poor document quality
- Unsupported country
- Missing country configuration

_Solutions_:

1. Improve document quality (scan at higher resolution)
2. Specify country explicitly in request
3. Add new country to configuration
4. Check if document is actually a business license

### 2. Debug Mode

**Enable Detailed Logging**:

```python
# In app.py, modify logging level
logging.basicConfig(level=logging.DEBUG)
```

**Local Debugging**:

```bash
# Run with debug mode
uvicorn app:app --host 0.0.0.0 --port 8080 --reload --log-level debug
```

**Test Individual Components**:

```python
# Test file processing
from services.file_processor import FileProcessor
processor = FileProcessor()
# ... test specific methods

# Test AI service
from services.gemini_service import GeminiService
service = GeminiService()
# ... test with sample data
```

### 3. Performance Issues

**Slow Response Times**:

_Symptoms_: Requests taking >30 seconds, timeouts
_Causes_:

- Large file processing
- AI model response delays
- Insufficient resources

_Solutions_:

1. Increase Cloud Run timeout (max 3600 seconds)
2. Increase memory allocation
3. Optimize image preprocessing
4. Consider async processing for large files

**Memory Issues**:

_Symptoms_: Out of memory errors, service restarts
_Causes_:

- Large PDF processing
- Multiple concurrent requests
- Memory leaks

_Solutions_:

```bash
# Increase Cloud Run memory
gcloud run services update document-processing-api \
  --memory=4Gi \
  --region us-central1

# Monitor memory usage
# Add memory monitoring to application
```

**Rate Limiting**:

_Symptoms_: 429 errors, "Quota exceeded" messages
_Causes_:

- Gemini API rate limits
- Too many concurrent requests

_Solutions_:

1. Implement request queuing
2. Add retry logic with exponential backoff
3. Request quota increase from Google
4. Optimize request patterns

### 4. Data Quality Issues

**Poor OCR Results**:

_Symptoms_: Missing or incorrect field extraction
_Causes_:

- Poor document quality
- Inadequate prompts
- Wrong document type

_Solutions_:

1. Improve document quality (higher resolution, better lighting)
2. Refine AI prompts with more specific instructions
3. Add document preprocessing (rotation, contrast adjustment)
4. Test with different Gemini models

**Inconsistent Results**:

_Symptoms_: Same document produces different results
_Causes_:

- AI model variability
- Ambiguous prompts
- Temperature settings

_Solutions_:

1. Set temperature to 0.0 for deterministic results
2. Make prompts more specific and structured
3. Add validation and consistency checks
4. Use multiple AI calls and compare results

### 5. Security Issues

**Authentication Failures**:

_Symptoms_: 401/403 errors from Google Cloud APIs
_Causes_:

- Expired credentials
- Insufficient permissions
- Wrong service account

_Solutions_:

```bash
# Refresh credentials
gcloud auth application-default login

# Check current authentication
gcloud auth list

# Verify service account permissions
gcloud projects get-iam-policy $PROJECT_ID

# Required roles:
# - AI Platform User
# - Cloud Run Developer
# - Storage Object Viewer (if using Cloud Storage)
```

**Data Privacy Concerns**:

_Symptoms_: Questions about data handling
_Solutions_:

1. Review Google Cloud AI data usage policies
2. Implement data retention policies
3. Consider data encryption for sensitive documents
4. Document data handling procedures

### 6. Configuration Issues

**Invalid Country Configuration**:

_Symptoms_: JSON parse errors, missing schema errors
_Causes_:

- Malformed JSON
- Missing required fields
- Encoding issues

_Solutions_:

```bash
# Validate JSON syntax
cat country_config.json | jq .

# Check encoding
file country_config.json

# Verify required fields exist
jq '.korea.gemini_ocr_schema' country_config.json
```

**Environment Variable Issues**:

_Symptoms_: Configuration loading failures
_Solutions_:

```bash
# List all environment variables
env | grep GCP

# Check Cloud Run environment
gcloud run services describe document-processing-api \
  --region us-central1 --format="value(spec.template.spec.template.spec.containers[0].env[].name,spec.template.spec.template.spec.containers[0].env[].value)"
```

## Contributing Guidelines

### 1. Development Standards

**Code Style**:

- Follow PEP 8 Python style guidelines
- Use type hints for all function parameters and return values
- Write descriptive variable and function names
- Keep functions focused and single-purpose

**Documentation**:

- Add docstrings to all classes and methods
- Update README for new features
- Include inline comments for complex logic
- Update this technical guide for architectural changes

**Error Handling**:

- Use custom exception classes from `utils.error_handlers`
- Include proper logging for all error scenarios
- Provide meaningful error messages to users
- Never expose internal implementation details in error responses

### 2. Code Review Process

**Before Submitting**:

1. Test changes locally with multiple document types
2. Verify no regression in existing functionality
3. Update relevant documentation
4. Check code style and formatting

**Pull Request Requirements**:

- Clear description of changes and rationale
- Test cases for new functionality
- Documentation updates
- Breaking change notifications

**Review Criteria**:

- Code correctness and efficiency
- Error handling completeness
- Security considerations
- Documentation quality

### 3. Testing Requirements

**New Features**:

- Unit tests for new service methods
- Integration tests for new endpoints
- Manual testing with diverse document samples
- Performance impact assessment

**Bug Fixes**:

- Test case that reproduces the bug
- Verification that fix resolves the issue
- Regression testing for related functionality

### 4. Release Process

**Version Control**:

- Use semantic versioning (MAJOR.MINOR.PATCH)
- Tag releases in Git
- Maintain CHANGELOG.md

**Deployment Process**:

1. Test changes in development environment
2. Deploy to staging environment (if available)
3. Run full integration test suite
4. Deploy to production
5. Monitor logs and metrics post-deployment

### 5. Feature Development

**Adding New Document Types**:

1. Create new processor class in `services/`
2. Add endpoint in `app.py`
3. Create Pydantic response model in `models.py`
4. Add comprehensive testing
5. Update documentation

**Extending Country Support**:

1. Research document format and common fields
2. Create schema in `country_config.json`
3. Test with representative document samples
4. Validate field extraction accuracy
5. Update supported countries documentation

**AI Model Updates**:

1. Test new model compatibility
2. Update model configuration
3. Compare accuracy with previous model
4. Update documentation if behavior changes

### 6. Security Guidelines

**Data Handling**:

- Never log sensitive document content
- Minimize data retention time
- Use secure communication channels
- Follow Google Cloud security best practices

**Authentication**:

- Use service accounts with minimal required permissions
- Regularly rotate credentials
- Monitor for unauthorized access attempts

**Input Validation**:

- Validate all file uploads
- Sanitize user inputs
- Implement rate limiting for public endpoints
- Guard against malicious file uploads

This technical guide provides comprehensive coverage of the OCR Document Processing API codebase. It serves as both a developer onboarding resource and an operational reference for maintaining and extending the system. Keep this guide updated as the system evolves to ensure it remains a valuable resource for team members and contributors.
