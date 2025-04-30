# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED True
# Cloud Run automatically sets the PORT environment variable
# ENV PORT 8080

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required by PyMuPDF (fitz) if any
# For Debian/Ubuntu based images like python:3.11-slim, common dependencies are already included.
# If you encounter issues, you might need: apt-get update && apt-get install -y --no-install-recommends some-package

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Run app.py when the container launches using Uvicorn
# Uvicorn is a high-performance ASGI server.
# Use the PORT environment variable provided by Cloud Run.
# Use --host 0.0.0.0 to listen on all available network interfaces.
# Uvicorn handles concurrency well; --workers can be added for multi-process if needed,
# but start with the default single worker, multiple threads managed by the event loop.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "120"]
# Note: Uvicorn uses $PORT automatically if available, but explicitly setting it avoids ambiguity.
# Timeout is set via --timeout-keep-alive. 