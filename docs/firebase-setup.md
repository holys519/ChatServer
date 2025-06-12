# Firebase Setup Guide for ChatServer

このドキュメントでは、ChatServerバックエンドでFirebase Firestoreを使用してチャット履歴を永続化するための詳細な設定方法を説明します。

## 前提条件

- Google Cloud Platform（GCP）アカウント
- Firebase プロジェクトの作成権限
- Python 3.11+
- uv パッケージマネージャー

## 1. Firebase プロジェクトの作成

### 1.1 Firebase Console でプロジェクトを作成

1. [Firebase Console](https://console.firebase.google.com/) にアクセス
2. 「プロジェクトを追加」をクリック
3. プロジェクト名を入力（例: `chatllm-app`）
4. Google Analytics の設定（オプション）を完了
5. プロジェクトが作成されるまで待機

### 1.2 Cloud Firestore データベースの有効化

1. Firebase Console で作成したプロジェクトを選択
2. 左サイドバーから「Firestore Database」を選択
3. 「データベースの作成」をクリック
4. セキュリティルールの選択:
   - **本番環境**: 「本番環境モードで開始」を選択
   - **開発環境**: 「テストモードで開始」を選択（30日間の読み書き許可）
5. ロケーションを選択（例: `asia-northeast1` - Tokyo）
6. 「完了」をクリック

### 1.3 Firestore セキュリティルールの設定

Firestore の「ルール」タブで以下のルールを設定:

```javascript
rules_version = '2';

service cloud.firestore {
  match /databases/{database}/documents {
    // チャットセッションの読み書き権限
    match /chatSessions/{sessionId} {
      allow read, write: if request.auth != null && 
        request.auth.uid == resource.data.userId;
      allow create: if request.auth != null && 
        request.auth.uid == request.resource.data.userId;
    }
    
    // ユーザー情報の読み書き権限
    match /users/{userId} {
      allow read, write: if request.auth != null && 
        request.auth.uid == userId;
    }
  }
}
```

## 2. Firebase Admin SDK の設定

### 2.1 サービスアカウントキーの生成

1. Firebase Console で「プロジェクトの設定」（歯車アイコン）をクリック
2. 「サービス アカウント」タブを選択
3. 「Python」タブを確認し、「新しい秘密鍵の生成」をクリック
4. JSON ファイルがダウンロードされることを確認
5. このファイルを安全な場所に保存（例: `firebase-adminsdk-xxxxx.json`）

**重要**: このJSONファイルには機密情報が含まれているため、Gitリポジトリにコミットしないでください。

### 2.2 環境変数の設定

ChatServer ルートディレクトリに `.env` ファイルを作成し、以下を追加:

```env
# Firebase Admin SDK
FIREBASE_ADMIN_SDK_PATH=/path/to/your/firebase-adminsdk-xxxxx.json

# または、環境変数でJSON文字列を直接指定
FIREBASE_ADMIN_SDK_JSON='{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
  "client_email": "...",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "...",
  "client_x509_cert_url": "..."
}'

# Firebase プロジェクト設定
FIREBASE_PROJECT_ID=your-project-id

# 既存の設定
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_LOCATION=us-central1
```

## 3. Python依存関係の追加

### 3.1 pyproject.toml の更新

`pyproject.toml` の dependencies セクションに Firebase Admin SDK を追加:

```toml
dependencies = [
    "fastapi>=0.104.1",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
    "google-generativeai>=0.3.2",
    "google-cloud-aiplatform>=1.38.0",
    "firebase-admin>=6.5.0",  # 追加
    "openai>=1.3.0",
    "websockets>=12.0",
    "python-multipart>=0.0.6",
    "httpx>=0.25.0",
]
```

### 3.2 依存関係のインストール

```bash
cd ChatServer
uv sync
```

## 4. Firebase Firestore データ構造

### 4.1 コレクション構造

```
chatSessions/
├── {sessionId}/
│   ├── id: string
│   ├── title: string
│   ├── userId: string
│   ├── createdAt: timestamp
│   ├── updatedAt: timestamp
│   ├── modelId: string (optional)
│   └── messages: array[
│       {
│         id: string,
│         content: string,
│         isUser: boolean,
│         timestamp: timestamp
│       }
│     ]
```

### 4.2 インデックスの作成

Firestore Console で以下の複合インデックスを作成:

1. **ユーザーセッション取得用**:
   - コレクション: `chatSessions`
   - フィールド: `userId` (昇順), `updatedAt` (降順)

2. **メッセージ検索用**（オプション）:
   - コレクション: `chatSessions`
   - フィールド: `userId` (昇順), `messages.timestamp` (降順)

## 5. Firebase Configuration Service の実装

### 5.1 Firebase初期化サービス

```python
# app/services/firebase_service.py
import os
import json
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client

class FirebaseService:
    def __init__(self):
        self.db: Optional[Client] = None
        self._initialize()
    
    def _initialize(self):
        """Firebase Admin SDK を初期化"""
        try:
            # 既に初期化済みの場合はスキップ
            if firebase_admin._apps:
                self.db = firestore.client()
                return
            
            # 環境変数からサービスアカウント情報を取得
            firebase_config_path = os.getenv('FIREBASE_ADMIN_SDK_PATH')
            firebase_config_json = os.getenv('FIREBASE_ADMIN_SDK_JSON')
            
            if firebase_config_path and os.path.exists(firebase_config_path):
                # ファイルパスから初期化
                cred = credentials.Certificate(firebase_config_path)
            elif firebase_config_json:
                # JSON文字列から初期化
                service_account_info = json.loads(firebase_config_json)
                cred = credentials.Certificate(service_account_info)
            else:
                raise ValueError(
                    "Firebase configuration not found. "
                    "Set FIREBASE_ADMIN_SDK_PATH or FIREBASE_ADMIN_SDK_JSON"
                )
            
            # Firebase Admin SDKを初期化
            firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            
            print("Firebase Admin SDK initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize Firebase: {e}")
            self.db = None

# シングルトンインスタンス
firebase_service = FirebaseService()
```

## 6. 設定の検証

### 6.1 接続テスト

```python
# test_firebase_connection.py
from app.services.firebase_service import firebase_service

def test_firebase_connection():
    if firebase_service.db is None:
        print("❌ Firebase connection failed")
        return False
    
    try:
        # テストドキュメントの作成
        test_ref = firebase_service.db.collection('test').document('connection_test')
        test_ref.set({
            'message': 'Firebase connection successful',
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        # ドキュメントの読み取り
        doc = test_ref.get()
        if doc.exists:
            print("✅ Firebase connection successful")
            # テストドキュメントの削除
            test_ref.delete()
            return True
        else:
            print("❌ Test document not found")
            return False
            
    except Exception as e:
        print(f"❌ Firebase test failed: {e}")
        return False

if __name__ == "__main__":
    test_firebase_connection()
```

### 6.2 テストの実行

```bash
cd ChatServer
uv run python test_firebase_connection.py
```

## 7. トラブルシューティング

### 7.1 よくあるエラーと解決方法

#### エラー: "The default Firebase app does not exist"
```
解決方法:
1. FIREBASE_ADMIN_SDK_PATH または FIREBASE_ADMIN_SDK_JSON が正しく設定されているか確認
2. サービスアカウントキーファイルが存在し、読み取り可能か確認
3. JSON形式が正しいか確認
```

#### エラー: "Permission denied"
```
解決方法:
1. Firestore セキュリティルールを確認
2. プロジェクトID が正しいか確認
3. サービスアカウントに適切な権限があるか確認
```

#### エラー: "Project not found"
```
解決方法:
1. FIREBASE_PROJECT_ID が正しく設定されているか確認
2. Firebase プロジェクトが実際に存在するか確認
3. サービスアカウントが正しいプロジェクトのものか確認
```

### 7.2 ログレベルの設定

開発時のデバッグのため、詳細なログを有効にする:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Firebase固有のログ
import google.cloud.logging
client = google.cloud.logging.Client()
client.setup_logging()
```

## 8. セキュリティのベストプラクティス

### 8.1 本番環境での注意事項

1. **サービスアカウントキーの管理**:
   - 環境変数やクラウドシークレット管理サービスを使用
   - ファイルを直接サーバーに配置しない

2. **Firestore セキュリティルール**:
   - 本番環境では厳格なルールを設定
   - 定期的にルールを見直し

3. **アクセス制御**:
   - 最小権限の原則を適用
   - 不要な権限を付与しない

### 8.2 コスト最適化

1. **インデックスの最適化**:
   - 不要な複合インデックスを削除
   - クエリパターンに基づいてインデックスを作成

2. **データ構造の最適化**:
   - 大きなドキュメントを避ける
   - 適切なコレクション分割を行う

## 9. 次のステップ

1. Firebase Firestore を使用した session_service の実装
2. 認証システムとの統合
3. リアルタイムアップデートの実装（オプション）
4. バックアップ戦略の検討

この設定が完了したら、`app/services/session_service.py` をFirestore を使用するように更新できます。