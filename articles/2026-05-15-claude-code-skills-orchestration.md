---
title: "Claude Code のスキルをオーケストレーションする方法：複数Skillを連鎖させる設計パターン"
emoji: "🎼"
type: "tech"
topics: ["ClaudeCode", "AI", "Skills", "開発効率化", "オーケストレーション"]
published: true
---

## はじめに

Claude Code の Skills を使い始めると、最初は「PDFを処理する」「コミットメッセージを書く」のような **単機能Skill** を1つだけ書く。これはこれでうまく動く。

問題は、現実のワークフローが単機能では収まらないことだ。「リサーチして」「ネタを選んで」「下書きを書いて」「PRを出して」「マージする」——これらは別々のSkillに分けたいが、別々に呼び出していたら結局自分が指揮者になる必要がある。

Anthropic は Skills を **「composable resources」** と位置づけている[^anthropic-blog]。つまり、Skills は最初から **複数を組み合わせて使う** ことが前提の設計だ。本記事では「複数Skillをどう連鎖させ、どこに状態を置き、どこをAIに判断させるか」というオーケストレーション設計に絞って整理する。

筆者自身がこのリポジトリで `/research-topic` と `/publish-article` の2つのSkillを使っており、本記事もこの2つを連鎖させて書いている。後半でその構成例も示す。

[^anthropic-blog]: [Equipping agents for the real world with Agent Skills - Anthropic Engineering](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

## 公式が示す判断軸：「how」はSkill、「access」はMCP

オーケストレーションの設計に入る前に、Skillの守備範囲を確定させておく。Anthropic公式blogはSkillsとMCPサーバーの使い分けを次のように示している[^anthropic-mcp]：

> If you're explaining how to do something, that's a skill. If you need Claude to access something, that's MCP.

そして、両者の関係はこう続く：

> This separation keeps the architecture composable. A single skill can orchestrate multiple MCP servers, while a single MCP server can support dozens of different skills.

つまり：

- **MCP**: 外部システム（GitHub、Notion、ファイルシステム等）への接続を提供する「手」
- **Skill**: 「どう使うか」「どんな順序で呼ぶか」を定義する「頭脳」

Skillが他のSkillを呼ぶことも、SkillがMCPサーバーを束ねることも、すべて **「howの記述」** に統一される。この視点で見ると、オーケストレーションは特別な機能ではなく、Skillsの本来の使い方そのものだとわかる。

[^anthropic-mcp]: [Extending Claude's capabilities with skills and MCP - Claude Blog](https://claude.com/blog/extending-claude-capabilities-with-skills-mcp-servers)

## オープン標準とClaude Code拡張を区別する

オーケストレーション機能を語る前に、Skillsには **2つのレイヤー** があることを意識しておきたい。

### オープン標準（agentskills.io/specification）

[Agent Skills 仕様](https://agentskills.io/specification)はAnthropicが発端でオープンソース化された規格で、Claude Code以外にも Cursor、Codex、Gemini CLI、VS Code、Copilotなど30以上のクライアントが採用している。標準フロントマターは以下：

| フィールド | 必須 | 制約 |
|---|---|---|
| `name` | Yes | 1-64文字、`a-z` `0-9` `-`、先頭・末尾ハイフン不可、連続ハイフン不可、親ディレクトリ名と一致 |
| `description` | Yes | 1-1024文字 |
| `license` | No | ライセンス情報 |
| `compatibility` | No | 最大500文字（環境要件） |
| `metadata` | No | 任意のkey-valueマップ |
| `allowed-tools` | No | スペース区切り（Experimental） |

仕様書には **Skill間連携・依存関係・状態共有に関する明示的な規定は存在しない**。連携は仕様の範囲外で、各クライアントが独自拡張で実現する設計になっている。

### Claude Code固有の拡張

[Claude Code Docs](https://code.claude.com/docs/en/skills) で追加されているフロントマターフィールドは以下：

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

オーケストレーションを支えるのは主に `context: fork`、`hooks`、`allowed-tools`、`paths`、それから本文中の動的コンテキスト注入（後述）だ。**これらはClaude Code固有なので、他のSkillsクライアントへの移植性はない** ことを覚えておく。

## Skill連携の4パターン

複数Skillを連鎖させる構造は、おおむね4つに分類できる[^mindstudio]。

[^mindstudio]: [Claude Code Skill Collaboration: How to Chain Skills Into End-to-End Workflows - MindStudio](https://www.mindstudio.ai/blog/claude-code-skill-collaboration-chaining-workflows)

### パターン1: Sequential Linear（直列）

最も基本のパイプライン。前段の出力が次段の入力になる。

```
/research-topic → /draft-article → /create-pr → /merge-pr
```

実装はシンプルで、orchestrator slash commandが状態ファイルを読み、現在のステージに応じて次のSkillを呼ぶ。

```yaml
---
name: blog-publish
description: Research, draft, and publish a blog article in sequence.
disable-model-invocation: true
---

State file: `.skills-state/blog-publish.json`

1. Read state file. If absent, initialize with `{ "stage": "research" }`.
2. Based on `stage`:
   - `research`: invoke `/research-topic`, write findings to state, advance stage to `draft`
   - `draft`: invoke `/draft-article`, write path to state, advance stage to `pr`
   - `pr`: invoke `/create-pr`, write PR number, advance stage to `done`
3. Stop when `stage == "done"`.
```

### パターン2: Parallel Fan-Out and Merge（並列展開）

1つのSkillがジョブをN個に分解し、サブエージェントで並列処理してマージする。`context: fork` を使うと各Skill実行が独立コンテキストで走るので、メインの会話文脈を汚さない[^code-docs]。

[^code-docs]: [Extend Claude with skills - Claude Code Docs](https://code.claude.com/docs/en/skills)

```yaml
---
name: review-all-changed-files
description: Review each changed file in parallel and summarize findings.
context: fork
agent: Explore
---

For each file in `git diff --name-only main...HEAD`:
1. Read the file
2. Identify potential bugs, security issues, performance concerns
3. Return findings as a structured list

Findings will be merged by the caller.
```

サブエージェント側は読み取り専用ツールのみ持ち、結果だけを呼び出し元に返す。バッチ処理の総実行時間を大幅に短縮できる。

### パターン3: Conditional Routing（条件分岐）

オーケストレーターが実行時の状態を見て、次にどのSkillを呼ぶかを決める。

```yaml
---
name: triage-and-fix
description: Classify the failing test and route to the appropriate fix skill.
---

1. Read the latest test output from `.skills-state/triage.json`.
2. Classify the failure category:
   - `flaky` → invoke `/fix-flaky-test`
   - `assertion` → invoke `/fix-assertion`
   - `import-error` → invoke `/fix-import`
   - else → stop and report
3. Write classification to state file.
```

このパターンで重要なのは、各Skillが **明確なステータス（カテゴリー）を返すこと**。文字列で曖昧に返すと分岐が壊れるので、JSONフィールドで返すよう設計する。

### パターン4: Iterative Loop（反復）

成功条件を満たすまでSkillを繰り返す。**最大反復回数か明確な成功条件を必ず定義する**[^mindstudio]——これを忘れると暴走する。

```yaml
---
name: fix-until-green
description: Keep fixing the failing tests until all pass or 5 iterations elapse.
---

State: `.skills-state/fix-loop.json` with `{ "iteration": 0, "max": 5, "passing": false }`

Loop:
1. If `iteration >= max` or `passing == true`, stop.
2. Run `pytest`. If exit 0, set `passing: true` and continue.
3. Invoke `/fix-failing-tests` with the failure output.
4. Increment `iteration`, write state, continue.
```

## 状態管理：JSONを単一の真実の源に

複数Skillをまたぐワークフローでは、状態を **構造化されたJSONファイル1つ** に集約する。テキストファイルで散らさない理由は2つ：

1. **パース信頼性**：プレーンテキストは曖昧。各Skillが「どこから読むか」で揺れる
2. **真実の源の一意性**：複数ファイルに状態を分けると、Skillが古いデータを読むリスクが出る

具体的なフィールド設計はワークフローによるが、最低限以下は必要だ：

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
- `history` は監査用。各Skillはここに自分の実行結果を追記する
- パスは絶対パスではなく **相対パス**（リポジトリのどこからでも参照できる）

## 3層責務分離：決定論的スクリプト × SKILL.md × AI判断

オーケストレーションの実装で最も効果が大きいのが **「どこに何を書くか」の責務分離** だ。playparkの実装例[^playpark]を参考に整理すると次のようになる。

[^playpark]: [【Claude Code】Skillオーケストレーション設計 - 複数Skillを連携させる実践パターン - playpark](https://www.playpark.co.jp/blog/claude-code-skill-orchestration)

| 層 | 担当 | 書く場所 | 例 |
|---|---|---|---|
| 第1層 | **決定論的処理** | シェルスクリプト | パス計算、日付計算、状態ファイル読み書き、git操作 |
| 第2層 | **条件分岐ロジック** | SKILL.md | 「stage が X ならこのSkillを呼ぶ」 |
| 第3層 | **AI判断** | SKILL.md内の指示 | 切り口提案、記事生成、コードレビュー |

第1層をスクリプトに押し出すメリットは大きい：

- **トークン消費ゼロ**でmillisecond単位で完了する
- 何度実行しても同じ結果になる（再現性）
- デバッグが容易（普通のシェルスクリプトとして単独実行できる）

具体的な分割例：

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

SKILL.md側ではこれを **動的コンテキスト注入** で取り込む：

```yaml
---
name: blog-publish
description: Research, draft, and publish a blog article end-to-end.
disable-model-invocation: true
allowed-tools: Bash(jq:*) Read Write Edit
---

## Current state
!`bash ${CLAUDE_SKILL_DIR}/scripts/init-state.sh "$ARGUMENTS"`

## Instructions
Read the state file printed above with `jq`. Based on `.stage`, invoke the next skill...
```

`` !`cmd` `` 構文は**Claudeに渡る前に**シェルでコマンドを実行し、その出力をプロンプトに差し込む[^code-docs]。Claudeが実行するのではなく、事前展開だ。これを使うと第1層の結果を第3層のAIに自然に渡せる。

`${CLAUDE_SKILL_DIR}` はSkillが置かれたディレクトリへの絶対パスに展開される変数で、これを使うとSkillが personal / project / plugin のどこに置かれても同じスクリプトを参照できる。

## Skillライフサイクルに紐づくhooks

Claude Code はSkillのフロントマター内で hooks を定義できる[^hooks-docs]。これは **そのSkillが有効な間だけ**フックが効く、というスコープが付くのが特徴。

[^hooks-docs]: [Hooks reference - Claude Code Docs](https://code.claude.com/docs/en/hooks)

```yaml
---
name: secure-operations
description: Perform operations with security checks.
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/security-check.sh"
          once: true
---
```

`once: true` は **Skillフロントマター限定** のフィールドで、settings.json や agent frontmatter では無視される。1セッション中に最初の `Bash` 実行直前で1回だけセキュリティチェックが走り、以降は走らない。

オーケストレーションでの使い所：

- **ガード**：危険なSkillを呼ぶ前に `PreToolUse` でガードする
- **計測**：`PostToolUse` で各Skillの実行ログを集約する
- **状態同期**：`Stop`（サブエージェントなら自動で `SubagentStop` に変換）で状態ファイルを永続化

## Agent Teams との混同に注意

Claude Codeには「Skillsのオーケストレーション」とは別に **Agent Teams** という機能がある。これは複数のClaude Codeインスタンスを協調させる仕組みで、現状（2026年5月時点）は **experimental** で GA未達。利用には：

- Claude Code **v2.1.32 以上**
- `settings.json` または環境変数で `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

が必要[^agent-teams]。既知の制限として session resumption / task coordination / shutdown behavior に課題がある段階。

[^agent-teams]: [Orchestrate teams of Claude Code sessions - Claude Code Docs](https://code.claude.com/docs/en/agent-teams)

**Skillsオーケストレーション** と **Agent Teams** は別レイヤーで、混同するとアーキテクチャ設計を誤る：

| | Skillsオーケストレーション | Agent Teams |
|---|---|---|
| 単位 | Skill（プロンプト＋スクリプト） | Claude Code インスタンス |
| 状態 | JSON状態ファイル | セッション間共有 |
| 安定度 | GA | Experimental |
| 用途 | 単一セッション内のワークフロー | 複数インスタンスの分散実行 |

本記事で扱うのは前者。後者は安定化を待ってから手を出した方がよい。

## アンチパターン集

実装で踏みがちな落とし穴を3つ。

### アンチパターン1: 全処理をSKILL.mdに書く

LLMにすべてやらせると、毎回挙動が微妙に違う、トークンが膨大、デバッグ困難という三重苦になる。決定論的に書ける部分（パス計算、日付計算、JSON読み書き、git操作）はすべてスクリプトに追い出す。

### アンチパターン2: フェーズ間の依存関係を明示しない

`/draft-article` → `/create-thumbnail` のように依存があるのに、それを書かないと、前段が失敗してもエラー判定せず後段が走る。状態ファイルに `previous_stage_success: true` のような明示的なフラグを必ず置く。

### アンチパターン3: 状態管理をサボる

途中で停止したときに最初からやり直しになる、または重複生成される。状態ファイルを必ず先頭で読み、各Skillの実行完了時に書き戻す。

## このリポジトリでの実例

参考までに、本記事自体が `/research-topic` → `/publish-article` の2段Skillで書かれている。構成は以下：

```
.claude/skills/
├── research-topic/
│   └── SKILL.md         # 一次ソース検証・着火点・インパクト分析の3層リサーチ
└── publish-article/
    └── SKILL.md         # 企画→ブランチ作成→執筆→PR→マージ
```

ユーザーが `/research-topic スキルをオーケストレーションする方法` を実行すると、リサーチレポート（一次ソースURL、フック候補、未検証項目）が生成される。続いて `/publish-article スキルをオーケストレーションする方法` を呼ぶと、リサーチ結果を引き継いで記事化に入る。

現状の構成では状態ファイルは持っておらず、Claudeが会話文脈で2つのSkillを橋渡ししているが、将来 `seed/<slug>/state.json` を導入すれば「リサーチ済みのトピックを記事化する」「途中停止から再開する」が容易になる予定だ。

## まとめ

Claude Code のSkillsは、最初から **複数を組み合わせて使う** ことが前提の「composable resources」として設計されている。オーケストレーションを実装するときの設計指針をまとめると：

1. **「how → Skill / access → MCP」** の使い分けを徹底する
2. **オープン標準フィールドとClaude Code拡張を区別する**（移植性に関わる）
3. **4つの連携パターン**（Sequential / Parallel / Conditional / Iterative）から適切なものを選ぶ
4. **状態はJSONファイル1つ** に集約する
5. **3層責務分離**（決定論的スクリプト / 条件分岐SKILL.md / AI判断）でレイヤーを切る
6. **`context: fork` + `hooks` + 動的コンテキスト注入**を組み合わせてオーケストレーションを実装する
7. **Agent Teams とは別レイヤー**であることを忘れない

Skillを単体で書き始めると、すぐに「複数のSkillをどう連鎖させるか」という課題に直面する。最初から状態ファイルと orchestrator slash command を含めて設計しておくと、後から書き直す手間が大幅に減る。

## 参考リンク

- [Agent Skills Specification - agentskills.io](https://agentskills.io/specification)
- [Equipping agents for the real world with Agent Skills - Anthropic Engineering](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Extending Claude's capabilities with skills and MCP - Claude Blog](https://claude.com/blog/extending-claude-capabilities-with-skills-mcp-servers)
- [Extend Claude with skills - Claude Code Docs](https://code.claude.com/docs/en/skills)
- [Hooks reference - Claude Code Docs](https://code.claude.com/docs/en/hooks)
- [Orchestrate teams of Claude Code sessions - Claude Code Docs](https://code.claude.com/docs/en/agent-teams)
- [anthropics/skills - GitHub](https://github.com/anthropics/skills)
