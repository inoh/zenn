---
title: "Claude Code プラグインおすすめ 2026 — 公式マーケットプレイスから入れるべきプラグイン & MCP サーバー"
emoji: "🔌"
type: "tech"
topics: ["claudecode", "plugin", "mcp", "ai"]
published: true
---

## はじめに

Claude Code のプラグインエコシステムが急速に拡大しています。2026 年 4 月時点で、公式マーケットプレイス（[claude-plugins-official](https://github.com/anthropics/claude-plugins-official)）には **160 個**のプラグインが登録されています。うち **32 個が Anthropic 製**、残りはサードパーティ製です。

しかし、数が多すぎて「結局どれを入れればいいの？」と迷う方も多いのではないでしょうか。

この記事では、公式マーケットプレイスの中身を実際に確認した上で、**おすすめのプラグイン**と **MCP サーバー系プラグイン**を紹介します。

## プラグインの基本

### プラグインとは

Claude Code プラグインは、**スキル・フック・MCP サーバー・エージェント**をパッケージ化して配布する仕組みです。プラグインをインストールするだけで、新しいスラッシュコマンドやツールが使えるようになります。

### インストール方法

```bash
# 公式マーケットプレイスからインストール
claude plugin install <プラグイン名>

# 特定のマーケットプレイスを指定する場合
claude plugin install <プラグイン名>@<マーケットプレイス名>

# インストール済みプラグインの確認
claude plugin list

# プラグインの更新
claude plugin update <プラグイン名>

# アンインストール
claude plugin uninstall <プラグイン名>
```

公式マーケットプレイス以外のプラグインを使いたい場合は、マーケットプレイスの追加も可能です。

```bash
# マーケットプレイスを追加（GitHub リポジトリから）
claude plugin marketplace add <owner>/<repo>

# マーケットプレイス一覧
claude plugin marketplace list
```

### コマンドの名前空間に注意

プラグイン経由でインストールしたコマンドは、**名前空間（namespace）が付与**されます。形式は `/<プラグイン名>:<コマンド名>` です。

```bash
# プラグイン経由のコマンド
/feature-dev:feature-dev
/code-review:code-review
/commit-commands:commit

# .claude/commands/ に直接置いた場合（名前空間なし）
/feature-dev
```

これは複数のプラグインが同名のコマンドを持つ場合の衝突を防ぐ仕組みです。公式の README では短縮形で `/feature-dev` のように記載されていることがありますが、**実際にプラグインとしてインストールすると `/<プラグイン名>:<コマンド名>` の形式**になります。

:::message
Claude Code 会話中に `/` を入力するとコマンド補完が表示されるので、正確なコマンド名はそこで確認できます。
:::

## おすすめプラグイン — Anthropic 製

### feature-dev — 構造化された機能開発ワークフロー

機能開発を **7 つのフェーズ**に構造化し、Claude が各フェーズを順に実行するプラグインです。Anthropic の Sid Bidasaria 氏が作成。

```bash
# インストール
claude plugin install feature-dev

# 使い方
/feature-dev:feature-dev ユーザー認証に OAuth を追加
```

**7 フェーズ:**

1. **Discovery（要件整理）** — 要求の明確化、制約の特定
2. **Codebase Exploration（コード調査）** — `code-explorer` エージェントが並列で既存コードを分析
3. **Clarifying Questions（質問）** — 曖昧な点をすべて洗い出し、回答を待ってから次へ
4. **Architecture Design（設計）** — `code-architect` エージェントが複数の実装方針を提案し、比較
5. **Implementation（実装）** — ユーザーの承認後にコーディング開始
6. **Quality Review（レビュー）** — `code-reviewer` エージェントが並列でコード品質をチェック（信頼度 80 以上のみ報告）
7. **Summary（まとめ）** — 変更内容・決定事項・次のステップを記録

「いきなりコードを書き始める」のではなく、**設計を先に固めてから実装に入る**のがポイントです。エージェントが自動で探索・設計・レビューを並列実行するため、複雑な機能追加で威力を発揮します。

### code-review — マルチエージェント並列コードレビュー

PR を **4 つの専門エージェントが並列でレビュー**するプラグインです。Anthropic の Boris Cherny 氏が作成。

```bash
# インストール
claude plugin install code-review

# 使い方
/code-review:code-review
```

**4 つのエージェント:**

| # | 担当 | 内容 |
|---|------|------|
| 1-2 | CLAUDE.md 準拠 | プロジェクトのガイドラインに沿っているか |
| 3 | バグ検出 | 変更箇所の明らかなバグ（既存の問題は対象外） |
| 4 | 履歴分析 | git blame/history から文脈を読み取る |

各 issue に **0〜100 の信頼度スコア**を付与し、デフォルトで **80 未満はフィルタ**されます。これにより false positive を大幅に削減しています。

レビュー結果は GitHub PR にコメントとして投稿されます。すでにレビュー済み・ドラフト・クローズ済みの PR は自動でスキップされます。

### commit-commands — Git ワークフローの自動化

コミット・プッシュ・PR 作成を簡単なコマンドで実行できるプラグインです。

```bash
# インストール
claude plugin install commit-commands

# 使い方
/commit-commands:commit        # 変更を分析してコミット
/commit-commands:commit-push-pr  # コミット→プッシュ→PR作成を一気に
/commit-commands:clean_gone    # マージ済みブランチのクリーンアップ
```

`/commit-commands:commit` は、staged/unstaged の変更を分析し、リポジトリのコミットスタイルに合ったメッセージを自動生成します。

### frontend-design — AI っぽくないフロントエンドデザイン

Claude がフロントエンドのコードを書く際に、**汎用的な「AI っぽい」デザインを避けて個性的な UI を生成**するスキルプラグインです。

```bash
# インストール
claude plugin install frontend-design
```

このプラグインはスラッシュコマンドではなく**スキル**として動作します。インストールするだけで、フロントエンド関連のタスクを依頼した際に Claude が自動的にこのスキルを参照し、以下のような品質でコードを生成します。

- 大胆なタイポグラフィ・カラーパレット
- インパクトのあるアニメーション
- コンテキストに応じた実装判断

### security-guidance — セキュリティ警告フック

ファイル編集時にセキュリティリスクを**自動で警告するフック**プラグインです。

```bash
# インストール
claude plugin install security-guidance
```

このプラグインは**コマンドではなくフック**として動作します。`Edit` / `Write` などのツール使用前に Python スクリプトが実行され、コマンドインジェクション・XSS・安全でないコードパターンなどの潜在的リスクを検出して警告します。

:::message alert
**注意**: Web 上で「security-sweep」というプラグインが紹介されていることがありますが、公式マーケットプレイスに security-sweep は存在しません。セキュリティ関連の Anthropic 製プラグインは **security-guidance** です。
:::

### その他の Anthropic 製プラグイン

| プラグイン | 種別 | 概要 |
|---|---|---|
| **pr-review-toolkit** | エージェント | コメント精度・テストカバレッジ・エラーハンドリング・型設計・コード品質・簡潔化の 6 エージェントで PR を多角的にレビュー |
| **hookify** | スキル | hooks.json を直接編集せず、Markdown ファイルで簡単にフックを作成。会話パターンの分析から自動ルール生成も可能 |
| **playground** | スキル | インタラクティブな HTML プレイグラウンド（コントロール + ライブプレビュー + プロンプト出力）を単一ファイルで生成 |
| **skill-creator** | スキル | 新しいスキルの作成・改善・パフォーマンス測定（eval 実行・ベンチマーク） |
| **plugin-dev** | スキル | プラグイン開発ツールキット。フック・MCP・構造・コマンド・エージェント・スキルの 7 つの専門スキルを提供 |
| **session-report** | スキル | セッションの使用状況（トークン数・キャッシュ・コスト）を HTML レポートとして出力 |
| **code-simplifier** | エージェント | コードの簡潔化・一貫性向上・保守性改善に特化したリファクタリングエージェント |
| **explanatory-output-style** | スキル | 実装の選択理由やコードベースのパターンについて教育的な解説を追加する出力スタイル |
| **LSP 系**（13 個） | LSP | TypeScript, Python, Go, Rust, Ruby, Java, C#, Kotlin, C/C++, PHP, Lua, Swift, Elixir の各言語サーバー |

## おすすめプラグイン — サードパーティ製

### superpowers — Claude の思考力を底上げ

Claude の**計画・質問・デバッグの質を向上**させるプラグインです。[obra 氏](https://github.com/obra/superpowers)が開発。

```bash
# 公式マーケットプレイスに登録済み
claude plugin install superpowers
```

- ブレインストーミング強化
- サブエージェント駆動の開発ワークフロー
- Red/Green TDD の実践
- 体系的なデバッグ手法
- 新しいスキルの自動作成・テスト

### codex（OpenAI）— AI コードレビューの多角化

Claude Code 内から **OpenAI Codex を呼び出し**、セカンドオピニオンのレビューやタスク委譲ができるプラグインです。

```bash
# OpenAI のマーケットプレイスを追加
claude plugin marketplace add openai/codex-plugin-cc

# インストール
claude plugin install codex@openai-codex
```

:::message
codex プラグインについては、別記事「[Claude Code × OpenAI Codex プラグインで AI コードレビューを多角化する](https://zenn.dev/inouehiroyuki/articles/2026-04-05-claude-code-codex-plugin)」で詳しく解説しています。
:::

### coderabbit — 外部 AI によるコードレビュー

CodeRabbit の専用 AI アーキテクチャと **40 以上の静的解析ツール**を組み合わせたコードレビュープラグインです。

```bash
claude plugin install coderabbit
```

### その他の注目サードパーティプラグイン

| プラグイン | カテゴリ | 概要 |
|---|---|---|
| **exa** | 検索 | Exa AI による Web 検索・ディープリサーチ・コンテンツ抽出 |
| **firecrawl** | 開発 | Web スクレイピング。任意の Web サイトを LLM 向けのクリーンなデータに変換 |
| **expo** | 開発 | React Native / Expo アプリのビルド・デプロイ・デバッグ |
| **stripe** | 開発 | Stripe 決済統合の開発支援 |
| **auth0** | セキュリティ | フレームワークを自動検出して Auth0 認証を追加 |
| **semgrep** | セキュリティ | リアルタイムのセキュリティ脆弱性検出 |
| **sonarqube** | セキュリティ | SonarQube のコード品質・セキュリティ基準を自動適用 |

## MCP サーバー系プラグイン

公式マーケットプレイスには、**MCP サーバーをプラグインとしてラップ**したものも多数登録されています。`claude plugin install` だけで MCP サーバーの設定が完了するため、`.mcp.json` を手動で書く必要がありません。

### ドキュメント参照

| プラグイン | 提供元 | 概要 |
|---|---|---|
| **context7** | Upstash | React・Next.js・Prisma 等のバージョン別最新ドキュメントを取得。古い API を使ってしまう問題を解消 |

### ブラウザ・テスト

| プラグイン | 提供元 | 概要 |
|---|---|---|
| **playwright** | Microsoft | ブラウザ操作の自動化、E2E テスト、スクリーンショット取得、フォーム操作 |

### 開発ツール連携

| プラグイン | 提供元 | 概要 |
|---|---|---|
| **github** | GitHub | リポジトリ・PR・Issue・コードレビューの操作 |
| **gitlab** | GitLab | リポジトリ・MR・CI/CD パイプラインの管理 |
| **linear** | Linear | Issue トラッキング・プロジェクト管理 |
| **sentry** | Sentry | エラーレポートの閲覧・スタックトレース分析・本番デバッグ |
| **figma** | Figma | デザインファイルへのアクセス・コンポーネント情報の抽出・デザイントークンの取得 |

### データベース

| プラグイン | 提供元 | 概要 |
|---|---|---|
| **mongodb** | MongoDB | データベース接続・クエリ・スキーマ管理 |
| **supabase** | Supabase | DB 操作・認証・ストレージ・エッジファンクション |
| **neon** | Neon | サーバーレス PostgreSQL のプロジェクト・DB 管理 |
| **firebase** | Google | Firestore・認証・Cloud Functions の管理 |
| **prisma** | Prisma | PostgreSQL の DB 管理・スキーママイグレーション・SQL 実行 |

### デプロイ・インフラ

| プラグイン | 提供元 | 概要 |
|---|---|---|
| **vercel** | Vercel | デプロイ管理・ビルド状況確認・環境設定 |
| **cloudflare** | Cloudflare | Workers・Durable Objects・Agents SDK の開発 |
| **railway** | Railway | アプリ・DB・インフラのデプロイと管理 |
| **terraform** | HashiCorp | Terraform エコシステムとの統合 |

### コミュニケーション

| プラグイン | 提供元 | 概要 |
|---|---|---|
| **slack** | Slack | メッセージ検索・チャンネルアクセス・スレッド閲覧 |
| **notion** | Notion | ページ検索・ドキュメント作成・DB 管理 |
| **atlassian** | Atlassian | Jira・Confluence の検索・作成・管理 |

## 目的別おすすめ構成

### 個人開発者 — まずはこの 3 つから

```bash
claude plugin install feature-dev
claude plugin install commit-commands
claude plugin install security-guidance
```

**feature-dev** で設計から実装、**commit-commands** でコミット・PR 作成、**security-guidance** でファイル編集時のセキュリティ警告。個人開発のワークフローを一通りカバーできます。

### チーム開発 — レビューを自動化

```bash
claude plugin install feature-dev
claude plugin install code-review
claude plugin install commit-commands
```

**code-review** の 4 エージェント並列レビューが、チーム内のレビュー負荷を軽減します。信頼度スコアによるフィルタリングで、ノイズの少ないレビューコメントが GitHub PR に自動投稿されます。

### 多角的な品質チェック

```bash
claude plugin install code-review
claude plugin install security-guidance

# Codex プラグインで別の AI の視点を追加
claude plugin marketplace add openai/codex-plugin-cc
claude plugin install codex@openai-codex
```

**code-review** でロジックの穴を検出、**security-guidance** でセキュリティパターンを警告、**codex** の Adversarial レビューで設計判断を検証。複数の視点で見逃しを減らします。

## 公式マーケットプレイスのカテゴリ分布

参考までに、2026 年 4 月時点の公式マーケットプレイス全 160 プラグインのカテゴリ分布を示します。

| カテゴリ | 数 | 主な例 |
|---|---|---|
| development | 66 | feature-dev, expo, stripe, terraform |
| productivity | 29 | code-review, github, slack, notion |
| database | 13 | mongodb, supabase, neon, firebase |
| security | 8 | security-guidance, auth0, semgrep, sonarqube |
| monitoring | 5 | sentry, datadog, posthog, amplitude |
| deployment | 5 | vercel, cloudflare, railway, azure |
| design | 2 | figma, miro |
| testing | 1 | playwright |
| その他 | 31 | superpowers, exa, firecrawl など |

## まとめ

| プラグイン | 作者 | 一言で表すと |
|---|---|---|
| **feature-dev** | Anthropic | 7 フェーズの構造化された機能開発ワークフロー |
| **code-review** | Anthropic | 4 エージェント並列レビュー + 信頼度スコアでフィルタ |
| **commit-commands** | Anthropic | コミット・プッシュ・PR 作成の自動化 |
| **frontend-design** | Anthropic | AI っぽくない個性的なフロントエンド生成 |
| **security-guidance** | Anthropic | ファイル編集時のセキュリティ自動警告 |
| **superpowers** | obra | Claude の計画・デバッグ能力を底上げ |

プラグインはすべて `claude plugin install <名前>` でインストールできます。まずは **feature-dev** と **code-review** の 2 つを試して、Claude Code の開発ワークフローがどう変わるか体感してみてください。
