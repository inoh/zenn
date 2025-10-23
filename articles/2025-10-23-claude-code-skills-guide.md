---
title: "Claude Code のスキル機能完全ガイド：モジュール型機能拡張で開発を効率化"
emoji: "🛠️"
type: "tech"
topics: ["ClaudeCode", "AI", "開発効率化", "Skills"]
published: false
---

Claude Code のスキル機能は、Claude の能力を特定のタスクに特化させるためのモジュール型拡張機能です。本記事では、スキル機能の基本概念から実践的な活用方法まで、包括的に解説します。

## スキルとは何か

スキルは、指示、メタデータ、オプションのリソース（スクリプト、テンプレート等）をパッケージ化したモジュール型の機能拡張です。Claude が関連する場合に自動的に使用する再利用可能なファイルシステムベースのリソースとして機能します。

### スキルの主な特徴

- **領域固有の専門知識**: 汎用アシスタントを特定タスクの専門家に変換
- **自動呼び出し**: ユーザーのリクエスト内容に基づいて Claude が自動的に判断して使用
- **効率的なトークン消費**: 3層アーキテクチャによる段階的な情報開示
- **再利用性**: 一度作成すれば複数の会話で自動的に利用可能

### スキルとサブエージェント・スラッシュコマンドの違い

| 機能 | 呼び出し方法 | 用途 |
|------|------------|------|
| **スキル** | モデルが自動判断 | 領域固有の専門知識を提供 |
| **サブエージェント** | 明示的指定または自動 | 独立したコンテキストで特定タスクを実行 |
| **スラッシュコマンド** | ユーザーが明示的に実行 | 定型的なワークフローを実行 |

スキルは従来のプロンプトとも異なります。プロンプトは「1回限りのタスク用の会話レベルの指示」であるのに対し、スキルは「オンデマンドで読み込まれ、複数の会話にわたって同じガイダンスを提供」します。

## 3層アーキテクチャによる段階的情報開示

スキルは効率的なトークン利用のために、3層の段階的読み込みモデルを採用しています。

### レベル1: メタデータ（常時読み込み）

YAMLフロントマターに記載されたスキル名と説明（約100トークン/スキル）が起動時に読み込まれます。Claude はどのスキルが存在し、いつ呼び出すべきかをコンテキストペナルティなしで認識できます。

```yaml
---
name: pdf-processor
description: PDF ファイルからテキストや表を抽出し、フォーム入力、ドキュメントマージを実行します。PDF 作業時に使用してください。
---
```

### レベル2: 指示（トリガー時）

ユーザーリクエストに関連する場合のみ、SKILL.md ファイル本体（5,000トークン以下推奨）が読み込まれます。手順的な知識やワークフローを含みます。

### レベル3: リソース（必要時）

追加ファイル、スクリプト、参照資料は参照された時のみ読み込まれ、アクセスされるまでトークンを消費しません。

**例**: PDF 処理スキルの場合
1. 起動時にメタデータを読み込み
2. ユーザーが PDF 作業を言及すると SKILL.md を読み込み
3. フォーム入力が必要な場合のみ FORMS.md を参照
4. ユーティリティスクリプトはコード自体を読み込まずに実行

この仕組みにより、使用されないコンテンツはトークンを消費しないため、多数のスキルを同時に利用可能な状態で維持できます。

## スキルの利用可能な場所

### Claude API

- プリビルドスキルとカスタムスキルの両方を利用可能
- ベータヘッダーを使用してアクセス

### Claude Code

- カスタムスキルのみ利用可能
- ファイルシステムベースで管理

### Claude.ai

- プリビルドスキルは組み込み済み
- カスタムスキルは ZIP ファイルとしてアップロード

**注意**: スキルはプラットフォーム間で自動同期されません。各プラットフォームで個別に設定が必要です。

## プリビルドスキル

Anthropic が提供する4つのプリビルドスキルが利用可能です：

- **PowerPoint (pptx)**: プレゼンテーション作成
- **Excel (xlsx)**: スプレッドシート処理とレポート生成
- **Word (docx)**: ドキュメント作成
- **PDF (pdf)**: PDF 生成

これらのスキルは Claude API と Claude.ai で利用できます。

## Claude Code でのスキル作成

### ファイル構造

スキルは以下の構造で整理されます：

```
skill-name/
├── SKILL.md (必須)
├── reference.md (オプション)
├── scripts/ (オプション: ユーティリティスクリプト)
└── templates/ (オプション: テンプレートファイル)
```

### 保存場所

**個人用スキル**: `~/.claude/skills/skill-name/`
- ユーザー全体で利用可能
- 個人設定として管理

**プロジェクトスキル**: `.claude/skills/skill-name/`
- プロジェクト固有
- Git でチーム共有可能

**プラグインスキル**: インストールされたプラグインにバンドル

### SKILL.md ファイルの作成

すべてのスキルには `SKILL.md` ファイルが必須です。以下の YAML フロントマターが必要です：

```markdown
---
name: data-analyzer
description: CSV や JSON データを分析し、統計サマリー、可視化、異常検出を実行します。データ分析や探索的解析が必要な場合に使用してください。
allowed-tools:
  - Read
  - Write
  - Bash
---

# データ分析スキル

このスキルは構造化データの包括的な分析を提供します。

## 機能

1. **データ読み込みと検証**
   - CSV, JSON, TSV ファイルのサポート
   - データ型の自動検出
   - 欠損値の識別

2. **統計分析**
   - 基本統計量（平均、中央値、標準偏差）
   - 分布の可視化
   - 相関分析

3. **異常検出**
   - 外れ値の識別
   - パターン認識
   - トレンド分析

## 使用方法

データファイルを提供し、実行したい分析のタイプを指定してください。
スキルは自動的に適切な処理パイプラインを選択します。

詳細な分析手法については、[reference.md](reference.md) を参照してください。
```

### YAMLフロントマターの詳細

**name** (必須)
- 小文字、数字、ハイフンのみ使用可能
- 最大64文字
- 予約語（"anthropic", "claude" 等）は使用不可
- 推奨: 動名詞形式（`processing-pdfs`, `analyzing-spreadsheets`）

**description** (必須)
- 1,024文字以内
- 機能と使用タイミングの両方を明記
- 三人称で記述（例: "Processes Excel files" ✓, "I process Excel files" ✗）
- 具体的なトリガーキーワードを含める
- XML タグは使用不可

**allowed-tools** (オプション)
- スキルがアクセスできるツールを制限
- セキュリティと効率性の向上

## 実践的なスキル例

### 1. PDF 処理スキル

```markdown
---
name: pdf-processor
description: PDF からテキスト・表を抽出、フォーム入力、複数ドキュメントのマージを実行します。PDF ファイル操作時に使用してください。
allowed-tools:
  - Read
  - Write
  - Bash
---

# PDF 処理スキル

## 主要機能

### テキスト抽出
- PDF からテキストコンテンツを抽出
- レイアウトとフォーマットを保持
- 複数ページの処理

### 表の抽出
- PDF 内の表を識別
- CSV や JSON 形式に変換
- ヘッダー行の自動検出

### フォーム処理
フォーム入力の詳細については [forms-guide.md](forms-guide.md) を参照してください。

## スクリプト

- `scripts/extract_text.py`: テキスト抽出
- `scripts/extract_tables.py`: 表抽出
- `scripts/fill_form.py`: フォーム入力

## 使用例

「この PDF から表を抽出して CSV に変換してください」と指示するだけで、
適切なスクリプトを自動選択して実行します。
```

### 2. コードレビュースキル

```markdown
---
name: code-reviewer
description: コード品質、セキュリティ脆弱性、パフォーマンス問題、ベストプラクティス遵守を評価します。コードレビューやコード品質改善が必要な場合に使用してください。
allowed-tools:
  - Read
  - Grep
  - Glob
---

# コードレビュースキル

経験豊富なシニア開発者の視点で、以下の観点からコードを評価します。

## レビュー観点

1. **セキュリティ**
   - SQL インジェクション
   - XSS 脆弱性
   - 認証・認可の問題
   - 機密情報の露出

2. **パフォーマンス**
   - アルゴリズムの効率性
   - メモリ使用量
   - データベースクエリの最適化
   - キャッシング戦略

3. **保守性**
   - コードの可読性
   - 命名規則の一貫性
   - コメントとドキュメンテーション
   - モジュール性と結合度

4. **テスト**
   - テストカバレッジ
   - エッジケースの処理
   - テストの品質

## レビュープロセス

1. コード全体の構造を理解
2. 各観点で問題を特定
3. 具体的で実行可能な改善提案を提供
4. 優先順位付け（クリティカル/重要/改善推奨）

言語固有のベストプラクティスについては、以下を参照：
- [javascript-practices.md](javascript-practices.md)
- [python-practices.md](python-practices.md)
- [go-practices.md](go-practices.md)
```

### 3. データベース管理スキル

```markdown
---
name: database-admin
description: データベーススキーマ設計、クエリ最適化、マイグレーション管理、パフォーマンスチューニングを実行します。データベース設計や最適化が必要な場合に使用してください。
allowed-tools:
  - Read
  - Write
  - Bash
  - Edit
---

# データベース管理スキル

## スキーマ設計

### ベストプラクティス
- 正規化の原則
- インデックス戦略
- 外部キー制約
- データ型の選択

### テンプレート
- `templates/migration.sql`: マイグレーションテンプレート
- `templates/schema.sql`: スキーマ定義テンプレート

## クエリ最適化

### 分析ツール
- `scripts/explain_analyzer.py`: EXPLAIN 出力の解析
- `scripts/slow_query_finder.sh`: スロークエリの検出

### 最適化手法
1. インデックスの適切な使用
2. クエリの書き換え
3. サブクエリの最適化
4. JOIN の効率化

詳細な最適化ガイドは [optimization-guide.md](optimization-guide.md) を参照。

## マイグレーション管理

### 安全なマイグレーション手順
1. バックアップの作成
2. トランザクションでの実行
3. ロールバック計画の準備
4. 段階的なデプロイ

検証スクリプト: `scripts/validate_migration.py`

## パフォーマンスモニタリング

定期的なパフォーマンスチェックリスト：
- [ ] スロークエリログの確認
- [ ] インデックス使用率の分析
- [ ] テーブルサイズの監視
- [ ] 接続プールの最適化
```

## ベストプラクティス

### 1. 効果的な説明文の記述

**良い例**:
```yaml
description: PDF からテキストや表を抽出し、フォーム入力、ドキュメントマージを実行します。PDF ファイル操作時に使用してください。
```

**悪い例**:
```yaml
description: ドキュメントの処理を支援します。
```

説明文には以下を含めてください：
- 具体的な機能の列挙
- 使用タイミングのトリガーキーワード
- 主要な対応フォーマットやタスクタイプ

### 2. SKILL.md のサイズ管理

- **500行以内を目標**: メイン SKILL.md ファイルは簡潔に保つ
- **段階的開示パターンの活用**: 詳細情報は別ファイルに分離

#### パターン1: 機能レベルでの分離

```markdown
# 基本機能

[簡潔な説明]

## 高度な機能

詳細は [advanced-features.md](advanced-features.md) を参照。
```

#### パターン2: ドメイン別の整理

```markdown
# 財務分析

財務データの処理は [finance-guide.md](finance-guide.md) を参照。

# 営業分析

営業データの処理は [sales-guide.md](sales-guide.md) を参照。
```

#### パターン3: 条件付き詳細

```markdown
# 基本的な使い方

[基本内容を表示]

高度な設定が必要な場合は [advanced-config.md](advanced-config.md) を参照。
```

### 3. 参照ファイルの構造化

長い参照ファイルには目次を含めることで、Claude が部分的に読み込んだ場合でも利用可能な情報を把握できます。

```markdown
# データ分析リファレンス

## 目次
1. [統計分析](#統計分析)
2. [機械学習](#機械学習)
3. [時系列分析](#時系列分析)
4. [テキスト分析](#テキスト分析)

## 統計分析
[詳細な内容]

## 機械学習
[詳細な内容]
```

### 4. 適切な自由度の設定

タスクの脆弱性に応じて指示の詳細度を調整します：

**高い自由度（柔軟なアプローチ）**
```markdown
データの異常値を検出し、適切な方法で処理してください。
```

**中程度の自由度（推奨パターン提示）**
```markdown
異常値検出は以下の手順で実行：
1. IQR 法で外れ値を特定
2. ドメイン知識に基づいて検証
3. {method} パラメータで処理方法を選択
```

**低い自由度（具体的スクリプト）**
```markdown
異常値処理には `scripts/detect_outliers.py` を使用してください。
このスクリプトは統計的に検証済みの手法を実装しています。
```

### 5. 実行可能コードのベストプラクティス

**エラー処理を明示的に実装**

```python
# 良い例
def process_data(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    try:
        data = pd.read_csv(file_path)
    except pd.errors.EmptyDataError:
        raise ValueError("CSV ファイルが空です")
    except Exception as e:
        raise ValueError(f"データ読み込みエラー: {str(e)}")

    return data

# 悪い例
def process_data(file_path):
    data = pd.read_csv(file_path)  # エラー時に失敗するだけ
    return data
```

**設定値の文書化**

```python
# 良い例
OUTLIER_THRESHOLD = 3.0  # IQR法: 3.0は一般的な閾値（外れ値検出の標準）
MAX_ITERATIONS = 100     # 収束判定: 100回で十分な精度を確保

# 悪い例
THRESHOLD = 3.0  # マジックナンバー、理由不明
MAX_ITER = 100
```

**検証ループの実装**

```python
# バッチ処理の検証パターン
def batch_process():
    # 1. 分析フェーズ
    files = analyze_input_files()

    # 2. 計画作成
    plan = create_processing_plan(files)
    save_plan("plan.json", plan)

    # 3. 計画の検証
    if not validate_plan(plan):
        raise ValueError("計画の検証に失敗")

    # 4. 実行
    results = execute_plan(plan)

    # 5. 結果検証
    verify_results(results)

    return results
```

### 6. 避けるべきアンチパターン

**❌ 時間依存情報を含める**
```markdown
このAPIは2025年8月まで使用してください。
```

**✅ 代わりに構造化して整理**
```markdown
## 現在推奨されるAPI

[現在のAPI情報]

<details>
<summary>レガシーAPI（非推奨）</summary>
[古いAPI情報]
</details>
```

**❌ 複数の同等オプションを提示**
```markdown
方法A、方法B、方法Cのいずれかを選択できます。
```

**✅ デフォルトと例外を明示**
```markdown
デフォルトで方法Aを使用します。特別な要件がある場合は方法Bを検討してください。
```

**❌ バックスラッシュを使用したパス**
```markdown
reference\guide.md  # Windows特有
```

**✅ フォワードスラッシュを使用**
```markdown
reference/guide.md  # クロスプラットフォーム対応
```

### 7. 一貫した用語の使用

同じ概念に対して複数の用語を使わないでください。

**悪い例**:
- "API endpoint"
- "API route"
- "API path"

**良い例**:
- プロジェクト全体で "API endpoint" に統一

### 8. 具体的な例の提供

抽象的な説明ではなく、具体的なコード例を含めてください。

```markdown
## データ変換

**抽象的（避ける）**:
データを適切な形式に変換します。

**具体的（推奨）**:
```python
# CSV を JSON に変換
import pandas as pd

df = pd.read_csv('data.csv')
df.to_json('data.json', orient='records', indent=2)
```

## テストとデバッグ

### 反復的開発アプローチ

Claude との反復的開発が効果的です：

1. **Claude にスキルを作成させる**: 1つの Claude インスタンスでスキルを設計
2. **別の Claude でテスト**: 他の Claude インスタンスで実際に使用
3. **観察と改善**: エージェントが苦労する箇所を特定して指示を洗練
4. **繰り返し**: 実際の動作に基づいて改善

### 評価シナリオの作成

本格的なドキュメント作成前に評価シナリオを構築することで、実際の問題を解決できます。

**最低3つのテストシナリオを作成**:

1. **基本ケース**: 一般的な使用パターン
2. **エッジケース**: 境界条件やエラー処理
3. **複雑なケース**: 複数機能の組み合わせ

### モデル横断テスト

サポート予定のすべてのモデルでテスト：

- **Claude Opus**: 最も高度、複雑なタスクに対応
- **Claude Sonnet**: バランス型、日常的な使用
- **Claude Haiku**: 高速・軽量、より詳細な指示が必要な場合あり

Opus で機能しても Haiku では追加の詳細が必要な場合があります。

### デバッグのヒント

スキルが期待通りに動作しない場合：

1. **説明文を確認**: トリガーキーワードが適切か
2. **ツール制限を確認**: 必要なツールへのアクセスが許可されているか
3. **参照パスを確認**: すべてのファイルパスが正しいか（フォワードスラッシュ使用）
4. **ログを確認**: Claude がスキルを読み込んだかどうか
5. **段階的に簡素化**: 複雑なスキルを基本バージョンから構築

## API でのスキル使用

### 利用可能なスキルの取得

```python
import anthropic

client = anthropic.Anthropic()

skills = client.beta.skills.list(
    source="anthropic",
    betas=["skills-2025-10-02"]
)

for skill in skills.data:
    print(f"{skill.id}: {skill.display_title}")
```

### メッセージ作成時にスキルを指定

```python
response = client.beta.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    betas=["code-execution-2025-08-25", "skills-2025-10-02"],
    container={
        "skills": [
            {
                "type": "anthropic",
                "skill_id": "pptx",
                "version": "latest"
            }
        ]
    },
    messages=[{
        "role": "user",
        "content": "再生可能エネルギーについて5スライドのプレゼンテーションを作成してください"
    }],
    tools=[{
        "type": "code_execution_20250825",
        "name": "code_execution"
    }]
)
```

### 生成ファイルのダウンロード

```python
file_id = None
for block in response.content:
    if block.type == 'tool_use' and block.name == 'code_execution':
        for result_block in block.content:
            if hasattr(result_block, 'file_id'):
                file_id = result_block.file_id
                break

if file_id:
    file_content = client.beta.files.download(
        file_id=file_id,
        betas=["files-api-2025-04-14"]
    )

    with open("output.pptx", "wb") as f:
        file_content.write_to_file(f.name)
```

### 他のドキュメントタイプの例

**Excel スプレッドシート**:
```python
"skill_id": "xlsx"
```

**Word ドキュメント**:
```python
"skill_id": "docx"
```

**PDF**:
```python
"skill_id": "pdf"
```

## チームでのスキル共有

### プロジェクトスキルの共有

プロジェクトレベルのスキル（`.claude/skills/`）は Git でバージョン管理し、チーム全体で共有できます。

```bash
# プロジェクトスキルの追加
mkdir -p .claude/skills/team-code-reviewer
cat > .claude/skills/team-code-reviewer/SKILL.md << 'EOF'
---
name: team-code-reviewer
description: チーム標準に基づいたコードレビューを実施
---

# チームコードレビュー基準

[チーム固有の基準]
EOF

# Git に追加
git add .claude/skills/
git commit -m "Add team code review skill"
git push
```

### スキルのドキュメント化

チームメンバーが簡単に理解できるよう、README を作成します。

```markdown
# プロジェクトスキル

## 利用可能なスキル

### team-code-reviewer
チームのコーディング基準に基づいたコードレビューを実施します。

**使用タイミング**: プルリクエスト作成前のコードレビュー

**主な機能**:
- チーム固有のスタイルガイド遵守確認
- プロジェクト特有のアンチパターン検出
- セキュリティベストプラクティス検証

### database-migration-helper
データベーススキーマのマイグレーション作成を支援します。

**使用タイミング**: データベーススキーマ変更時

**主な機能**:
- 安全なマイグレーションスクリプト生成
- ロールバック計画の作成
- マイグレーション前の検証
```

## セキュリティと制限事項

### セキュリティ考慮事項

- **信頼できるソースのみ使用**: 不明なソースからのスキルは慎重に評価
- **ツール制限の活用**: 必要最小限のツールアクセスのみ許可
- **機密情報の保護**: スキル内に API キーや認証情報を含めない

### 技術的制限

- **ネットワークアクセスなし**: スキルは外部 API を直接呼び出せません
- **実行時パッケージインストール不可**: 事前インストールされたパッケージのみ使用可能
- **クロスプラットフォーム同期なし**: プラットフォーム間でスキルは自動同期されません

### 共有スコープ

- **Claude.ai**: 個別ユーザーレベル
- **API**: ワークスペース全体で共有

## まとめ

Claude Code のスキル機能は、領域固有の専門知識をモジュール化し、効率的に再利用するための強力なツールです。

### 主なポイント

1. **3層アーキテクチャ**: 効率的なトークン消費で多数のスキルを維持可能
2. **自動呼び出し**: Claude が文脈に応じて適切なスキルを自動選択
3. **段階的開示**: 必要な情報のみを段階的に読み込み
4. **チーム共有**: プロジェクトスキルを Git で管理しチーム全体で活用
5. **ベストプラクティス**: 明確な説明、簡潔な構造、段階的な詳細提供

### 次のステップ

1. **小規模から開始**: 簡単なスキルから作成を始める
2. **反復的に改善**: 実際の使用状況に基づいて洗練
3. **チームで共有**: プロジェクト固有のスキルをチームで活用
4. **評価とテスト**: 複数のシナリオとモデルで検証

スキル機能を活用して、開発ワークフローをより効率的かつ一貫性のあるものにしていきましょう。

## 参考リンク

- [Claude Code 公式ドキュメント](https://docs.claude.com/ja/docs/claude-code/overview)
- [Agent Skills 概要](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
- [Skills API リファレンス](https://docs.claude.com/en/api/skills-guide)
