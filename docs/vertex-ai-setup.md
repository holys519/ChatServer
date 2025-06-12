# Google Cloud Vertex AI セットアップガイド

このガイドでは、ChatServerバックエンド用のGoogle Cloud Vertex AIとGeminiモデルをセットアップするための包括的な手順を提供します。

## 前提条件

- 課金が有効なGoogle Cloudプロジェクト
- Google Cloud CLIがインストールおよび設定済み
- Python 3.9+環境

## ステップ1: Google Cloudプロジェクトのセットアップ

### 1.1 プロジェクトの作成または選択

```bash
# 新しいプロジェクトを作成
gcloud projects create YOUR_PROJECT_ID --name="Chat Application"

# プロジェクトをアクティブに設定
gcloud config set project YOUR_PROJECT_ID
```

### 1.2 必要なAPIの有効化

```bash
# Vertex AI APIを有効化
gcloud services enable aiplatform.googleapis.com

# Cloud Resource Manager API（プロジェクト管理用）を有効化
gcloud services enable cloudresourcemanager.googleapis.com

# Service Usage APIを有効化
gcloud services enable serviceusage.googleapis.com
```

### 1.3 認証のセットアップ

#### オプションA: サービスアカウント（本番環境推奨）

```bash
# サービスアカウントを作成
gcloud iam service-accounts create chatserver-vertex-ai \
    --description="Service account for ChatServer Vertex AI access" \
    --display-name="ChatServer Vertex AI"

# 必要なロールを付与
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:chatserver-vertex-ai@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# キーファイルを作成してダウンロード
gcloud iam service-accounts keys create ~/chatserver-vertex-ai-key.json \
    --iam-account=chatserver-vertex-ai@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

#### オプションB: アプリケーションデフォルト認証情報（開発用）

```bash
# Googleアカウントで認証
gcloud auth application-default login

# 自分自身に必要なロールを付与
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="user:YOUR_EMAIL@gmail.com" \
    --role="roles/aiplatform.user"
```

## ステップ2: 環境設定

### 2.1 環境ファイルの作成

`ChatServer/`ディレクトリに`.env`ファイルを作成します：

```env
# Vertex AIに必要
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_LOCATION=us-central1

# オプション: サービスアカウントキー（上記オプションAを使用する場合）
GOOGLE_APPLICATION_CREDENTIALS=/path/to/chatserver-vertex-ai-key.json

# オプション: デバッグ用
DEBUG=true
```

### 2.2 利用可能なリージョン

Vertex AIは以下のリージョンで利用可能です：
- `us-central1`（アイオワ、米国）- **推奨**
- `us-east1`（サウスカロライナ、米国）
- `us-west1`（オレゴン、米国）
- `europe-west4`（オランダ）
- `asia-southeast1`（シンガポール）

## ステップ3: 依存関係のインストール

```bash
# ChatServerディレクトリに移動
cd ChatServer

# すべての依存関係をインストール
uv sync

# または手動でインストール
pip install google-genai google-cloud-aiplatform
```

## ステップ4: サポートされるGeminiモデル

### 現在利用可能なモデル

| フロントエンドモデルID | Vertex AIモデル名 | 説明 | ステータス |
|------------------|---------------------|-------------|---------|
| `gemini-2-0-flash-001` | `gemini-2.0-flash-001` | 高速マルチモーダルモデル | ✅ GA |
| `gemini-2-0-flash-lite-001` | `gemini-2.0-flash-lite-001` | コスト最適化バージョン | ✅ GA |
| `gemini-2-5-pro` | `gemini-2.5-pro` | 最も高度な推論 | 🔄 プレビュー |
| `gemini-2-5-flash` | `gemini-2.5-flash` | 思考プロセスモデル | 🔄 プレビュー |

### モデル機能

- **テキスト生成**: すべてのモデルがテキスト入出力をサポート
- **マルチモーダル**: Gemini 2.0 Flashは画像、音声、ビデオをサポート
- **コンテキストウィンドウ**: Flash-Liteは最大1Mトークン、他は2Mトークン
- **ストリーミング**: リアルタイムレスポンスストリーミングをサポート
- **言語**: 40以上の言語をネイティブにサポート

## ステップ5: セットアップのテスト

### 5.1 クイックテストスクリプト

`ChatServer/`ディレクトリに`test_vertex_ai.py`を作成します：

```python
import os
from dotenv import load_dotenv

# 環境変数を読み込む
load_dotenv()

try:
    from google import genai
    
    # クライアントを初期化
    client = genai.Client(
        vertexai=True,
        project=os.getenv('GOOGLE_CLOUD_PROJECT'),
        location=os.getenv('VERTEX_AI_LOCATION', 'us-central1')
    )
    
    # 生成をテスト
    response = client.models.generate_content(
        model='gemini-2.0-flash-001',
        contents='Hello, how are you?'
    )
    
    print("✅ Vertex AIセットアップ成功!")
    print(f"応答: {response.text}")
    
except Exception as e:
    print(f"❌ エラー: {e}")
    print("\n以下を確認してください:")
    print("1. GOOGLE_CLOUD_PROJECTが正しく設定されているか")
    print("2. Vertex AI APIが有効になっているか")
    print("3. 認証が設定されているか")
    print("4. google-genaiパッケージがインストールされているか")
```

### 5.2 テストの実行

```bash
# ChatServerディレクトリから
python test_vertex_ai.py
```

## ステップ6: ChatServerの実行

### 6.1 開発モード

```bash
# 自動リロード付き開発サーバーを起動
./scripts/dev.sh
```

### 6.2 本番モード

```bash
# 本番サーバーを起動
./scripts/start.sh
```

## ステップ7: モニタリングとロギング

### 7.1 Cloud Loggingの有効化

```bash
# Cloud Logging APIを有効化
gcloud services enable logging.googleapis.com
```

### 7.2 API使用状況の表示

```bash
# Vertex AI使用状況を確認
gcloud logging read "resource.type=ai_platform_api" --limit=50
```

### 7.3 コストのモニタリング

- [Google Cloud Console](https://console.cloud.google.com/billing)にアクセス
- 「請求」→「レポート」に移動
- 「Vertex AI」サービスでフィルタリング

## トラブルシューティング

### 一般的な問題

#### 1. 「権限が拒否されました」エラー

```bash
# 現在の認証を確認
gcloud auth list

# 必要に応じて再認証
gcloud auth application-default login
```

#### 2. 「APIが有効になっていません」エラー

```bash
# 有効なAPIを確認
gcloud services list --enabled | grep aiplatform

# 不足している場合は有効化
gcloud services enable aiplatform.googleapis.com
```

#### 3. 「プロジェクトが見つかりません」エラー

```bash
# 利用可能なプロジェクトを一覧表示
gcloud projects list

# 正しいプロジェクトを設定
gcloud config set project YOUR_PROJECT_ID
```

#### 4. 「モデルが見つかりません」エラー

モデルがリージョンで利用可能かどうかを確認します：
- 一部のモデルはリージョンによって利用が制限される場合があります
- プレビューモデルはすべてのリージョンで利用できない場合があります

### デバッグコマンド

```bash
# プロジェクト設定を確認
gcloud config list

# APIアクセスをテスト
gcloud ai models list --region=us-central1

# クォータを確認
gcloud compute project-info describe --format="value(quotas[].metric)"
```

## セキュリティのベストプラクティス

### 1. サービスアカウントのセキュリティ

- 最小権限の原則を使用
- サービスアカウントキーを定期的にローテーション
- キーを安全に保管（バージョン管理には絶対に含めない）

### 2. 環境変数

```bash
# 本番環境で設定
export GOOGLE_CLOUD_PROJECT=your-project-id
export VERTEX_AI_LOCATION=us-central1
export GOOGLE_APPLICATION_CREDENTIALS=/secure/path/to/key.json
```

### 3. ネットワークセキュリティ

```bash
# IPによるAPIアクセスの制限（オプション）
gcloud compute firewall-rules create allow-vertex-ai \
    --allow tcp:443 \
    --source-ranges="YOUR_SERVER_IP/32" \
    --description="Vertex AI APIアクセスを許可"
```

## コスト最適化

### 1. 適切なモデルの選択

- コスト重視のアプリケーションにはGemini 2.0 Flash-Liteを使用
- バランスの取れたパフォーマンス/コストにはGemini 2.0 Flashを使用
- 複雑な推論タスクにはGemini 2.5 Proを使用

### 2. リクエストの最適化

```python
# 適切なパラメータを使用
config = types.GenerateContentConfig(
    max_output_tokens=1000,  # 出力長を制限
    temperature=0.7,         # 創造性と一貫性のバランスを取る
    top_p=0.9,              # 可能性の高いトークンに集中
    top_k=40                # 語彙を制限
)
```
### 3. 使用状況のモニタリング

```bash
# 請求アラートを設定
gcloud alpha billing budgets create \
    --billing-account=YOUR_BILLING_ACCOUNT \
    --display-name="Vertex AI Budget" \
    --budget-amount=100USD
```

## 次のステップ

1. **フロントエンド統合**: フロントエンドの`aiModels.ts`にサポートされるモデルが含まれていることを確認
2. **エラー処理**: API障害に対する堅牢なエラー処理を実装
3. **キャッシュ**: 繰り返しのクエリに対するレスポンスキャッシュの実装を検討
4. **モニタリング**: Google Cloud Operationsによるアプリケーションモニタリングを設定
5. **スケーリング**: API使用パターンに基づく自動スケーリングを設定

## 追加リソース

- [Vertex AIドキュメント](https://cloud.google.com/vertex-ai/docs)
- [Gemini APIリファレンス](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference)
- [Google Gen AI Python SDK](https://googleapis.github.io/python-genai/)
- [Vertex AI料金](https://cloud.google.com/vertex-ai/pricing)
- [Vertex AIクォータと制限](https://cloud.google.com/vertex-ai/docs/quotas)



# Google Cloud Vertex AI Setup Guide

This guide provides comprehensive instructions for setting up Google Cloud Vertex AI with Gemini models for the ChatServer backend.

## Prerequisites

- Google Cloud Project with billing enabled
- Google Cloud CLI installed and configured
- Python 3.9+ environment

## Step 1: Google Cloud Project Setup

### 1.1 Create or Select a Project

```bash
# Create a new project
gcloud projects create YOUR_PROJECT_ID --name="Chat Application"

# Set the project as active
gcloud config set project YOUR_PROJECT_ID
```

### 1.2 Enable Required APIs

```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Enable Cloud Resource Manager API (for project management)
gcloud services enable cloudresourcemanager.googleapis.com

# Enable Service Usage API
gcloud services enable serviceusage.googleapis.com
```

### 1.3 Set Up Authentication

#### Option A: Service Account (Recommended for Production)

```bash
# Create a service account
gcloud iam service-accounts create chatserver-vertex-ai \
    --description="Service account for ChatServer Vertex AI access" \
    --display-name="ChatServer Vertex AI"

# Grant necessary roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:chatserver-vertex-ai@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# Create and download key file
gcloud iam service-accounts keys create ~/chatserver-vertex-ai-key.json \
    --iam-account=chatserver-vertex-ai@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

#### Option B: Application Default Credentials (for Development)

```bash
# Authenticate with your Google account
gcloud auth application-default login

# Grant yourself the necessary roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="user:YOUR_EMAIL@gmail.com" \
    --role="roles/aiplatform.user"
```

## Step 2: Environment Configuration

### 2.1 Create Environment File

Create a `.env` file in the `ChatServer/` directory:

```env
# Required for Vertex AI
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_LOCATION=us-central1

# Optional: Service Account Key (if using Option A above)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/chatserver-vertex-ai-key.json

# Optional: For debugging
DEBUG=true
```

### 2.2 Available Regions

Vertex AI is available in the following regions:
- `us-central1` (Iowa, USA) - **Recommended**
- `us-east1` (South Carolina, USA)
- `us-west1` (Oregon, USA)
- `europe-west4` (Netherlands)
- `asia-southeast1` (Singapore)

## Step 3: Install Dependencies

```bash
# Navigate to ChatServer directory
cd ChatServer

# Install all dependencies
uv sync

# Or install manually
pip install google-genai google-cloud-aiplatform
```

## Step 4: Supported Gemini Models

### Currently Available Models

| Frontend Model ID | Vertex AI Model Name | Description | Status |
|------------------|---------------------|-------------|---------|
| `gemini-2-0-flash-001` | `gemini-2.0-flash-001` | Fast, multimodal model | ✅ GA |
| `gemini-2-0-flash-lite-001` | `gemini-2.0-flash-lite-001` | Cost-optimized version | ✅ GA |
| `gemini-2-5-pro` | `gemini-2.5-pro` | Most advanced reasoning | 🔄 Preview |
| `gemini-2-5-flash` | `gemini-2.5-flash` | Thinking model | 🔄 Preview |

### Model Capabilities

- **Text Generation**: All models support text input/output
- **Multimodal**: Gemini 2.0 Flash supports images, audio, video
- **Context Window**: Up to 1M tokens for Flash-Lite, 2M for others
- **Streaming**: Real-time response streaming supported
- **Languages**: 40+ languages natively supported

## Step 5: Testing the Setup

### 5.1 Quick Test Script

Create `test_vertex_ai.py` in the `ChatServer/` directory:

```python
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from google import genai
    
    # Initialize client
    client = genai.Client(
        vertexai=True,
        project=os.getenv('GOOGLE_CLOUD_PROJECT'),
        location=os.getenv('VERTEX_AI_LOCATION', 'us-central1')
    )
    
    # Test generation
    response = client.models.generate_content(
        model='gemini-2.0-flash-001',
        contents='Hello, how are you?'
    )
    
    print("✅ Vertex AI setup successful!")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nPlease check:")
    print("1. GOOGLE_CLOUD_PROJECT is set correctly")
    print("2. Vertex AI API is enabled")
    print("3. Authentication is configured")
    print("4. google-genai package is installed")
```

### 5.2 Run the Test

```bash
# From ChatServer directory
python test_vertex_ai.py
```

## Step 6: Running the ChatServer

### 6.1 Development Mode

```bash
# Start development server with auto-reload
./scripts/dev.sh
```

### 6.2 Production Mode

```bash
# Start production server
./scripts/start.sh
```

## Step 7: Monitoring and Logging

### 7.1 Enable Cloud Logging

```bash
# Enable Cloud Logging API
gcloud services enable logging.googleapis.com
```

### 7.2 View API Usage

```bash
# Check Vertex AI usage
gcloud logging read "resource.type=ai_platform_api" --limit=50
```

### 7.3 Monitor Costs

- Visit [Google Cloud Console](https://console.cloud.google.com/billing)
- Navigate to "Billing" → "Reports"
- Filter by "Vertex AI" service

## Troubleshooting

### Common Issues

#### 1. "Permission denied" errors

```bash
# Check current authentication
gcloud auth list

# Re-authenticate if needed
gcloud auth application-default login
```

#### 2. "API not enabled" errors

```bash
# Check enabled APIs
gcloud services list --enabled | grep aiplatform

# Enable if missing
gcloud services enable aiplatform.googleapis.com
```

#### 3. "Project not found" errors

```bash
# List available projects
gcloud projects list

# Set correct project
gcloud config set project YOUR_PROJECT_ID
```

#### 4. "Model not found" errors

Check if the model is available in your region:
- Some models may have limited regional availability
- Preview models may not be available in all regions

### Debug Commands

```bash
# Check project configuration
gcloud config list

# Test API access
gcloud ai models list --region=us-central1

# Check quotas
gcloud compute project-info describe --format="value(quotas[].metric)"
```

## Security Best Practices

### 1. Service Account Security

- Use least-privilege principle
- Regularly rotate service account keys
- Store keys securely (never in version control)

### 2. Environment Variables

```bash
# Set in production environment
export GOOGLE_CLOUD_PROJECT=your-project-id
export VERTEX_AI_LOCATION=us-central1
export GOOGLE_APPLICATION_CREDENTIALS=/secure/path/to/key.json
```

### 3. Network Security

```bash
# Restrict API access by IP (optional)
gcloud compute firewall-rules create allow-vertex-ai \
    --allow tcp:443 \
    --source-ranges="YOUR_SERVER_IP/32" \
    --description="Allow Vertex AI API access"
```

## Cost Optimization

### 1. Choose Appropriate Models

- Use Gemini 2.0 Flash-Lite for cost-sensitive applications
- Use Gemini 2.0 Flash for balanced performance/cost
- Reserve Gemini 2.5 Pro for complex reasoning tasks

### 2. Optimize Requests

```python
# Use appropriate parameters
config = types.GenerateContentConfig(
    max_output_tokens=1000,  # Limit output length
    temperature=0.7,         # Balance creativity/consistency
    top_p=0.9,              # Focus on likely tokens
    top_k=40                # Limit vocabulary
)
```

### 3. Monitor Usage

```bash
# Set up billing alerts
gcloud alpha billing budgets create \
    --billing-account=YOUR_BILLING_ACCOUNT \
    --display-name="Vertex AI Budget" \
    --budget-amount=100USD
```

## Next Steps

1. **Frontend Integration**: Ensure the frontend `aiModels.ts` includes the supported models
2. **Error Handling**: Implement robust error handling for API failures
3. **Caching**: Consider implementing response caching for repeated queries
4. **Monitoring**: Set up application monitoring with Google Cloud Operations
5. **Scaling**: Configure auto-scaling based on API usage patterns

## Additional Resources

- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Gemini API Reference](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference)
- [Google Gen AI Python SDK](https://googleapis.github.io/python-genai/)
- [Vertex AI Pricing](https://cloud.google.com/vertex-ai/pricing)
- [Vertex AI Quotas and Limits](https://cloud.google.com/vertex-ai/docs/quotas)