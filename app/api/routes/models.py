from fastapi import APIRouter
from typing import List
from app.models.schemas import AIModel

router = APIRouter()

# Available models
AVAILABLE_MODELS = [
    AIModel(
        id="gpt4o-mini",
        name="GPT-4o mini",
        provider="OpenAI",
        description="Cost-efficient small version of GPT-4o",
        icon="logo-openai",
        color="#10a37f"
    ),
    AIModel(
        id="gpt4o",
        name="GPT-4o",
        provider="OpenAI",
        description="OpenAI's latest multimodal model",
        icon="logo-openai",
        color="#10a37f"
    ),
    AIModel(
        id="claude-3-5-sonnet",
        name="Claude 3.5 Sonnet",
        provider="Anthropic",
        description="Balanced performance and efficiency",
        icon="sparkles-outline",
        color="#5436da"
    ),
    AIModel(
        id="claude-3-haiku",
        name="Claude 3 Haiku",
        provider="Anthropic",
        description="Fast and efficient responses",
        icon="sparkles-outline",
        color="#5436da"
    ),
    # 動作確認済みGeminiモデル
    AIModel(
        id="gemini-2-0-flash-001",
        name="Gemini 2.0 Flash",
        provider="Google",
        description="Fast and efficient version of Gemini 2.0 (verified working)",
        icon="logo-google",
        color="#4285f4"
    ),
    AIModel(
        id="gemini-2-0-flash-lite-001",
        name="Gemini 2.0 Flash Lite",
        provider="Google",
        description="Lightweight version of Gemini 2.0 Flash (verified working)",
        icon="logo-google",
        color="#4285f4"
    )
]

@router.get("/", response_model=List[AIModel])
async def get_available_models():
    """Get list of available AI models"""
    return AVAILABLE_MODELS

@router.get("/{model_id}", response_model=AIModel)
async def get_model_by_id(model_id: str):
    """Get specific model by ID"""
    for model in AVAILABLE_MODELS:
        if model.id == model_id:
            return model
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Model not found")