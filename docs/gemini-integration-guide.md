
# Gemini 統合実装ガイド

このガイドでは、最新の Vertex AI Gemini モデルが ChatServer バックエンドにどのように統合されているかを説明します。

## 概要

ChatServer は現在、Google の最新の Gen AI SDK と Vertex AI を使用して Gemini 2.0 および 2.5 モデルへのアクセスを提供し、パフォーマンスの向上、マルチモーダル機能、およびコスト効率を実現しています。

## アーキテクチャの変更

### 1. サービスレイヤーの更新

**ファイル**: `app/services/gemini_service.py`

サービスは以下を使用するために完全に書き直されました：
- **Google Gen AI SDK**: Vertex AI 用の最新 Python SDK
- **改善されたモデルサポート**: すべての現行 Gemini モデル
- **より良いエラー処理**: 包括的なエラー管理
- **ストリーミングサポート**: リアルタイムレスポンスストリーミング

### 2. モデルマッピング

フロントエンドのモデル ID は Vertex AI モデル名にマッピングされます：

```python
model_mapping = {
    # 一般提供モデル
    "gemini-2-0-flash-001": "gemini-2.0-flash-001",
    "gemini-2-0-flash-lite-001": "gemini-2.0-flash-lite-001",
    
    # プレビューモデル（すべてのリージョンで利用できない場合があります）
    "gemini-2-5-pro": "gemini-2.5-pro",
    "gemini-2-5-flash": "gemini-2.5-flash"
}
```

## フロントエンド統合

### 1. モデルリストの更新

**ファイル**: `ChatLLMApp/src/data/aiModels.ts`

新しい Gemini モデルを追加：
- **Gemini 2.0 Flash**: 画像/音声/ビデオをサポートするマルチモーダルモデル
- **Gemini 2.0 Flash Lite**: コスト最適化バージョン
- **Gemini 2.5 Pro**: 高度な推論（プレビュー）
- **Gemini 2.5 Flash**: プロセスの可視性を持つ思考モデル（プレビュー）

### 2. モデル選択フロー

1. ユーザーがフロントエンド UI でモデルを選択
2. モデル ID が API を通じてバックエンドに送信
3. バックエンドが ID を Vertex AI モデル名にマッピング
4. API リクエストが Vertex AI に送信
5. レスポンスがフロントエンドにストリーミング

## API エンドポイント

### 1. チャットエンドポイント

**POST** `/api/chat/`

```json
{
  "message": "こんにちは、元気ですか？",
  "model": "gemini-2-0-flash-001",
  "history": [
    {"role": "user", "content": "以前のメッセージ"},
    {"role": "assistant", "content": "以前の応答"}
  ]
}
```

### 2. WebSocket ストリーミング

**WebSocket** `/ws/chat/{client_id}`

モデル選択をサポートするチャットレスポンスのリアルタイムストリーミング。

## 主な機能

### 1. マルチモーダルサポート

Gemini 2.0 Flash は以下をサポート：
- **テキスト**: 標準テキスト会話
- **画像**: 画像分析と説明
- **音声**: 音声文字起こしと分析
- **ビデオ**: ビデオコンテンツ理解

### 2. 高度な設定

```python
config = types.GenerateContentConfig(
    temperature=0.7,        # 創造性レベル
    top_p=0.9,             # 核サンプリング
    top_k=40,              # 語彙制限
    max_output_tokens=8192  # 応答長制限
)
```

### 3. エラー処理

- **モデル可用性**: 利用可能なモデルへの優雅なフォールバック
- **レート制限**: バックオフによる自動再試行
- **認証**: 認証問題に関する明確なエラーメッセージ
- **ネットワーク問題**: タイムアウトと接続エラー処理

## テスト

### 1. 自動テスト

包括的なテストスイートを実行：

```bash
cd ChatServer
python test_vertex_ai.py
```

これは以下をテストします：
- 環境設定
- サービス初期化
- モデル可用性
- API 接続性
- ストリーミング機能

### 2. 手動テスト

1. **バックエンド起動**:
   ```bash
   cd ChatServer
   ./scripts/dev.sh
   ```

2. **フロントエンド起動**:
   ```bash
   cd ChatLLMApp
   npm start
   ```

3. **モデルテスト**:
   - 異なる Gemini モデルを選択
   - テストメッセージを送信
   - ストリーミングレスポンスを確認

## パフォーマンス最適化

### 1. モデル選択戦略

- **Gemini 2.0 Flash Lite**: 単純なクエリとコスト効率向け
- **Gemini 2.0 Flash**: バランスの取れたパフォーマンスとマルチモーダルニーズ向け
- **Gemini 2.5 Pro**: 複雑な推論タスク向け
- **Gemini 2.5 Flash**: 思考過程の可視化が必要なタスク向け

### 2. リクエスト最適化

```python
# 異なるユースケース向けの最適設定
SETTINGS = {
    "chat": {"temperature": 0.7, "max_tokens": 2048},
    "analysis": {"temperature": 0.3, "max_tokens": 4096},
    "creative": {"temperature": 0.9, "max_tokens": 8192}
}
```

### 3. キャッシュ戦略

以下のレスポンスキャッシュの実装を検討：
- 繰り返しの質問
- システムプロンプト
- モデルメタデータ

## セキュリティ考慮事項

### 1. 認証

```bash
# サービスアカウント（本番環境）
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# アプリケーションデフォルト認証情報（開発環境）
gcloud auth application-default login
```

### 2. API セキュリティ

- **レート制限**: アプリケーションレベルで実装
- **入力検証**: すべての入力がサニタイズされる
- **エラーサニタイズ**: エラーメッセージに機密データなし

### 3. コスト管理

```python
# リクエスト制限
MAX_TOKENS_PER_REQUEST = 8192
MAX_REQUESTS_PER_MINUTE = 60
MAX_MONTHLY_COST = 100  # USD
```

## モニタリングとデバッグ

### 1. ロギング

```python
import logging

# デバッグロギングを有効化
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

### 2. メトリクス追跡

重要なメトリクスを追跡：
- モデル別応答時間
- リクエスト毎のトークン使用量
- エラー率
- インタラクション毎のコスト

### 3. ヘルスチェック

```python
# ヘルスチェックエンドポイント
@app.get("/health/gemini")
async def gemini_health():
    try:
        # 最小トークンでの簡易テスト
        response = await gemini_service.send_message(
            "gemini-2-0-flash-001", [], "test"
        )
        return {"status": "healthy", "models": ["gemini-2.0-flash-001"]}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## トラブルシューティング

### 一般的な問題

1. **"モデルが見つかりません"**
   - リージョンでのモデル可用性を確認
   - モデル名マッピングを確認
   - 安定したモデルへのフォールバックを試す

2. **"権限が拒否されました"**
   - Google Cloud 認証を確認
   - IAM ロール（aiplatform.user）を確認
   - API が有効になっていることを確認

3. **"クォータ超過"**
   - Vertex AI クォータを確認
   - レート制限を実装
   - モデル切り替えを検討

### デバッグコマンド

```bash
# サービスステータスを確認
curl http://localhost:8000/health/gemini

# 特定のモデルをテスト
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"test","model":"gemini-2-0-flash-001","history":[]}'

# ログを表示
tail -f /var/log/chatserver/app.log
```

## 将来の拡張

### 1. 計画されている機能

- **関数呼び出し**: 外部 API との統合
- **コード実行**: サンドボックス化されたコード実行
- **グラウンディング**: Web 検索統合
- **安全性フィルタリング**: コンテンツモデレーション

### 2. パフォーマンス改善

- **モデルプリロード**: コールドスタート時間の短縮
- **レスポンスキャッシュ**: 頻繁なレスポンスをキャッシュ
- **並列リクエスト**: 複数モデル推論
- **自動スケーリング**: 動的リソース割り当て

### 3. モニタリング強化

- **リアルタイムダッシュボード**: Grafana 統合
- **アラートシステム**: 問題の事前検出
- **コスト分析**: 詳細な使用レポート
- **A/B テスト**: モデルパフォーマンス比較

## 貢献

新機能を追加する際：

1. **モデルマッピングの更新**: 新しいモデルをマッピングに追加
2. **テストカバレッジ**: 新機能のテストを追加
3. **ドキュメント**: このガイドを更新
4. **パフォーマンス**: 新機能のベンチマーク
5. **セキュリティ**: セキュリティへの影響を確認


# Gemini Integration Implementation Guide

This guide explains how the latest Vertex AI Gemini models are integrated into the ChatServer backend.

## Overview

The ChatServer now uses Google's latest Gen AI SDK with Vertex AI to provide access to Gemini 2.0 and 2.5 models, offering improved performance, multimodal capabilities, and cost efficiency.

## Architecture Changes

### 1. Updated Service Layer

**File**: `app/services/gemini_service.py`

The service has been completely rewritten to use:
- **Google Gen AI SDK**: Latest Python SDK for Vertex AI
- **Improved Model Support**: All current Gemini models
- **Better Error Handling**: Comprehensive error management
- **Streaming Support**: Real-time response streaming

### 2. Model Mapping

Frontend model IDs are mapped to Vertex AI model names:

```python
model_mapping = {
    # Generally Available Models
    "gemini-2-0-flash-001": "gemini-2.0-flash-001",
    "gemini-2-0-flash-lite-001": "gemini-2.0-flash-lite-001",
    
    # Preview Models (may not be available in all regions)
    "gemini-2-5-pro": "gemini-2.5-pro",
    "gemini-2-5-flash": "gemini-2.5-flash"
}
```

## Frontend Integration

### 1. Updated Model List

**File**: `ChatLLMApp/src/data/aiModels.ts`

Added new Gemini models:
- **Gemini 2.0 Flash**: Multimodal model with image/audio/video support
- **Gemini 2.0 Flash Lite**: Cost-optimized version
- **Gemini 2.5 Pro**: Advanced reasoning (Preview)
- **Gemini 2.5 Flash**: Thinking model with process visibility (Preview)

### 2. Model Selection Flow

1. User selects model in frontend UI
2. Model ID sent to backend via API
3. Backend maps ID to Vertex AI model name
4. API request sent to Vertex AI
5. Response streamed back to frontend

## API Endpoints

### 1. Chat Endpoint

**POST** `/api/chat/`

```json
{
  "message": "Hello, how are you?",
  "model": "gemini-2-0-flash-001",
  "history": [
    {"role": "user", "content": "Previous message"},
    {"role": "assistant", "content": "Previous response"}
  ]
}
```

### 2. WebSocket Streaming

**WebSocket** `/ws/chat/{client_id}`

Real-time streaming for chat responses with model selection support.

## Key Features

### 1. Multimodal Support

Gemini 2.0 Flash supports:
- **Text**: Standard text conversations
- **Images**: Image analysis and description
- **Audio**: Audio transcription and analysis
- **Video**: Video content understanding

### 2. Advanced Configuration

```python
config = types.GenerateContentConfig(
    temperature=0.7,        # Creativity level
    top_p=0.9,             # Nucleus sampling
    top_k=40,              # Vocabulary limitation
    max_output_tokens=8192  # Response length limit
)
```

### 3. Error Handling

- **Model Availability**: Graceful fallback to available models
- **Rate Limiting**: Automatic retry with backoff
- **Authentication**: Clear error messages for auth issues
- **Network Issues**: Timeout and connection error handling

## Testing

### 1. Automated Testing

Run the comprehensive test suite:

```bash
cd ChatServer
python test_vertex_ai.py
```

This tests:
- Environment configuration
- Service initialization
- Model availability
- API connectivity
- Streaming functionality

### 2. Manual Testing

1. **Start Backend**:
   ```bash
   cd ChatServer
   ./scripts/dev.sh
   ```

2. **Start Frontend**:
   ```bash
   cd ChatLLMApp
   npm start
   ```

3. **Test Models**:
   - Select different Gemini models
   - Send test messages
   - Verify streaming responses

## Performance Optimizations

### 1. Model Selection Strategy

- **Gemini 2.0 Flash Lite**: For simple queries and cost efficiency
- **Gemini 2.0 Flash**: For balanced performance and multimodal needs
- **Gemini 2.5 Pro**: For complex reasoning tasks
- **Gemini 2.5 Flash**: For tasks requiring visible thinking

### 2. Request Optimization

```python
# Optimal settings for different use cases
SETTINGS = {
    "chat": {"temperature": 0.7, "max_tokens": 2048},
    "analysis": {"temperature": 0.3, "max_tokens": 4096},
    "creative": {"temperature": 0.9, "max_tokens": 8192}
}
```

### 3. Caching Strategy

Consider implementing response caching for:
- Repeated questions
- System prompts
- Model metadata

## Security Considerations

### 1. Authentication

```bash
# Service Account (Production)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Application Default Credentials (Development)
gcloud auth application-default login
```

### 2. API Security

- **Rate Limiting**: Implemented at application level
- **Input Validation**: All inputs sanitized
- **Error Sanitization**: No sensitive data in error messages

### 3. Cost Controls

```python
# Request limits
MAX_TOKENS_PER_REQUEST = 8192
MAX_REQUESTS_PER_MINUTE = 60
MAX_MONTHLY_COST = 100  # USD
```

## Monitoring and Debugging

### 1. Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

### 2. Metrics Tracking

Track important metrics:
- Response time by model
- Token usage per request
- Error rates
- Cost per interaction

### 3. Health Checks

```python
# Health check endpoint
@app.get("/health/gemini")
async def gemini_health():
    try:
        # Quick test with minimal tokens
        response = await gemini_service.send_message(
            "gemini-2-0-flash-001", [], "test"
        )
        return {"status": "healthy", "models": ["gemini-2.0-flash-001"]}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Troubleshooting

### Common Issues

1. **"Model not found"**
   - Check model availability in your region
   - Verify model name mapping
   - Try fallback to stable models

2. **"Permission denied"**
   - Verify Google Cloud authentication
   - Check IAM roles (aiplatform.user)
   - Ensure API is enabled

3. **"Quota exceeded"**
   - Check Vertex AI quotas
   - Implement rate limiting
   - Consider model switching

### Debug Commands

```bash
# Check service status
curl http://localhost:8000/health/gemini

# Test specific model
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"test","model":"gemini-2-0-flash-001","history":[]}'

# View logs
tail -f /var/log/chatserver/app.log
```

## Future Enhancements

### 1. Planned Features

- **Function Calling**: Integration with external APIs
- **Code Execution**: Sandboxed code execution
- **Grounding**: Web search integration
- **Safety Filtering**: Content moderation

### 2. Performance Improvements

- **Model Preloading**: Reduce cold start times
- **Response Caching**: Cache frequent responses
- **Parallel Requests**: Multiple model inference
- **Auto-scaling**: Dynamic resource allocation

### 3. Monitoring Enhancements

- **Real-time Dashboards**: Grafana integration
- **Alert System**: Proactive issue detection
- **Cost Analytics**: Detailed usage reports
- **A/B Testing**: Model performance comparison

## Contributing

When adding new features:

1. **Update Model Mapping**: Add new models to the mapping
2. **Test Coverage**: Add tests for new functionality
3. **Documentation**: Update this guide
4. **Performance**: Benchmark new features
5. **Security**: Review security implications