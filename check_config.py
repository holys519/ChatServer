#!/usr/bin/env python3
"""
Quick configuration check for Gemini service
"""

import os
from dotenv import load_dotenv

def check_gemini_config():
    load_dotenv()
    
    print("🔧 Gemini Service Configuration Check")
    print("=" * 50)
    
    # Check environment variables
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
    credentials = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    print(f"GOOGLE_CLOUD_PROJECT: {project_id if project_id else '❌ Not set'}")
    print(f"VERTEX_AI_LOCATION: {location}")
    print(f"GOOGLE_APPLICATION_CREDENTIALS: {credentials if credentials else '❌ Not set (using default auth)'}")
    
    if not project_id:
        print("\n❌ Error: GOOGLE_CLOUD_PROJECT is not set!")
        print("💡 Set it in your .env file:")
        print("   GOOGLE_CLOUD_PROJECT=your-project-id")
        return False
    
    # Check if google-genai is available
    try:
        import google.genai
        print(f"✅ google-genai package: Available (version: {google.genai.__version__})")
    except ImportError:
        print("❌ google-genai package: Not installed")
        print("💡 Install with: pip install google-genai")
        return False
    
    # Test basic initialization
    try:
        from google import genai
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location
        )
        print("✅ Google Gen AI client: Created successfully")
        return True
    except Exception as e:
        print(f"❌ Google Gen AI client: Failed to create - {e}")
        print("💡 Check your Google Cloud authentication:")
        print("   gcloud auth application-default login")
        return False

if __name__ == "__main__":
    success = check_gemini_config()
    if success:
        print("\n🎉 Configuration looks good!")
    else:
        print("\n❌ Configuration issues found. Please fix them and try again.")