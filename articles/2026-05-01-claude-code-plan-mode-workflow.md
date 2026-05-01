---
title: "Plan Mode 中心の Claude Code 開発手法 — 計画→実装→検証の4フェーズで AI を味方につける"
emoji: "🗺️"
type: "tech"
topics: ["claudecode", "ai", "planmode", "anthropic", "agent"]
published: true
---

## はじめに：なぜ「いきなり実装」が罠なのか

Claude Code を使い始めて数週間も経つと、誰もが一度は次の体験をする。

> 「ざっくり要件を投げる → なぜか動くコードが返ってくる → でも要件と微妙にズレている → 直してもらう → さらにズレる → 自分で書き直したほうが速かった」

この感覚は気のせいではない。METR が 2025 年に行った RCT（ランダム化比較試験）では、**経験豊富な OSS 開発者 16 名・246 タスクで AI ツール使用時の完了時間が 19% 増加**した。さらに興味深いのは、参加者本人は「AI で 20% 速くなった」と感じていたことだ。客観値と主観値が 40 ポイント近く乖離している[^metr2025]。

[^metr2025]: METR, [Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/) (2025-07-10). 16 名の開発者が 246 のタスクを実施した RCT。

ところが、METR が 2026 年 2 月に追加で行ったトランスクリプト分析では、生産性向上が確認できた事例（high-uplift transcripts）には共通点があった。それは **「事前に書かれたプラン」に基づく大規模実装やリファクタリング** だったということだ[^metr2026]。

[^metr2026]: METR, [Analyzing coding agent transcripts to upper bound productivity gains from AI agents](https://metr.org/notes/2026-02-17-exploratory-transcript-analysis-for-estimating-time-savings-from-coding-agents/) (2026-02-17).

つまり「AI で速くなる人」と「遅くなる人」を分けているのは、**実装前にどれだけ構造化された計画を作るか** だった。

Anthropic 公式の Best Practices にも、まさにこの順序が明記されている。

> Explore first, then plan, then code
> ([Best Practices for Claude Code](https://code.claude.com/docs/en/best-practices))

本記事では、この「Explore → Plan → Implement → Commit」の 4 フェーズを支える機能 **Plan Mode** を軸に、2026 年現在の実践的な Claude Code 開発手法を整理する。

:::message
本記事の検証環境：Claude Code v2.1.126（macOS）。コマンドオプションは `claude --help` の出力から確認。
:::

## Plan Mode とは何か

Plan Mode は **読み取り専用で動作する Claude Code の動作モード** だ。Plan Mode 中の Claude は、ファイルを読み込み、コードベースを分析し、質問に答え、実装計画を提示するが、**ファイルの編集もコマンド実行も一切行わない**[^docs-planmode]。

[^docs-planmode]: Anthropic, [Common workflows: Use Plan Mode for safe code analysis](https://code.claude.com/docs/en/common-workflows#use-plan-mode-for-safe-code-analysis).

「計画」と「実行」を強制的に分離するための仕組み、と捉えるとわかりやすい。

### Plan Mode への入り方（3 つの入り口）

| 方法 | 用途 |
|---|---|
| `Shift+Tab` を 2 回押す | 既存セッションの途中で切り替え（Normal → Auto-Accept → Plan の順で循環） |
| `claude --permission-mode plan` | セッション開始時から Plan Mode |
| `/plan`（v2.1.0+） | セッション中にスラッシュコマンドで切り替え |

実機確認：

```bash
$ claude --version
2.1.126 (Claude Code)

$ claude --help | grep permission-mode
  --permission-mode <mode>  ... (choices: "acceptEdits", "auto", "bypassPermissions", "default", "dontAsk", "plan")
```

`--permission-mode plan` が正式オプションとして提供されており、`plan` 以外にも `acceptEdits`（自動承認）、`auto`（リスク判定付き自動承認）、`bypassPermissions`（全承認スキップ）など複数の権限モードが存在する。

### ヘッドレス実行も可能

Plan Mode は対話セッションだけでなく、`-p` フラグと組み合わせてヘッドレス実行もできる。

```bash
claude --permission-mode plan -p "Analyze the authentication system and suggest improvements"
```

CI で Pull Request の差分に対する設計レビューを自動化したい、といった用途で有用だ。

## 公式推奨の 4 フェーズワークフロー

Anthropic Best Practices が推奨するワークフローは、以下の 4 つのフェーズで構成される[^docs-bp]。

[^docs-bp]: Anthropic, [Best Practices for Claude Code: Explore first, then plan, then code](https://code.claude.com/docs/en/best-practices#explore-first-then-plan-then-code).

```
Explore（調査）→ Plan（計画）→ Implement（実装）→ Commit（コミット）
```

### Phase 1: Explore — まずは読む

Plan Mode に入って、関連ファイルを読ませる。プロンプトは「実装してくれ」ではなく「読んで理解しろ」にする。

```text
[Plan Mode]
read /src/auth and understand how we handle sessions and login.
also look at how we manage environment variables for secrets.
```

このフェーズで Claude は `Read` / `Grep` / `Glob` などの読み取り系ツールしか使わない。コードベースに対する Claude の理解度を、まずこちらが把握する段階だ。

### Phase 2: Plan — 計画を作らせる

Claude に詳細な実装計画を作らせる。

```text
[Plan Mode]
I want to add Google OAuth. What files need to change?
What's the session flow? Create a plan.
```

ここで重要なのが **`Ctrl+G` でプランをテキストエディタで開いて直接編集できる** という点。AI が出したプランをそのまま受け入れるのではなく、人間が手を加えてから実装に進める。

プランが固まると Claude は内部的に `ExitPlanMode` を呼び出し、承認を求めてくる。選択肢には「Yes」「Yes, and auto-accept edits」などがあり、ここで Auto-Accept Edits Mode に切り替えると、その後の実装フェーズで個別の承認プロンプトを省略できる。

### Phase 3: Implement — 計画に沿って実装させる

Normal Mode（または Auto-Accept Edits Mode）に戻して、計画に基づいて実装させる。重要なのは **「計画に基づいて」と明示すること**、そして **検証手段（テストなど）も同じプロンプトに含めること**。

```text
[Normal Mode]
implement the OAuth flow from your plan. write tests for the
callback handler, run the test suite and fix any failures.
```

Anthropic 公式の言葉を借りれば、「Claude が自分の仕事を検証できる手段を提供することが、最もレバレッジの高い行為」だ[^docs-verify]。

[^docs-verify]: Anthropic, [Best Practices: Give Claude a way to verify its work](https://code.claude.com/docs/en/best-practices#give-claude-a-way-to-verify-its-work).

### Phase 4: Commit — そのまま PR まで

```text
[Normal Mode]
commit with a descriptive message and open a PR
```

`gh` CLI が入っていれば、Claude は PR の作成までやってくれる。Plan の段階で文脈が固まっているので、PR の説明文も的を射たものになりやすい。

## CLAUDE.md と Plan Mode は両輪である

Plan Mode を使い始めると、しばしば次のような違和感に遭遇する。

> プランの方向性は合っているが、ファイル配置の流儀やテストの書き方がプロジェクト規約と違う

この症状について、公式 docs は明確に指摘している。

> If Claude generates a plan that doesn't match your project's architecture or conventions, this almost always means your CLAUDE.md is missing or incomplete
> ([Best Practices](https://code.claude.com/docs/en/best-practices))

つまり Plan Mode 単体で精度を上げようとせず、**プロジェクト規約は CLAUDE.md に書いておく** のが前提になる。

### CLAUDE.md に「書くべき／書かない」公式ガイド

| ✅ 書くべき | ❌ 書かない |
|---|---|
| Claude が推測できない Bash コマンド | コードを読めばわかること |
| デフォルトと異なるコードスタイル | 言語の標準的な慣習 |
| テスト実行手順・優先するテストランナー | 詳細な API ドキュメント（リンクで十分） |
| リポジトリのエチケット（ブランチ名、PR 規約） | 頻繁に変わる情報 |
| プロジェクト固有のアーキテクチャ判断 | 長い説明やチュートリアル |
| 開発環境のクセ（必須の環境変数等） | ファイル単位の説明 |
| よくあるハマりどころ | 「綺麗なコードを書け」のような自明な指示 |

公式 docs より整理[^docs-claudemd]。

[^docs-claudemd]: Anthropic, [Best Practices: Write an effective CLAUDE.md](https://code.claude.com/docs/en/best-practices#write-an-effective-claudemd).

「書きすぎた CLAUDE.md は、重要なルールがノイズに埋もれて Claude が無視する」と公式が警告している点は重要。CLAUDE.md は **コードと同じくレビューと剪定の対象** にすべきだ。

判断基準として `/init` コマンドが用意されている。プロジェクト構造を解析して、たたき台の CLAUDE.md を生成してくれる。そこから不要な行を削っていくのが現実的なスタートポイントになる。

## 「Plan Mode を使わない」判断も同じくらい大事

Plan Mode は万能ではない。公式 docs は次のように釘を刺している。

> Plan Mode is useful, but also adds overhead.
>
> For tasks where the scope is clear and the fix is small (like fixing a typo, adding a log line, or renaming a variable) ask Claude to do it directly.
>
> Planning is most useful when you're uncertain about the approach, when the change modifies multiple files, or when you're unfamiliar with the code being modified. **If you could describe the diff in one sentence, skip the plan.**

要約すると：

| Plan Mode を使う | Plan Mode を skip |
|---|---|
| アプローチが不確実 | スコープが明確 |
| 複数ファイルにまたがる変更 | 単一ファイルの小さな修正 |
| 不慣れなコードベース | 1文で diff を説明できる |

「タイポ修正」「ログ追加」「変数リネーム」を Plan Mode でやるのは過剰、と公式が明言している。

## METR が示した「真の勝ちパターン」

冒頭で触れた METR の結果を、もう少し深く見てみる。

### 主観と実測の乖離

2025 年の RCT では、開発者は事前に「AI で 24% 速くなる」と予測し、実施後は「20% 速くなった」と感じていた。だが客観的な完了時間は **19% 増加** していた[^metr2025]。

これは認知バイアスの典型例で、AI が「考えている時間」「コードを生成している時間」が、開発者の主観では待ち時間ではなく能動的な作業時間として記憶されやすい、という解釈ができる。

### 「速くなった人」に共通する条件

ところが METR の 2026 年 2 月のフォローアップでは、**生産性向上が確認できた事例には明確な共通点** があった[^metr2026]。

- 事前にプランが書かれている
- 大規模な実装やリファクタリングである
- タスクが「監督と検証」に向いている

つまり Claude（や類似の AI エージェント）は、**「実装そのもの」より「監督・検証」を効率化するツール** として真価を発揮する。これは独立した SSRN のワーキングペーパーでも「AI エージェントは労働者の労力を実装から監督へとシフトさせる」と報告されている[^sarkar]。

[^sarkar]: Sarkar, S. K. [AI Agents and Higher-Order Work](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5713646). SSRN Working Paper.

Plan Mode はこの構造変化を **明示的にワークフローに組み込んだもの** だと言える。

> 「Claude にコードを書かせる」のではなく、「Claude が書こうとしているコードをレビューする」立場に最初から立つ。

これが Plan Mode の本質だ。

## 実践 Tips

### Tip 1: `defaultMode: "plan"` でデフォルト化する

毎回 `Shift+Tab` を押すのが面倒なら、プロジェクトの `.claude/settings.json` でデフォルトを Plan Mode にできる。

```json
{
  "permissions": {
    "defaultMode": "plan"
  }
}
```

「不慣れな大規模リポジトリ」「壊したくない本番コード」を扱うときの安全装置として有効。

### Tip 2: Plan Mode → Auto-Accept Edits の連携

公式が推奨する流れは：

```
Plan Mode で計画を固める
  ↓ Ctrl+G でプランを編集（任意）
  ↓ 承認時に「Yes, and auto-accept edits」を選択
Auto-Accept Edits Mode で実装が一気に進む
```

計画段階では人間が関与し、実装段階では介入を最小化する。**「重要な意思決定は人間が、機械的な実装は Claude が」** という役割分担を明示的に作るパターンだ。

### Tip 3: 「2 回直したら `/clear`」 ルール

公式 Best Practices が「common failure pattern」として挙げているもののひとつ：

> **Correcting over and over.** Claude does something wrong, you correct it, it's still wrong, you correct again. Context is polluted with failed approaches.
>
> Fix: After two failed corrections, `/clear` and write a better initial prompt incorporating what you learned.

同じことを 2 回直しても直らないなら、コンテキストが「失敗した試行」で汚染されている。`/clear` で仕切り直し、得た学びを Plan Mode で再計画したほうが速い。

### Tip 4: ヘッドレス Plan Mode で設計レビュー bot を作る

```bash
gh pr diff 123 | claude --permission-mode plan -p \
  "Review this PR diff. Identify edge cases, missing tests, and potential regressions. Output as a markdown checklist."
```

PR の差分を Plan Mode で分析させ、結果をコメントとして投稿する CI ジョブが組める。Plan Mode は読み取り専用なので、CI で安全に動かせる点もメリット。

## まとめ：2026 年は「計画する人」が勝つ

ここまでの内容を 1 行で言うと：

> Claude Code の生産性は **「いきなり実装させない訓練」** で決まる。

具体的には：

1. **Plan Mode を入り口にする**（`--permission-mode plan` / `Shift+Tab×2` / `/plan`）
2. **4 フェーズを意識する**（Explore → Plan → Implement → Commit）
3. **CLAUDE.md を磨く**（プロジェクト規約は CLAUDE.md に集約）
4. **使わない判断も大事**（小さな差分はオーバーヘッド）
5. **「監督と検証」が AI 時代のレバレッジポイント**（METR が示した）

「AI を使うほど遅くなる」という METR の結果は、AI そのものの限界ではなく、**人間側のワークフローが追いついていない** ことの表れだ。Plan Mode はその差を埋めるためのツールであり、2026 年の Claude Code 開発の中心に置くべき機能だと言える。

逆に言えば、Plan Mode を使わずに毎回いきなり実装させているなら、まだ Claude Code の半分の力しか引き出せていない可能性が高い。今日の最後のセッションから、`Shift+Tab` を 2 回押すところから始めてみてほしい。

## 参考リンク

- [Best Practices for Claude Code](https://code.claude.com/docs/en/best-practices)（公式）
- [Common workflows: Plan Mode](https://code.claude.com/docs/en/common-workflows#use-plan-mode-for-safe-code-analysis)（公式）
- [METR: Measuring the Impact of Early-2025 AI on Experienced OSS Developer Productivity](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)
- [METR: Analyzing coding agent transcripts to upper bound productivity gains](https://metr.org/notes/2026-02-17-exploratory-transcript-analysis-for-estimating-time-savings-from-coding-agents/)
- [arXiv: Measuring the Impact of Early-2025 AI (2507.09089)](https://arxiv.org/abs/2507.09089)
