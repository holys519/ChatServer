from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any
import json
from app.models.schemas import ChatRequest, ChatResponse, ChatHistoryItem
from app.services.gemini_service import gemini_service
from app.services.openai_service import openai_service

router = APIRouter()

@router.post("/send", response_model=ChatResponse)
async def send_chat_message(request: ChatRequest):
    """Send a chat message and get complete response"""
    try:
        # デバッグ用ログ
        print(f"Received request: {request.model_dump_json()}")
        print(f"Model provider: {request.model.provider}")
        
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
            response_text = await gemini_service.send_message(
                model_name=request.model.id,
                history=history,
                message=request.message
            )
            
            return ChatResponse(
                content=response_text,
                model_id=request.model.id,
                is_streaming=False
            )
        
        # OpenAI models
        elif request.model.provider.lower() == "openai" and openai_service and openai_service.initialized:
            response_text = await openai_service.send_message(
                model_name=request.model.id,
                history=history,
                message=request.message
            )
            
            return ChatResponse(
                content=response_text,
                model_id=request.model.id,
                is_streaming=False
            )
        
        # Fallback for other providers or when service is not initialized
        else:
            return ChatResponse(
                content=f"[{request.model.provider} {request.model.id}] This is a dummy response. Actual implementation needed for {request.model.provider} models.",
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