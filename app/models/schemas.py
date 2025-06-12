from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Literal, Union
from datetime import datetime
import uuid
from datetime import datetime

class AIModel(BaseModel):
    id: str
    name: str
    provider: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    
    @validator('provider')
    def validate_provider(cls, v):
        # Case-insensitive validation
        valid_providers = ["OpenAI", "Anthropic", "Google"]
        if v not in valid_providers:
            # Try case-insensitive match
            for valid in valid_providers:
                if v.lower() == valid.lower():
                    return valid
            raise ValueError(f"Provider must be one of {valid_providers}")
        return v
    

class ChatHistoryItem(BaseModel):
    id: str
    content: str
    is_user: bool = Field(..., alias='isUser')  # aliasを追加
    timestamp: datetime

    class Config:
        populate_by_name = True # Pydantic v2 の場合
        # allow_population_by_field_name = True # Pydantic v1 の場合

class ChatResponse(BaseModel):
    content: str
    model_id: str
    is_streaming: bool = False


class ChatRequest(BaseModel):
    message: str
    model: AIModel
    history: List[ChatHistoryItem] = []
    session_id: Optional[str] = None
    
    # リクエストの検証と変換を行うモデルクラスメソッドを追加
    @validator('history', pre=True)
    def validate_history(cls, v):
        if not v:
            return []
        
        # フロントエンドから送られてくる形式に対応
        result = []
        for item in v:
            # 既にChatHistoryItemの形式であれば、そのまま使用
            if isinstance(item, dict) and all(k in item for k in ['id', 'content', 'is_user']):
                # timestampがない場合は現在時刻を設定
                if 'timestamp' not in item:
                    item['timestamp'] = datetime.now()
                # timestampが文字列の場合はdatetimeに変換
                elif isinstance(item['timestamp'], str):
                    try:
                        item['timestamp'] = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
                    except ValueError:
                        item['timestamp'] = datetime.now()
                result.append(item)
        return result
    
class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    role: Literal["user", "assistant"]
    timestamp: datetime = Field(default_factory=datetime.now)

class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str  # Remove Literal validation to match AIModel
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    available: bool = True
    
    @validator('provider')
    def validate_provider(cls, v):
        # Case-insensitive validation
        valid_providers = ["OpenAI", "Anthropic", "Google"]
        if v not in valid_providers:
            # Try case-insensitive match
            for valid in valid_providers:
                if v.lower() == valid.lower():
                    return valid
            raise ValueError(f"Provider must be one of {valid_providers}")
        return v

class ModelsResponse(BaseModel):
    models: List[ModelInfo]

# チャット履歴管理用のスキーマ
class ChatMessage(BaseModel):
    id: str
    content: str
    is_user: bool
    timestamp: datetime

class ChatSession(BaseModel):
    id: str
    title: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessage] = []
    model_id: Optional[str] = None

class ChatSessionCreate(BaseModel):
    title: str
    model_id: Optional[str] = None

class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    model_id: Optional[str] = None

class ChatSessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessage]
    model_id: Optional[str] = None

class ChatSessionListResponse(BaseModel):
    sessions: List[ChatSessionResponse]