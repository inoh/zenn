---
title: "AI コーディングエージェント比較 2026 — Claude Code・Codex・Copilot・Cursor の違いと選び方"
emoji: "⚔️"
type: "tech"
topics: ["claudecode", "openai", "githubcopilot", "cursor", "ai"]
published: true
---

## はじめに

2026 年、AI コーディングエージェントは群雄割拠の時代に入りました。Anthropic の **Claude Code**、OpenAI の **Codex CLI**、GitHub の **Copilot（CLI + Coding Agent）**、そして **Cursor Agent** — いずれも「自然言語でコードを書かせる」という共通のゴールを持ちながら、アーキテクチャや思想は大きく異なります。

本記事では、これら 4 つのツールの機能を横断的に比較し、それぞれの強みと使いどころを整理します。

## 各ツールの概要

### Claude Code（Anthropic）

Anthropic が提供するターミナルベースの AI コーディングエージェントです。CLI から起動し、ファイルの読み書き・コマンド実行・Web 検索などを自律的に行います。

```bash
# インストール
npm install -g @anthropic-ai/claude-code

# 起動
claude
```

**特徴的な機能**:
- サブエージェント（専門タスクを隔離されたコンテキストで処理）
- Skills システム（3 層の遅延ロードで効率的に拡張）
- Hooks（ツール実行前後にシェルコマンドを自動実行）
- MCP（Model Context Protocol）による外部ツール連携
- プラグインエコシステム（OpenAI Codex との連携など）

### Codex CLI（OpenAI）

OpenAI が 2025 年 4 月にオープンソースで公開したターミナルベースのコーディングエージェントです。サンドボックス内でコードを安全に実行できるのが特徴です。

```bash
# インストール
npm install -g @openai/codex

# 起動
codex
```

**特徴的な機能**:
- サンドボックス実行（ネットワーク無効・ディレクトリ制限）
- 3 段階の自律モード（Suggest / Auto-edit / Full auto）
- マルチモーダル入力（スクリーンショットを渡せる）
- 完全オープンソース（Apache 2.0）

### GitHub Copilot（GitHub / Microsoft）

GitHub が提供する AI コーディング支援ツールです。ターミナルエージェントと GitHub 上のコーディングエージェントの 2 つの形態があります。

```bash
# CLI のインストール
npm install -g @github/copilot

# 起動
copilot
```

**2 つの形態**:
- **Copilot CLI**: ターミナルで動作する AI コーディングエージェント。モデル選択（`/model`）、並列実行（`/fleet`）、セッション継続（`/resume`）、VS Code 連携（`/IDE`）、MCP 対応など、本格的なエージェント機能を備える
- **Copilot Coding Agent**: GitHub Issue を割り当てると、自律的にコードを書いて PR を作成

### Cursor Agent（Cursor）

VS Code フォークの AI エディタ Cursor に内蔵されたエージェントモードです。IDE との深い統合が強みです。

**特徴的な機能**:
- Agent モード（Composer パネルから複数ファイルを自律編集）
- Background Agent（クラウド VM 上でタスクをバックグラウンド実行）
- Tab 補完（インラインのコード補完）
- コードベースインデックスによるコンテキスト理解

## 機能比較表

| 機能 | Claude Code | Codex CLI | Copilot | Cursor Agent |
|------|:-----------:|:---------:|:-------:|:------------:|
| **動作環境** | ターミナル | ターミナル | ターミナル / GitHub | IDE（VS Code フォーク） |
| **自律的なコード編集** | ○ | ○ | ○（Coding Agent） | ○ |
| **コマンド実行** | ○ | ○（サンドボックス内） | △（提案のみ） | ○ |
| **複数ファイル編集** | ○ | ○ | ○ | ○ |
| **サンドボックス** | × | ○ | ○（GitHub Actions VM） | ○（Background Agent） |
| **バックグラウンド実行** | ○（サブエージェント） | △ | ○（Coding Agent） | ○（Background Agent） |
| **Web 検索** | ○ | △（設定で有効化可） | △（Copilot Chat で Bing 連携） | △ |
| **画像入力** | ○ | ○ | △ | ○ |
| **プラグイン / 拡張** | ○（MCP, Skills, Plugins） | △ | ○（Extensions） | ○（MCP） |
| **オープンソース** | × | ○ | × | × |
| **Git 連携** | ○ | ○ | ◎（GitHub ネイティブ） | ○ |

## 詳細比較

### 動作環境とセットアップ

**Claude Code** と **Codex CLI** はどちらもターミナルネイティブです。SSH 越しやリモートサーバーでも動作し、IDE に依存しません。一方で Claude Code は VS Code / JetBrains 向けの拡張も提供しています。

**Copilot** はターミナルと GitHub の両方で動作します。Copilot CLI はターミナルベースの本格的なエージェントで、Claude Code や Codex CLI と同カテゴリのツールです。Copilot Coding Agent は GitHub 上で完結し、Issue を割り当てるだけで PR が作成されます。

**Cursor Agent** は IDE 内蔵のため、エディタの機能（シンタックスハイライト、インテリセンス、デバッガ）とシームレスに連携します。ターミナルだけで作業したい人には向きません。

### 安全性と自律性のバランス

各ツールは、AI にどこまで自律的に動かせるかについて異なるアプローチを取っています。

**Codex CLI** はサンドボックスが最も厳格です。デフォルトでネットワークアクセスを無効化し、ディレクトリアクセスも制限します。macOS では Apple の Seatbelt、Linux では Docker コンテナを使用します。

```
# Codex の 3 段階の自律モード
Suggest    → 提案のみ、全て人間が承認
Auto-edit  → ファイル編集は自動、コマンド実行は承認制
Full auto  → 読み書き・実行すべて自動（サンドボックス内）
```

**Claude Code** はサンドボックスを持ちませんが、許可モードで制御します。ツール呼び出しごとにユーザー承認を求める設定が可能です。また、Git 操作では安全プロトコル（force-push 禁止、シークレットファイルの除外など）が組み込まれています。

**Copilot Coding Agent** は GitHub Actions の VM 内で動作するため、本番環境に影響を与えるリスクが低いです。結果は必ず PR として提出され、人間のレビューを経ます。

**Cursor Agent** は IDE 内で動作するため、ローカルファイルに直接アクセスします。Background Agent はクラウド VM で動作するため、こちらはサンドボックス的な安全性があります。

### 拡張性とエコシステム

**Claude Code** の拡張性は群を抜いています。

- **MCP**: 外部ツールサーバーと接続（Playwright、Slack、データベースなど）
- **Skills**: 3 層の遅延ロードアーキテクチャで効率的に機能追加
- **Hooks**: ツール実行前後にシェルコマンドを自動実行（lint、テスト、通知）
- **サブエージェント**: 専門タスクを隔離コンテキストで並列処理
- **プラグイン**: サードパーティ製プラグイン（codex-plugin-cc など）

```bash
# 例: Hooks でファイル保存後に自動 lint
# .claude/hooks.json
{
  "PostToolUse": [{
    "matcher": "Write",
    "command": "eslint --fix $FILE_PATH"
  }]
}
```

**Codex CLI** はオープンソースなのでコードレベルでのカスタマイズが可能ですが、プラグインシステムのような構造化された拡張機構はまだ発展途上です。

**Copilot** は GitHub エコシステムとの統合が最大の強みです。Issue → Agent → PR → Review のワークフローが GitHub 上で完結します。

**Cursor** は MCP 対応に加え、IDE ネイティブの拡張（VS Code エクステンション互換）を活用できます。

### 料金体系

| ツール | 料金モデル | 目安 |
|--------|-----------|------|
| **Claude Code** | サブスクリプション + API 従量課金 | Pro: $20/月、Max: $100〜200/月 |
| **Codex CLI** | API 従量課金（CLI 自体は無料） | 使用量による（OSS 開発者向け $1,000 クレジットあり） |
| **Copilot** | サブスクリプション | Pro: $10/月、Pro+: $39/月（Coding Agent 利用可） |
| **Cursor** | サブスクリプション | Pro: $20/月、Ultra: $200/月 |

**Codex CLI** は CLI 自体がオープンソースで無料のため、ライトユースなら最もコストを抑えられます。一方で大量に使うと API 料金が膨らむ点に注意が必要です。

**Copilot** は Coding Agent を使わないなら $10/月と最安です。ただし Coding Agent には Pro+（$39/月）が必要です。

## ユースケース別おすすめ

### ターミナル中心で最大限の自律性が欲しい → Claude Code

MCP・Hooks・Skills・サブエージェントによる拡張性と、Web 検索を含む豊富なツールセットが魅力です。複雑なタスクを一気通貫で処理させたい場合に最適です。

### 安全性を最優先にしたい → Codex CLI

サンドボックスによる厳格な実行環境が、セキュリティを重視するチームやプロジェクトに向いています。オープンソースなので、実行環境を自分で検証できる安心感もあります。

### GitHub ワークフローに統合したい → Copilot Coding Agent

Issue を割り当てるだけで PR が上がってくるワークフローは、チーム開発との相性が抜群です。既に Copilot を導入済みのチームなら移行コストもゼロです。

### IDE との統合を重視する → Cursor Agent

エディタの中で完結する体験を求めるなら Cursor が最適です。Tab 補完からエージェントモード、Background Agent まで、コーディングの全フェーズを IDE 内でカバーします。

### 複数ツールの組み合わせ

これらのツールは排他的ではありません。たとえば:

- **Claude Code + Codex プラグイン**: Claude Code をメインに使いつつ、Codex の視点でレビューを受ける
- **Cursor + Copilot**: IDE 内の作業は Cursor Agent、Issue 駆動の自動化は Copilot Coding Agent
- **Claude Code + Copilot**: ローカル開発は Claude Code、CI/CD パイプラインでの自動修正は Copilot

## まとめ

4 つの AI コーディングエージェントの特徴を整理します。

| | Claude Code | Codex CLI | Copilot | Cursor Agent |
|---|---|---|---|---|
| **一言で表すと** | 万能ターミナルエージェント | 安全なオープンソースエージェント | GitHub ネイティブ万能エージェント | IDE 統合エージェント |
| **最大の強み** | 拡張性（MCP, Skills, Hooks） | サンドボックスの安全性 | GitHub ワークフロー統合 | IDE との深い統合 |
| **向いている人** | ターミナル派・パワーユーザー | セキュリティ重視・OSS 志向 | GitHub 中心のチーム開発 | GUI エディタ派 |

AI コーディングエージェントは「どれが最強か」ではなく、**自分のワークフローに合うものを選ぶ**（あるいは組み合わせる）のが正解です。各ツールの進化は速いので、定期的に最新情報をキャッチアップしていきましょう。
