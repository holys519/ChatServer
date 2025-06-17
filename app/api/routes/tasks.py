from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
import json
import uuid
from datetime import datetime
from app.models.schemas import TaskRequest, TaskResponse, TaskStatus, TaskProgress
from app.services.task_service import task_service
from app.services.session_service import session_service

router = APIRouter()

async def get_user_id_from_auth(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Authorization ヘッダーからユーザーIDを取得"""
    if not authorization:
        return None
    
    try:
        scheme, user_id = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            return None
        return user_id
    except ValueError:
        return None

@router.post("/execute", response_model=TaskResponse)
async def execute_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None)
):
    """統一タスク実行エンドポイント"""
    try:
        user_id = await get_user_id_from_auth(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # タスクIDを生成
        task_id = str(uuid.uuid4())
        
        # タスクをDBに登録
        task_progress = TaskProgress(
            task_id=task_id,
            user_id=user_id,
            session_id=request.session_id,
            task_type=request.task_type,
            input_data=request.input_data,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        await task_service.create_task(task_progress)
        
        # バックグラウンドでタスクを実行
        background_tasks.add_task(
            task_service.execute_task_background,
            task_id=task_id,
            user_id=user_id,
            request=request
        )
        
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="Task has been queued for execution"
        )
        
    except Exception as e:
        print(f"Error in execute_task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{task_id}", response_model=TaskProgress)
async def get_task_status(
    task_id: str,
    authorization: Optional[str] = Header(None)
):
    """タスクの進捗状況を取得"""
    try:
        user_id = await get_user_id_from_auth(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        task_progress = await task_service.get_task_progress(task_id, user_id)
        if not task_progress:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return task_progress
        
    except Exception as e:
        print(f"Error in get_task_status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def get_user_tasks(
    authorization: Optional[str] = Header(None),
    limit: int = 50,
    offset: int = 0
):
    """ユーザーのタスク一覧を取得"""
    try:
        user_id = await get_user_id_from_auth(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        tasks = await task_service.get_user_tasks(user_id, limit, offset)
        return {"tasks": tasks}
        
    except Exception as e:
        print(f"Error in get_user_tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    authorization: Optional[str] = Header(None)
):
    """タスクをキャンセル"""
    try:
        user_id = await get_user_id_from_auth(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        success = await task_service.cancel_task(task_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
        
        return {"message": "Task cancelled successfully"}
        
    except Exception as e:
        print(f"Error in cancel_task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream/{task_id}")
async def stream_task_progress(
    task_id: str,
    authorization: Optional[str] = Header(None)
):
    """タスク進捗のリアルタイムストリーミング"""
    async def generate_progress_stream():
        try:
            user_id = await get_user_id_from_auth(authorization)
            if not user_id:
                yield f"data: {json.dumps({'error': 'Authentication required'})}\n\n"
                return
            
            # タスクの存在確認
            task_progress = await task_service.get_task_progress(task_id, user_id)
            if not task_progress:
                yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
                return
            
            # 進捗ストリーミング
            async for progress_update in task_service.stream_task_progress(task_id, user_id):
                yield f"data: {json.dumps(progress_update.dict())}\n\n"
                
                # タスクが完了またはエラーの場合はストリーミングを終了
                if progress_update.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    break
                    
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_progress_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )