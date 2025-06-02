# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED True

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

# Expose port (Cloud Run will set the PORT environment variable)
EXPOSE 8080

# Use Gunicorn as the process manager for Uvicorn workers for production
# The PORT environment variable is automatically set by Cloud Run
# If PORT is not set, default to 8080
CMD exec gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:${PORT:-8080} --timeout 120 