#!/usr/bin/env python3
import requests
import json

# Test the chat endpoint with the exact structure from frontend
url = "http://localhost:8000/api/chat/send"

# Simulate the exact request from frontend
request_data = {
    "message": "Hello, Gemini!",
    "model": {
        "id": "gemini-2-0-flash-001",
        "name": "Gemini 2.0 Flash",
        "provider": "Google",
        "description": "Gemini 2.0の高速バージョン（動作確認済み）",
        "icon": "logo-google",
        "color": "#4285f4"
    },
    "history": []
}

headers = {
    "Content-Type": "application/json",
    "Origin": "http://localhost:8081",  # Simulate frontend origin
}

print("Sending request to:", url)
print("Request data:", json.dumps(request_data, indent=2))
print("\n" + "="*50 + "\n")

try:
    # First, test OPTIONS request (CORS preflight)
    print("Testing OPTIONS request (CORS preflight)...")
    options_response = requests.options(url, headers=headers)
    print(f"OPTIONS Status: {options_response.status_code}")
    print(f"OPTIONS Headers: {dict(options_response.headers)}")
    
    print("\n" + "="*50 + "\n")
    
    # Then test actual POST request
    print("Testing POST request...")
    response = requests.post(url, json=request_data, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error Response: {response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")