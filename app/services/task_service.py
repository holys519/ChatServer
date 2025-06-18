import asyncio
import json
from typing import Dict, List, Optional, AsyncGenerator, Any
from datetime import datetime, timedelta
from app.models.schemas import (
    TaskRequest, TaskProgress, TaskStatus, TaskType, AgentStep
)
from app.services.firebase_service import firebase_service
from app.services.firestore_session_service import FirestoreSessionService

class TaskService:
    def __init__(self):
        """タスク管理サービスの初期化"""
        self.firestore_service = FirestoreSessionService()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
    async def create_task(self, task_progress: TaskProgress) -> bool:
        """新しいタスクをFirestoreに作成"""
        try:
            if not firebase_service.is_available():
                print("⚠️ Firebase not available, using local storage")
                return await self._create_task_local(task_progress)
            
            db = firebase_service.get_firestore_client()
            task_ref = db.collection('tasks').document(task_progress.task_id)
            
            task_data = task_progress.dict()
            # datetimeオブジェクトをFirestore Timestampに変換
            task_data['created_at'] = task_progress.created_at
            task_data['updated_at'] = task_progress.updated_at
            
            task_ref.set(task_data)
            print(f"✅ Task {task_progress.task_id} created in Firestore")
            return True
            
        except Exception as e:
            print(f"❌ Error creating task: {str(e)}")
            return False
    
    async def _create_task_local(self, task_progress: TaskProgress) -> bool:
        """ローカルファイルにタスクを保存（Firestore利用不可時のフォールバック）"""
        try:
            import os
            import json
            
            tasks_dir = "local_tasks"
            os.makedirs(tasks_dir, exist_ok=True)
            
            task_file = os.path.join(tasks_dir, f"{task_progress.task_id}.json")
            task_data = task_progress.dict()
            
            # datetimeをISO文字列に変換
            for key, value in task_data.items():
                if isinstance(value, datetime):
                    task_data[key] = value.isoformat()
            
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Task {task_progress.task_id} created locally")
            return True
            
        except Exception as e:
            print(f"❌ Error creating local task: {str(e)}")
            return False
    
    async def get_task_progress(self, task_id: str, user_id: str) -> Optional[TaskProgress]:
        """タスクの進捗情報を取得"""
        try:
            if not firebase_service.is_available():
                return await self._get_task_progress_local(task_id, user_id)
            
            db = firebase_service.get_firestore_client()
            task_ref = db.collection('tasks').document(task_id)
            task_doc = task_ref.get()
            
            if not task_doc.exists:
                return None
            
            task_data = task_doc.to_dict()
            
            # ユーザー権限チェック
            if task_data.get('user_id') != user_id:
                return None
            
            return TaskProgress(**task_data)
            
        except Exception as e:
            print(f"❌ Error getting task progress: {str(e)}")
            return None
    
    async def _get_task_progress_local(self, task_id: str, user_id: str) -> Optional[TaskProgress]:
        """ローカルファイルからタスク進捗を取得"""
        try:
            import os
            import json
            
            task_file = os.path.join("local_tasks", f"{task_id}.json")
            if not os.path.exists(task_file):
                return None
            
            with open(task_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
            
            # ユーザー権限チェック
            if task_data.get('user_id') != user_id:
                return None
            
            # ISO文字列をdatetimeに変換
            for key, value in task_data.items():
                if key.endswith('_at') and isinstance(value, str):
                    try:
                        task_data[key] = datetime.fromisoformat(value)
                    except ValueError:
                        pass
            
            return TaskProgress(**task_data)
            
        except Exception as e:
            print(f"❌ Error getting local task progress: {str(e)}")
            return None
    
    async def update_task_progress(
        self, 
        task_id: str, 
        status: Optional[TaskStatus] = None,
        progress_percentage: Optional[float] = None,
        current_step: Optional[str] = None,
        steps_completed: Optional[int] = None,
        total_steps: Optional[int] = None,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """タスクの進捗を更新"""
        try:
            update_data = {
                'updated_at': datetime.now()
            }
            
            if status:
                update_data['status'] = status.value
                if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    update_data['completed_at'] = datetime.now()
            
            if progress_percentage is not None:
                update_data['progress_percentage'] = progress_percentage
            
            if current_step:
                update_data['current_step'] = current_step
            
            if steps_completed is not None:
                update_data['steps_completed'] = steps_completed
            
            if total_steps is not None:
                update_data['total_steps'] = total_steps
            
            if output_data:
                update_data['output_data'] = output_data
            
            if error_message:
                update_data['error_message'] = error_message
            
            if not firebase_service.is_available():
                return await self._update_task_progress_local(task_id, update_data)
            
            db = firebase_service.get_firestore_client()
            task_ref = db.collection('tasks').document(task_id)
            task_ref.update(update_data)
            
            print(f"✅ Task {task_id} progress updated")
            return True
            
        except Exception as e:
            print(f"❌ Error updating task progress: {str(e)}")
            return False
    
    async def _update_task_progress_local(self, task_id: str, update_data: Dict[str, Any]) -> bool:
        """ローカルファイルのタスク進捗を更新"""
        try:
            import os
            import json
            
            task_file = os.path.join("local_tasks", f"{task_id}.json")
            if not os.path.exists(task_file):
                return False
            
            with open(task_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
            
            # 更新データをマージ
            for key, value in update_data.items():
                if isinstance(value, datetime):
                    task_data[key] = value.isoformat()
                else:
                    task_data[key] = value
            
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating local task progress: {str(e)}")
            return False
    
    async def get_user_tasks(self, user_id: str, limit: int = 50, offset: int = 0) -> List[TaskProgress]:
        """ユーザーのタスク一覧を取得"""
        try:
            if not firebase_service.is_available():
                return await self._get_user_tasks_local(user_id, limit, offset)
            
            db = firebase_service.get_firestore_client()
            query = db.collection('tasks')\
                     .where('user_id', '==', user_id)\
                     .order_by('created_at', direction='desc')\
                     .limit(limit)\
                     .offset(offset)
            
            docs = query.get()
            tasks = []
            for doc in docs:
                task_data = doc.to_dict()
                tasks.append(TaskProgress(**task_data))
            
            return tasks
            
        except Exception as e:
            print(f"❌ Error getting user tasks: {str(e)}")
            return []
    
    async def _get_user_tasks_local(self, user_id: str, limit: int = 50, offset: int = 0) -> List[TaskProgress]:
        """ローカルファイルからユーザーのタスク一覧を取得"""
        try:
            import os
            import json
            
            tasks_dir = "local_tasks"
            if not os.path.exists(tasks_dir):
                return []
            
            tasks = []
            for filename in os.listdir(tasks_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(tasks_dir, filename), 'r', encoding='utf-8') as f:
                            task_data = json.load(f)
                        
                        if task_data.get('user_id') == user_id:
                            # ISO文字列をdatetimeに変換
                            for key, value in task_data.items():
                                if key.endswith('_at') and isinstance(value, str):
                                    try:
                                        task_data[key] = datetime.fromisoformat(value)
                                    except ValueError:
                                        pass
                            
                            tasks.append(TaskProgress(**task_data))
                    except Exception:
                        continue
            
            # 作成日時でソート
            tasks.sort(key=lambda x: x.created_at, reverse=True)
            
            # ページネーション
            return tasks[offset:offset + limit]
            
        except Exception as e:
            print(f"❌ Error getting local user tasks: {str(e)}")
            return []
    
    async def cancel_task(self, task_id: str, user_id: str) -> bool:
        """タスクをキャンセル"""
        try:
            # 実行中のタスクがあれば停止
            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]
            
            # ステータスを更新
            return await self.update_task_progress(
                task_id=task_id,
                status=TaskStatus.CANCELLED
            )
            
        except Exception as e:
            print(f"❌ Error cancelling task: {str(e)}")
            return False
    
    async def execute_task_background(self, task_id: str, user_id: str, request: TaskRequest):
        """バックグラウンドでタスクを実行"""
        try:
            print(f"🚀 Starting background task execution: {task_id}")
            
            # タスクを実行中に更新
            await self.update_task_progress(
                task_id=task_id,
                status=TaskStatus.RUNNING,
                current_step="Initializing task execution"
            )
            
            # タスクタイプに応じて実行
            if request.task_type == TaskType.SIMPLE_CHAT:
                await self._execute_simple_chat(task_id, request)
            elif request.task_type == TaskType.PAPER_SCOUT:
                await self._execute_paper_scout(task_id, request)
            elif request.task_type == TaskType.REVIEW_CREATION:
                await self._execute_review_creation(task_id, request)
            else:
                raise ValueError(f"Unknown task type: {request.task_type}")
            
        except asyncio.CancelledError:
            print(f"⚠️ Task {task_id} was cancelled")
            await self.update_task_progress(
                task_id=task_id,
                status=TaskStatus.CANCELLED
            )
        except Exception as e:
            print(f"❌ Error in background task execution: {str(e)}")
            await self.update_task_progress(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_message=str(e)
            )
        finally:
            # 実行中タスクリストから削除
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    async def _execute_simple_chat(self, task_id: str, request: TaskRequest):
        """シンプルチャットタスクの実行（LangChainエージェント使用）"""
        try:
            from app.services.agent_base import agent_orchestrator
            
            await self.update_task_progress(
                task_id=task_id,
                current_step="Initializing chat agent",
                progress_percentage=10.0
            )
            
            # エージェントオーケストレータを使用してタスクを実行
            result = await agent_orchestrator.execute_task(
                task_id=task_id,
                agent_id="simple_chat",
                input_data=request.input_data,
                config=request.config
            )
            
            await self.update_task_progress(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                progress_percentage=100.0,
                steps_completed=1,
                total_steps=1,
                output_data=result
            )
            
        except Exception as e:
            raise Exception(f"Simple chat execution failed: {str(e)}")
    
    async def _execute_paper_scout(self, task_id: str, request: TaskRequest):
        """論文スカウトタスクの実行"""
        try:
            from app.services.agent_base import agent_orchestrator
            
            await self.update_task_progress(
                task_id=task_id,
                current_step="Initializing Paper Scout agent",
                progress_percentage=5.0
            )
            
            # エージェントオーケストレータを使用してタスクを実行
            result = await agent_orchestrator.execute_task(
                task_id=task_id,
                agent_id="paper_scout",
                input_data=request.input_data,
                config=request.config
            )
            
            await self.update_task_progress(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                progress_percentage=100.0,
                steps_completed=1,
                total_steps=1,
                output_data=result
            )
            
        except Exception as e:
            raise Exception(f"Paper scout execution failed: {str(e)}")
    
    async def _execute_review_creation(self, task_id: str, request: TaskRequest):
        """レビュー作成タスクの実行"""
        try:
            from app.services.agent_base import agent_orchestrator
            
            await self.update_task_progress(
                task_id=task_id,
                current_step="Initializing Review Creation multi-agent",
                progress_percentage=5.0
            )
            
            # エージェントオーケストレータを使用してタスクを実行
            result = await agent_orchestrator.execute_task(
                task_id=task_id,
                agent_id="review_creation",
                input_data=request.input_data,
                config=request.config
            )
            
            await self.update_task_progress(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                progress_percentage=100.0,
                steps_completed=1,
                total_steps=1,
                output_data=result
            )
            
        except Exception as e:
            raise Exception(f"Review creation execution failed: {str(e)}")
    
    async def stream_task_progress(self, task_id: str, user_id: str) -> AsyncGenerator[TaskProgress, None]:
        """タスク進捗のリアルタイムストリーミング"""
        try:
            last_update = None
            while True:
                current_progress = await self.get_task_progress(task_id, user_id)
                
                if not current_progress:
                    break
                
                # 変更があった場合のみ送信
                if last_update != current_progress.updated_at:
                    yield current_progress
                    last_update = current_progress.updated_at
                
                # 完了状態の場合はストリーミング終了
                if current_progress.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    break
                
                await asyncio.sleep(1)  # 1秒間隔でポーリング
                
        except Exception as e:
            print(f"❌ Error in stream_task_progress: {str(e)}")

# シングルトンインスタンス
task_service = TaskService()