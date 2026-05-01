---
title: "Plan Mode 中心の Claude Code 開発手法 — 計画→実装→検証の4フェーズで AI を味方につける"
emoji: "🗺️"
type: "tech"
topics: ["claudecode", "ai", "planmode", "anthropic", "agent"]
published: true
---

## はじめに

Claude Code を使い始めて少し経つと、こんな経験をしたことはないでしょうか。

> ざっくり要件を投げる → なぜか動くコードが返ってくる → でも要件と微妙にズレている → 直してもらう → さらにズレる → 自分で書き直したほうが速かった

実はこれ、データでも裏付けられています。METR が 2025 年に行った RCT（ランダム化比較試験）では、経験豊富な OSS 開発者 16 名が 246 タスクを実施したところ、**AI ツールを使った場合の完了時間が 19% 増加**していました。さらに面白いのは、参加者本人は「AI で 20% 速くなった」と感じていたという点です（[METR の研究](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)）。

ところが METR は 2026 年 2 月に追加分析を公開していて、**生産性が向上した事例には共通点がある**ことを報告しています。それは「事前に書かれたプランに基づく大規模な実装やリファクタリング」だった、というものです（[METR トランスクリプト分析](https://metr.org/notes/2026-02-17-exploratory-transcript-analysis-for-estimating-time-savings-from-coding-agents/)）。

つまり「AI で速くなる人」と「遅くなる人」を分けているのは、**実装前にどれだけ計画を作っているか**でした。

Anthropic 公式の Best Practices にも、このことがそのまま書かれています。

> Explore first, then plan, then code

この記事では、Claude Code の **Plan Mode** という機能を軸に、「Explore → Plan → Implement → Commit」の 4 フェーズワークフローを紹介します。

:::message
本記事の検証環境：Claude Code v2.1.126（macOS）
:::

## Plan Mode とは

Plan Mode は **ソースコードを編集しない動作モード**です。Plan Mode 中の Claude は、ファイルを読んだり、コードベースを調査するためのシェルコマンド（grep など）を実行したり、実装計画を書いたりはできますが、**ソースの編集は一切行いません**。

「計画」と「実行」を強制的に分けるための仕組み、と考えるとイメージしやすいです。

### Plan Mode への入り方

入り口は 3 つあります。

| 方法 | 用途 |
|---|---|
| `Shift+Tab` を押す | セッション途中で切り替え（`default` → `acceptEdits` → `plan` の順で循環） |
| `claude --permission-mode plan` | セッション開始時から Plan Mode |
| プロンプト先頭に `/plan` を付ける | 単発のプロンプトだけ Plan Mode で動かす |

実機で確認すると、こんな感じです。

```bash
$ claude --version
2.1.126 (Claude Code)

$ claude --help | grep permission-mode
  --permission-mode <mode>  ... (choices: "acceptEdits", "auto", "bypassPermissions", "default", "dontAsk", "plan")
```

`--permission-mode plan` は正式オプションとして提供されています。`plan` 以外にも `acceptEdits`（自動承認）、`auto`（リスク判定付き自動承認）、`bypassPermissions`（全承認スキップ）など複数の権限モードがあります。

### ヘッドレス実行もできる

Plan Mode は対話セッションだけでなく、`-p` フラグと組み合わせてヘッドレス実行も可能です。

```bash
claude --permission-mode plan -p "Analyze the authentication system and suggest improvements"
```

CI で PR の差分に対する設計レビューを自動化したい、といった用途で使えます。

## 公式推奨の 4 フェーズワークフロー

Anthropic Best Practices が推奨するワークフローは、4 つのフェーズで構成されています。

```
Explore（調査）→ Plan（計画）→ Implement（実装）→ Commit（コミット）
```

順番に見ていきます。

### Phase 1: Explore — まずは読ませる

Plan Mode に入って、関連ファイルを読ませます。プロンプトは「実装してくれ」ではなく「読んで理解して」にするのがポイントです。

```text
[Plan Mode]
read /src/auth and understand how we handle sessions and login.
also look at how we manage environment variables for secrets.
```

このフェーズでは Claude は `Read` / `Grep` / `Glob` などの読み取り系ツールしか使いません。コードベースに対する Claude の理解度を、まず把握する段階です。

### Phase 2: Plan — 計画を作らせる

次に、Claude に詳細な実装計画を作らせます。

```text
[Plan Mode]
I want to add Google OAuth. What files need to change?
What's the session flow? Create a plan.
```

ここで便利なのが **`Ctrl+G` でプランをテキストエディタで開いて直接編集できる**機能です。AI が出したプランをそのまま受け入れるのではなく、人間が手を加えてから実装に進められます。

プランが固まると Claude は承認プロンプトを表示します。公式 docs によると選択肢は次の 5 つです。

- Approve and start in auto mode（Auto Mode で実装開始）
- Approve and accept edits（編集を自動承認しつつ実装開始）
- Approve and review each edit manually（編集を 1 件ずつレビューしながら実装）
- Keep planning with feedback（フィードバックを伝えて計画を継続）
- Refine with Ultraplan（[Ultraplan](https://code.claude.com/docs/en/ultraplan) でブラウザベースのレビュー）

それぞれの「Approve」系オプションは、計画フェーズのコンテキストをクリアしてから実装を始めるかどうかも選べるようになっています。

### Phase 3: Implement — 計画に沿って実装させる

Normal Mode（または Auto-Accept Edits Mode）に戻して、計画に基づいて実装させます。コツは 2 つです。

- **「計画に基づいて」と明示する**
- **検証手段（テストなど）も同じプロンプトに含める**

```text
[Normal Mode]
implement the OAuth flow from your plan. write tests for the
callback handler, run the test suite and fix any failures.
```

Anthropic 公式は「Claude が自分の仕事を検証できる手段を提供することが、最もレバレッジの高い行為」と書いています。テストやリンターなど、Claude が自分で正しさを確認できる仕組みを用意しておくと精度が一気に上がります。

### Phase 4: Commit — そのまま PR まで

```text
[Normal Mode]
commit with a descriptive message and open a PR
```

`gh` CLI が入っていれば、Claude は PR の作成までやってくれます。Plan の段階で文脈が固まっているので、PR の説明文も的を射たものになりやすいです。

## CLAUDE.md と Plan Mode はセットで効く

Plan Mode を使い始めると、こんな違和感に出会うことがあります。

> プランの方向性は合っているけど、ファイル配置の流儀やテストの書き方がプロジェクト規約と違う

この症状について、公式 docs は明確に書いています。

> If Claude generates a plan that doesn't match your project's architecture or conventions, this almost always means your CLAUDE.md is missing or incomplete

プランが規約に合わないときは、ほぼ間違いなく CLAUDE.md が不足している、ということです。Plan Mode 単体で精度を上げようとせず、**プロジェクト規約は CLAUDE.md にあらかじめ書いておく**のが前提になります。

### CLAUDE.md に書くべきこと・書かないこと

公式の Best Practices より整理しました。

| ✅ 書くべき | ❌ 書かない |
|---|---|
| Claude が推測できない Bash コマンド | コードを読めばわかること |
| デフォルトと異なるコードスタイル | 言語の標準的な慣習 |
| テスト実行手順・優先するテストランナー | 詳細な API ドキュメント（リンクで十分） |
| リポジトリのエチケット（ブランチ名、PR 規約） | 頻繁に変わる情報 |
| プロジェクト固有のアーキテクチャ判断 | 長い説明やチュートリアル |
| 開発環境のクセ（必須の環境変数等） | ファイル単位の説明 |
| よくあるハマりどころ | 「綺麗なコードを書け」のような自明な指示 |

公式は「書きすぎた CLAUDE.md は、重要なルールがノイズに埋もれて Claude が無視する」とも指摘しています。CLAUDE.md は **コードと同じくレビューと剪定の対象**にしておくとよさそうです。

`/init` コマンドを使うとプロジェクト構造を解析して、たたき台の CLAUDE.md を生成してくれます。そこから不要な行を削っていくのが現実的なスタートポイントになります。

## Plan Mode を「使わない」判断も大事

Plan Mode は万能ではありません。公式 docs は次のように釘を刺しています。

> Plan Mode is useful, but also adds overhead.
>
> ... If you could describe the diff in one sentence, skip the plan.

要するに、こういう使い分けです。

| Plan Mode を使う | Plan Mode を skip |
|---|---|
| アプローチが不確実 | スコープが明確 |
| 複数ファイルにまたがる変更 | 単一ファイルの小さな修正 |
| 不慣れなコードベース | 1文で diff を説明できる |

「タイポ修正」「ログ追加」「変数リネーム」を Plan Mode でやるのは過剰、と公式が明言しています。

## METR が示した「真の勝ちパターン」

冒頭の METR の話を、もう少し掘り下げてみます。

### 主観と実測の乖離

2025 年の RCT では、開発者は事前に「AI で 24% 速くなる」と予測し、実施後は「20% 速くなった」と感じていました。でも実測は **19% 増加**でした。

これは認知バイアスの典型例で、AI が「考えている時間」「コードを生成している時間」が、開発者の主観では待ち時間ではなく能動的な作業時間として記憶されやすい、という解釈ができます。

### 速くなった人に共通する条件

ところが METR の 2026 年 2 月のフォローアップでは、生産性が確認できた事例に共通点がありました。

- 事前にプランが書かれている
- 大規模な実装やリファクタリングである
- タスクが「監督と検証」に向いている

つまり Claude（や類似の AI エージェント）は、「実装そのもの」より「監督・検証」を効率化するツールとして真価を発揮するようです。Plan Mode はこの構造変化を、**明示的にワークフローに組み込んだ機能**だと言えそうです。

「Claude にコードを書かせる」のではなく「Claude が書こうとしているコードをレビューする」立場に最初から立つ、というイメージです。

## 実践 Tips

### Tip 1: `defaultMode: "plan"` でデフォルト化する

毎回 `Shift+Tab` を押すのが面倒なら、プロジェクトの `.claude/settings.json` でデフォルトを Plan Mode にできます。

```json
{
  "permissions": {
    "defaultMode": "plan"
  }
}
```

不慣れな大規模リポジトリや、壊したくない本番コードを扱うときの安全装置として便利です。

### Tip 2: Plan Mode → Auto-Accept Edits の連携

公式が推奨する流れはこんな感じです。

```
Plan Mode で計画を固める
  ↓ Ctrl+G でプランを編集（任意）
  ↓ 承認時に「Approve and accept edits」を選択
Auto-Accept Edits Mode で実装が一気に進む
```

計画段階では人間が関与し、実装段階では介入を最小化する。「重要な意思決定は人間が、機械的な実装は Claude が」という役割分担を明示的に作るパターンです。

### Tip 3: 「2 回直したら `/clear`」 ルール

公式 Best Practices が「common failure pattern」として挙げているもののひとつです。

> Correcting over and over. Claude does something wrong, you correct it, it's still wrong, you correct again. Context is polluted with failed approaches.

同じことを 2 回直しても直らないなら、コンテキストが「失敗した試行」で汚染されています。`/clear` で仕切り直して、得た学びを Plan Mode で再計画したほうが速いことが多いです。

### Tip 4: ヘッドレス Plan Mode で設計レビュー bot

```bash
gh pr diff 123 | claude --permission-mode plan -p \
  "Review this PR diff. Identify edge cases, missing tests, and potential regressions. Output as a markdown checklist."
```

PR の差分を Plan Mode で分析させて、結果をコメントとして投稿する CI ジョブが組めます。Plan Mode は読み取り専用なので、CI で安全に動かせるのもメリットです。

## まとめ

ここまでの内容をまとめると、こんな感じになります。

1. **Plan Mode を入り口にする**（`--permission-mode plan` / `Shift+Tab×2` / `/plan`）
2. **4 フェーズを意識する**（Explore → Plan → Implement → Commit）
3. **CLAUDE.md を磨く**（プロジェクト規約は CLAUDE.md に集約）
4. **使わない判断も大事**（小さな差分はオーバーヘッド）
5. **「監督と検証」が AI 時代のレバレッジポイント**（METR の知見）

「AI を使うほど遅くなる」という METR の結果は、AI そのものの限界というより、人間側のワークフローが追いついていない部分が大きそうです。Plan Mode はその差を埋めるためのツールで、2026 年の Claude Code 開発の中心に置いておくとよいかもしれません。

普段 Plan Mode を使っていない方は、次のセッションで `Shift+Tab` を 2 回押すところから試してみてください。

## 参考リンク

- [Best Practices for Claude Code](https://code.claude.com/docs/en/best-practices)（公式）
- [Common workflows: Plan Mode](https://code.claude.com/docs/en/common-workflows#use-plan-mode-for-safe-code-analysis)（公式）
- [METR: Measuring the Impact of Early-2025 AI on Experienced OSS Developer Productivity](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)
- [METR: Analyzing coding agent transcripts to upper bound productivity gains](https://metr.org/notes/2026-02-17-exploratory-transcript-analysis-for-estimating-time-savings-from-coding-agents/)
- [arXiv: Measuring the Impact of Early-2025 AI (2507.09089)](https://arxiv.org/abs/2507.09089)
