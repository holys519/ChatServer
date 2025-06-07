#!/usr/bin/env python3
"""
Simple test server to verify localhost connectivity
"""
import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Test Server")

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Test server is running"}

@app.get("/")
async def root():
    return {"message": "Hello from test server"}

if __name__ == "__main__":
    print("Starting test server on localhost:8000...")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )