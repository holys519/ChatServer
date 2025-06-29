"""
認証・認可ミドルウェア
"""
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import security_manager, TokenValidationError

security = HTTPBearer(auto_error=False)

class AuthMiddleware:
    """認証ミドルウェア"""
    
    def __init__(self):
        self.public_paths = {
            "/health",
            "/docs", 
            "/redoc",
            "/openapi.json",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/refresh",
            "/api/models/list"  # 認証不要のエンドポイント
        }
    
    async def __call__(self, request: Request, call_next):
        """認証ミドルウェアのメイン処理"""
        
        # パブリックパスは認証不要
        if request.url.path in self.public_paths:
            return await call_next(request)
        
        # Authorizationヘッダーから認証情報を取得
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            
            # トークンを検証
            payload = security_manager.validate_session_token(token)
            if payload:
                # リクエストにユーザー情報を追加
                request.state.user_id = payload.get("user_id")
                request.state.session_id = payload.get("session_id")
                request.state.permissions = payload.get("permissions", [])
                request.state.roles = payload.get("roles", [])
            else:
                # 無効なトークンの場合はクリア
                request.state.user_id = None
        else:
            # 認証情報がない場合
            request.state.user_id = None
        
        return await call_next(request)

# Dependency functions for FastAPI
async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    """現在のユーザーを取得（オプショナル）"""
    if not credentials:
        return None
    
    payload = security_manager.validate_session_token(credentials.credentials)
    return payload

async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """認証を必須とする"""
    if not credentials:
        raise TokenValidationError("Authentication required")
    
    payload = security_manager.validate_session_token(credentials.credentials)
    if not payload:
        raise TokenValidationError("Invalid or expired token")
    
    return payload

async def require_permission(permission: str):
    """特定の権限を必須とする"""
    def permission_checker(user: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
        user_permissions = user.get("permissions", [])
        if permission not in user_permissions and "admin" not in user.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return user
    return permission_checker

async def require_role(role: str):
    """特定のロールを必須とする"""
    def role_checker(user: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
        user_roles = user.get("roles", [])
        if role not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required"
            )
        return user
    return role_checker

# 認証関連のヘルパー関数
async def get_user_id_from_request(request: Request) -> Optional[str]:
    """リクエストからユーザーIDを取得"""
    return getattr(request.state, 'user_id', None)

async def get_user_permissions(request: Request) -> list:
    """リクエストからユーザー権限を取得"""
    return getattr(request.state, 'permissions', [])

async def get_user_roles(request: Request) -> list:
    """リクエストからユーザーロールを取得"""
    return getattr(request.state, 'roles', [])

# ミドルウェアインスタンス
auth_middleware = AuthMiddleware()