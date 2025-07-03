# import os
# import json
# from typing import Optional
# import firebase_admin
# from firebase_admin import credentials, firestore
# from google.cloud.firestore import Client

# class FirebaseService:
#     def __init__(self):
#         self.db: Optional[Client] = None
#         self.initialized = False
#         self._initialize()
    
#     def _initialize(self):
#         """Firebase Admin SDK を初期化"""
#         try:
#             # 既に初期化済みの場合はスキップ
#             if firebase_admin._apps:
#                 self.db = firestore.client()
#                 self.initialized = True
#                 print("Firebase Admin SDK already initialized")
#                 return
            
#             # 環境変数からサービスアカウント情報を取得
#             firebase_config_path = os.getenv('FIREBASE_ADMIN_SDK_PATH')
#             firebase_config_json = os.getenv('FIREBASE_ADMIN_SDK_JSON')
#             project_id = os.getenv('FIREBASE_PROJECT_ID')
            
#             if firebase_config_path and os.path.exists(firebase_config_path):
#                 # ファイルパスから初期化
#                 print(f"Initializing Firebase from file: {firebase_config_path}")
#                 cred = credentials.Certificate(firebase_config_path)
#             elif firebase_config_json:
#                 # JSON文字列から初期化
#                 print("Initializing Firebase from JSON environment variable")
#                 service_account_info = json.loads(firebase_config_json)
#                 cred = credentials.Certificate(service_account_info)
#             else:
#                 print("Warning: Firebase configuration not found. Using default credentials if available.")
#                 # デフォルト認証情報を使用（Google Cloud環境で実行する場合）
#                 try:
#                     cred = credentials.ApplicationDefault()
#                 except Exception as e:
#                     print(f"Failed to use default credentials: {e}")
#                     raise ValueError(
#                         "Firebase configuration not found. "
#                         "Set FIREBASE_ADMIN_SDK_PATH, FIREBASE_ADMIN_SDK_JSON, or configure default credentials"
#                     )
            
#             # Firebase Admin SDKを初期化
#             firebase_admin.initialize_app(cred, {
#                 'projectId': project_id
#             } if project_id else None)
            
#             self.db = firestore.client()
#             self.initialized = True
            
#             print("Firebase Admin SDK initialized successfully")
            
#         except Exception as e:
#             print(f"Failed to initialize Firebase: {e}")
#             self.db = None
#             self.initialized = False

#     def get_db(self) -> Optional[Client]:
#         """Firestore クライアントを取得"""
#         return self.db
    
#     def get_firestore_client(self) -> Optional[Client]:
#         """Firestore クライアントを取得 (alias for get_db)"""
#         return self.get_db()

#     def is_available(self) -> bool:
#         """Firebase サービスが利用可能かどうかを確認"""
#         return self.initialized and self.db is not None

#     async def test_connection(self) -> bool:
#         """Firebase 接続をテスト"""
#         if not self.is_available():
#             return False
        
#         try:
#             # テストドキュメントの作成
#             test_ref = self.db.collection('test').document('connection_test')
#             test_ref.set({
#                 'message': 'Firebase connection test',
#                 'timestamp': firestore.SERVER_TIMESTAMP
#             })
            
#             # ドキュメントの読み取り
#             doc = test_ref.get()
#             if doc.exists:
#                 # テストドキュメントの削除
#                 test_ref.delete()
#                 print("✅ Firebase connection test successful")
#                 return True
#             else:
#                 print("❌ Firebase test document not found")
#                 return False
                
#         except Exception as e:
#             print(f"❌ Firebase connection test failed: {e}")
#             return False

# # シングルトンインスタンス
# firebase_service = FirebaseService()

import os
import json
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client

class FirebaseService:
    def __init__(self):
        self.db: Optional[Client] = None
        self.initialized = False
        self._initialize()

    def _initialize(self):
        """
        Firebase Admin SDKを初期化します。
        本番環境（Cloud Run）とローカル開発環境を自動で判別します。
        """
        try:
            # 既に初期化済みの場合は何もしない
            if firebase_admin._apps:
                self.db = firestore.client()
                self.initialized = True
                print("Firebase Admin SDK already initialized.")
                return

            # Cloud RunなどのGoogle Cloud環境で実行されているかを確認
            # K_SERVICE環境変数はCloud Runによって自動で設定されます
            is_production = os.getenv('K_SERVICE') is not None

            cred: credentials.Base
            project_id = os.getenv('FIREBASE_PROJECT_ID')

            if is_production:
                # --- 本番環境（Cloud Run）用の設定 ---
                # 鍵ファイルは使わず、割り当てられたサービスアカウントを自動で使用します
                print("Initializing Firebase for Production (Cloud Run)...")
                cred = credentials.ApplicationDefault()
                if not project_id:
                    # 本番環境ではプロジェクトIDが必須
                    raise ValueError("FIREBASE_PROJECT_ID environment variable is not set for production.")
            else:
                # --- ローカル開発環境用の設定 ---
                # ローカルの鍵ファイルパスを環境変数から取得します
                firebase_config_path = os.getenv('FIREBASE_ADMIN_SDK_PATH')
                print(f"Initializing Firebase for Local Development from: {firebase_config_path}")
                if not firebase_config_path or not os.path.exists(firebase_config_path):
                    raise ValueError(
                        "Local development environment requires FIREBASE_ADMIN_SDK_PATH "
                        "to be set to a valid service account key file path."
                    )
                cred = credentials.Certificate(firebase_config_path)

            # Firebase Admin SDKを初期化
            firebase_admin.initialize_app(cred, {
                'projectId': project_id
            })

            self.db = firestore.client()
            self.initialized = True
            print("✅ Firebase Admin SDK initialized successfully.")

        except Exception as e:
            print(f"❌ Failed to initialize Firebase: {e}")
            self.db = None
            self.initialized = False

    def get_db(self) -> Optional[Client]:
        """Firestore クライアントを取得"""
        return self.db

    def get_firestore_client(self) -> Optional[Client]:
        """Firestore クライアントを取得 (alias for get_db)"""
        return self.get_db()

    def is_available(self) -> bool:
        """Firebase サービスが利用可能かどうかを確認"""
        return self.initialized and self.db is not None

    async def test_connection(self) -> bool:
        """Firebase 接続をテスト"""
        if not self.is_available():
            return False
        
        try:
            # テストドキュメントの作成
            test_ref = self.db.collection('__test__').document('connection_test')
            test_ref.set({'timestamp': firestore.SERVER_TIMESTAMP})
            
            # ドキュメントの読み取り
            doc = test_ref.get()
            if doc.exists:
                test_ref.delete()
                print("✅ Firebase connection test successful")
                return True
            else:
                print("❌ Firebase test document not found")
                return False
                
        except Exception as e:
            print(f"❌ Firebase connection test failed: {e}")
            return False

# シングルトンインスタンス
firebase_service = FirebaseService()
