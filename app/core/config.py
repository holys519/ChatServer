from pydantic_settings import BaseSettings
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # アプリケーション設定
    APP_NAME: str = "ChatLLM API"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS設定 - プロダクション環境では厳格化
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",   # React/Next.js dev server
        "http://localhost:8081",   # React Native Metro bundler
        "http://localhost:19000",  # Expo dev server
        "http://localhost:19006",  # Expo web
        "exp://localhost:19000",   # Expo development
        "exp://localhost:19006",   # Expo web development
    ] if os.getenv("ENVIRONMENT", "development") == "development" else [
        # プロダクション環境では実際のドメインのみ許可
        os.getenv("FRONTEND_URL", "https://yourdomain.com")
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
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    
    # JWT設定
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Rate Limiting設定
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "60"))  # seconds
    
    # セキュリティ設定
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = [
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-CSRF-Token"
    ]
    
    # .envファイルから読み込まれる追加設定
    FRONTEND_URL: Optional[str] = os.getenv("FRONTEND_URL", "http://localhost:19006")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")
    CORS_MAX_AGE: int = int(os.getenv("CORS_MAX_AGE", "86400"))
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # 追加フィールドを許可

settings = Settings()