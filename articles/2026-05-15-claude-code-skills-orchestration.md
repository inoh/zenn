---
title: "Claude Code のスキルをオーケストレーションする方法：複数Skillを連鎖させる設計パターン"
emoji: "🎼"
type: "tech"
topics: ["ClaudeCode", "AI", "Skills", "開発効率化", "オーケストレーション"]
published: true
---

## はじめに

Claude Code の Skills を使い始めると、最初は「PDFを処理する」「コミットメッセージを書く」のような **単機能Skill** を1つだけ書くことが多いと思います。これはこれでうまく動きます。

問題は、現実のワークフローが単機能では収まらないことです。「リサーチして」「ネタを選んで」「下書きを書いて」「PRを出して」「マージする」——これらは別々のSkillに分けたいのですが、別々に呼び出していたら結局自分が指揮者になる必要があります。

Anthropic は Skills を **「composable resources」** と位置づけています[^anthropic-blog]。つまり Skills は最初から **複数を組み合わせて使う** ことが前提の設計です。本記事では「複数Skillをどう連鎖させ、どこに状態を置き、どこをAIに判断させるか」というオーケストレーション設計に絞って整理します。

筆者自身もこのリポジトリで `/research-topic` と `/publish-article` の2つのSkillを使っており、本記事もこの2つを連鎖させて書いています。後半でその構成例もご紹介します。

[^anthropic-blog]: [Equipping agents for the real world with Agent Skills - Anthropic Engineering](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

## 公式が示す判断軸：「how」はSkill、「access」はMCP

オーケストレーションの設計に入る前に、Skillの守備範囲を確定させておきましょう。Anthropic公式blogは SkillsとMCPサーバーの使い分けを次のように示しています[^anthropic-mcp]。

> If you're explaining how to do something, that's a skill. If you need Claude to access something, that's MCP.

そして、両者の関係はこう続きます。

> This separation keeps the architecture composable. A single skill can orchestrate multiple MCP servers, while a single MCP server can support dozens of different skills.

つまり次のような役割分担になります。

- **MCP**: 外部システム（GitHub、Notion、ファイルシステム等）への接続を提供する「手」
- **Skill**: 「どう使うか」「どんな順序で呼ぶか」を定義する「頭脳」

Skillが他のSkillを呼ぶことも、SkillがMCPサーバーを束ねることも、すべて **「howの記述」** に統一されます。この視点で見ると、オーケストレーションは特別な機能ではなく、Skillsの本来の使い方そのものだとわかります。

[^anthropic-mcp]: [Extending Claude's capabilities with skills and MCP - Claude Blog](https://claude.com/blog/extending-claude-capabilities-with-skills-mcp-servers)

## オープン標準とClaude Code拡張を区別する

オーケストレーション機能を語る前に、Skillsには **2つのレイヤー** があることを意識しておきたいです。

### オープン標準（agentskills.io/specification）

[Agent Skills 仕様](https://agentskills.io/specification)はAnthropicが発端でオープンソース化された規格で、Claude Code以外にも Cursor、Codex、Gemini CLI、VS Code、Copilotなど30以上のクライアントが採用しています。標準フロントマターは以下の通りです。

| フィールド | 必須 | 制約 |
|---|---|---|
| `name` | Yes | 1-64文字、`a-z` `0-9` `-`、先頭・末尾ハイフン不可、連続ハイフン不可、親ディレクトリ名と一致 |
| `description` | Yes | 1-1024文字 |
| `license` | No | ライセンス情報 |
| `compatibility` | No | 最大500文字（環境要件） |
| `metadata` | No | 任意のkey-valueマップ |
| `allowed-tools` | No | スペース区切り（Experimental） |

仕様書には **Skill間連携・依存関係・状態共有に関する明示的な規定は存在しません**。連携は仕様の範囲外で、各クライアントが独自拡張で実現する設計になっています。

### Claude Code固有の拡張

[Claude Code Docs](https://code.claude.com/docs/en/skills) で追加されているフロントマターフィールドは以下の通りです。

| フィールド | 用途 |
|---|---|
| `when_to_use` | 起動条件の補足説明 |
| `argument-hint` / `arguments` | 引数の宣言 |
| `disable-model-invocation` | Claudeの自動起動を無効化（ユーザー手動のみ） |
| `user-invocable` | `/`メニューから隠す |
| `allowed-tools` | パーミッション事前承認 |
| `model` / `effort` | Skill固有のモデル・推論深度 |
| `context: fork` + `agent` | サブエージェントで隔離実行 |
| `hooks` | Skillライフサイクルに紐づくフック |
| `paths` | 特定ファイルパスで自動ロード |
| `shell` | 動的コンテキスト注入のシェル指定 |

オーケストレーションを支えるのは主に `context: fork`、`hooks`、`allowed-tools`、`paths`、それから本文中の動的コンテキスト注入（後述）です。**これらはClaude Code固有なので、他のSkillsクライアントへの移植性はない** という点には注意しておきましょう。

## Skill連携の4パターン

複数Skillを連鎖させる構造は、おおむね4つに分類できます[^mindstudio]。

[^mindstudio]: [Claude Code Skill Collaboration: How to Chain Skills Into End-to-End Workflows - MindStudio](https://www.mindstudio.ai/blog/claude-code-skill-collaboration-chaining-workflows)

### パターン1: Sequential Linear（直列）

最も基本のパイプラインです。前段の出力が次段の入力になります。

```
/research-topic → /draft-article → /create-pr → /merge-pr
```

実装はシンプルで、orchestrator slash commandが状態ファイルを読み、現在のステージに応じて次のSkillを呼びます。

```yaml
---
name: blog-publish
description: ブログ記事のリサーチ、下書き、公開を一連のフローで実行する。
disable-model-invocation: true
---

状態ファイル: `.skills-state/blog-publish.json`

1. 状態ファイルを読み込む。存在しなければ `{ "stage": "research" }` で初期化する
2. `stage` の値に応じて分岐する
   - `research`: `/research-topic` を呼び、結果を状態に書き込み、`stage` を `draft` に進める
   - `draft`: `/draft-article` を呼び、生成パスを状態に書き込み、`stage` を `pr` に進める
   - `pr`: `/create-pr` を呼び、PR番号を状態に書き込み、`stage` を `done` に進める
3. `stage == "done"` で停止する
```

### パターン2: Parallel Fan-Out and Merge（並列展開）

1つのSkillがジョブをN個に分解し、サブエージェントで並列処理してマージする構造です。`context: fork` を使うと各Skill実行が独立コンテキストで走るので、メインの会話文脈を汚しません[^code-docs]。

[^code-docs]: [Extend Claude with skills - Claude Code Docs](https://code.claude.com/docs/en/skills)

```yaml
---
name: review-all-changed-files
description: 変更されたファイルを並列でレビューし、指摘事項を集約する。
context: fork
agent: Explore
---

`git diff --name-only main...HEAD` の各ファイルについて以下を実行する。

1. ファイルを読み込む
2. バグの可能性、セキュリティ上の懸念、パフォーマンスの問題を特定する
3. 指摘事項を構造化されたリストとして返す

結果は呼び出し元でマージされる。
```

サブエージェント側は読み取り専用ツールのみ持ち、結果だけを呼び出し元に返します。バッチ処理の総実行時間を大幅に短縮できます。

### パターン3: Conditional Routing（条件分岐）

オーケストレーターが実行時の状態を見て、次にどのSkillを呼ぶかを決めます。

```yaml
---
name: triage-and-fix
description: 失敗したテストを分類し、適切な修正スキルにルーティングする。
---

1. `.skills-state/triage.json` から最新のテスト出力を読み込む
2. 失敗カテゴリを分類する
   - `flaky` → `/fix-flaky-test` を呼ぶ
   - `assertion` → `/fix-assertion` を呼ぶ
   - `import-error` → `/fix-import` を呼ぶ
   - その他 → 停止して報告する
3. 分類結果を状態ファイルに書き込む
```

このパターンで重要なのは、各Skillが **明確なステータス（カテゴリー）を返すこと** です。文字列で曖昧に返すと分岐が壊れますので、JSONフィールドで返すよう設計しましょう。

### パターン4: Iterative Loop（反復）

成功条件を満たすまでSkillを繰り返します。**最大反復回数か明確な成功条件を必ず定義する**[^mindstudio]——これを忘れると暴走します。

```yaml
---
name: fix-until-green
description: 全テストがパスするか5回反復するまで、失敗テストの修正を繰り返す。
---

状態: `.skills-state/fix-loop.json` に `{ "iteration": 0, "max": 5, "passing": false }` を保持する

ループ処理:
1. `iteration >= max` または `passing == true` の場合は停止する
2. `pytest` を実行する。exit code 0 なら `passing: true` をセットして継続する
3. 失敗出力を引数に `/fix-failing-tests` を呼ぶ
4. `iteration` をインクリメントし、状態を書き戻して継続する
```

## 状態管理：JSONを単一の真実の源に

複数Skillをまたぐワークフローでは、状態を **構造化されたJSONファイル1つ** に集約します。テキストファイルで散らさない理由は2つあります。

1. **パース信頼性**：プレーンテキストは曖昧で、各Skillが「どこから読むか」で揺れます
2. **真実の源の一意性**：複数ファイルに状態を分けると、Skillが古いデータを読むリスクが出ます

具体的なフィールド設計はワークフローによりますが、最低限以下は必要です。

```json
{
  "stage": "draft",
  "topic": "Skillをオーケストレーションする方法",
  "research_path": "seed/skills-orchestration/research.md",
  "article_path": "articles/2026-05-15-skills-orchestration.md",
  "pr_number": null,
  "history": [
    { "stage": "research", "completed_at": "2026-05-15T10:00:00Z" }
  ]
}
```

- `stage` は次に実行するSkillを決定する単一フィールド
- `history` は監査用で、各Skillはここに自分の実行結果を追記します
- パスは絶対パスではなく **相対パス**（リポジトリのどこからでも参照できます）

## 3層責務分離：決定論的スクリプト × SKILL.md × AI判断

オーケストレーションの実装で最も効果が大きいのが **「どこに何を書くか」の責務分離** です。playparkの実装例[^playpark]を参考に整理すると次のようになります。

[^playpark]: [【Claude Code】Skillオーケストレーション設計 - 複数Skillを連携させる実践パターン - playpark](https://www.playpark.co.jp/blog/claude-code-skill-orchestration)

| 層 | 担当 | 書く場所 | 例 |
|---|---|---|---|
| 第1層 | **決定論的処理** | シェルスクリプト | パス計算、日付計算、状態ファイル読み書き、git操作 |
| 第2層 | **条件分岐ロジック** | SKILL.md | 「stage が X ならこのSkillを呼ぶ」 |
| 第3層 | **AI判断** | SKILL.md内の指示 | 切り口提案、記事生成、コードレビュー |

第1層をスクリプトに押し出すメリットは大きいです。

- **トークン消費ゼロ**でmillisecond単位で完了します
- 何度実行しても同じ結果になります（再現性）
- デバッグが容易です（普通のシェルスクリプトとして単独実行できます）

具体的な分割例は次の通りです。

```bash
# scripts/init-state.sh （決定論的層）
#!/usr/bin/env bash
set -euo pipefail

TOPIC="$1"
SLUG=$(echo "$TOPIC" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')
DATE=$(date +%Y-%m-%d)
STATE_DIR="seed/${SLUG}"
mkdir -p "${STATE_DIR}"

cat > "${STATE_DIR}/state.json" <<EOF
{
  "stage": "research",
  "topic": "${TOPIC}",
  "slug": "${SLUG}",
  "date": "${DATE}",
  "state_dir": "${STATE_DIR}"
}
EOF

echo "${STATE_DIR}/state.json"
```

SKILL.md側ではこれを **動的コンテキスト注入** で取り込みます。

```yaml
---
name: blog-publish
description: ブログ記事のリサーチから公開までを一気通貫で実行する。
disable-model-invocation: true
allowed-tools: Bash(jq:*) Read Write Edit
---

## 現在の状態
!`bash ${CLAUDE_SKILL_DIR}/scripts/init-state.sh "$ARGUMENTS"`

## 指示
上に出力された状態ファイルを `jq` で読み込む。`.stage` の値に応じて次のスキルを呼び出す...
```

`` !`cmd` `` 構文は **Claudeに渡る前に** シェルでコマンドを実行し、その出力をプロンプトに差し込みます[^code-docs]。Claudeが実行するのではなく、事前展開という点がポイントです。これを使うと第1層の結果を第3層のAIに自然に渡せます。

`${CLAUDE_SKILL_DIR}` はSkillが置かれたディレクトリへの絶対パスに展開される変数で、これを使うとSkillが personal / project / plugin のどこに置かれても同じスクリプトを参照できます。

## Skillライフサイクルに紐づくhooks

Claude Code はSkillのフロントマター内で hooks を定義できます[^hooks-docs]。これは **そのSkillが有効な間だけ** フックが効く、というスコープが付くのが特徴です。

[^hooks-docs]: [Hooks reference - Claude Code Docs](https://code.claude.com/docs/en/hooks)

```yaml
---
name: secure-operations
description: セキュリティチェック付きで操作を実行する。
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/security-check.sh"
          once: true
---
```

`once: true` は **Skillフロントマター限定** のフィールドで、settings.json や agent frontmatter では無視されます。1セッション中に最初の `Bash` 実行直前で1回だけセキュリティチェックが走り、以降は走りません。

オーケストレーションでの使い所は次の通りです。

- **ガード**：危険なSkillを呼ぶ前に `PreToolUse` でガードします
- **計測**：`PostToolUse` で各Skillの実行ログを集約します
- **状態同期**：`Stop`（サブエージェントなら自動で `SubagentStop` に変換されます）で状態ファイルを永続化します

## Agent Teams との混同に注意

Claude Codeには「Skillsのオーケストレーション」とは別に **Agent Teams** という機能があります。これは複数のClaude Codeインスタンスを協調させる仕組みで、現状（2026年5月時点）は **experimental** で GA未達です。利用には次の条件が必要です[^agent-teams]。

- Claude Code **v2.1.32 以上**
- `settings.json` または環境変数で `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

既知の制限として session resumption / task coordination / shutdown behavior に課題がある段階です。

[^agent-teams]: [Orchestrate teams of Claude Code sessions - Claude Code Docs](https://code.claude.com/docs/en/agent-teams)

**Skillsオーケストレーション** と **Agent Teams** は別レイヤーで、混同するとアーキテクチャ設計を誤ります。

| | Skillsオーケストレーション | Agent Teams |
|---|---|---|
| 単位 | Skill（プロンプト＋スクリプト） | Claude Code インスタンス |
| 状態 | JSON状態ファイル | セッション間共有 |
| 安定度 | GA | Experimental |
| 用途 | 単一セッション内のワークフロー | 複数インスタンスの分散実行 |

本記事で扱うのは前者です。後者は安定化を待ってから手を出す方が無難でしょう。

## アンチパターン集

実装で踏みがちな落とし穴を3つご紹介します。

### アンチパターン1: 全処理をSKILL.mdに書く

LLMにすべてやらせると、毎回挙動が微妙に違う、トークンが膨大、デバッグ困難という三重苦になります。決定論的に書ける部分（パス計算、日付計算、JSON読み書き、git操作）はすべてスクリプトに追い出しましょう。

### アンチパターン2: フェーズ間の依存関係を明示しない

`/draft-article` → `/create-thumbnail` のように依存があるのに、それを書かないと、前段が失敗してもエラー判定せず後段が走ってしまいます。状態ファイルに `previous_stage_success: true` のような明示的なフラグを必ず置きましょう。

### アンチパターン3: 状態管理をサボる

途中で停止したときに最初からやり直しになる、または重複生成されることがあります。状態ファイルを必ず先頭で読み、各Skillの実行完了時に書き戻しましょう。

## このリポジトリでの実例

参考までに、本記事自体が `/research-topic` → `/publish-article` の2段Skillで書かれています。構成は以下の通りです。

```
.claude/skills/
├── research-topic/
│   └── SKILL.md         # 一次ソース検証・着火点・インパクト分析の3層リサーチ
└── publish-article/
    └── SKILL.md         # 企画→ブランチ作成→執筆→PR→マージ
```

ユーザーが `/research-topic スキルをオーケストレーションする方法` を実行すると、リサーチレポート（一次ソースURL、フック候補、未検証項目）が生成されます。続いて `/publish-article スキルをオーケストレーションする方法` を呼ぶと、リサーチ結果を引き継いで記事化に入ります。

現状の構成では状態ファイルは持っておらず、Claudeが会話文脈で2つのSkillを橋渡ししていますが、将来 `seed/<slug>/state.json` を導入すれば「リサーチ済みのトピックを記事化する」「途中停止から再開する」といった運用が容易になる予定です。

## まとめ

Claude Code のSkillsは、最初から **複数を組み合わせて使う** ことが前提の「composable resources」として設計されています。オーケストレーションを実装するときの設計指針をまとめると、次のようになります。

1. **「how → Skill / access → MCP」** の使い分けを徹底する
2. **オープン標準フィールドとClaude Code拡張を区別する**（移植性に関わります）
3. **4つの連携パターン**（Sequential / Parallel / Conditional / Iterative）から適切なものを選ぶ
4. **状態はJSONファイル1つ** に集約する
5. **3層責務分離**（決定論的スクリプト / 条件分岐SKILL.md / AI判断）でレイヤーを切る
6. **`context: fork` + `hooks` + 動的コンテキスト注入** を組み合わせてオーケストレーションを実装する
7. **Agent Teams とは別レイヤー** であることを忘れない

Skillを単体で書き始めると、すぐに「複数のSkillをどう連鎖させるか」という課題に直面します。最初から状態ファイルと orchestrator slash command を含めて設計しておくと、後から書き直す手間が大幅に減らせるでしょう。

## 参考リンク

- [Agent Skills Specification - agentskills.io](https://agentskills.io/specification)
- [Equipping agents for the real world with Agent Skills - Anthropic Engineering](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Extending Claude's capabilities with skills and MCP - Claude Blog](https://claude.com/blog/extending-claude-capabilities-with-skills-mcp-servers)
- [Extend Claude with skills - Claude Code Docs](https://code.claude.com/docs/en/skills)
- [Hooks reference - Claude Code Docs](https://code.claude.com/docs/en/hooks)
- [Orchestrate teams of Claude Code sessions - Claude Code Docs](https://code.claude.com/docs/en/agent-teams)
- [anthropics/skills - GitHub](https://github.com/anthropics/skills)
