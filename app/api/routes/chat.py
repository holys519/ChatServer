from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
import json
import uuid
from datetime import datetime
from app.models.schemas import ChatRequest, ChatResponse, ChatHistoryItem, ChatMessage
from app.services.gemini_service import gemini_service
from app.services.openai_service import openai_service
from app.services.session_service import session_service

router = APIRouter()

async def get_user_id_from_auth(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    Authorization ヘッダーからユーザーIDを取得（オプショナル）
    ユーザーがログインしていない場合は None を返す
    """
    if not authorization:
        return None
    
    try:
        scheme, user_id = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            return None
        return user_id
    except ValueError:
        return None

@router.post("/send", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    """Send a chat message and get complete response"""
    try:
        # デバッグ用ログ
        print(f"Received request: {request.model_dump_json()}")
        print(f"Model provider: {request.model.provider}")
        
        user_id = await get_user_id_from_auth(authorization)
        
        # Convert history to the format expected by services
        history = [
            {
                "role": "user" if msg.is_user else "model",
                "content": msg.content
            }
            for msg in request.history
        ]
        
        response_text = ""
        
        # Google Gemini models
        if request.model.provider.lower() == "google":
            print(f"Attempting to use Google Gemini model: {request.model.id}")
            print(f"Gemini service available: {gemini_service is not None}")
            print(f"Gemini service initialized: {gemini_service.initialized if gemini_service else False}")
            
            if gemini_service and gemini_service.initialized:
                try:
                    print(f"Calling Gemini API with model: {request.model.id}")
                    response_text = await gemini_service.send_message(
                        model_name=request.model.id,
                        history=history,
                        message=request.message
                    )
                    print(f"Gemini API response received: {len(response_text)} characters")
                except Exception as gemini_error:
                    print(f"Gemini API error: {type(gemini_error).__name__}: {str(gemini_error)}")
                    # Re-raise to be caught by outer exception handler
                    raise
            else:
                print("Gemini service not available or not initialized")
                response_text = f"[ERROR] Gemini service is not available. Please check Google Cloud configuration."
        
        # OpenAI models
        elif request.model.provider.lower() == "openai" and openai_service and openai_service.initialized:
            print(f"Using OpenAI model: {request.model.id}")
            response_text = await openai_service.send_message(
                model_name=request.model.id,
                history=history,
                message=request.message
            )
        
        # Fallback for other providers or when service is not initialized
        else:
            print(f"Using fallback for provider: {request.model.provider}")
            response_text = f"[{request.model.provider} {request.model.id}] This is a dummy response. Actual implementation needed for {request.model.provider} models."
        
        # セッションにメッセージを保存（ユーザーがログインしている場合のみ）
        if user_id and request.session_id:
            # ユーザーメッセージを追加
            user_message = ChatMessage(
                id=str(uuid.uuid4()),
                content=request.message,
                is_user=True,
                timestamp=datetime.now()
            )
            await session_service.add_message_to_session(request.session_id, user_id, user_message)
            
            # AI応答を追加
            ai_message = ChatMessage(
                id=str(uuid.uuid4()),
                content=response_text,
                is_user=False,
                timestamp=datetime.now()
            )
            await session_service.add_message_to_session(request.session_id, user_id, ai_message)
        
        return ChatResponse(
            content=response_text,
            model_id=request.model.id,
            is_streaming=False
        )
            
    except Exception as e:
        print(f"Error in send_chat_message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ストリーミングエンドポイントも同様に修正
@router.post("/stream")
async def stream_chat_message(request: ChatRequest):
    """Stream chat response"""
    async def generate_stream():
        try:
            # Convert history to the format expected by services
            history = [
                {
                    "role": "user" if msg.is_user else "model",
                    "content": msg.content
                }
                for msg in request.history
            ]
            
            # Google Gemini models
            if request.model.provider.lower() == "google" and gemini_service and gemini_service.initialized:
                async for chunk in gemini_service.stream_chat(
                    model_name=request.model.id,
                    history=history,
                    message=request.message
                ):
                    yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                
                yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
            
            # OpenAI models
            elif request.model.provider.lower() == "openai" and openai_service and openai_service.initialized:
                async for chunk in openai_service.stream_chat(
                    model_name=request.model.id,
                    history=history,
                    message=request.message
                ):
                    yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                
                yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
            
            # Fallback for other providers
            else:
                dummy_response = f"[{request.model.provider} {request.model.id}] This is a dummy streaming response for {request.model.provider} models."
                words = dummy_response.split()
                
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                    import asyncio
                    await asyncio.sleep(0.05)
                
                yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'content': f'Error: {str(e)}', 'done': True})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )
    
@router.options("/send")
async def options_chat_send():
    return {}

@router.options("/stream")
async def options_chat_stream():
    return {}