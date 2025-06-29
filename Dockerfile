# ステージ1: Pythonのベースイメージを設定
FROM python:3.12-slim

# 作業ディレクトリを設定
WORKDIR /app

# 環境変数を設定
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 8080

# まず、pyproject.tomlだけをコピーして依存関係をインストールする
# これにより、ソースコードの変更時に毎回インストールが走るのを防ぎ、ビルドキャッシュが効率的に機能する
COPY pyproject.toml .

# pip自体をアップグレードし、pyproject.tomlから直接依存関係をインストール
RUN pip install --upgrade pip
# `.` はカレントディレクトリ（pyproject.tomlがある場所）を指す
RUN pip install .

# アプリケーションのソースコードをコピー
# `app`フォルダにソースコードがあると仮定
COPY app ./app

# アプリケーションを実行するコマンド
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]