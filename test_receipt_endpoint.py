#!/usr/bin/env python3
"""
Simple test script to demonstrate the receipt processing endpoint.
This script creates a mock receipt image and tests the /process-receipt endpoint.
The endpoint now uses dynamic JSON structure determined by the LLM.
"""

import requests
import json
from PIL import Image, ImageDraw, ImageFont
import io
import os

def create_mock_receipt():
    """Create a mock receipt image for testing."""
    # Create a white image
    width, height = 400, 600
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Try to use a default font, fallback to basic if not available
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        small_font = ImageFont.truetype("arial.ttf", 12)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Draw receipt content
    y_position = 20
    line_height = 25
    
    receipt_lines = [
        "SUPER MARKET",
        "123 Main Street",
        "Anytown, ST 12345",
        "Tel: (555) 123-4567",
        "",
        "Receipt #: REC-001234",
        "Date: 2024-01-15",
        "Time: 14:30",
        "",
        "Items:",
        "Coffee x2        $9.00",
        "Sandwich x1      $8.99",
        "Chips x1         $2.50",
        "",
        "Subtotal:       $20.49",
        "Tax:             $1.84",
        "Total:          $22.33",
        "",
        "Payment: Credit Card",
        "Thank you!"
    ]
    
    for line in receipt_lines:
        if line.startswith("SUPER MARKET"):
            # Center the store name
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x_position = (width - text_width) // 2
            draw.text((x_position, y_position), line, fill='black', font=font)
        else:
            draw.text((20, y_position), line, fill='black', font=small_font)
        y_position += line_height
    
    return image

def test_receipt_endpoint():
    """Test the receipt processing endpoint."""
    # Create mock receipt
    receipt_image = create_mock_receipt()
    
    # Convert to bytes
    img_byte_arr = io.BytesIO()
    receipt_image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    # Save the test image for reference
    receipt_image.save("test_receipt.png")
    print("Created test receipt image: test_receipt.png")
    
    # Test the endpoint
    url = "http://localhost:8080/process-receipt"
    
    try:
        files = {'file': ('test_receipt.png', img_byte_arr, 'image/png')}
        
        print(f"Testing endpoint: {url}")
        print("Note: The response format is now dynamically determined by the LLM")
        response = requests.post(url, files=files, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("Success! Extracted data with LLM-determined structure:")
            print(json.dumps(result, indent=2))
            print("\nThe JSON structure above was automatically determined by the AI")
            print("based on the receipt content for optimal data organization.")
        else:
            print("Error response:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server.")
        print("Make sure the FastAPI server is running on http://localhost:8080")
        print("Run: uvicorn app:app --host 0.0.0.0 --port 8080")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_receipt_endpoint() 