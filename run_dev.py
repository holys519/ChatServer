#!/usr/bin/env python3
"""
ChatServer Development Server Startup Script
Alternative to shell script for cross-platform compatibility
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🚀 Starting ChatServer development server with uv...")
    
    # Check if .env file exists
    if not Path(".env").exists():
        print("⚠️  .env file not found. Creating from .env.example...")
        if Path(".env.example").exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print("📝 Please edit .env file with your API keys before running again.")
            print("   Especially set GOOGLE_CLOUD_API_KEY for Gemini API functionality.")
            return 1
        else:
            print("❌ .env.example file not found. Please create .env file manually.")
            return 1
    
    # Check if GOOGLE_CLOUD_API_KEY is set
    try:
        with open(".env", "r") as f:
            env_content = f.read()
            if "GOOGLE_CLOUD_API_KEY=your_google_cloud_api_key_here" not in env_content:
                print("✅ .env file exists and API key appears to be configured.")
            else:
                print("⚠️  Please set your GOOGLE_CLOUD_API_KEY in .env file.")
                print("   Current value appears to be the default placeholder.")
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
        return 1
    
    # Install dependencies using uv
    print("📦 Installing dependencies with uv...")
    try:
        subprocess.run(["uv", "sync"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return 1
    except FileNotFoundError:
        print("❌ uv command not found. Please install uv first.")
        return 1
    
    # Start the development server
    print("🌐 Starting FastAPI server on http://localhost:8000")
    print("📖 API documentation will be available at http://localhost:8000/docs")
    print("🔍 Health check endpoint: http://localhost:8000/health")
    print("")
    print("Press Ctrl+C to stop the server")
    print("")
    
    # Run the server using uv
    try:
        subprocess.run([
            "uv", "run", "uvicorn", 
            "app.main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start server: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
        return 0

if __name__ == "__main__":
    sys.exit(main())