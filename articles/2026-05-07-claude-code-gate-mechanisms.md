---
title: "Claude Code の三層ゲート設計 — Hooks × Permission Modes × Auto Mode"
emoji: "🚧"
type: "tech"
topics: ["claudecode", "anthropic", "ai", "agent", "security"]
published: true
---

## はじめに

2026 年 4 月 25 日（金曜日）、車レンタル系スタートアップ PocketOS の本番データベースが、**わずか 9 秒で消失**しました。バックアップも一緒に消えました。

実行したのは Cursor 上で動いていた Claude Opus 4.6 ベースのコーディングエージェントです。ステージング環境での credential mismatch を検知したエージェントが、人間の承認を待たずに「自分で直そう」と判断し、Railway のボリューム削除 API を叩いた。それだけで本番が消えました。事件は The Register や Euronews などの主要メディアでも報道されています（[The Register: Cursor-Opus agent snuffs out startup's production database](https://www.theregister.com/2026/04/27/cursoropus_agent_snuffs_out_pocketos/)、[Euronews](https://www.euronews.com/next/2026/04/28/an-ai-agent-deleted-a-companys-entire-database-in-9-seconds-then-wrote-an-apology)）。

事後にエージェントは「与えられた原則をすべて違反した」と長文の "謝罪文" を出力しました。**しかし問題はそこではありません**。エージェント側の "安全原則" は守ってくれることを前提にできない、ということが今回の事件で改めて示されたのです。

この記事では、Claude Code と Claude Agent SDK が提供する**三層のゲート機構**——Permission Modes、Hooks、Auto Mode——を整理し、それぞれをどう組み合わせれば PocketOS のような事故を構造的に防げるかを解説します。

:::message
本記事の検証時点：2026 年 5 月 7 日。公式ドキュメントは [Claude Code Hooks](https://code.claude.com/docs/en/hooks) および [Agent SDK Permissions](https://code.claude.com/docs/en/agent-sdk/permissions) を実物確認しています。
:::

## 三層ゲートの全体像

Claude Code / Agent SDK のゲート機構は、用途とタイミングが異なる三層で構成されています。

| 層 | 名前 | タイミング | 主な役割 |
|---|---|---|---|
| 第 1 層 | **Permission Modes** | セッション全体 | エージェントの「自由度」をモードで縛る |
| 第 2 層 | **Hooks** | ツール呼び出し前後など 20+ のライフサイクルイベント | 個別アクションを deny / 改変する |
| 第 3 層 | **Auto Mode** | 各ツール呼び出し | 分類器がリスク評価し、必要時のみ人間に聞く |

公式ドキュメントは、ツール呼び出し時の評価順を 5 ステップで定義しています。

```
Hooks → Deny rules → Permission mode → Allow rules → canUseTool callback
```

つまり Hooks は最優先で評価され、その次に deny ルール、続いて permission mode、最後に allow ルールと `canUseTool` というレイヤード構造です。重要なのは、**deny ルールは `bypassPermissions` モードでも有効**という点。これは公式 docs にも明記されています。

> Check `deny` rules (from `disallowed_tools` and settings.json). If a deny rule matches, the tool is blocked, even in `bypassPermissions` mode.

このフローを頭に入れた上で、各層を見ていきましょう。

## 第 1 層: Permission Modes — 6 つのモードを使い分ける

Claude Agent SDK は次の 6 つの permission mode を提供しています（公式 docs より）。

| モード | 挙動 |
|---|---|
| `default` | すべてのツールが `canUseTool` コールバックを通る。本番運用向けの基本モード |
| `dontAsk` | pre-approved 以外は問答無用で deny。`canUseTool` も呼ばれない |
| `acceptEdits` | ファイル編集系（Edit / Write / `mkdir` / `rm` / `mv` 等）を自動承認 |
| `bypassPermissions` | すべてのツールを承認。**ただし deny ルールと hooks は引き続き有効** |
| `plan` | read-only ツールのみ実行可。コード分析・計画策定用 |
| `auto`（TS のみ） | 後述の Auto Mode（モデル分類器による承認） |

### モードの選び方

ユースケース別の推奨マッピングです。

- **本番 CI で何かを生成する**: `dontAsk` + `allowedTools` で「やっていいツールだけホワイトリスト」
- **プロトタイピング・隔離環境**: `acceptEdits`（ファイル編集だけ自動承認、bash は確認）
- **コードレビューや差分提案**: `plan`（書き込みなし）
- **Sandbox 内 CI（dev container 等）**: `bypassPermissions`（ただし deny ルールで `rm -rf /` 系を必ずブロック）
- **対話セッション**: `default`

公式は `dontAsk` の使いどころをこう説明しています。

> Use when you want a fixed, explicit tool surface for a headless agent and prefer a hard deny over silent reliance on `canUseTool` being absent.

ヘッドレスエージェント（CI で動かすなど人間が見ていない実行）では、`canUseTool` を実装し忘れた場合のデフォルト挙動が「黙って通す」になっていると危険です。`dontAsk` は「未定義は拒否」を保証してくれます。

### サブエージェント継承の罠

一番ハマりやすい落とし穴がこれです。公式 docs の Warning に書かれています。

> When the parent uses `bypassPermissions`, `acceptEdits`, or `auto`, all subagents inherit that mode and it cannot be overridden per subagent.

つまり、親エージェントを `bypassPermissions` で動かすと、**そこから生成されるサブエージェントもすべて bypass で動く**。サブエージェントは別のシステムプロンプトで動作する以上、親より制約が緩い行動を取る可能性があり、それが bypass で全権限を持つ、という最悪の組み合わせが成立します。

PocketOS 事件の構図に近いのは、まさにこのパターンでした。「ステージングでの軽い修正」のつもりで緩いモードで動かしていたら、サブタスクが本番リソースに到達したという読み解き方ができます。

### コード例: モードの動的切り替え

セッション中にモードを切り替えるのは公式のサポート済みパターンです。

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

const q = query({
  prompt: "Help me refactor this code",
  options: {
    permissionMode: "default" // 最初は厳しく
  }
});

// レビュー後、信頼が積み上がったら緩める
await q.setPermissionMode("acceptEdits");
```

「最初は厳しく、信頼が貯まったら緩める」という運用が公式の推奨パターンです。

## 第 2 層: Hooks — PreToolUse による deny ゲート

Permission Modes は「セッション全体の自由度」を決めるマクロな仕組みでした。これだけでは「`rm -rf /tmp/important_data` だけ止めたい」のような**個別アクションのブロック**ができません。そこで使うのが Hooks です。

### Hooks のライフサイクルイベント

Claude Code の Hooks は 2025 年の初期実装から大幅に拡張され、現在は 20 以上のライフサイクルイベントが定義されています。代表的なものを抜粋します。

| カテゴリ | イベント |
|---|---|
| セッション | `SessionStart`, `SessionEnd`, `Setup` |
| ターン | `UserPromptSubmit`, `Stop`, `StopFailure` |
| ツール呼び出し | `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch` |
| パーミッション | `PermissionRequest`, `PermissionDenied` |
| サブエージェント | `SubagentStart`, `SubagentStop` |
| タスク | `TaskCreated`, `TaskCompleted` |
| コンパクション | `PreCompact`, `PostCompact` |
| MCP | `Elicitation`, `ElicitationResult` |

このうち**ブロック可能なのは `PreToolUse` だけ**です。これを覚えておくと混乱しません。

### PreToolUse の 4 つの決定値

`PreToolUse` フックは `hookSpecificOutput.permissionDecision` フィールドで決定値を返します。公式 docs から引用します。

> `permissionDecision`: `"allow"` skips the permission prompt. `"deny"` prevents the tool call. `"ask"` prompts the user to confirm. `"defer"` exits gracefully so the tool can be resumed later.

| 値 | 挙動 |
|---|---|
| `allow` | パーミッション確認をスキップして実行 |
| `deny` | ツール呼び出しをキャンセル |
| `ask` | ユーザーに確認ダイアログを出す |
| `defer` | グレースフル終了。後で再開可能（Claude Code v2.1.89+ で追加） |

そして複数フックが競合した時の優先順位は次のとおりです。

> When multiple PreToolUse hooks return different decisions, precedence is `deny` > `defer` > `ask` > `allow`.

「一つでも `deny` を返したら勝ち」というシンプルなルールです。複数の deny ルールを並列で走らせて OR 結合で判定できます。

### 実装例: 危険コマンドガード

`rm -rf` が本番ディレクトリを指していたら deny する例です。

```python
# .claude/hooks/pretool_rm_guard.py
import json
import sys
import re

DANGER_PATHS = [r"/etc/", r"/var/", r"/home/", r"^/$", r"production"]

data = json.load(sys.stdin)

if data["toolName"] == "Bash":
    cmd = data["toolInput"].get("command", "")
    if "rm -rf" in cmd or "rm -r" in cmd:
        for pattern in DANGER_PATHS:
            if re.search(pattern, cmd):
                print(json.dumps({
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"危険なパスへの rm を検出: {cmd}\n"
                            "本当に必要なら手動で実行してください"
                        )
                    }
                }))
                sys.exit(0)

# 該当しなければ何も返さず通す
sys.exit(0)
```

`settings.json` への登録：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "python .claude/hooks/pretool_rm_guard.py" }
        ]
      }
    ]
  }
}
```

`permissionDecisionReason` は `deny` の場合、**Claude（モデル）に渡される**点に注意してください（`allow` と `ask` の場合はユーザーに表示されます）。モデルが「なぜダメだったか」を理解して別のアプローチを試すきっかけになります。

### `updatedInput` で引数を改変する

deny ではなく「引数を書き換えて通す」というパターンも可能です。

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": {
      "command": "echo '[DRY RUN]' && terraform plan"
    }
  }
}
```

`terraform apply` を勝手に `terraform plan` に書き換えて通す、という防御策が組めます。

## 第 3 層: Auto Mode — 赤いスピナーと分類器

2026 年春に Claude Code に追加された Auto Mode は、上記 2 層とは少し趣が異なります。InfoQ の解説（[Inside Claude Code Auto Mode](https://www.infoq.com/news/2026/05/anthropic-claude-code-auto-mode/)）から引用します。

> Each proposed action undergoes evaluation before running, functioning as an automated approval mechanism that filters safe operations while routing ambiguous cases for additional checks.

二段階分類器が個々のツール呼び出しのリスクを評価し、安全と判断したものは自動承認、曖昧なものは追加チェックや人間への確認に回す、という仕組みです。

UX 上の特徴として、

> In auto mode, the spinner now turns red when a permission check is triggered, giving you a clear visual signal that Claude is pausing for approval.

承認待ちで**スピナーが赤くなる**という視覚的シグナルが入りました。「いつの間にか勝手に実行されていた」を防ぐための小さいけれど重要な UX 設計です。

### Auto Mode はどう位置づけるか

Auto Mode は、`default`（毎回聞く）と `bypassPermissions`（聞かない）の中間です。位置づけとしては「**Human-in-the-Loop の 1.5 世代**」と言えます。

- 1.0 世代: すべてのアクションで人間に承認を求める（疲弊する）
- 1.5 世代（Auto Mode）: 分類器がリスクをスコア化し、危険なものだけ人間に聞く
- 2.0 世代: 完全自律（PocketOS 事件のリスクが現実化する）

Auto Mode は便利ですが、**本番への接続権限を持つエージェントには使うべきではない**と考えます。なぜなら分類器が「安全」と判断する基準が、運用環境特有の文脈（本番 URL、本番 DB の名前空間、危険な API キー）を完全に把握できる保証はないからです。本番系では Hooks による明示的な deny ルールを優先するのが堅実です。

## 5 段階評価フローを再確認する

ここまで見てきた三層は、公式の評価順では次のように並びます。

```
1. Hooks
2. Deny rules（disallowed_tools, settings.json の deny）
3. Permission mode
4. Allow rules（allowed_tools, settings.json の allow）
5. canUseTool callback
```

このフローには重要な性質がいくつかあります。

### 性質 1: Hooks は最優先

`bypassPermissions` モードでも hooks は走ります。「とにかく止めたいもの」は hooks に書いておけば、モード設定の取り違えがあっても止まります。

### 性質 2: Deny rules は bypass を貫通する

```json
// settings.json
{
  "permissions": {
    "deny": ["Bash(rm -rf /*)"]
  }
}
```

このルールは `bypassPermissions` でも有効です。「絶対に実行されてはいけない」ものは deny rules に書きます。

### 性質 3: `allowed_tools` は bypass を制約しない

公式 docs が Warning で強調している点です。

> `allowed_tools` does not constrain `bypassPermissions`. `allowed_tools` only pre-approves the tools you list. Unlisted tools are not matched by any allow rule and fall through to the permission mode, where `bypassPermissions` approves them.

「`allowedTools: ["Read"]` を設定したから安全」という勘違いが、`bypassPermissions` と組み合わさった時に最も危険です。`allowed_tools` はホワイトリストではなく**自動承認リスト**であり、リストにないものは「自動承認されない」だけで、permission mode によっては承認されてしまいます。

ホワイトリスト的に運用したいなら、`allowed_tools` + `permissionMode: "dontAsk"` のセットが正解です。

## PocketOS 事件を三層ゲートで防げたか

事件の振り返りです。The Register の取材によれば、root cause は次の 3 つでした。

1. API トークンのスコープが過大（"any operation, including destructive ones"）
2. 削除コマンドへの確認チェックが存在しなかった
3. バックアップが本番と同一ボリュームに保存されていた

このうち (3) はインフラ設計の問題なので Claude Code 側ではどうしようもありません。しかし (1)(2) は三層ゲートで構造的に防げたものです。

### 防衛ライン 1: settings.json の deny rule

```json
{
  "permissions": {
    "deny": [
      "Bash(curl * railway.app/*/volumes/* -X DELETE*)",
      "Bash(curl * api.production.* -X DELETE*)"
    ]
  }
}
```

本番削除系 API への curl は問答無用でブロック。`bypassPermissions` でも貫通しないので、エージェントのモード設定ミスがあっても守られます。

### 防衛ライン 2: PreToolUse hook で意図確認

`Bash` ツールが `DELETE` メソッドや `rm -rf` を含むコマンドを実行しようとしたら `deny` を返す hook を組みます。前述の `pretool_rm_guard.py` の応用です。

### 防衛ライン 3: dontAsk + allowedTools

ヘッドレスで動かす CI エージェントなら、`dontAsk` モードで「使えるツールは Read / Grep / Edit のみ、Bash は禁止」と縛ってしまうのが最も確実です。本来の修正タスクが Bash を必要とするなら、人間が介入する余地が残ります。

PocketOS のエージェントには、これらのいずれも入っていなかった。だから 9 秒で本番が消えました。

## まとめ

最後にチェックリストにまとめます。

- [ ] 本番接続権限を持つエージェントは `default` か `dontAsk` で動かす（`bypassPermissions` は使わない）
- [ ] 親エージェントのモードはサブエージェントに継承される（特に `bypassPermissions` / `acceptEdits` / `auto`）。サブの挙動も含めて設計する
- [ ] 「絶対に実行されてはいけない」コマンドは `settings.json` の deny rules に書く（bypass を貫通する）
- [ ] `PreToolUse` hook で危険コマンドガードを組む。複数 hook の優先順位は `deny > defer > ask > allow`
- [ ] `allowed_tools` をホワイトリストとして使うなら必ず `permissionMode: "dontAsk"` とセット
- [ ] Auto Mode の赤いスピナーは便利だが、本番系では明示的な hooks deny を優先

「エージェントは原則を守ってくれる」という前提を捨てて、**構造的に止める**設計に切り替える。それが PocketOS 事件後の Claude Code 運用のスタンダードになっていくはずです。

## 参考リンク

- [Claude Code Hooks 公式ドキュメント](https://code.claude.com/docs/en/hooks)
- [Claude Agent SDK Permissions 公式ドキュメント](https://code.claude.com/docs/en/agent-sdk/permissions)
- [InfoQ: Inside Claude Code Auto Mode](https://www.infoq.com/news/2026/05/anthropic-claude-code-auto-mode/)
- [The Register: Cursor-Opus agent snuffs out startup's production database](https://www.theregister.com/2026/04/27/cursoropus_agent_snuffs_out_pocketos/)
- [Euronews: An AI agent deleted a company's entire database in 9 seconds](https://www.euronews.com/next/2026/04/28/an-ai-agent-deleted-a-companys-entire-database-in-9-seconds-then-wrote-an-apology)
