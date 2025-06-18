# Paper Scout実装解説ドキュメント

## 概要

Paper Scout（論文スカウト）は、PubMedデータベースから研究論文を検索・分析し、包括的なレポートを生成するAIエージェントシステムです。非同期タスク実行とリアルタイムプログレス表示により、ユーザーに優れた体験を提供します。

## システムアーキテクチャ

### 1. システム構成要素

```
Frontend (React Native/Expo)
    ↓ タスク実行要求
Backend API (/api/tasks/execute)
    ↓ バックグラウンドタスク作成
TaskService (タスク管理)
    ↓ エージェント実行
PaperScoutAgent (論文検索・分析)
    ↓ データ取得
PubMedService (論文データ取得)
    ↓ 結果保存
Firestore/LocalStorage (結果保存)
```

### 2. データフロー

1. **タスク作成**: ユーザーがフロントエンドで検索クエリを入力
2. **バックグラウンド実行**: TaskServiceがPaperScoutAgentを非同期実行
3. **進捗追跡**: フロントエンドが定期的にステータスをポーリング
4. **結果表示**: タスク完了時に結果をフロントエンドに表示

## 実装詳細

### 1. PaperScoutAgent (`app/agents/paper_scout_agent.py`)

#### 主要機能
- **クエリ最適化**: 入力クエリをPubMed検索に最適化
- **論文検索**: PubMedAPIを使用して関連論文を検索
- **論文分析**: AI（Gemini）を使用して論文内容を分析
- **レポート生成**: 構造化された包括的なレポートを作成

#### 実行ステップ
```python
async def execute(self, task_id: str, input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
    # ステップ1: クエリ最適化 (25%完了)
    optimized_query = await self._optimize_search_query(query)
    
    # ステップ2: PubMed検索 (60%完了)
    papers = await pubmed_service.search_papers(optimized_query, max_results, years_back)
    
    # ステップ3: 論文分析 (90%完了)
    analysis_result = await self._analyze_papers(papers, analysis_type, query)
    
    # ステップ4: レポート生成 (100%完了)
    final_report = await self._generate_report(query, papers, analysis_result, config)
```

#### 出力データ構造
```python
output_data = {
    'original_query': str,           # 元のクエリ
    'optimized_query': str,          # 最適化されたクエリ
    'papers_found': int,             # 発見された論文数
    'papers': List[Dict],            # 論文データリスト
    'analysis': Dict,                # 分析結果
    'report': str,                   # マークダウン形式の最終レポート
    'search_metadata': Dict          # 検索メタデータ
}
```

### 2. TaskService (`app/services/task_service.py`)

#### 主要機能
- **タスク作成・管理**: Firestore/ローカルストレージでタスク情報管理
- **進捗追跡**: リアルタイムでタスク進捗を更新
- **バックグラウンド実行**: 非同期でエージェントタスクを実行

#### 進捗更新フロー
```python
async def update_task_progress(
    task_id: str,
    status: Optional[TaskStatus] = None,
    progress_percentage: Optional[float] = None,
    current_step: Optional[str] = None,
    steps_completed: Optional[int] = None,
    output_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
):
```

### 3. API エンドポイント (`app/api/routes/tasks.py`)

#### `/api/tasks/execute` (POST)
- **機能**: タスクの実行開始
- **処理**: TaskProgressをDBに作成し、バックグラウンドタスクを開始
- **戻り値**: `task_id`とステータス

#### `/api/tasks/status/{task_id}` (GET)
- **機能**: タスクの現在の進捗状況を取得
- **処理**: Firestore/ローカルストレージからTaskProgressを取得
- **戻り値**: TaskProgressオブジェクト

## 現在発生している問題

### 問題1: `total_steps`パラメータエラー

**エラーメッセージ**:
```
TaskService.update_task_progress() got an unexpected keyword argument 'total_steps'
```

**原因**: 
- `TaskProgress`スキーマに`total_steps`フィールドが定義されている
- しかし`TaskService.update_task_progress()`メソッドに`total_steps`パラメータが未定義
- `task_service.py:349`で`total_steps=1`を渡そうとしている

**影響**: 
- タスクの最終段階でエラーが発生
- 結果データ（`output_data`）が保存されない
- フロントエンドに最終結果が表示されない

### 問題2: エラー処理不備

**症状**: 
- PaperScoutAgentは正常に実行完了している
- しかし最終的な結果保存時にエラーが発生している
- ユーザーは進捗は見えるが最終結果が見えない

## 解決方法

### 1. TaskService修正

`update_task_progress`メソッドに`total_steps`パラメータを追加:

```python
async def update_task_progress(
    self, 
    task_id: str, 
    status: Optional[TaskStatus] = None,
    progress_percentage: Optional[float] = None,
    current_step: Optional[str] = None,
    steps_completed: Optional[int] = None,
    total_steps: Optional[int] = None,  # ← 追加
    output_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> bool:
```

### 2. エラーハンドリング強化

try-catch文を改善し、部分的失敗時でも結果を保存できるようにする。

### 3. フロントエンド対応

最終結果の表示ロジックを改善し、`output_data`フィールドの内容を適切に表示する。

## フロントエンドとの連携

### 1. タスク実行フロー

```javascript
// 1. タスク実行開始
const response = await fetch('/api/tasks/execute', {
    method: 'POST',
    body: JSON.stringify(taskRequest)
});
const { task_id } = await response.json();

// 2. 進捗ポーリング
const pollInterval = setInterval(async () => {
    const progress = await fetch(`/api/tasks/status/${task_id}`);
    const progressData = await progress.json();
    
    // ステータスバー更新
    updateProgressBar(progressData.progress_percentage);
    updateCurrentStep(progressData.current_step);
    
    // 完了時の処理
    if (progressData.status === 'completed') {
        clearInterval(pollInterval);
        displayResults(progressData.output_data);
    }
}, 1000);
```

### 2. 結果表示

`output_data.report`にマークダウン形式の最終レポートが含まれており、これをレンダリングしてユーザーに表示する。

## 今後の改善点

1. **リアルタイムストリーミング**: Server-Sent Eventsを使用したリアルタイム進捗更新
2. **エラー復旧**: 部分的失敗からの自動復旧機能
3. **キャッシュ機能**: 同じクエリの結果をキャッシュして高速化
4. **論文品質評価**: より詳細な論文品質評価機能
5. **複数データベース対応**: PubMed以外の学術データベースとの連携

## トラブルシューティング

### よくある問題

1. **タスクが途中で停止する**
   - Firestore接続問題の可能性
   - ローカルフォールバックが動作しているか確認

2. **検索結果が0件**
   - クエリ最適化の問題
   - PubMed APIの接続状況確認

3. **進捗が更新されない**
   - フロントエンドのポーリング間隔確認
   - TaskService の進捗更新ロジック確認

### ログ確認方法

```bash
# タスク実行ログ
grep "🚀 Starting background task execution" server.log

# 進捗更新ログ  
grep "✅ Task.*progress updated" server.log

# エラーログ
grep "❌ Error" server.log
```