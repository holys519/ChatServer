import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from firebase_admin import firestore

from app.models.schemas import (
    ChatSession,
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionResponse,
    ChatMessage
)
from app.services.firebase_service import firebase_service

class FirestoreSessionService:
    def __init__(self):
        """
        Firebase Firestore を使用するセッション管理サービス
        """
        self.collection_name = 'chatSessions'

    def _get_db(self):
        """Firestore クライアントを取得"""
        if not firebase_service.is_available():
            raise RuntimeError("Firebase service is not available")
        return firebase_service.get_db()

    def _convert_firestore_timestamp(self, timestamp):
        """Firestore のタイムスタンプを datetime に変換"""
        if hasattr(timestamp, 'timestamp'):
            return datetime.fromtimestamp(timestamp.timestamp())
        elif isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif isinstance(timestamp, datetime):
            return timestamp
        else:
            return datetime.now()

    def _session_to_dict(self, session_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Firestore ドキュメントを辞書形式に変換"""
        return {
            'id': session_id,
            'title': session_data.get('title', ''),
            'user_id': session_data.get('userId', ''),
            'created_at': self._convert_firestore_timestamp(session_data.get('createdAt')),
            'updated_at': self._convert_firestore_timestamp(session_data.get('updatedAt')),
            'messages': [
                {
                    'id': msg.get('id', ''),
                    'content': msg.get('content', ''),
                    'is_user': msg.get('isUser', False),
                    'timestamp': self._convert_firestore_timestamp(msg.get('timestamp'))
                }
                for msg in session_data.get('messages', [])
            ],
            'model_id': session_data.get('modelId')
        }

    async def get_user_sessions(self, user_id: str) -> List[ChatSessionResponse]:
        """ユーザーのチャットセッション一覧を取得"""
        try:
            db = self._get_db()
            sessions_ref = db.collection(self.collection_name)
            query = sessions_ref.where('userId', '==', user_id).order_by('updatedAt', direction=firestore.Query.DESCENDING)
            
            docs = query.get()
            
            user_sessions = []
            for doc in docs:
                session_data = doc.to_dict()
                session_dict = self._session_to_dict(session_data, doc.id)
                
                user_sessions.append(ChatSessionResponse(
                    id=session_dict['id'],
                    title=session_dict['title'],
                    created_at=session_dict['created_at'],
                    updated_at=session_dict['updated_at'],
                    messages=[
                        ChatMessage(**message) for message in session_dict['messages']
                    ],
                    model_id=session_dict['model_id']
                ))
            
            return user_sessions
            
        except Exception as e:
            print(f"Error getting user sessions: {e}")
            raise

    async def create_session(self, user_id: str, session_data: ChatSessionCreate) -> ChatSessionResponse:
        """新しいチャットセッションを作成"""
        try:
            db = self._get_db()
            session_id = str(uuid.uuid4())
            now = datetime.now()
            
            new_session_data = {
                'title': session_data.title,
                'userId': user_id,
                'createdAt': now,
                'updatedAt': now,
                'messages': [],
                'modelId': session_data.model_id
            }
            
            # Firestoreにドキュメントを作成
            doc_ref = db.collection(self.collection_name).document(session_id)
            doc_ref.set(new_session_data)
            
            return ChatSessionResponse(
                id=session_id,
                title=new_session_data['title'],
                created_at=new_session_data['createdAt'],
                updated_at=new_session_data['updatedAt'],
                messages=[],
                model_id=new_session_data['modelId']
            )
            
        except Exception as e:
            print(f"Error creating session: {e}")
            raise

    async def get_session(self, session_id: str, user_id: str) -> Optional[ChatSessionResponse]:
        """特定のチャットセッションを取得"""
        try:
            db = self._get_db()
            doc_ref = db.collection(self.collection_name).document(session_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            session_data = doc.to_dict()
            
            # ユーザーIDの確認
            if session_data.get('userId') != user_id:
                return None
            
            session_dict = self._session_to_dict(session_data, session_id)
            
            return ChatSessionResponse(
                id=session_dict['id'],
                title=session_dict['title'],
                created_at=session_dict['created_at'],
                updated_at=session_dict['updated_at'],
                messages=[
                    ChatMessage(**message) for message in session_dict['messages']
                ],
                model_id=session_dict['model_id']
            )
            
        except Exception as e:
            print(f"Error getting session: {e}")
            raise

    async def update_session(
        self, 
        session_id: str, 
        user_id: str, 
        session_data: ChatSessionUpdate
    ) -> Optional[ChatSessionResponse]:
        """チャットセッションを更新"""
        try:
            db = self._get_db()
            doc_ref = db.collection(self.collection_name).document(session_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            existing_data = doc.to_dict()
            
            # ユーザーIDの確認
            if existing_data.get('userId') != user_id:
                return None
            
            # 更新データの準備
            update_data = {
                'updatedAt': datetime.now()
            }
            
            if session_data.title is not None:
                update_data['title'] = session_data.title
            if session_data.model_id is not None:
                update_data['modelId'] = session_data.model_id
            
            # ドキュメントを更新
            doc_ref.update(update_data)
            
            # 更新後のドキュメントを取得
            updated_doc = doc_ref.get()
            updated_data = updated_doc.to_dict()
            session_dict = self._session_to_dict(updated_data, session_id)
            
            return ChatSessionResponse(
                id=session_dict['id'],
                title=session_dict['title'],
                created_at=session_dict['created_at'],
                updated_at=session_dict['updated_at'],
                messages=[
                    ChatMessage(**message) for message in session_dict['messages']
                ],
                model_id=session_dict['model_id']
            )
            
        except Exception as e:
            print(f"Error updating session: {e}")
            raise

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """チャットセッションを削除"""
        try:
            db = self._get_db()
            doc_ref = db.collection(self.collection_name).document(session_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            session_data = doc.to_dict()
            
            # ユーザーIDの確認
            if session_data.get('userId') != user_id:
                return False
            
            # ドキュメントを削除
            doc_ref.delete()
            return True
            
        except Exception as e:
            print(f"Error deleting session: {e}")
            raise

    def _generate_title_from_message(self, message: str) -> str:
        """ユーザーメッセージからタイトルを生成"""
        # メッセージが長い場合は最初の50文字で切り詰める
        if len(message) > 50:
            return message[:47] + "..."
        return message

    async def add_message_to_session(
        self, 
        session_id: str, 
        user_id: str, 
        message: ChatMessage
    ) -> Optional[ChatSessionResponse]:
        """チャットセッションにメッセージを追加"""
        try:
            db = self._get_db()
            doc_ref = db.collection(self.collection_name).document(session_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            session_data = doc.to_dict()
            
            # ユーザーIDの確認
            if session_data.get('userId') != user_id:
                return None
            
            # 新しいメッセージを追加
            new_message = {
                'id': message.id,
                'content': message.content,
                'isUser': message.is_user,
                'timestamp': message.timestamp
            }
            
            # 既存のメッセージリストに追加
            messages = session_data.get('messages', [])
            messages.append(new_message)
            
            # ドキュメントを更新
            update_data = {
                'messages': messages,
                'updatedAt': datetime.now()
            }
            
            # 最初のユーザーメッセージの場合、セッションタイトルを更新
            if message.is_user and len(messages) == 1:  # 追加後のメッセージ数が1の場合
                update_data['title'] = self._generate_title_from_message(message.content)
            
            doc_ref.update(update_data)
            
            # 更新後のセッションを取得
            return await self.get_session(session_id, user_id)
            
        except Exception as e:
            print(f"Error adding message to session: {e}")
            raise

# Firestore セッションサービスのインスタンス
firestore_session_service = FirestoreSessionService()