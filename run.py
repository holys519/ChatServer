import uvicorn
import os
from dotenv import load_dotenv

# 環境変数を読み込む
load_dotenv()

if __name__ == "__main__":
    # デバッグモードの設定
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    # ホストとポートの設定
    host = os.getenv("HOST", "localhost")
    port = int(os.getenv("PORT", "8000"))
    
    print(f"Starting server in {'debug' if debug else 'production'} mode")
    print(f"Listening on {host}:{port}")
    
    # サーバー起動
    uvicorn.run(
        "app.main:app", 
        host=host, 
        port=port, 
        reload=debug
    )