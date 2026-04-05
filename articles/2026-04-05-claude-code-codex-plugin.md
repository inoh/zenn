---
title: "Claude Code × OpenAI Codex プラグインで AI コードレビューを多角化する"
emoji: "🔌"
type: "tech"
topics: ["claudecode", "openai", "codex", "codereview", "ai"]
published: true
---

## はじめに

Claude Code をメインの AI コーディングツールとして使っている方は多いと思います。一方で、OpenAI の Codex も強力なコーディング能力を持っています。

「どちらか一方を選ぶ」のではなく、**両方を組み合わせて使えたら？** という発想から生まれたのが、OpenAI 公式の Claude Code プラグイン **codex-plugin-cc** です。

この記事では、codex-plugin-cc でできることと、導入するメリットを紹介します。

## codex-plugin-cc とは

[codex-plugin-cc](https://github.com/openai/codex-plugin-cc) は、**Claude Code の中から OpenAI Codex を呼び出せるようにする公式プラグイン**です。

- **開発元**: OpenAI（公式リポジトリ）
- **ライセンス**: Apache-2.0
- **対応環境**: Node.js 18.18 以上

Claude Code のワークフローを離れることなく、Codex によるコードレビューやタスク委譲を実行できます。

## 主な機能

プラグインは **7 つのスラッシュコマンド**と **1 つのサブエージェント**を提供します。

### コマンド一覧

| コマンド | 用途 |
|---|---|
| `/codex:review` | コードレビュー（読み取り専用）。未コミットの変更やブランチ差分を対象 |
| `/codex:adversarial-review` | 設計判断・トレードオフ・障害モードを問い詰める挑戦的レビュー |
| `/codex:rescue` | タスクを Codex に委譲（バグ調査、修正、継続作業など） |
| `/codex:status` | 実行中・完了済みジョブの状態確認 |
| `/codex:result` | 完了ジョブの最終出力を表示 |
| `/codex:cancel` | バックグラウンドジョブのキャンセル |
| `/codex:setup` | インストール・認証状態のチェック |

### サブエージェント: codex-rescue

Claude Code が行き詰まったときに、**自動的に Codex にタスクを転送する**サブエージェントです。セカンドオピニオンが欲しい場面や、別の視点からの調査が必要な場面で活躍します。

## インストールと設定

### 前提条件

- ChatGPT サブスクリプション（Free 含む）または OpenAI API キー
- Node.js 18.18 以上
- Claude Code がインストール済みであること

### 導入手順

```bash
# 1. マーケットプレイスを追加
/plugin marketplace add openai/codex-plugin-cc

# 2. プラグインをインストール
/plugin install codex@openai-codex

# 3. プラグインをリロード
/reload-plugins

# 4. セットアップ確認
/codex:setup
```

Codex CLI が未インストールの場合は、先にインストールします。

```bash
npm install -g @openai/codex
```

Codex の認証がまだの場合は以下を実行します。

```bash
codex login
```

### 設定ファイル

Codex の標準的な設定ファイルをそのまま利用できます。

```toml
# ~/.codex/config.toml（ユーザーレベル）
# または .codex/config.toml（プロジェクトレベル）

model = "gpt-5.4-mini"
model_reasoning_effort = "xhigh"
```

## 実践的な使い方

### 通常のコードレビュー

```
/codex:review
```

未コミットの変更を Codex がレビューします。読み取り専用なので、コードが勝手に変更される心配はありません。ブランチの差分を対象にすることも可能です。

### Adversarial レビュー

```
/codex:adversarial-review
```

通常のレビューとは異なり、**意図的に厳しい目線**でコードを検証します。具体的には以下のような観点でチェックされます。

- 設計判断の妥当性
- セキュリティリスク（認証、データ損失、レースコンディションなど）
- エッジケースの考慮漏れ
- トレードオフの検討不足

「自分では気づけない穴」を見つけるのに効果的です。

### タスク委譲（Rescue）

```
/codex:rescue
```

Claude Code で解決が難しい問題に直面したとき、タスクを丸ごと Codex に委譲できます。

- `--resume-last` で前回のスレッドを継続
- `--write` でワークスペースへの書き込みを許可
- `--background` でバックグラウンド実行

バックグラウンドで実行した場合は `/codex:status` で進捗を確認できます。

## Stop レビューゲート

このプラグインのユニークな機能の一つが **Stop レビューゲート**です。

Claude Code がセッションを終了（Stop）しようとした際に、**自動的に Codex がレビューを実行**します。問題が見つかれば Stop をブロックし、Claude に修正を促します。

```
/codex:setup
```

セットアップコマンドからレビューゲートの有効/無効を切り替えられます。

この仕組みにより、セッション終了前に品質チェックが自動で挟まるため、問題の見逃しリスクを低減できます。

## 使うメリット

### 1. ワークフローを変えずに多角的なレビューが得られる

Claude Code を離れることなく、Codex の視点でコードレビューを受けられます。ツール間の切り替えコストがゼロです。

### 2. 2 つの AI の得意分野を活かせる

Claude と Codex はそれぞれ異なる学習データやアーキテクチャを持っています。片方では見逃すバグや設計上の問題を、もう片方が検出できる可能性があります。

### 3. 行き詰まったときの脱出口になる

Claude Code で解決できない問題に遭遇しても、Codex に委譲して別のアプローチを試せます。作業を最初からやり直す必要がありません。

### 4. バックグラウンド実行で待ち時間を削減

レビューやタスクをバックグラウンドで走らせながら、Claude Code での作業を続けられます。

### 5. 品質ゲートの自動化

Stop レビューゲートにより、セッション終了前の品質チェックを仕組み化できます。人間がレビューを忘れるリスクを補完できます。

### 6. 既存の Codex 設定をそのまま使える

Codex CLI の認証や `config.toml` の設定がそのまま引き継がれるため、追加の設定はほぼ不要です。

## まとめ

codex-plugin-cc は、Claude Code と OpenAI Codex を**対立ではなく協調**させるプラグインです。

- Claude Code のワークフロー内で Codex のレビュー・コーディング能力を活用できる
- Adversarial レビューや Stop レビューゲートで、多角的な品質チェックを実現できる
- 行き詰まった際のタスク委譲で、作業の中断を最小限に抑えられる

AI コーディングツールは「どれか一つに絞る」のではなく、**組み合わせて強みを引き出す**時代に入っています。Claude Code ユーザーであれば、導入を検討する価値のあるプラグインです。
