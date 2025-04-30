# --- Configuration ---
# !!! IMPORTANT: Replace with your actual GCP Project ID and Region !!!
$env:GCP_PROJECT_ID = "electric-charge-431108-f7"
$env:GCP_REGION = "us-central1" # Or your preferred region
# Optional: $env:MODEL_NAME = "gemini-1.5-flash-001"

Write-Host "Starting FastAPI server locally..."
Write-Host "Using GCP Project: $($env:GCP_PROJECT_ID)"
Write-Host "Using GCP Region: $($env:GCP_REGION)"

# Check if required packages are installed (optional but helpful)
try {
    pip show fastapi | Out-Null
    pip show uvicorn | Out-Null
} catch {
    Write-Warning "FastAPI or Uvicorn might not be installed."
    Write-Warning "Please run: pip install -r requirements.txt"
}

# Run Uvicorn server
# Use port 8080 for local testing
Write-Host "Running Uvicorn... Press CTRL+C to stop."
uvicorn app:app --host 0.0.0.0 --port 8080 --reload

Write-Host "Server stopped."
Write-Host "Note: Ensure you have run 'gcloud auth application-default login' previously."
# Keep PowerShell window open if run directly
# Read-Host -Prompt "Press Enter to exit" 