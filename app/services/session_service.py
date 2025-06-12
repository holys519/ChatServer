import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
import os

from app.models.schemas import (
    ChatSession,
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionResponse,
    ChatMessage
)

# Firebase実装をインポート（利用可能な場合）
try:
    from app.services.firestore_session_service import firestore_session_service
    from app.services.firebase_service import firebase_service
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("Firebase dependencies not available, using local storage")

class SessionService:
    def __init__(self):
        """
        セッション管理サービス
        Firebase Firestore が利用可能な場合はFirestoreを使用
        そうでなければローカルストレージを使用
        """
        self.use_firestore = FIREBASE_AVAILABLE and firebase_service.is_available()
        
        if self.use_firestore:
            print("Using Firebase Firestore for session storage")
        else:
            print("Using local file storage for sessions")
            self.sessions: Dict[str, Dict[str, Any]] = {}
            self.data_file = "/tmp/chat_sessions.json"
            self._load_sessions()

    def _load_sessions(self):
        """保存されたセッションデータを読み込み"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 日付文字列をdatetimeオブジェクトに変換
                    for session_id, session_data in data.items():
                        session_data['created_at'] = datetime.fromisoformat(session_data['created_at'])
                        session_data['updated_at'] = datetime.fromisoformat(session_data['updated_at'])
                        for message in session_data.get('messages', []):
                            message['timestamp'] = datetime.fromisoformat(message['timestamp'])
                    self.sessions = data
        except Exception as e:
            print(f"Error loading sessions: {e}")
            self.sessions = {}

    def _save_sessions(self):
        """セッションデータを保存"""
        try:
            # datetimeオブジェクトを文字列に変換
            data_to_save = {}
            for session_id, session_data in self.sessions.items():
                session_copy = session_data.copy()
                session_copy['created_at'] = session_data['created_at'].isoformat()
                session_copy['updated_at'] = session_data['updated_at'].isoformat()
                session_copy['messages'] = []
                for message in session_data.get('messages', []):
                    message_copy = message.copy()
                    message_copy['timestamp'] = message['timestamp'].isoformat()
                    session_copy['messages'].append(message_copy)
                data_to_save[session_id] = session_copy

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving sessions: {e}")

    async def get_user_sessions(self, user_id: str) -> List[ChatSessionResponse]:
        """ユーザーのチャットセッション一覧を取得"""
        if self.use_firestore:
            return await firestore_session_service.get_user_sessions(user_id)
        
        # ローカルストレージの実装
        user_sessions = []
        for session_id, session_data in self.sessions.items():
            if session_data.get('user_id') == user_id:
                user_sessions.append(ChatSessionResponse(
                    id=session_id,
                    title=session_data['title'],
                    created_at=session_data['created_at'],
                    updated_at=session_data['updated_at'],
                    messages=[
                        ChatMessage(**message) for message in session_data.get('messages', [])
                    ],
                    model_id=session_data.get('model_id')
                ))
        
        # 更新日時で降順ソート
        user_sessions.sort(key=lambda x: x.updated_at, reverse=True)
        return user_sessions

    async def create_session(self, user_id: str, session_data: ChatSessionCreate) -> ChatSessionResponse:
        """新しいチャットセッションを作成"""
        if self.use_firestore:
            return await firestore_session_service.create_session(user_id, session_data)
        
        # ローカルストレージの実装
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        new_session = {
            'id': session_id,
            'title': session_data.title,
            'user_id': user_id,
            'created_at': now,
            'updated_at': now,
            'messages': [],
            'model_id': session_data.model_id
        }
        
        self.sessions[session_id] = new_session
        self._save_sessions()
        
        return ChatSessionResponse(
            id=session_id,
            title=new_session['title'],
            created_at=new_session['created_at'],
            updated_at=new_session['updated_at'],
            messages=[],
            model_id=new_session['model_id']
        )

    async def get_session(self, session_id: str, user_id: str) -> Optional[ChatSessionResponse]:
        """特定のチャットセッションを取得"""
        if self.use_firestore:
            return await firestore_session_service.get_session(session_id, user_id)
        
        # ローカルストレージの実装
        session_data = self.sessions.get(session_id)
        if not session_data or session_data.get('user_id') != user_id:
            return None
        
        return ChatSessionResponse(
            id=session_id,
            title=session_data['title'],
            created_at=session_data['created_at'],
            updated_at=session_data['updated_at'],
            messages=[
                ChatMessage(**message) for message in session_data.get('messages', [])
            ],
            model_id=session_data.get('model_id')
        )

    async def update_session(
        self, 
        session_id: str, 
        user_id: str, 
        session_data: ChatSessionUpdate
    ) -> Optional[ChatSessionResponse]:
        """チャットセッションを更新"""
        if self.use_firestore:
            return await firestore_session_service.update_session(session_id, user_id, session_data)
        
        # ローカルストレージの実装
        existing_session = self.sessions.get(session_id)
        if not existing_session or existing_session.get('user_id') != user_id:
            return None
        
        # 更新可能なフィールドのみ更新
        if session_data.title is not None:
            existing_session['title'] = session_data.title
        if session_data.model_id is not None:
            existing_session['model_id'] = session_data.model_id
        
        existing_session['updated_at'] = datetime.now()
        self._save_sessions()
        
        return ChatSessionResponse(
            id=session_id,
            title=existing_session['title'],
            created_at=existing_session['created_at'],
            updated_at=existing_session['updated_at'],
            messages=[
                ChatMessage(**message) for message in existing_session.get('messages', [])
            ],
            model_id=existing_session.get('model_id')
        )

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """チャットセッションを削除"""
        if self.use_firestore:
            return await firestore_session_service.delete_session(session_id, user_id)
        
        # ローカルストレージの実装
        session_data = self.sessions.get(session_id)
        if not session_data or session_data.get('user_id') != user_id:
            return False
        
        del self.sessions[session_id]
        self._save_sessions()
        return True

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
        if self.use_firestore:
            return await firestore_session_service.add_message_to_session(session_id, user_id, message)
        
        # ローカルストレージの実装
        session_data = self.sessions.get(session_id)
        if not session_data or session_data.get('user_id') != user_id:
            return None
        
        # メッセージを辞書形式で保存
        message_dict = {
            'id': message.id,
            'content': message.content,
            'is_user': message.is_user,
            'timestamp': message.timestamp
        }
        
        # 最初のユーザーメッセージの場合、セッションタイトルを更新
        if message.is_user and len(session_data.get('messages', [])) == 0:
            session_data['title'] = self._generate_title_from_message(message.content)
        
        session_data['messages'].append(message_dict)
        session_data['updated_at'] = datetime.now()
        self._save_sessions()
        
        return ChatSessionResponse(
            id=session_id,
            title=session_data['title'],
            created_at=session_data['created_at'],
            updated_at=session_data['updated_at'],
            messages=[
                ChatMessage(**msg) for msg in session_data['messages']
            ],
            model_id=session_data.get('model_id')
        )

# シングルトンインスタンス
session_service = SessionService()