# Google Cloud Run Deployment Script for Document Processing API (PowerShell)
# This script builds and deploys the application to Google Cloud Run

param(
    [string]$ProjectId = "electric-charge-431108-f7",  # Replace with your GCP project ID
    [string]$Region = "us-central1",                   # Replace with your preferred region
    [string]$ServiceName = "document-processing-api",  # Cloud Run service name
    [string]$ImageName = "document-processing-api"     # Container image name
)

# Error handling
$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting deployment to Google Cloud Run" -ForegroundColor Green
Write-Host "Project ID: $ProjectId"
Write-Host "Region: $Region"
Write-Host "Service Name: $ServiceName"
Write-Host ""

# Check if gcloud is installed
try {
    $null = Get-Command gcloud -ErrorAction Stop
} catch {
    Write-Host "❌ gcloud CLI is not installed. Please install it first." -ForegroundColor Red
    Write-Host "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
}

# Check if user is authenticated
$activeAccount = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
if (-not $activeAccount) {
    Write-Host "⚠️  You are not authenticated with gcloud. Please run:" -ForegroundColor Yellow
    Write-Host "gcloud auth login"
    exit 1
}

# Set the project
Write-Host "📋 Setting project to $ProjectId" -ForegroundColor Yellow
gcloud config set project $ProjectId

# Enable required APIs
Write-Host "🔧 Enabling required APIs..." -ForegroundColor Yellow
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable aiplatform.googleapis.com

# Build the container image using Cloud Build
Write-Host "🏗️  Building container image..." -ForegroundColor Yellow
gcloud builds submit --tag "gcr.io/$ProjectId/$ImageName"

# Deploy to Cloud Run
Write-Host "🚀 Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
    --image "gcr.io/$ProjectId/$ImageName" `
    --platform managed `
    --region $Region `
    --allow-unauthenticated `
    --set-env-vars="GCP_PROJECT_ID=$ProjectId,GCP_REGION=$Region,MODEL_NAME=gemini-2.0-flash-001" `
    --memory=2Gi `
    --cpu=2 `
    --timeout=300 `
    --max-instances=10 `
    --min-instances=0

# Get the service URL
$ServiceUrl = gcloud run services describe $ServiceName --platform managed --region $Region --format 'value(status.url)'

Write-Host ""
Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
Write-Host "🌐 Service URL: $ServiceUrl" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Test your endpoints:" -ForegroundColor Yellow
Write-Host "Health check: curl $ServiceUrl/health"
Write-Host "Business License: curl -X POST `"$ServiceUrl/process-business-license`" -F `"file=@your-license.pdf`" -F `"country=korea`""
Write-Host "Receipt: curl -X POST `"$ServiceUrl/process-receipt`" -F `"file=@your-receipt.jpg`""
Write-Host ""
Write-Host "📊 Monitor your service:" -ForegroundColor Yellow
Write-Host "Logs: gcloud run services logs tail $ServiceName --region $Region"
Write-Host "Console: https://console.cloud.google.com/run/detail/$Region/$ServiceName" 