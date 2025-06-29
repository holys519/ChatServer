from fastapi import APIRouter, HTTPException, Header, Depends
from typing import List, Optional
import uuid
from datetime import datetime

from app.models.schemas import (
    ChatSession,
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionResponse,
    ChatSessionListResponse,
    ChatMessage
)
from app.services.session_service import session_service
from app.middleware.auth import get_current_user, require_auth

router = APIRouter()

# 後方互換性のための認証ヘルパー
async def get_current_user_id(
    current_user: Optional[dict] = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
) -> str:
    """
    新しいJWT認証システムまたは従来の認証システムでユーザーIDを取得
    後方互換性を保つため両方をサポート
    """
    print(f"🔐 Auth check - JWT user: {current_user is not None}, Auth header: {authorization is not None}")
    
    # 新しいJWT認証を優先
    if current_user and current_user.get("user_id"):
        user_id = current_user["user_id"]
        print(f"🔐 Using JWT user_id: {user_id}")
        return user_id
    
    # 従来の認証システムをフォールバック
    if authorization:
        try:
            scheme, user_id = authorization.split(" ", 1)
            if scheme.lower() == "bearer":
                print(f"🔐 Using Bearer user_id: {user_id}")
                return user_id
        except ValueError:
            print(f"🔐 Invalid authorization format: {authorization}")
            pass
    
    print(f"🔐 No valid authentication found")
    raise HTTPException(status_code=401, detail="Authentication required")

@router.get("/", response_model=ChatSessionListResponse)
async def get_user_sessions(user_id: str = Depends(get_current_user_id)):
    """ユーザーのチャットセッション一覧を取得"""
    try:
        print(f"📋 Getting sessions for user: {user_id}")
        sessions = await session_service.get_user_sessions(user_id)
        print(f"📋 Found {len(sessions)} sessions")
        return ChatSessionListResponse(sessions=sessions)
    except Exception as e:
        print(f"❌ Error getting sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=ChatSessionResponse)
async def create_session(
    session_data: ChatSessionCreate,
    user_id: str = Depends(get_current_user_id)
):
    """新しいチャットセッションを作成"""
    try:
        session = await session_service.create_session(user_id, session_data)
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """特定のチャットセッションを取得"""
    try:
        session = await session_service.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: str,
    session_data: ChatSessionUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """チャットセッションを更新"""
    try:
        session = await session_service.update_session(session_id, user_id, session_data)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """チャットセッションを削除"""
    try:
        success = await session_service.delete_session(session_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"message": "Session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/messages", response_model=ChatSessionResponse)
async def add_message_to_session(
    session_id: str,
    message: ChatMessage,
    user_id: str = Depends(get_current_user_id)
):
    """チャットセッションにメッセージを追加"""
    try:
        session = await session_service.add_message_to_session(session_id, user_id, message)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))