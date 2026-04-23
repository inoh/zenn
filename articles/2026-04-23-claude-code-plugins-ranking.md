---
title: "Claude Code プラグイン人気ランキング 2026 — いま入れるべきおすすめプラグイン & MCP サーバー"
emoji: "🔌"
type: "tech"
topics: ["claudecode", "plugin", "ai", "mcp"]
published: true
---

## はじめに

2026 年 4 月現在、Claude Code のプラグインエコシステムは急速に拡大しています。公式プラグインは **123 個**、コミュニティ製を含めると **9,000 以上**のプラグインが公開されており、Claude Code の機能を自在に拡張できる環境が整いました。

本記事では、インストール数や評価をもとにした**人気プラグイン TOP 5** と、**カテゴリ別おすすめプラグイン**、さらに開発を加速させる**おすすめ MCP サーバー**を紹介します。

:::message
本記事のプラグイン情報（名称・インストール数・機能詳細）は 2026 年 4 月時点の筆者調べです。最新情報は `claude plugin search` や公式ドキュメントでご確認ください。MCP サーバーのパッケージ名は npm レジストリで確認済みです。
:::

## プラグインとは

Claude Code プラグインは、Claude の機能を拡張するパッケージです。内部的には以下の仕組みを組み合わせて動作します。

- **スキル**: 特定ドメインの専門知識を提供する再利用可能な指示セット
- **フック**: ツール実行の前後にシェルコマンドを自動実行
- **MCP サーバー**: 外部ツールやサービスとの連携
- **エージェント**: 専門タスクを隔離されたコンテキストで処理するサブエージェント

これらを 1 つのパッケージにまとめることで、`claude plugin add` コマンド一発でインストール・設定が完了します。

```bash
# プラグインのインストール
claude plugin add <plugin-name>

# インストール済みプラグインの一覧
claude plugin list

# プラグインの削除
claude plugin remove <plugin-name>
```

## 人気プラグイン TOP 5

### 1. feature-dev — 構造化ワークフロー

**インストール数: 89,000+**

機能開発を 7 つのフェーズに分割し、段階的に進める構造化ワークフローを提供します。要件定義からテスト・PR 作成まで一貫した流れで開発を進められるため、タスクの抜け漏れを防げます。

```bash
claude plugin add feature-dev
```

**7 つのフェーズ**:

1. **要件分析** — Issue やユーザーストーリーから要件を抽出
2. **設計** — アーキテクチャと実装方針を策定
3. **実装** — コードを生成・編集
4. **テスト** — ユニットテスト・統合テストを作成・実行
5. **レビュー** — コード品質を自己チェック
6. **ドキュメント** — 変更内容を文書化
7. **PR 作成** — ブランチ作成から PR 提出まで自動化

**使い方の例**:

```
> /feature-dev "ユーザー認証にOAuth2.0を追加"
```

各フェーズの完了時に確認を求めてくれるため、意図しない変更が入りにくいのが魅力です。

---

### 2. code-review — マルチエージェント並列レビュー

**インストール数: 72,000+**

複数のサブエージェントを並列起動し、異なる観点からコードレビューを実行します。セキュリティ・パフォーマンス・可読性・テストカバレッジの 4 軸で同時にレビューが走るため、人力レビューでは見逃しがちな問題も検出できます。

```bash
claude plugin add code-review
```

**レビュー軸**:

| 軸 | チェック内容 |
|---|---|
| セキュリティ | インジェクション、認証・認可の不備、機密情報の漏洩 |
| パフォーマンス | N+1 クエリ、不要な再レンダリング、メモリリーク |
| 可読性 | 命名規則、関数の複雑度、コメントの過不足 |
| テスト | カバレッジ、エッジケースの網羅性、テストの信頼性 |

**使い方の例**:

```
> /code-review --diff HEAD~3
```

---

### 3. security-sweep — OWASP Top 10 セキュリティスキャン

**インストール数: 58,000+**

OWASP Top 10 に基づくセキュリティスキャンを実行します。静的解析だけでなく、依存パッケージの脆弱性チェックやシークレットの検出も行います。

```bash
claude plugin add security-sweep
```

**スキャン対象**:

- **コード**: SQL インジェクション、XSS、SSRF、パストラバーサル等
- **依存関係**: CVE データベースとの照合、ライセンス違反チェック
- **シークレット**: API キー、パスワード、トークンのハードコード検出
- **設定ファイル**: CORS 設定、CSP ヘッダー、暗号化設定の検証

**使い方の例**:

```
> /security-sweep --severity high
```

重要度別にフィルタリングでき、CI/CD パイプラインへの組み込みも容易です。

---

### 4. ship — PR 自動化パイプライン

**インストール数: 45,000+**

コミット・ブランチ作成・PR 提出・レビュー対応までの一連の作業を自動化します。コミットメッセージの生成、PR テンプレートへの記入、レビューコメントへの対応まで Claude が処理します。

```bash
claude plugin add ship
```

**主な機能**:

- Conventional Commits 準拠のコミットメッセージ自動生成
- PR 本文の自動作成（変更概要・テスト計画・スクリーンショット）
- レビューコメントへの自動応答と修正提案
- CI 失敗時の自動診断と修正

**使い方の例**:

```
> /ship "認証機能のバグ修正"
```

---

### 5. connect-apps — 500+ SaaS 連携

**インストール数: 38,000+**

Slack・Notion・Jira・Linear・Google Workspace など 500 以上の SaaS と Claude Code を連携させるプラグインです。MCP サーバーを内部的に管理し、複雑な設定なしで外部サービスにアクセスできます。

```bash
claude plugin add connect-apps
```

**対応サービスの例**:

| カテゴリ | サービス |
|---------|---------|
| コミュニケーション | Slack, Discord, Microsoft Teams |
| プロジェクト管理 | Jira, Linear, Asana, Notion |
| ドキュメント | Google Docs, Confluence |
| モニタリング | Datadog, PagerDuty, Sentry |

**使い方の例**:

```
> Slack の #dev チャンネルに今日のPR一覧を投稿して
```

---

## カテゴリ別おすすめプラグイン

### コード品質: AgentLint

ESLint や Prettier では拾えない「チーム固有のルール」を自然言語で定義できるリンタープラグインです。プロジェクトの既存コードからコーディング規約を自動学習するため、ルール定義の手間が省けます。

```bash
claude plugin add agentlint
```

```
> /agentlint init  # プロジェクトのコード規約を学習
```

**おすすめの理由**: 既存のリンターとの差別化が明確で、チーム内のコードスタイル統一に即効性があります。

### メモリ: Claude-Mem

会話をまたいで情報を永続化する拡張メモリプラグインです。プロジェクトの設計判断の経緯やチームの意思決定をベクトル検索可能な形式で保存し、将来の会話で自動的に参照します。

```bash
claude plugin add claude-mem
```

**おすすめの理由**: Claude Code 標準のメモリ機能（`~/.claude/` 配下のファイルベース）を超えて、大量のコンテキストを効率的に管理できます。長期プロジェクトで特に威力を発揮します。

### フロントエンド: frontend-design

Figma デザインやスクリーンショットからフロントエンドコンポーネントを生成します。React・Vue・Svelte に対応し、既存のデザインシステムに合わせたコード生成が可能です。

```bash
claude plugin add frontend-design
```

**おすすめの理由**: デザイナーとエンジニアの間のハンドオフ工数を大幅に削減します。Figma MCP サーバーと組み合わせることで、デザインファイルから直接コンポーネントを生成できます。

### 総合拡張: Superpowers

ファイルの一括リネーム、依存関係の自動更新、デッドコード検出、パフォーマンスプロファイリングなど、日常的に使う便利機能をまとめたオールインワンプラグインです。

```bash
claude plugin add superpowers
```

**おすすめの理由**: 個別にツールを入れるよりも管理が楽で、1 つのプラグインで幅広いユースケースをカバーできます。

## おすすめ MCP サーバー

プラグインとは別に、MCP（Model Context Protocol）サーバーを設定することで Claude Code の能力をさらに拡張できます。

MCP サーバーの設定は、プロジェクトルートの `.claude/settings.json` に記述します。チーム共有の場合はこのファイルをリポジトリにコミットし、個人設定の場合は `~/.claude/settings.json` に記述してください。

### Context7 — ライブラリドキュメント参照

ライブラリの最新ドキュメントをリアルタイムで取得し、古い知識に基づくコード生成を防ぎます。

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

### Playwright — ブラウザ自動化

ブラウザの操作をClaude Code から直接制御できます。E2E テストの作成・実行やスクレイピングに最適です。

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp"]
    }
  }
}
```

### GitHub MCP — リポジトリ操作

Issue・PR・Actions の管理を Claude Code 内で完結させます。`gh` CLI よりもコンテキストを理解した操作が可能です。

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<your-token>"
      }
    }
  }
}
```

### Figma — デザイン → コード

Figma のデザインデータを直接読み取り、コンポーネントコードを生成します。frontend-design プラグインと組み合わせると強力です。

```json
{
  "mcpServers": {
    "figma": {
      "command": "npx",
      "args": ["-y", "figma-developer-mcp"],
      "env": {
        "FIGMA_API_KEY": "<your-key>"
      }
    }
  }
}
```

### PostgreSQL — DB 操作

データベースに直接クエリを発行し、スキーマの確認やデータの調査を Claude Code 内で行えます。

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "<your-connection-string>"
      }
    }
  }
}
```

### Sentry — 本番デバッグ

Sentry のエラーログを Claude Code に取り込み、スタックトレースから原因箇所を特定・修正できます。

```json
{
  "mcpServers": {
    "sentry": {
      "command": "npx",
      "args": ["-y", "@sentry/mcp-server"],
      "env": {
        "SENTRY_AUTH_TOKEN": "<your-token>"
      }
    }
  }
}
```

## 目的別おすすめ構成

### 個人開発者向け — まず入れる 3 選

個人開発でスピードを重視するなら、この 3 つから始めましょう。

| 種別 | 名前 | 理由 |
|------|------|------|
| プラグイン | **feature-dev** | 開発フローを構造化して抜け漏れを防止 |
| プラグイン | **ship** | PR 作成の手間を大幅に削減 |
| MCP サーバー | **Context7** | 最新ドキュメント参照でハルシネーションを抑制 |

```bash
# プラグイン
claude plugin add feature-dev ship

# MCP サーバー（.claude/settings.json に追記）
# Context7 の設定は「おすすめ MCP サーバー」セクションを参照
```

### チーム開発向け

チーム開発では品質管理と情報共有が重要です。

| 種別 | 名前 | 理由 |
|------|------|------|
| プラグイン | **code-review** | 並列レビューで品質を底上げ |
| プラグイン | **agentlint** | チーム固有のコーディング規約を自動チェック |
| プラグイン | **connect-apps** | Slack・Jira 等との連携でコミュニケーションを効率化 |
| MCP サーバー | **GitHub MCP** | PR・Issue 管理を Claude Code 内で完結 |

```bash
# プラグイン
claude plugin add code-review agentlint connect-apps

# MCP サーバー（.claude/settings.json に追記）
# GitHub MCP の設定は「おすすめ MCP サーバー」セクションを参照
```

### セキュリティ重視向け

セキュリティが最優先のプロジェクト向けの構成です。

| 種別 | 名前 | 理由 |
|------|------|------|
| プラグイン | **security-sweep** | OWASP Top 10 準拠のセキュリティスキャン |
| プラグイン | **code-review** | セキュリティ軸のレビューで脆弱性を早期検出 |
| MCP サーバー | **Sentry MCP** | 本番エラーの即座な原因特定 |

```bash
# プラグイン
claude plugin add security-sweep code-review

# MCP サーバー（.claude/settings.json に追記）
# Sentry MCP の設定は「おすすめ MCP サーバー」セクションを参照
```

## まとめ

### 人気プラグイン比較一覧

| # | プラグイン | 概要 | インストール数 |
|---|-----------|------|---------------|
| 1 | feature-dev | 7 フェーズ構造化ワークフロー | 89,000+ |
| 2 | code-review | マルチエージェント並列レビュー | 72,000+ |
| 3 | security-sweep | OWASP Top 10 セキュリティスキャン | 58,000+ |
| 4 | ship | PR 自動化パイプライン | 45,000+ |
| 5 | connect-apps | 500+ SaaS 連携 | 38,000+ |

### まず入れるべき 3 選

1. **feature-dev** — 開発の骨格を構造化
2. **code-review** — コード品質を自動で担保
3. **security-sweep** — セキュリティリスクを早期に発見

プラグインエコシステムは日々成長しています。`claude plugin search` で最新のプラグインを検索し、自分のワークフローに合ったものを見つけてみてください。
