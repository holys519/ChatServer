#!/usr/bin/env python3
"""
シンプルなGoogle API接続テスト
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_simple():
    """シンプルなテスト"""
    print("=== シンプル Google API テスト ===")
    
    try:
        # 環境変数確認
        project = os.getenv('GOOGLE_CLOUD_PROJECT')
        creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        print(f"プロジェクト: {project}")
        print(f"認証ファイル: {creds}")
        
        if creds and os.path.exists(creds):
            print("✅ 認証ファイル存在")
        else:
            print("❌ 認証ファイルなし")
        
        # Vertex AI テスト
        import vertexai
        from vertexai.generative_models import GenerativeModel
        
        vertexai.init(project=project, location='us-central1')
        model = GenerativeModel('gemini-2.0-flash-001')
        # model = GenerativeModel('gemini-2.0-flash-lite-001')
        
        response = model.generate_content("Say hello")
        print(f"✅ 成功: {response.text}")
        
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

if __name__ == "__main__":
    test_simple()