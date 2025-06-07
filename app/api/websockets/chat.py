from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from typing import Dict
from app.services.gemini_service import gemini_service

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

manager = ConnectionManager()

@router.websocket("/ws/chat/{client_id}")
async def websocket_chat_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            request_data = json.loads(data)
            
            message = request_data.get("message", "")
            model = request_data.get("model", {})
            history = request_data.get("history", [])
            
            if model.get("provider", "").lower() == "google" and gemini_service:
                # Convert history format
                formatted_history = [
                    {
                        "role": "user" if msg["is_user"] else "model",
                        "content": msg["content"]
                    }
                    for msg in history
                ]
                
                # Stream response
                async for chunk in gemini_service.stream_chat(
                    model_name=model["id"],
                    history=formatted_history,
                    message=message
                ):
                    await manager.send_message(
                        json.dumps({
                            "type": "chunk",
                            "content": chunk,
                            "done": False
                        }),
                        client_id
                    )
                
                # Send completion signal
                await manager.send_message(
                    json.dumps({
                        "type": "chunk",
                        "content": "",
                        "done": True
                    }),
                    client_id
                )
            else:
                # Fallback for other providers
                response = f"[{model.get('provider', 'AI')} {model.get('id', 'Unknown')}] WebSocket response for {message}"
                await manager.send_message(
                    json.dumps({
                        "type": "response",
                        "content": response,
                        "done": True
                    }),
                    client_id
                )
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        