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

router = APIRouter()

# ユーザー認証のヘルパー関数（簡易版）
async def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    簡易的なユーザー認証。実際の実装では JWT トークンの検証などを行う
    現在は Authorization ヘッダーから user_id を直接取得
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    # "Bearer user_id" 形式を想定
    try:
        scheme, user_id = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")
        return user_id
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization format")

@router.get("/", response_model=ChatSessionListResponse)
async def get_user_sessions(user_id: str = Depends(get_current_user_id)):
    """ユーザーのチャットセッション一覧を取得"""
    try:
        sessions = await session_service.get_user_sessions(user_id)
        return ChatSessionListResponse(sessions=sessions)
    except Exception as e:
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