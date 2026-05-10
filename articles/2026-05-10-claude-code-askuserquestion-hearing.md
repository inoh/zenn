---
title: "Claude Code の AskUserQuestion で業務委託の要件ヒアリングを構造化する"
emoji: "🎤"
type: "tech"
topics: ["claudecode", "ai", "anthropic", "agent", "askuserquestion"]
published: true
---

## はじめに

業務委託でコードを書いていると、こんな経験はないでしょうか。

> 顧客と打ち合わせ → 「要件まとまったので作っておきます」と持ち帰る → 実装中に決まっていない事項が次々出る → Slack で都度確認 → 返信待ちで止まる → 結局自分で意思決定して進める → 納品時に「思ってたのと違う」

原因は腕でもツール選定でもなく、**ヒアリングの抜け漏れ**であることがほとんどです。

この問題に対して、Anthropic が 2026 年に公式ベストプラクティスで提示しているのが `AskUserQuestion` ツールを使った「Claude にインタビューさせる」パターンです。

> For larger features, have Claude interview you first. Start with a minimal prompt and ask Claude to interview you using the `AskUserQuestion` tool.
>
> — [Anthropic 公式 Best Practices](https://code.claude.com/docs/en/best-practices)

この記事では、`AskUserQuestion` の挙動を実機で確認したうえで、**業務委託の顧客ヒアリング工程に組み込むワークフロー**を整理します。

:::message
本記事の検証環境：Claude Code v2.1.138（macOS）
:::

## AskUserQuestion とは

`AskUserQuestion` は Claude Code に組み込まれているネイティブツールで、Claude が**選択式の質問を 1〜4 問まとめてユーザーに投げる**ためのものです。普段の自由入力と違い、質問・選択肢・複数選択可否がスキーマで構造化されており、UI 側で選択肢ボタンとして描画されます。

公式ドキュメントは Agent SDK 配下に置かれています：

- [Handle approvals and user input](https://code.claude.com/docs/en/agent-sdk/user-input)

Best Practices ページにも独立した節があり、「Let Claude interview you」として推奨されています。

### スキーマから読み取れる仕様

実機で取得できる `AskUserQuestion` のスキーマを要約すると以下です（公式ドキュメントの記述と一致）。

| 項目 | 制約 |
|---|---|
| `questions` | 1〜4 問 |
| `options` | 2〜4 選択肢 |
| `header` | 12 文字以下のチップラベル |
| `multiSelect` | `true` で複数選択可 |
| 自由入力 | 「Other」が UI 側で自動付与 |
| `preview` | 各選択肢に Markdown / HTML プレビューを付けられる（TypeScript SDK 限定） |

公式ドキュメントには重要な制限が 2 つ明記されています。

> - **Subagents**: `AskUserQuestion` is not currently available in subagents spawned via the Agent tool
> - **Question limits**: each `AskUserQuestion` call supports 1-4 questions with 2-4 options each
>
> — [Handle approvals and user input — Limitations](https://code.claude.com/docs/en/agent-sdk/user-input)

つまり「サブエージェントに長時間ヒアリングさせて、その結果を親に返す」設計は今のところ取れません。後述しますが、ここは業務委託フローを組むときの設計分岐になります。

### Plan Mode との結びつき

公式ドキュメントは `AskUserQuestion` が **Plan Mode と特に相性が良い**と明言しています。

> Clarifying questions are especially common in `plan` mode, where Claude explores the codebase and asks questions before proposing a plan. This makes plan mode ideal for interactive workflows where you want Claude to gather requirements before making changes.
>
> — [Handle approvals and user input](https://code.claude.com/docs/en/agent-sdk/user-input)

「コードを書く前に計画を作る」Plan Mode と、「**計画を作る前に要件を固める**」AskUserQuestion を組み合わせると、`要件 → 計画 → 実装` の 3 段ロケットになります。

## 実機での挙動

実際にプロンプトを投げると、Claude はチップ風のラベル（`header`）と質問本文・選択肢を表示し、ユーザーが選択するまで処理を止めます。CLI でも IDE 拡張でも同じ挙動です。

公式が勧めるテンプレートはこれです。

```text
I want to build [brief description]. Interview me in detail using the AskUserQuestion tool.

Ask about technical implementation, UI/UX, edge cases, concerns, and tradeoffs.
Don't ask obvious questions, dig into the hard parts I might not have considered.

Keep interviewing until we've covered everything, then write a complete spec to SPEC.md.
```

ポイントは 3 つあります。

1. **「AskUserQuestion を使え」と明示する** — 指定しないと普通に自由入力で聞いてくる
2. **「分かりきった質問はするな（don't ask obvious questions）」** と入れる — これがないと「何を作りたいですか？」レベルで終わる
3. **最後に SPEC.md として書き出させる** — その場の対話を成果物として残す

公式が後段で強調しているのが、**spec が完成したら新しいセッションを開いて実装を始める**という運用です。

> Once the spec is complete, start a fresh session to execute it. The new session has clean context focused entirely on implementation, and you have a written spec to reference.
>
> — [Anthropic 公式 Best Practices](https://code.claude.com/docs/en/best-practices)

ヒアリングと実装でセッションを分ける理由は、コンテキスト窓の汚染を避けるためです。要件を詰めるフェーズで読んだ参考資料・選択肢の議論ログがそのまま実装セッションに残ると、Claude は無関係な過去の発言に引きずられます。

## 業務委託のヒアリングに組み込む

ここからが本題です。業務委託の流れに沿って `AskUserQuestion` をどこに差し込むかを整理します。

### 全体像

```
顧客とのMTG（人間 ↔ 人間）
        ↓
   メモ起こし
        ↓
[セッション1] Claude がインタビューする ← AskUserQuestion
        ↓
   SPEC.md 完成
        ↓
   顧客レビュー（人間 ↔ 人間）
        ↓
[セッション2] 実装  ← Plan Mode
```

ポイントは、**顧客と直接話すフェーズは置き換えない**ことです。AskUserQuestion は「自分が顧客に聞き忘れたことを発掘する」ために使います。

### ステップ 1: 打ち合わせ前 — 質問リスト案を作らせる

打ち合わせ前に、Claude にメモを渡して **顧客に聞くべき項目を AskUserQuestion で詰めさせる** のが効きます。

```text
業務委託で「サロン予約システムの管理画面リニューアル」の打ち合わせがあります。
既存仕様は @docs/current-spec.md、顧客のヒアリング依頼書は @docs/rfp.md です。

私がまだ顧客に聞けていない論点を、AskUserQuestion で順番に確認してください。
私が答えに詰まったら、ヒアリングシートに「顧客に聞く」と書いてください。
最後にヒアリングシート interview-sheet.md を出力してください。
```

ここで Claude が出してくる質問は、自分が普段見落としがちな論点（権限設計、論理削除 vs 物理削除、画面遷移時のローディング閾値、など）が混じってきます。

業務委託の場合、自分の脳内にしかない常識（「この顧客は本番環境に Basic 認証をかけるのが好き」など）を Claude は知らないため、**自分で答えられる質問は即答し、答えられないものを顧客に聞きに行く**という分業ができます。

### ステップ 2: 打ち合わせ後 — メモから SPEC.md を作る

打ち合わせのメモ（録音文字起こしでも可）を渡し、Claude に AskUserQuestion で抜けを詰めさせます。

```text
@docs/meeting-2026-05-08.md は今日の打ち合わせメモです。
このメモから要件を SPEC.md に起こしたいので、AskUserQuestion で
私に追加質問してください。

- 分かりきった質問はしない
- 顧客にしか答えられない質問は「顧客確認」とラベルを付ける
- 全部詰まったら SPEC.md を書き出す
```

ここでも 1 回の AskUserQuestion で投げられる質問は最大 4 問なので、Claude は自然に「重要なものから順に」聞いてきます。慣れてくると、4 択の中に「顧客確認が必要」を毎回混ぜる癖を付けると、後で顧客に投げる確認事項リストがそのまま出来上がります。

#### サンプル: 入力するMTGメモ

打ち合わせ直後の生メモはこのくらい雑然としているのが普通です。**整え過ぎると Claude が補足質問する余地が無くなって AskUserQuestion の効果が弱まる**ので、自分用の略記が混じったまま渡すのがコツです。

:::details meeting-2026-05-08.md（生メモのサンプル）

````markdown
# 2026-05-08 ○○サロン MTG メモ

## 出席者
- 顧客: 田中（社長）、佐藤（店舗マネージャ）
- 自分

## 現状の困りごと
- 既存の管理画面が遅い、特に予約一覧の月次表示
- スタッフの権限管理がない（全員フル権限）→ 退職スタッフが触れる
- 予約のキャンセル対応が手動で電話、ログも残らない

## やりたいこと（顧客発言ベース）
- 「予約一覧をもっと見やすく」← どう見やすく？
- 「権限を分けたい」← 何種類？店長/スタッフ/受付？
- キャンセルは画面から → メール自動送信したい
- 売上集計は今と同じでOK
- スマホでも見たい（社長が出先で確認したい）

## その場で確認できたこと
- リリース希望: 7月末（夏の繁忙期前）
- 既存DB（PostgreSQL）はそのまま使う
- 認証は今と同じBasic認証で良い ← 田中社長が強くこだわる
- デザインは「今より綺麗なら任せる」

## 自分が聞き忘れた / 持ち帰り
- 権限の具体的な区分
- スマホは PWA でいいのか専用アプリが必要か
- キャンセルメールの文面は誰が書く
- 既存予約データの移行は必要か（or 切替日以降のみ）
- 退職スタッフのアカウント削除フローは現状どうしてる
- 月次レポートの形式 (PDF出力欲しい？)
- ログイン後の TOP 画面に何を出すか

## 雑談で出たキーワード
- 「他店舗展開も視野に入れたい」← 今回のスコープではない、と確認
- 「インスタ連携できると嬉しい」← 優先度低
````

:::

#### サンプル: 出力される SPEC.md

`AskUserQuestion` で順番に質問が来て、自分が答えられるものは即答、答えられないものは「顧客確認」ラベルで残させた結果がこれです。

:::details SPEC.md（成果物のサンプル）

````markdown
# サロン予約システム管理画面リニューアル SPEC

## 1. 目的
既存管理画面の動作改善・権限分離・キャンセル対応のシステム化を行い、
店舗マネージャの運用負荷を下げる。

## 2. スコープ
### 含む
- 予約一覧画面のリニューアル（パフォーマンス改善 + UI 改善）
- スタッフ権限管理機能の新規追加
- キャンセル機能のシステム化（画面操作 + メール自動送信）
- スマホ対応（PWA）

### 含まない（明示的に除外）
- 他店舗展開機能（将来検討）
- Instagram 連携
- 売上集計機能の改修（現行流用）

## 3. 機能要件

### 3.1 予約一覧
- 月次表示で 2 秒以内に描画（受け入れ基準）
- フィルタ: 日付範囲・スタッフ・ステータス
- ✅ 決定: 仮想スクロールで実装
- ⚠️ 顧客確認: 1 画面に表示する初期件数（50/100/全件）

### 3.2 権限管理
- ロール: 管理者 / 店長 / スタッフ / 受付
- ✅ 決定: 4 ロールで進める
- ⚠️ 顧客確認: 各ロールが触れる機能の境界
  （特に「予約のキャンセルは誰までできるか」）
- ⚠️ 顧客確認: 退職スタッフの扱い
  （無効化のみ / 完全削除 / 一定期間後に自動削除）

### 3.3 キャンセル機能
- 管理画面からキャンセル操作 → 顧客にメール自動送信
- ログを 1 年間保持
- ⚠️ 顧客確認: メール文面のドラフトは誰が用意するか
- ⚠️ 顧客確認: キャンセル理由の必須/任意

### 3.4 スマホ対応
- ✅ 決定: PWA で実装（専用アプリは作らない）
- 主要動線: 予約確認・キャンセルのみ。設定系は PC 想定

## 4. 非機能要件
- 認証: 既存の Basic 認証を踏襲（田中社長の強い希望）
- DB: 既存 PostgreSQL を流用、新規テーブル追加可
- リリース希望: 2026-07-31

## 5. データ移行
- ⚠️ 顧客確認: 既存予約データの取り扱い
  （全件移行 / 切替日以降のみ / 過去 N ヶ月分のみ）

## 6. 顧客確認事項一覧（次回 MTG で詰める）
- [ ] 予約一覧の初期表示件数
- [ ] 各ロールが触れる機能の境界（特にキャンセル権限）
- [ ] 退職スタッフアカウントの扱い
- [ ] キャンセルメール文面のドラフト責任者
- [ ] キャンセル理由フィールドの必須/任意
- [ ] 既存データの移行範囲
- [ ] ログイン後 TOP 画面に表示する内容
- [ ] 月次レポートの形式（PDF 出力の要否）

## 7. 未確定の論点（自分の判断で進める）
- UI ライブラリは既存に合わせて Tailwind CSS で統一
- 仮想スクロールは TanStack Virtual を採用予定
````

:::

サンプルから読み取れる勘所が 3 つあります。

- **`✅ 決定` / `⚠️ 顧客確認` のラベルを Claude に入れさせる** — プロンプトに明示しておくと、最終セクション「顧客確認事項一覧」が自動で集約される
- **「自分の判断で進める」セクションを設ける** — 業務委託は決裁を待つと止まるので、判断したものは判断したと書いておくと顧客レビュー時の議論ポイントが明確になる
- **顧客に見せられる粒度で書かせる** — 自分の備忘録としてではなく、そのまま顧客レビュー資料として使える文体・構造にしておくと往復が減る

### ステップ 3: 別セッションで実装

SPEC.md と Plan Mode の組み合わせは、本リポジトリの別記事 [Plan Mode 中心の Claude Code 開発手法](2026-05-01-claude-code-plan-mode-workflow) で詳しく扱っています。要点だけ繰り返すと：

```bash
# ヒアリングセッションは閉じる
# 新セッションで実装に入る
claude --permission-mode plan
```

```text
@SPEC.md を読んで、実装計画を作ってください。
ファイルは編集せず、計画のみ提示してください。
```

ここで `AskUserQuestion` が再び呼ばれることがありますが、SPEC.md がしっかりしていれば「実装方針の選択（DB マイグレーションを破壊的にやるか段階的にやるか）」など、要件ではなく実装判断の確認に絞られます。

## SDD 系プラグインとの位置関係

`AskUserQuestion` を使ったインタビューは「素のままの Claude Code でできること」です。一方で同じ思想を**プラグイン化して定型化**した OSS が複数あります。簡単な比較：

| ツール | 立ち位置 | 業務委託で向くケース |
|---|---|---|
| 素の `AskUserQuestion` | 公式ネイティブ。自由度高い | 案件ごとに違うフォーマットが必要なとき |
| [classmethod/tsumiki](https://github.com/classmethod/tsumiki) | EARS 記法・信号機で曖昧さ可視化 | 顧客に「ここが赤なので決めてください」と説明したいとき |
| [gotalab/cc-sdd](https://github.com/gotalab/cc-sdd) | discovery → spec → design → tasks → impl の固いハーネス | 複数機能を並行で進める中規模案件 |
| [rizethereum/claude-code-requirements-builder](https://github.com/rizethereum/claude-code-requirements-builder) | 5+5 の Yes/No で進む | 非エンジニア顧客に伴走してもらうとき |

業務委託の最初の数案件では、まず素の `AskUserQuestion` でフローを体に入れる → 案件特性が見えたら SDD 系プラグインに乗せ替える、という順が無理がないと感じています。プラグインは強力ですが、最初から乗ると「何が暗黙のルールで何が AI の判断か」の境界が曖昧になりがちです。

## ハマりどころ

### サブエージェントに任せられない

公式が明記しているとおり、`AskUserQuestion` は **Agent ツール経由のサブエージェントでは使えません**。「ヒアリング担当のサブエージェント」を作って親に結果を返す設計はできないので、必要なら親セッションで直接動かしてください。

### 「分かりきった質問しない」を入れないと退屈

入れない場合、Claude は丁寧すぎて「ターゲットユーザーは誰ですか？」「主要機能は何ですか？」から始めます。これは初対面の顧客には有用ですが、メモを既に渡している場合は時間の無駄です。プロンプトに `Don't ask obvious questions` を必ず入れるのが効きます。

### コンテキストを汚さないためにセッションを分ける

業務委託で複数案件を並行している場合、ヒアリング中に他案件の話を混ぜたくなりますが、コンテキスト共有はノイズの温床になります。`/clear` でリセットするか、案件ごとに `claude --resume <session>` で名前付きセッションに分けるほうが結果的に速いです。

## まとめ

- `AskUserQuestion` は Claude Code のネイティブツールで、構造化された選択式の質問を Claude 側から投げてもらうためのもの
- 業務委託のヒアリングを置き換えるのではなく、**自分が聞き漏らした論点を発掘する**ために使うと効く
- ヒアリングセッションと実装セッションは分ける（公式推奨）
- サブエージェントでは使えない・1 回 4 問まで、という制約は知っておく
- 案件特性が見えてきたら tsumiki / cc-sdd / requirements-builder へ乗せ替える順番が安全

「顧客に聞き忘れて納品後に揉める」という業務委託あるあるは、自分の準備不足が原因のことが多いです。`AskUserQuestion` は、その準備のところに AI を 1 人挟むだけで、聞くべきだったことが浮かび上がってくる地味だが効く道具です。

## 参考リンク

- [Best practices for Claude Code (Anthropic)](https://code.claude.com/docs/en/best-practices)
- [Handle approvals and user input (Anthropic)](https://code.claude.com/docs/en/agent-sdk/user-input)
- [classmethod/tsumiki](https://github.com/classmethod/tsumiki)
- [gotalab/cc-sdd](https://github.com/gotalab/cc-sdd)
- [rizethereum/claude-code-requirements-builder](https://github.com/rizethereum/claude-code-requirements-builder)
- [Plan Mode 中心の Claude Code 開発手法（本リポジトリ別記事）](https://zenn.dev/inoh/articles/2026-05-01-claude-code-plan-mode-workflow)
