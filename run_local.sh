#!/bin/bash

# --- Configuration ---
# !!! IMPORTANT: Replace with your actual GCP Project ID and Region !!!
export GCP_PROJECT_ID="your-gcp-project-id"
export GCP_REGION="us-central1" # Or your preferred region
# Optional: export MODEL_NAME="gemini-1.5-flash-001"

echo "Starting FastAPI server locally..."
echo "Using GCP Project: $GCP_PROJECT_ID"
echo "Using GCP Region: $GCP_REGION"

# Check if required packages are installed (optional but helpful)
if ! pip show fastapi > /dev/null || ! pip show uvicorn > /dev/null; then
  echo "Warning: FastAPI or Uvicorn might not be installed."
  echo "Please run: pip install -r requirements.txt"
fi

# Run Uvicorn server
# Use port 8080 for local testing
uvicorn app:app --host 0.0.0.0 --port 8080 --reload

# Note: Ensure you have run 'gcloud auth application-default login' previously. 