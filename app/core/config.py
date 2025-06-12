from pydantic_settings import BaseSettings
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # アプリケーション設定
    APP_NAME: str = "ChatLLM API"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS設定
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",   # React/Next.js dev server
        "http://localhost:8081",   # React Native Metro bundler
        "http://localhost:19000",  # Expo dev server
        "http://localhost:19006",  # Expo web
        "exp://localhost:*",       # Expo development
        "exp://*",                 # Expo tunnels
        "*"  # Allow all origins for development
    ]
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    GOOGLE_CLOUD_API_KEY: Optional[str] = os.getenv("GOOGLE_CLOUD_API_KEY")
    
    # Google Cloud / Vertex AI Settings
    google_cloud_project: Optional[str] = os.getenv("GOOGLE_CLOUD_PROJECT")
    google_application_credentials: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    vertex_ai_location: str = os.getenv("VERTEX_AI_LOCATION", "us-central1")
    
    # Firebase Settings
    firebase_project_id: Optional[str] = os.getenv("FIREBASE_PROJECT_ID")
    firebase_admin_sdk_path: Optional[str] = os.getenv("FIREBASE_ADMIN_SDK_PATH")
    firebase_admin_sdk_json: Optional[str] = os.getenv("FIREBASE_ADMIN_SDK_JSON")
    
    # モデル設定
    AVAILABLE_MODELS: Dict = {
        "openai": ["gpt4o-mini", "gpt4o", "o3-mini", "o1-mini"],
        "anthropic": ["claude-3-7-sonnet", "claude-3-5-sonnet-v2", "claude-3-5-sonnet", "claude-3-haiku"],
        "google": [
            # Latest Gemini 2.0 models
            "gemini-2-0-flash-001", 
            "gemini-2-0-flash-lite-001",
            # Gemini 2.5 preview models
            "gemini-2-5-pro",
            "gemini-2-5-flash",
            # Legacy 1.5 models
            "gemini-1-5-pro", 
            "gemini-1-5-flash"
        ]
    }
    
    # セキュリティ設定
    API_KEY_HEADER: str = "X-API-Key"
    API_KEY: Optional[str] = os.getenv("API_KEY")
    
    class Config:
        env_file = ".env"

settings = Settings()