"""
セキュリティ関連のユーティリティとJWT実装
"""
import jwt
from jose import JWTError
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union
from fastapi import HTTPException, status
from passlib.context import CryptContext
from app.core.config import settings

# パスワードハッシュ化
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT設定
SECRET_KEY = settings.SECRET_KEY or secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

class SecurityManager:
    """セキュリティ管理クラス"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """パスワードをハッシュ化"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """パスワードを検証"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """アクセストークンを生成"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        })
        
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """リフレッシュトークンを生成"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        })
        
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """トークンを検証"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # トークンタイプの検証
            if payload.get("type") != token_type:
                return None
            
            # 有効期限の検証
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                return None
            
            return payload
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def create_session_token(user_id: str, session_data: Dict[str, Any]) -> str:
        """セッショントークンを生成"""
        data = {
            "user_id": user_id,
            "session_id": secrets.token_urlsafe(32),
            "permissions": session_data.get("permissions", []),
            "roles": session_data.get("roles", [])
        }
        return SecurityManager.create_access_token(data)
    
    @staticmethod
    def validate_session_token(token: str) -> Optional[Dict[str, Any]]:
        """セッショントークンを検証"""
        payload = SecurityManager.verify_token(token, "access")
        if not payload:
            return None
        
        # 必須フィールドの確認
        required_fields = ["user_id", "session_id"]
        if not all(field in payload for field in required_fields):
            return None
        
        return payload
    
    @staticmethod
    def generate_csrf_token() -> str:
        """CSRFトークンを生成"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_sensitive_data(data: str) -> str:
        """機密データをハッシュ化"""
        return hashlib.sha256(data.encode()).hexdigest()

# トークン検証エラー
class TokenValidationError(HTTPException):
    def __init__(self, detail: str = "Token validation failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

# セキュリティヘルパー関数
def create_secure_headers() -> Dict[str, str]:
    """セキュアなHTTPヘッダーを生成"""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }

# セキュリティミドルウェア用関数
def sanitize_input(data: Union[str, Dict, Any]) -> Union[str, Dict, Any]:
    """入力データをサニタイズ"""
    if isinstance(data, str):
        # HTMLエスケープ
        return (data.replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;")
               .replace('"', "&quot;")
               .replace("'", "&#x27;"))
    elif isinstance(data, dict):
        return {key: sanitize_input(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    return data

security_manager = SecurityManager()