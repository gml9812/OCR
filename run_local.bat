@echo off

REM --- Configuration ---
REM !!! IMPORTANT: Replace with your actual GCP Project ID and Region !!!
set GCP_PROJECT_ID=electric-charge-431108-f7
set GCP_REGION=us-central1
REM Optional: set MODEL_NAME=gemini-1.5-flash-001

echo Starting FastAPI server locally...
echo Using GCP Project: %GCP_PROJECT_ID%
echo Using GCP Region: %GCP_REGION%

REM Check if required packages are installed (basic check)
pip show fastapi > nul 2>&1
if errorlevel 1 (
    echo Warning: FastAPI might not be installed.
    echo Please run: pip install -r requirements.txt
)

REM Run Uvicorn server
REM Use port 8080 for local testing
uvicorn app:app --host 0.0.0.0 --port 8080 --reload

echo.
echo Note: Ensure you have run 'gcloud auth application-default login' previously.
pause 