#!/bin/bash

# Google Cloud Run Deployment Script for Document Processing API
# This script builds and deploys the application to Google Cloud Run

set -e  # Exit on any error

# Configuration - Update these values for your project
PROJECT_ID="electric-charge-431108-f7"  # Replace with your GCP project ID
REGION="us-central1"                     # Replace with your preferred region
SERVICE_NAME="document-processing-api"   # Cloud Run service name
IMAGE_NAME="document-processing-api"     # Container image name

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting deployment to Google Cloud Run${NC}"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service Name: $SERVICE_NAME"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed. Please install it first.${NC}"
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}⚠️  You are not authenticated with gcloud. Please run:${NC}"
    echo "gcloud auth login"
    exit 1
fi

# Set the project
echo -e "${YELLOW}📋 Setting project to $PROJECT_ID${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable aiplatform.googleapis.com

# Build the container image using Cloud Build
echo -e "${YELLOW}🏗️  Building container image...${NC}"
gcloud builds submit --tag gcr.io/$PROJECT_ID/$IMAGE_NAME

# Deploy to Cloud Run
echo -e "${YELLOW}🚀 Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=$REGION,MODEL_NAME=gemini-2.0-flash-001" \
    --memory=2Gi \
    --cpu=2 \
    --timeout=300 \
    --max-instances=10 \
    --min-instances=0

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')

echo ""
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Service URL: $SERVICE_URL${NC}"
echo ""
echo -e "${YELLOW}📝 Test your endpoints:${NC}"
echo "Health check: curl $SERVICE_URL/health"
echo "Business License: curl -X POST \"$SERVICE_URL/process-business-license\" -F \"file=@your-license.pdf\" -F \"country=korea\""
echo "Receipt: curl -X POST \"$SERVICE_URL/process-receipt\" -F \"file=@your-receipt.jpg\""
echo ""
echo -e "${YELLOW}📊 Monitor your service:${NC}"
echo "Logs: gcloud run services logs tail $SERVICE_NAME --region $REGION"
echo "Console: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME" 