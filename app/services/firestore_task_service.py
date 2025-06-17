from typing import Dict, List, Optional, Any
from datetime import datetime
from google.cloud import firestore
from app.models.schemas import TaskProgress, TaskStatus, TaskType, AgentStep
from app.services.firebase_service import firebase_service

class FirestoreTaskService:
    """Firestore specific task management service"""
    
    def __init__(self):
        self.db = None
        if firebase_service.is_available():
            self.db = firebase_service.get_firestore_client()
    
    def create_task_document(self, task_progress: TaskProgress) -> bool:
        """Create a new task document in Firestore"""
        if not self.db:
            return False
        
        try:
            task_ref = self.db.collection('tasks').document(task_progress.task_id)
            
            # Convert TaskProgress to Firestore-compatible dict
            task_data = self._task_to_firestore_dict(task_progress)
            
            task_ref.set(task_data)
            print(f"✅ Task document created: {task_progress.task_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating task document: {str(e)}")
            return False
    
    def update_task_document(self, task_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a task document in Firestore"""
        if not self.db:
            return False
        
        try:
            task_ref = self.db.collection('tasks').document(task_id)
            
            # Add timestamp
            firestore_data = {
                **update_data,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            task_ref.update(firestore_data)
            print(f"✅ Task document updated: {task_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating task document: {str(e)}")
            return False
    
    def get_task_document(self, task_id: str, user_id: str) -> Optional[TaskProgress]:
        """Get a task document from Firestore"""
        if not self.db:
            return None
        
        try:
            task_ref = self.db.collection('tasks').document(task_id)
            task_doc = task_ref.get()
            
            if not task_doc.exists:
                return None
            
            task_data = task_doc.to_dict()
            
            # Verify user access
            if task_data.get('user_id') != user_id:
                return None
            
            return self._firestore_dict_to_task(task_data)
            
        except Exception as e:
            print(f"❌ Error getting task document: {str(e)}")
            return None
    
    def list_user_tasks(
        self, 
        user_id: str, 
        limit: int = 50, 
        offset: int = 0,
        status_filter: Optional[TaskStatus] = None,
        task_type_filter: Optional[TaskType] = None
    ) -> List[TaskProgress]:
        """List tasks for a specific user with optional filters"""
        if not self.db:
            return []
        
        try:
            query = self.db.collection('tasks')\
                         .where('user_id', '==', user_id)\
                         .order_by('created_at', direction=firestore.Query.DESCENDING)\
                         .limit(limit)\
                         .offset(offset)
            
            # Add status filter if provided
            if status_filter:
                query = query.where('status', '==', status_filter.value)
            
            # Add task type filter if provided
            if task_type_filter:
                query = query.where('task_type', '==', task_type_filter.value)
            
            docs = query.get()
            tasks = []
            
            for doc in docs:
                task_data = doc.to_dict()
                task_progress = self._firestore_dict_to_task(task_data)
                if task_progress:
                    tasks.append(task_progress)
            
            return tasks
            
        except Exception as e:
            print(f"❌ Error listing user tasks: {str(e)}")
            return []
    
    def create_agent_step(self, agent_step: AgentStep) -> bool:
        """Create an agent step document in Firestore"""
        if not self.db:
            return False
        
        try:
            step_ref = self.db.collection('tasks')\
                            .document(agent_step.task_id)\
                            .collection('steps')\
                            .document(agent_step.step_id)
            
            step_data = self._agent_step_to_firestore_dict(agent_step)
            
            step_ref.set(step_data)
            print(f"✅ Agent step created: {agent_step.step_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating agent step: {str(e)}")
            return False
    
    def update_agent_step(self, task_id: str, step_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an agent step document in Firestore"""
        if not self.db:
            return False
        
        try:
            step_ref = self.db.collection('tasks')\
                            .document(task_id)\
                            .collection('steps')\
                            .document(step_id)
            
            firestore_data = {
                **update_data,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            step_ref.update(firestore_data)
            print(f"✅ Agent step updated: {step_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating agent step: {str(e)}")
            return False
    
    def get_task_steps(self, task_id: str) -> List[AgentStep]:
        """Get all agent steps for a task"""
        if not self.db:
            return []
        
        try:
            steps_ref = self.db.collection('tasks')\
                             .document(task_id)\
                             .collection('steps')\
                             .order_by('started_at')
            
            docs = steps_ref.get()
            steps = []
            
            for doc in docs:
                step_data = doc.to_dict()
                agent_step = self._firestore_dict_to_agent_step(step_data)
                if agent_step:
                    steps.append(agent_step)
            
            return steps
            
        except Exception as e:
            print(f"❌ Error getting task steps: {str(e)}")
            return []
    
    def _task_to_firestore_dict(self, task_progress: TaskProgress) -> Dict[str, Any]:
        """Convert TaskProgress to Firestore-compatible dictionary"""
        task_dict = task_progress.dict()
        
        # Convert datetime objects to Firestore Timestamps
        for key, value in task_dict.items():
            if isinstance(value, datetime):
                task_dict[key] = value
        
        return task_dict
    
    def _firestore_dict_to_task(self, task_data: Dict[str, Any]) -> Optional[TaskProgress]:
        """Convert Firestore dictionary to TaskProgress"""
        try:
            # Convert Firestore Timestamps to datetime objects
            for key, value in task_data.items():
                if hasattr(value, 'timestamp'):  # Firestore Timestamp
                    task_data[key] = value.to_datetime()
            
            return TaskProgress(**task_data)
            
        except Exception as e:
            print(f"❌ Error converting Firestore data to TaskProgress: {str(e)}")
            return None
    
    def _agent_step_to_firestore_dict(self, agent_step: AgentStep) -> Dict[str, Any]:
        """Convert AgentStep to Firestore-compatible dictionary"""
        step_dict = agent_step.dict()
        
        # Convert datetime objects to Firestore Timestamps
        for key, value in step_dict.items():
            if isinstance(value, datetime):
                step_dict[key] = value
        
        return step_dict
    
    def _firestore_dict_to_agent_step(self, step_data: Dict[str, Any]) -> Optional[AgentStep]:
        """Convert Firestore dictionary to AgentStep"""
        try:
            # Convert Firestore Timestamps to datetime objects
            for key, value in step_data.items():
                if hasattr(value, 'timestamp'):  # Firestore Timestamp
                    step_data[key] = value.to_datetime()
            
            return AgentStep(**step_data)
            
        except Exception as e:
            print(f"❌ Error converting Firestore data to AgentStep: {str(e)}")
            return None
    
    def cleanup_old_tasks(self, days_old: int = 30) -> int:
        """Clean up tasks older than specified days"""
        if not self.db:
            return 0
        
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Query old completed tasks
            query = self.db.collection('tasks')\
                         .where('status', 'in', ['completed', 'failed', 'cancelled'])\
                         .where('created_at', '<', cutoff_date)\
                         .limit(100)  # Process in batches
            
            docs = query.get()
            deleted_count = 0
            
            batch = self.db.batch()
            for doc in docs:
                batch.delete(doc.reference)
                deleted_count += 1
            
            if deleted_count > 0:
                batch.commit()
                print(f"✅ Cleaned up {deleted_count} old tasks")
            
            return deleted_count
            
        except Exception as e:
            print(f"❌ Error cleaning up old tasks: {str(e)}")
            return 0

# Singleton instance
firestore_task_service = FirestoreTaskService()