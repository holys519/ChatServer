"""
セキュリティミドルウェア統合
"""
import re
import json
from typing import Any, Dict
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.core.security import sanitize_input, create_secure_headers

class SecurityMiddleware:
    """セキュリティミドルウェア"""
    
    def __init__(self):
        # XSS攻撃パターン
        self.xss_patterns = [
            re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'on\w+\s*=', re.IGNORECASE),
            re.compile(r'<iframe[^>]*>', re.IGNORECASE),
            re.compile(r'<object[^>]*>', re.IGNORECASE),
            re.compile(r'<embed[^>]*>', re.IGNORECASE),
        ]
        
        # SQL Injectionパターン
        self.sql_patterns = [
            re.compile(r'(union\s+select|select\s+.*\s+from)', re.IGNORECASE),
            re.compile(r'(drop\s+table|delete\s+from|insert\s+into)', re.IGNORECASE),
            re.compile(r'(\';|\";\s*--|\/\*|\*\/)', re.IGNORECASE),
            re.compile(r'(exec\s*\(|execute\s*\()', re.IGNORECASE),
        ]
        
        # 危険なファイルアップロード拡張子
        self.dangerous_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
            '.jar', '.php', '.asp', '.aspx', '.jsp', '.pl', '.py', '.rb'
        }
    
    def detect_xss(self, text: str) -> bool:
        """XSS攻撃を検出"""
        return any(pattern.search(text) for pattern in self.xss_patterns)
    
    def detect_sql_injection(self, text: str) -> bool:
        """SQL Injection攻撃を検出"""
        return any(pattern.search(text) for pattern in self.sql_patterns)
    
    def validate_content_type(self, request: Request) -> bool:
        """Content-Typeを検証"""
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "").lower()
            allowed_types = [
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
                "text/plain"
            ]
            return any(allowed_type in content_type for allowed_type in allowed_types)
        return True
    
    def validate_request_size(self, request: Request) -> bool:
        """リクエストサイズを検証"""
        content_length = request.headers.get("content-length")
        if content_length:
            size = int(content_length)
            max_size = 10 * 1024 * 1024  # 10MB
            return size <= max_size
        return True
    
    async def validate_json_body(self, request: Request) -> bool:
        """JSONボディを検証"""
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "").lower()
            if "application/json" in content_type:
                try:
                    body = await request.body()
                    if body:
                        data = json.loads(body)
                        return self.validate_data_security(data)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return False
        return True
    
    def validate_data_security(self, data: Any) -> bool:
        """データのセキュリティを検証"""
        if isinstance(data, str):
            if self.detect_xss(data) or self.detect_sql_injection(data):
                return False
        elif isinstance(data, dict):
            for key, value in data.items():
                if not self.validate_data_security(key) or not self.validate_data_security(value):
                    return False
        elif isinstance(data, list):
            for item in data:
                if not self.validate_data_security(item):
                    return False
        return True
    
    async def __call__(self, request: Request, call_next):
        """セキュリティミドルウェアのメイン処理"""
        
        # 基本的なセキュリティチェック
        if not self.validate_content_type(request):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid content type"}
            )
        
        if not self.validate_request_size(request):
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request too large"}
            )
        
        # JSONボディのセキュリティ検証
        if not await self.validate_json_body(request):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Potentially malicious content detected"}
            )
        
        # リクエストを続行
        response = await call_next(request)
        
        # セキュリティヘッダーを追加
        security_headers = create_secure_headers()
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response

# ミドルウェアインスタンス
security_middleware = SecurityMiddleware()