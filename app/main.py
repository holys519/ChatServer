from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.chat import router as chat_router
from app.api.routes.models import router as models_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.commands import router as commands_router
from app.api.routes.workflows import router as workflows_router
from app.api.websockets.chat import router as ws_chat_router
from app.core.config import settings
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.services.openai_service import openai_service
from app.services.gemini_service import gemini_service

# Firebase サービスをインポート（利用可能な場合）
try:
    from app.services.firebase_service import firebase_service
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

app = FastAPI(title="ChatLLM API", debug=True)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発中は全てのオリジンを許可
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)
# バリデーションエラーのハンドラーを追加
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"Validation error details: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.errors()},
    )

# ルーターの登録
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(models_router, prefix="/api/models", tags=["models"])
app.include_router(sessions_router, prefix="/api/sessions", tags=["sessions"])
app.include_router(tasks_router, prefix="/api/tasks", tags=["tasks"])
app.include_router(knowledge_router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(commands_router, prefix="/api/commands", tags=["commands"])
app.include_router(workflows_router, prefix="/api/workflows", tags=["workflows"])

# WebSocketの登録
app.include_router(ws_chat_router)

@app.get("/health")
async def health_check():
    services_status = {
        "openai": openai_service.initialized,
        "gemini": hasattr(gemini_service, 'initialized') and gemini_service.initialized,
    }
    
    # Firebase状況を追加
    if FIREBASE_AVAILABLE:
        services_status["firebase"] = firebase_service.is_available()
        services_status["session_storage"] = "firestore" if firebase_service.is_available() else "local_file"
    else:
        services_status["firebase"] = False
        services_status["session_storage"] = "local_file"
    
    return {
        "status": "healthy",
        "services": services_status
    }

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "message": str(exc)},
    )
    
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"Request: {request.method} {request.url}")
    print(f"Headers: {request.headers}")
    
    # リクエストボディを読み取る（必要に応じて）
    # body = await request.body()
    # if body:
    #     print(f"Body: {body.decode()}")
    
    # 元のリクエストボディを復元するために新しいリクエストを作成
    # request = Request(
    #     scope=request.scope,
    #     receive=request._receive,
    #     send=request._send,
    # )
    
    response = await call_next(request)
    print(f"Response status: {response.status_code}")
    
    return response