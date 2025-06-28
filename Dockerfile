# 1. ベースイメージとして公式のPythonイメージを使用
FROM python:3.12-slim

# 2. 環境変数を設定
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. 作業ディレクトリを作成・設定
WORKDIR /app

# 4. 依存関係をインストール
# requirements.txtを先にコピーしてインストールすることで、コード変更時に毎回インストールが走るのを防ぐ
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. アプリケーションのコードをコピー
COPY ./app /app/app

# 6. uvicornがリッスンするポートを指定
EXPOSE 8080

# 7. アプリケーションを起動
# Cloud Runが環境変数PORTを自動で設定するため、そのポートでリッスンする
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
