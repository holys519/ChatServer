# 1. ベースイメージとして公式のPythonイメージを使用
FROM python:3.12-slim

# 2. 環境変数を設定
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. 作業ディレクトリを作成・設定
WORKDIR /app

# 4. 依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 非rootユーザーを作成
RUN useradd -m appuser

# 6. アプリケーションのコードをコピーし、所有者を変更
COPY --chown=appuser:appuser ./app /app/app

# 7. ユーザーを切り替え
USER appuser

# 8. uvicornがリッスンするポートを指定
EXPOSE 8080

# 9. アプリケーションを起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]