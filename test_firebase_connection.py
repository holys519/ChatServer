#!/usr/bin/env python3
"""
Firebase接続テストスクリプト

このスクリプトは Firebase Firestore の接続をテストし、
基本的な読み書き操作が正常に動作することを確認します。

実行方法:
    cd ChatServer
    uv run python test_firebase_connection.py
"""

import sys
import os
from datetime import datetime

# プロジェクトのパスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.firebase_service import firebase_service
from app.services.firestore_session_service import firestore_session_service
from app.models.schemas import ChatSessionCreate, ChatMessage

def test_firebase_connection():
    """Firebase 接続をテスト"""
    print("🔥 Firebase 接続テストを開始します...")
    
    if not firebase_service.is_available():
        print("❌ Firebase service is not available")
        print("\n設定を確認してください:")
        print("1. .env ファイルで FIREBASE_ADMIN_SDK_PATH または FIREBASE_ADMIN_SDK_JSON を設定")
        print("2. FIREBASE_PROJECT_ID を設定")
        print("3. Firebase Admin SDK サービスアカウントキーを配置")
        return False
    
    print("✅ Firebase service is available")
    
    # 接続テスト
    print("\n📡 Firebase 接続テスト中...")
    try:
        db = firebase_service.get_db()
        if db is None:
            print("❌ Failed to get Firestore client")
            return False
        
        # テストドキュメントの作成
        test_ref = db.collection('test').document('connection_test')
        test_data = {
            'message': 'Firebase connection test successful',
            'timestamp': datetime.now(),
            'test_id': 'firebase_test_2025'
        }
        
        test_ref.set(test_data)
        print("✅ テストドキュメントの作成に成功")
        
        # ドキュメントの読み取り
        doc = test_ref.get()
        if doc.exists:
            data = doc.to_dict()
            print(f"✅ テストドキュメントの読み取りに成功: {data['message']}")
            
            # テストドキュメントの削除
            test_ref.delete()
            print("✅ テストドキュメントの削除に成功")
            
        else:
            print("❌ テストドキュメントが見つかりません")
            return False
            
    except Exception as e:
        print(f"❌ Firebase 接続テストに失敗: {e}")
        return False
    
    print("✅ Firebase 基本接続テスト完了")
    return True

async def test_session_service():
    """セッション管理サービスをテスト"""
    print("\n🗂️  セッション管理サービステストを開始...")
    
    try:
        test_user_id = "test_user_12345"
        
        # 1. セッション作成テスト
        print("📝 セッション作成テスト...")
        session_create = ChatSessionCreate(
            title="テストセッション",
            model_id="gemini-2-0-flash-001"
        )
        
        created_session = await firestore_session_service.create_session(test_user_id, session_create)
        print(f"✅ セッション作成成功: {created_session.id}")
        session_id = created_session.id
        
        # 2. セッション取得テスト
        print("📖 セッション取得テスト...")
        retrieved_session = await firestore_session_service.get_session(session_id, test_user_id)
        if retrieved_session:
            print(f"✅ セッション取得成功: {retrieved_session.title}")
        else:
            print("❌ セッション取得失敗")
            return False
        
        # 3. メッセージ追加テスト
        print("💬 メッセージ追加テスト...")
        test_message = ChatMessage(
            id="msg_001",
            content="これはテストメッセージです",
            is_user=True,
            timestamp=datetime.now()
        )
        
        updated_session = await firestore_session_service.add_message_to_session(
            session_id, test_user_id, test_message
        )
        if updated_session and len(updated_session.messages) > 0:
            print(f"✅ メッセージ追加成功: {len(updated_session.messages)} 件のメッセージ")
        else:
            print("❌ メッセージ追加失敗")
            return False
        
        # 4. ユーザーセッション一覧取得テスト
        print("📋 ユーザーセッション一覧取得テスト...")
        user_sessions = await firestore_session_service.get_user_sessions(test_user_id)
        print(f"✅ ユーザーセッション取得成功: {len(user_sessions)} 件のセッション")
        
        # 5. セッション削除テスト
        print("🗑️  セッション削除テスト...")
        delete_result = await firestore_session_service.delete_session(session_id, test_user_id)
        if delete_result:
            print("✅ セッション削除成功")
        else:
            print("❌ セッション削除失敗")
            return False
        
        print("✅ セッション管理サービステスト完了")
        return True
        
    except Exception as e:
        print(f"❌ セッション管理サービステスト失敗: {e}")
        return False

async def main():
    """メインテスト実行関数"""
    print("🧪 Firebase & Firestore 総合テスト")
    print("=" * 50)
    
    # 1. Firebase 基本接続テスト
    connection_ok = test_firebase_connection()
    
    if not connection_ok:
        print("\n❌ Firebase 基本接続テストに失敗しました")
        print("\n🔧 トラブルシューティング:")
        print("1. docs/firebase-setup.md を参照して設定を確認")
        print("2. Firebase プロジェクトが正しく設定されているか確認")
        print("3. サービスアカウントキーが正しく配置されているか確認")
        return False
    
    # 2. セッション管理サービステスト
    session_ok = await test_session_service()
    
    print("\n" + "=" * 50)
    if connection_ok and session_ok:
        print("🎉 すべてのテストが成功しました！")
        print("\n✅ Firebase Firestore の設定が正常に完了しています")
        print("✅ ChatServer でFirestore を使用してチャット履歴を保存できます")
        return True
    else:
        print("❌ 一部のテストが失敗しました")
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())