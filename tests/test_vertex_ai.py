#!/usr/bin/env python3
"""
Test script for Vertex AI Gemini integration.
Run this to verify your Vertex AI setup is working correctly.
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_vertex_ai_setup():
    """Test Vertex AI setup with Gemini models"""
    print("🧪 Testing Vertex AI Gemini Setup...")
    print("=" * 50)
    
    # Check environment variables
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
    
    print(f"Project ID: {project_id}")
    print(f"Location: {location}")
    print()
    
    if not project_id:
        print("❌ Error: GOOGLE_CLOUD_PROJECT environment variable is not set")
        print("Please set it in your .env file or environment")
        return False
    
    try:
        # Import the service
        from app.services.gemini_service import gemini_service
        
        print("✅ GeminiService imported successfully")
        
        # Check if service is initialized
        if not gemini_service.initialized:
            print("❌ Error: GeminiService is not initialized")
            print("Check your Google Cloud credentials and project setup")
            return False
        
        print("✅ GeminiService initialized successfully")
        print()
        
        # Test models
        models_to_test = [
            "gemini-2-0-flash-001",
            "gemini-2-0-flash-lite-001"
        ]
        
        test_message = "Hello! Please respond with 'Vertex AI is working correctly' if you can understand this message."
        
        for model_id in models_to_test:
            print(f"🔄 Testing model: {model_id}")
            
            try:
                # Test regular message
                response = await gemini_service.send_message(model_id, [], test_message)
                print(f"✅ Response from {model_id}:")
                print(f"   {response[:100]}{'...' if len(response) > 100 else ''}")
                
                # Test streaming
                print(f"🔄 Testing streaming for {model_id}...")
                stream_response = ""
                async for chunk in gemini_service.stream_chat(model_id, [], "Count from 1 to 5"):
                    stream_response += chunk
                
                print(f"✅ Streaming response from {model_id}:")
                print(f"   {stream_response[:100]}{'...' if len(stream_response) > 100 else ''}")
                print()
                
            except Exception as e:
                print(f"❌ Error testing {model_id}: {str(e)}")
                print()
        
        print("🎉 All tests completed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed:")
        print("  uv sync")
        print("  or pip install google-genai")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print()
        print("Common solutions:")
        print("1. Check GOOGLE_CLOUD_PROJECT is set correctly")
        print("2. Ensure Vertex AI API is enabled:")
        print("   gcloud services enable aiplatform.googleapis.com")
        print("3. Verify authentication:")
        print("   gcloud auth application-default login")
        print("4. Check project permissions for Vertex AI")
        return False

async def test_api_endpoints():
    """Test the API endpoints that use Gemini"""
    print("\n🌐 Testing API Endpoints...")
    print("=" * 50)
    
    try:
        import httpx
        
        # Test chat endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/chat/",
                json={
                    "message": "Hello from test script!",
                    "model": "gemini-2-0-flash-001",
                    "history": []
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                print("✅ Chat API endpoint working")
                data = response.json()
                print(f"   Response: {data.get('response', '')[:100]}...")
            else:
                print(f"❌ Chat API error: {response.status_code}")
                print(f"   {response.text}")
        
    except httpx.ConnectError:
        print("❌ Cannot connect to API server")
        print("Make sure the server is running:")
        print("   cd ChatServer && ./scripts/dev.sh")
    except ImportError:
        print("❌ httpx not installed. Skipping API tests.")
        print("Install with: pip install httpx")
    except Exception as e:
        print(f"❌ API test error: {e}")

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("📦 Checking Dependencies...")
    print("=" * 50)
    
    required_packages = [
        "google.genai",
        "fastapi",
        "uvicorn",
        "pydantic",
        "dotenv"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Install with: uv sync")
        return False
    
    print("\n✅ All dependencies are installed")
    return True

if __name__ == "__main__":
    print("🚀 ChatServer Vertex AI Test Suite")
    print("=" * 60)
    
    # Check dependencies first
    if not check_dependencies():
        exit(1)
    
    # Run async tests
    success = asyncio.run(test_vertex_ai_setup())
    
    if success:
        # Test API endpoints if basic tests pass
        asyncio.run(test_api_endpoints())
        print("\n🎉 Setup verification complete!")
        print("Your Vertex AI integration is ready to use.")
    else:
        print("\n❌ Setup verification failed!")
        print("Please review the error messages above and fix the issues.")
        exit(1)