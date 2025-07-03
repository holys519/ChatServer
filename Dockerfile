# 1. ベースイメージとして公式のPythonイメージを使用
FROM python:3.12-slim

# 2. 環境変数を設定
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 8080

# 3. 作業ディレクトリを作成・設定
WORKDIR /app

# 4. 【変更点】pyproject.tomlを使って依存関係をインストール
# まず、プロジェクトの定義ファイルだけをコピーします
COPY pyproject.toml .

# pipを最新版に更新し、pyproject.tomlから直接依存関係をインストールします
# これにより、pipが最適なバージョンのライブラリを自動で解決してくれます
RUN pip install --upgrade pip
RUN pip install .

# 5. 非rootユーザーを作成（セキュリティのための良い習慣です）
RUN useradd -m appuser

# 6. アプリケーションのコードをコピーし、所有者を変更
# このステップは、依存関係のインストール後に行うことで、ビルドキャッシュを効率化します
COPY --chown=appuser:appuser ./app /app/app

# 7. ユーザーを切り替え
USER appuser

# 8. uvicornがリッスンするポートを指定
# Cloud Runはコンテナのポートを自動で検出しますが、明記しておくのが丁寧です
EXPOSE 8080

# 9. アプリケーションを起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
