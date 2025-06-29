"""
認証関連のAPIエンドポイント
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.core.security import security_manager
from app.middleware.auth import get_current_user, require_auth
from datetime import datetime, timedelta

router = APIRouter()

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserProfile(BaseModel):
    user_id: str
    email: str
    name: str
    created_at: datetime
    permissions: list
    roles: list

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """ユーザーログイン"""
    try:
        # TODO: 実際のユーザー認証ロジックに置き換える
        # 現在はFirebase認証との統合を想定
        
        # デモ用の簡易認証（実装時は削除）
        if user_data.email == "demo@example.com" and user_data.password == "demo123":
            user_info = {
                "user_id": "demo_user_123",
                "email": user_data.email,
                "permissions": ["chat", "tasks"],
                "roles": ["user"]
            }
            
            access_token = security_manager.create_session_token(
                user_info["user_id"], 
                {
                    "permissions": user_info["permissions"],
                    "roles": user_info["roles"]
                }
            )
            
            refresh_token = security_manager.create_refresh_token({
                "user_id": user_info["user_id"]
            })
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=1800  # 30分
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """ユーザー登録"""
    try:
        # TODO: 実際のユーザー登録ロジックに置き換える
        # パスワードハッシュ化、ユーザー情報の保存など
        
        # デモ用の実装
        user_info = {
            "user_id": f"user_{user_data.email.split('@')[0]}",
            "email": user_data.email,
            "name": user_data.name,
            "permissions": ["chat", "tasks"],
            "roles": ["user"]
        }
        
        access_token = security_manager.create_session_token(
            user_info["user_id"],
            {
                "permissions": user_info["permissions"],
                "roles": user_info["roles"]
            }
        )
        
        refresh_token = security_manager.create_refresh_token({
            "user_id": user_info["user_id"]
        })
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=1800
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token_data: RefreshTokenRequest):
    """リフレッシュトークンでアクセストークンを更新"""
    try:
        # リフレッシュトークンを検証
        payload = security_manager.verify_token(token_data.refresh_token, "refresh")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # TODO: ユーザー情報を取得（データベースから）
        # 現在はデモ用
        user_info = {
            "permissions": ["chat", "tasks"],
            "roles": ["user"]
        }
        
        # 新しいアクセストークンを生成
        new_access_token = security_manager.create_session_token(
            user_id,
            user_info
        )
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=token_data.refresh_token,  # リフレッシュトークンは再利用
            expires_in=1800
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: dict = Depends(require_auth)):
    """ユーザープロフィール取得"""
    try:
        # TODO: データベースからユーザー情報を取得
        # 現在はトークンの情報を返す
        
        return UserProfile(
            user_id=current_user["user_id"],
            email=f"{current_user['user_id']}@example.com",  # TODO: 実際のメールアドレス
            name="Demo User",  # TODO: 実際の名前
            created_at=datetime.now(),  # TODO: 実際の作成日時
            permissions=current_user.get("permissions", []),
            roles=current_user.get("roles", [])
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )

@router.post("/logout")
async def logout(current_user: dict = Depends(require_auth)):
    """ユーザーログアウト"""
    try:
        # TODO: トークンの無効化（ブラックリスト等）
        # 現在は成功レスポンスのみ返す
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.get("/verify")
async def verify_token(current_user: Optional[dict] = Depends(get_current_user)):
    """トークン検証"""
    if current_user:
        return {"valid": True, "user_id": current_user["user_id"]}
    else:
        return {"valid": False}