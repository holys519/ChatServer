#!/usr/bin/env python3
"""
Google API接続テストスクリプト
Vertex AI と Google Generative AI の両方をテストします
"""

import os
import asyncio
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

def test_environment_variables():
    """環境変数の設定を確認"""
    print("=== 環境変数の確認 ===")
    
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
    
    print(f"GOOGLE_CLOUD_PROJECT: {project_id}")
    print(f"GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")
    print(f"VERTEX_AI_LOCATION: {location}")
    
    # 認証ファイルの存在確認
    if creds_path and os.path.exists(creds_path):
        print(f"✅ 認証ファイルが存在します: {creds_path}")
        return True
    else:
        print(f"❌ 認証ファイルが見つかりません: {creds_path}")
        return False

def test_vertex_ai():
    """Vertex AI接続テスト"""
    print("\n=== Vertex AI 接続テスト ===")
    
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
        
        if not project_id:
            print("❌ GOOGLE_CLOUD_PROJECT が設定されていません")
            return False
        
        # Vertex AI初期化
        print(f"Vertex AI初期化中... (Project: {project_id}, Location: {location})")
        vertexai.init(project=project_id, location=location)
        
        # モデル作成テスト
        model = GenerativeModel('gemini-2.0-flash-001')
        print("✅ Vertex AI接続成功")
        
        # 簡単なテストメッセージ
        print("テストメッセージ送信中...")
        response = model.generate_content("Hello, this is a test message. Please respond briefly.")
        print(f"✅ Gemini応答: {response.text[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Vertex AI接続エラー: {str(e)}")
        return False

def test_google_generativeai():
    """Google Generative AI直接接続テスト"""
    print("\n=== Google Generative AI 直接接続テスト ===")
    
    try:
        import google.generativeai as genai
        
        # API Keyを確認
        api_key = os.getenv('GOOGLE_CLOUD_API_KEY')
        if not api_key or api_key == 'your_google_cloud_api_key_here':
            print("❌ GOOGLE_CLOUD_API_KEY が設定されていません")
            return False
        
        # API Key設定
        genai.configure(api_key=api_key)
        
        # モデル一覧取得テスト
        print("利用可能なモデル一覧取得中...")
        models = list(genai.list_models())
        if models:
            print(f"✅ 利用可能なモデル数: {len(models)}")
            for model in models[:3]:  # 最初の3つを表示
                print(f"  - {model.name}")
        
        # テストメッセージ送信
        print("テストメッセージ送信中...")
        model = genai.GenerativeModel('gemini-2.0-flash-001')
        response = model.generate_content("Hello, this is a test. Please respond briefly.")
        print(f"✅ Gemini応答: {response.text[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Google Generative AI接続エラー: {str(e)}")
        return False

async def test_gemini_service():
    """Gemini Serviceクラスのテスト"""
    print("\n=== Gemini Service クラステスト ===")
    
    try:
        from app.services.gemini_service import gemini_service
        
        # 初期化状態確認
        print(f"Gemini Service初期化状態: {gemini_service.initialized}")
        
        if not gemini_service.initialized:
            print("❌ Gemini Serviceが初期化されていません")
            return False
        
        # テストメッセージ送信
        print("テストメッセージ送信中...")
        response = await gemini_service.send_message(
            model_name="gemini-2.0-flash-001",
            history=[],
            message="Hello, this is a test message from the service class."
        )
        
        print(f"✅ Gemini Service応答: {response[:100]}...")
        
        # ストリーミングテスト
        print("ストリーミングテスト中...")
        chunks = []
        async for chunk in gemini_service.stream_chat(
            model_name="gemini-2.0-flash-001",
            history=[],
            message="Count from 1 to 5."
        ):
            chunks.append(chunk)
            if len(chunks) > 10:  # 最初の10チャンクのみ
                break
        
        print(f"✅ ストリーミング成功: {len(chunks)} チャンク受信")
        
        return True
        
    except Exception as e:
        print(f"❌ Gemini Service エラー: {str(e)}")
        return False

async def main():
    """メインテスト関数"""
    print("🚀 Google API 接続テスト開始\n")
    
    # 1. 環境変数チェック
    env_ok = test_environment_variables()
    
    # 2. Vertex AI テスト
    vertex_ok = test_vertex_ai()
    
    # 3. Google Generative AI 直接テスト
    genai_ok = test_google_generativeai()
    
    # 4. Gemini Service テスト
    service_ok = await test_gemini_service()
    
    # 結果サマリー
    print("\n" + "="*50)
    print("🔍 テスト結果サマリー")
    print("="*50)
    print(f"環境変数設定: {'✅' if env_ok else '❌'}")
    print(f"Vertex AI: {'✅' if vertex_ok else '❌'}")
    print(f"Google Generative AI: {'✅' if genai_ok else '❌'}")
    print(f"Gemini Service: {'✅' if service_ok else '❌'}")
    
    if vertex_ok or genai_ok:
        print("\n🎉 Google API接続成功！ChatServerで利用可能です。")
    else:
        print("\n❌ Google API接続に問題があります。設定を確認してください。")
        
        print("\n📝 対処方法:")
        if not env_ok:
            print("1. Google Cloud認証ファイルパスを確認")
            print("2. GOOGLE_CLOUD_PROJECT を正しく設定")
        if not genai_ok:
            print("3. GOOGLE_CLOUD_API_KEY を設定 (代替手段)")
        print("4. Google Cloud SDKでログイン: gcloud auth application-default login")

if __name__ == "__main__":
    asyncio.run(main())