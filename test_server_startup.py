#!/usr/bin/env python3
"""
サーバー起動テストスクリプト
フロントエンドとの通信をテストします
"""

import requests
import json
import time
import sys

def test_server_connection():
    """サーバー接続をテストします"""
    base_url = "http://localhost:8000"
    
    print("🚀 サーバー接続テストを開始...")
    print(f"   Base URL: {base_url}")
    
    try:
        # ヘルスチェック
        print("\n1. ヘルスチェック...")
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print("   ✅ ヘルスチェック成功")
            print(f"   📊 ステータス: {health_data.get('status')}")
            print(f"   🔧 サービス状況:")
            for service, status in health_data.get('services', {}).items():
                print(f"      {service}: {'✅' if status else '❌'}")
        else:
            print(f"   ❌ ヘルスチェック失敗: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ❌ サーバーに接続できません")
        print("\n🔧 解決方法:")
        print("   1. バックエンドサーバーが起動していることを確認してください")
        print("   2. ChatServer ディレクトリで以下を実行:")
        print("      cd ChatServer")
        print("      ./scripts/dev.sh")
        print("   3. または手動で起動:")
        print("      uv sync")
        print("      uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        return False
    except Exception as e:
        print(f"   ❌ 予期しないエラー: {str(e)}")
        return False
    
    try:
        # モデル一覧取得テスト
        print("\n2. モデル一覧取得テスト...")
        response = requests.get(f"{base_url}/api/models/", timeout=5)
        if response.status_code == 200:
            models = response.json()
            print(f"   ✅ モデル一覧取得成功 ({len(models)}個のモデル)")
            for model in models[:3]:  # 最初の3個だけ表示
                print(f"      - {model.get('name', 'Unknown')} ({model.get('provider', 'Unknown')})")
        else:
            print(f"   ⚠️ モデル一覧取得エラー: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ モデル一覧取得エラー: {str(e)}")
    
    try:
        # チャットエンドポイントテスト
        print("\n3. チャットエンドポイントテスト...")
        test_payload = {
            "message": "接続テストメッセージです",
            "model": {
                "id": "gemini-2-0-flash-001",
                "name": "Gemini 2.0 Flash",
                "provider": "google"
            },
            "history": []
        }
        
        response = requests.post(
            f"{base_url}/api/chat/send",
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            print("   ✅ チャットエンドポイント応答成功")
            data = response.json()
            content_length = len(data.get('content', ''))
            print(f"   📝 応答長: {content_length}文字")
        else:
            print(f"   ⚠️ チャットエンドポイントエラー: {response.status_code}")
            print(f"   📝 応答: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   ❌ チャットエンドポイントエラー: {str(e)}")
    
    print("\n✅ サーバー接続テスト完了")
    print("\n📱 フロントエンドの設定確認:")
    print("   1. ChatLLMApp/.env ファイルで以下を確認:")
    print("      EXPO_PUBLIC_API_URL=http://localhost:8000")
    print("   2. Expo開発サーバーを再起動:")
    print("      npm start")
    print("   3. ブラウザコンソールでネットワークリクエストを確認")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 ChatLLMApp サーバー接続テスト")
    print("=" * 60)
    
    success = test_server_connection()
    
    if success:
        print("\n🎉 テスト完了!")
        sys.exit(0)
    else:
        print("\n❌ テスト失敗")
        sys.exit(1)