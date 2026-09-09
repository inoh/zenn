---
title: "Claude Fable 5と5.1の違いは、破壊的変更3件とキャッシュ読み1/4に集約される"
emoji: "🔗"
type: "tech"
topics: ["claude", "anthropic", "claudecode", "llm", "ai"]
published: true
---

## はじめに

2026年9月1日、AnthropicがClaude Fable 5.1とClaude Mythos 5.1を発表しました。Fable 5が2026年6月9日でしたから、約3か月でのマイナーバージョンアップです。

「5 → 5.1」という刻み方から想像されるのは、ベンチマークが数ポイント伸びた程度の穏当な更新です。実際、コンテキストウィンドウも最大出力もトークナイザも料金の単価も、Fable 5とまったく同じです。モデルIDを `claude-fable-5` から `claude-fable-5-1` に書き換えるだけで動きます。

ところが公式ドキュメントを読むと、そのモデルIDの書き換えの後ろに**3つの破壊的変更**が並んでいます。そのうち2つは、自分で `messages` 配列を組み立てているコードの設計前提を壊します。しかも1つは、**2026年8月31日以降に作成されたアカウントでは既定で強制**されます。

この記事では、Fable 5と5.1の差分を「ベンチマークの数字」ではなく「エージェントハーネスの設計にとって何が変わったか」という観点で整理します。あわせて、単価据え置きのなかで唯一動いた価格——キャッシュ読み取りの1/4への値下げ——が持つ非対称性も見ていきます。

:::message
この記事のAPI挙動に関する記述は、公式ドキュメントの記載を根拠にしています。手元の環境にAnthropic APIの認証情報がなかったため、400エラーの発生などをAPI呼び出しで独自に再現したわけではありません。一方、Claude Codeの挙動については `gh` CLIでCHANGELOGを実取得して確認しています（コマンドは後述します）。
:::

## まずスペックを並べる——ほとんど同じ

公式のモデル比較表とpricingページ、および移行ガイドから拾うと、両者のスペックはこうなります。

| 項目 | Claude Fable 5 | Claude Fable 5.1 |
|---|---|---|
| モデルID | `claude-fable-5` | `claude-fable-5-1` |
| 発表日 | 2026-06-09 | 2026-09-01 |
| コンテキストウィンドウ | 1M（既定=最大） | 1M（既定=最大） |
| 最大出力 | 128K | 128K |
| トークナイザ | Opus 4.7世代 | 同一（トークン数は変わらない） |
| thinking | 常時ON（adaptiveのみ） | 常時ON（adaptiveのみ） |
| effort | low / medium / high / xhigh / max | 同じ（API既定は `high`） |
| 入力 / 出力単価 | $10 / $50 per MTok | $10 / $50 per MTok |
| データ保持 | Covered Model（30日保持が必須） | 同じ |
| Priority Tier | 対応 | **非対応** |

トークナイザが同じというのは移行にとって地味に重要です。Opus 4.6以前から上がってくる場合は同じ文章でおよそ30%多いトークンになりますが、Fable 5からの移行ならトークン数の再計測は不要です。

逆に、表のなかで唯一はっきり失うものがPriority Tierです。Fable 5でPriority Tierを使っていた場合、5.1に移ると使えなくなります。

## ベンチマーク：伸びているのは「賢さ」より「持久力」

発表ページに載っている比較表から、Fable 5.1 / Fable 5 / Opus 5 の3列を抜き出します。

| ベンチマーク | Fable 5.1 | Fable 5 | Opus 5 |
|---|---|---|---|
| Terminal-Bench-Science 0.1 | 52.6% | 24.7% | 29.0% |
| Terminal-Bench 4.0 | 55.8% | 42.0% | 52.3% |
| AutomationBench | 31.4% | 17.1% | 26.9% |
| GDPval-AA v2 | 1853 | 1723 | 1824 |
| OSWorld 2.0 (partial) | 77.9% | 72.9% | 75.4% |
| OSWorld 2.0 (strict) | 41.7% | 36.1% | 39.6% |
| Humanity's Last Exam (ツールなし) | 60.9% | 57.8% | 56.6% |
| Humanity's Last Exam (ツールあり) | 65.0% | 63.8% | 63.6% |
| CursorBench 3.2.0 | 73.4% | 70.5% | 70.0% |

この表の読みどころは2つあります。

ひとつめは、**伸び幅がタスクの長さと相関している**ことです。Terminal-Bench-Scienceは24.7% → 52.6%で2倍以上、AutomationBenchは17.1% → 31.4%で1.8倍近い。どちらも複数ステップを跨いで自律的に走るタイプの評価です。いっぽう単発の推論力を測るHumanity's Last Exam（ツールなし）は57.8% → 60.9%で、伸びは3ポイント程度にとどまります。「賢くなった」というより「長く走り続けられるようになった」という更新です。

ふたつめは、**Opus 5の列**です。Terminal-Bench 4.0、GDPval-AA v2、AutomationBench、OSWorldのいずれでも、Opus 5がFable 5を上回っています。Opus 5の単価は $5 / $25 で、Fable 5のちょうど半分です。つまり2026年6月から9月までの間に、「Fableのほうが上位クラス」という関係は少なくともこれらの評価軸では成立しなくなっていました。5.1はその状況を巻き返した更新でもあります。

このあたりの位置づけは公式ドキュメントのモデル比較ページにも明記されています。

> If you're unsure which model to use, start with Claude Opus 5 for most workloads. Use Claude Fable 5.1 for demanding reasoning and long-horizon agentic work, or when your evals on Claude Opus 5 at higher effort still fall short.

「まずOpus 5から始めよ。Opus 5をhigh以上のeffortで回してもなお評価が足りないときにFable 5.1を使え」という順序です。Fable 5.1は「常に上位のモデル」ではなく、**Opus 5でeffortを上げても届かなかったときの選択肢**として置かれています。

なお、既定のeffortはプロダクトによって違います。発表ページには次のようにあります。

> Fable 5.1 defaults to High effort in Claude Code, and to Medium in Claude Cowork and on Claude.ai.

APIの既定も `high` です。

## 本題：破壊的変更3件

ここからが本題です。公式の「What's new in Claude Fable 5.1」ページは、冒頭で次のように宣言しています。

> If you already call Claude Fable 5, three changes are breaking

3件を順に見ていきます。

### 1. forced tool use が400になる

`tool_choice` に `{"type": "any"}` または `{"type": "tool", "name": "..."}` を指定すると、`400 invalid_request_error` が返ります。エラーメッセージは公式ドキュメントに次のように記載されています。

> ```
> tool_choice: type "tool" and "any" are not supported for this model.
> ```

`{"type": "auto"}`（既定）と `{"type": "none"}` は変わりません。この制限はMessages APIだけでなく、Message Batches APIとトークンカウントのエンドポイントにも同じように適用されます。つまり「本番に出す前にcount_tokensで見積もる」という手順を踏んでいても、そこで先に落ちます。

理由も公式が説明しています。

> Thinking is always on for these models, and a forced tool call would skip it. The model would write its working-out into the tool arguments instead, which lowers argument quality.

思考が常時ONのモデルに対してツール呼び出しを強制すると、思考のプロセスがツール引数のなかに書き込まれてしまい、引数の品質が落ちる、という説明です。

ここで注意したいのは、**これが「常時ON思考の必然的な帰結」ではない**点です。Fable 5もOpus 5も同じく思考は常時ONですが、forced tool choiceは受理されます。5.1で新たに入ったモデル固有の制限です。

移行は「なぜ強制していたのか」で分岐します。

```python
# Before —— Fable 5.1では400
response = client.messages.create(
    model="claude-fable-5",
    max_tokens=4096,
    tools=[get_weather_tool],
    tool_choice={"type": "tool", "name": "get_weather"},
    messages=[{"role": "user", "content": "東京の天気を確認して要約してください。"}],
)

# After —— autoに戻し、プロンプトでツール名を明示、
#          引数のスキーマ保証は strict tool use で担保する
get_weather_tool["strict"] = True  # スキーマ側に additionalProperties: false が必要
response = client.messages.create(
    model="claude-fable-5-1",
    max_tokens=4096,
    tools=[get_weather_tool],
    tool_choice={"type": "auto"},
    messages=[{
        "role": "user",
        "content": "get_weather ツールを使って東京の天気を確認し、要約してください。",
    }],
)
```

- **ツールを確実に呼ばせたかった**なら、`auto` のままプロンプトで「このツールを使え」と書きます。公式は「Claude Fable 5.1 follows explicit tool instructions reliably」としています
- **引数がスキーマに沿うことを保証したかった**なら、`strict: true`（strict tool use）に移します。`any` が与えていた「引数が必ずスキーマに合致する」という保証は、こちらで取り戻せます
- **JSONを取り出したかっただけ**なら、structured outputs（`output_config.format`）に移すのが素直です

そして地味に効くのが、**「ツールが呼ばれなかったらリトライする」ループの削除**です。`any` を前提に書かれたそういうループは、`auto` では意味が変わります。

### 2. thinkingブロックが、それを生成したモデルに束縛される

公式の表現はこうです。

> Every thinking block records which model produced it, and it's preserved in one direction only: Claude Fable 5.1 reads earlier models' thinking blocks, and no earlier model reads Claude Fable 5.1's.

thinkingブロックには「どのモデルが生成したか」が記録され、束縛は**一方向**です。整理するとこうなります。

- Opus 5 / Fable 5 / それ以前 → **Fable 5.1へは持ち込める**。会話の途中でFable 5.1に切り替えても、それまでの推論は引き継がれます
- Fable 5.1 → **他のどのモデルも読めない**。Fable 5.1で走った会話を他モデルに引き継ぐと、そのターンぶんの推論は失われます

読めないブロックを含むリクエストが来た場合、APIはモデルに渡す前にそれを落とします。リクエスト自体は成功し、落ちたブロックは `input_tokens` にも計上されず課金もされません。

これが効いてくるのは**モデルを跨ぐ経路**です。ルーターによる切り替え、クライアント側のリトライ、そしてrefusal時のフォールバックです。Fable 5.1のフォールバック先はOpus 4.8とOpus 5ですが、どちらもFable 5.1のthinkingブロックを読めません。したがってフォールバック後の1ターン目は、それまでの推論なしで組み立て直しになります。レイテンシもコストも上がると見込んでおくのが安全です。

ここで**やってはいけないのが、自分でブロックを剥がすこと**です。読めないブロックはAPIが無課金で落としてくれるので、入力トークンの節約にはなりません。手で消すと順序やシグネチャの検証で400を踏む可能性が出てきます。素直にそのまま渡すのが正解です。

落ちたことを検知したい場合は、`thinking-binding-controls-2026-08-01` betaヘッダを付けます。レスポンスのトップレベルに `input_transformations` 配列が返り、どのブロックがなぜ落ちたかがわかります。ヘッダなしだと**サイレントに落ちます**。

### 3. 過去のターンを編集すると、それ以降のthinkingが無効になる

3つめがいちばん広範囲に影響します。公式の記述です。

> Modifying anything before a Claude Fable 5.1 thinking block (the `system` prompt, the `tools`, or an earlier message) results in an error on the next request, or in the block being dropped if you opt into that.

thinkingブロックの `signature` には、そのブロックを生成した会話のprefix——トップレベルの `system`、`tools` の集合、そのブロックより前のすべてのメッセージ——が記録されています。次のリクエストで会話が戻ってきたとき、APIはこのprefixが変わっていないかを検証します。

**以降のthinkingブロックを全部無効化する操作**として、公式は次を挙げています。

- 過去のターンを編集・並べ替え・削除しながら、それ以降のターンを残すこと
- リクエストごとに過去ターンへテキストを注入し、次のリクエストで消すこと（リマインダやステータス行）
- 同じ会話のなかでトップレベルの `system` や `tools` 配列を組み直すこと
- 後のリクエストで異なるバイト列を返す画像・ドキュメントのURL（検証対象はURL文字列ではなくバイト列なので、同じファイルを指す署名付きURLのローテーションは問題ありません）

逆に、**以降のブロックを無効化しない操作**も明示されています。先頭から古い順にthinkingブロックを取り除くこと、サーバサイドのcontext editingやcompactionで履歴を刈ること、`cache_control` マーカーを動かすこと、リクエスト間で `effort` を変えること。つまり**先頭からは削れるが、途中からは削れない**という設計です。

検証に引っかかった場合のエラーメッセージは `The block is bound to a different conversation` です。エラーにせず落として続行したい場合は、beta ヘッダ `thinking-binding-controls-2026-08-01` とあわせて `thinking.block_binding.prefix_mismatch_behavior: "drop_block"` を指定します。

そして、この記事でいちばん見落とされやすいと思っている一文がこれです。

> The check is enforced for new accounts created on or after August 31, 2026.

**2026年8月31日以降に作成されたアカウントでは、既定で強制されます**。それ以前に作られたアカウントでは、APIは不一致を記録するものの、リクエストが `thinking.block_binding.prefix_mismatch_behavior` を明示的にセットしたときにだけ作動します。

ここに罠があります。自分の組織が古ければ手元では何も起きませんが、**そのコードを他人が自分のAPIキーで動かすツールとして配布している場合、新しい組織のユーザーは自分より先に強制されます**。ライブラリやCLIを配っているなら、`prefix_mismatch_behavior` を明示的にセットした状態でテストしておく必要があります。

なお、Claude Code、claude.ai、Claude Managed Agents、Claude Agent SDKは、このprefixをフレームワーク側で保ってくれます。問題になるのは**`messages` 配列を自分で組み立てているコード**です。

## 追加機能5件は、破壊的変更の受け皿として設計されている

公式は破壊的変更3件に続けて、追加機能を5件挙げています。並べてみると、**追加機能が破壊的変更の回避策として対応している**ことがわかります。

| 追加機能 | 何のためにあるか |
|---|---|
| turn-scoped system message（beta） | 破壊的変更3の回避策そのもの |
| per-message effort（beta） | effort変更でキャッシュを壊さない |
| `thinking.display: "updates"`（beta） | 長時間ツール実行中の「沈黙」対策 |
| キャッシュ読み取りの値下げ | 後述 |
| content provenance | 生成テキストへの統計的透かし |

### turn-scoped system message

「このターンだけ有効な指示」をハーネスがモデルに伝えたい場面は珍しくありません。「コードを走らせる前に受信箱を確認して」「そのツール出力はユーザーには見えていない」といった類です。

従来のやり方は、リマインダを注入して次のリクエストで消すことでした。しかしこれは破壊的変更3でいうところの履歴編集そのもので、プロンプトキャッシュをリセットし、以降のthinkingブロックを無効化します。

そこで `role: "system"` メッセージに `clear_at: "next_user_message"` を付けます。

```json
{
  "role": "system",
  "clear_at": "next_user_message",
  "content": "この結果は受信箱に届いています。次のコード実行の前に確認してください。"
}
```

このメッセージはそのターンではシステムプロンプト相当の権威を持ち、後続の `user` メッセージが現れた時点でレンダリングされなくなります。ポイントは、**`messages` からは消さない**ことです。毎回そのまま送り返します。履歴は変わらないのでキャッシュも一致し続け、以降のthinkingブロックも有効なままで、しかもクリア済みのメッセージは入力トークンを消費しません。

betaヘッダは `mid-conversation-system-clear-at-2026-08-21` です。

### per-message effort

空の `content` を持つ `role: "system"` メッセージに `output_config` を載せることで、会話の途中でeffortを変えられます。

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: mid-conversation-output-config-2026-07-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-fable-5-1",
    "max_tokens": 4096,
    "output_config": {"effort": "high"},
    "messages": [
      {"role": "user", "content": "SQLiteからPostgreSQLへの移行手順を3ステップで。"},
      {"role": "assistant", "content": "1. SQLiteのデータをエクスポート。2. PostgreSQL側にスキーマを作成。3. インポートして行数を検証。"},
      {"role": "system", "content": [], "output_config": {"effort": "low"}},
      {"role": "user", "content": "いまの手順を1文にまとめてください。"}
    ]
  }'
```

新しいレベルは次の `user` ターンから効き、さらに後ろの `role: "system"` メッセージが変えるまで持続します。**この形式ならプロンプトキャッシュが壊れません**。effort だけを載せたメッセージはテキストを持たないため、通常のmid-conversation system messageの配置ルール（`user` の後ろに置く等）の対象外で、`messages` のどこにでも置けます。

対応モデルはFable 5.1、Mythos 5.1、Opus 5で、betaヘッダは `mid-conversation-output-config-2026-07-01` です。Fable 5を含む非対応モデルでは400が返ります。

### `thinking.display: "updates"`

Fable 5.1はツール呼び出しの合間に「いま何がわかったか、次に何をするか」という短い進捗メモを書きます。これは `text` ブロックではなく、**それぞれ独立した `thinking` ブロック**として、対応するツール呼び出しの直前に返されます。

`thinking.display` の既定値は `"omitted"` なので、これらのブロックは推論と同じく**空で返ってきます**。結果として、長いエージェントターンはユーザーから見ると数分間なにも喋らないように見えます。

`display: "updates"` を指定すると、推論は隠したまま進捗メモだけがテキストで返ります。`"updates"` のもとでは、**テキストが空でない `thinking` ブロックはすべて進捗メモ**なので、そのままステータス行として表示できます。betaヘッダは `thinking-display-updates-2026-08-18` です。

## キャッシュ読み取り1/4がもたらす非対称性

単価が据え置きのなか、唯一動いた価格がキャッシュ読み取りです。

| | 入力 | 5分キャッシュ書き | 1時間キャッシュ書き | キャッシュ読み | 出力 |
|---|---|---|---|---|---|
| Claude Fable 5 | $10 | $12.50 | $20 | **$1** | $50 |
| Claude Fable 5.1 | $10 | $12.50 | $20 | **$0.25** | $50 |
| （参考）Claude Opus 5 | $5 | $6.25 | $10 | $0.50 | $25 |

公式pricingページの脚注はこうです。

> Cache hits and refreshes on Claude Fable 5.1 and Claude Mythos 5.1 are priced at 0.025x the base input price. All other models use the standard 0.1x multiplier.

他の全モデルが基本入力価格の0.1倍なのに対し、Fable 5.1とMythos 5.1だけが0.025倍です。5分・1時間のキャッシュ書き込み価格も、キャッシュ可能な最小プロンプト長（512トークン）も変わっていません。読み取りだけが1/4になりました。

Anthropicは「典型的なワークロードで約25%安くなる」と説明し、エージェント的な用途では「up to approximately 45%」としています。

### 誰の財布に効くのか

ここから2つの帰結が出ます。

**ひとつめ。恩恵は長いエージェントセッションに集中します。** 単発のリクエストは入力も出力も定価のままなので、1円も安くなりません。安くなるのは「同じprefixを何度も読み直す」形をしたワークロードだけです。

たとえば200Kトークンのprefixを50ターン読み直すセッションを考えます。

- Fable 5: 50 × 0.2 MTok × $1 = **$10**
- Fable 5.1: 50 × 0.2 MTok × $0.25 = **$2.50**
- Opus 5: 50 × 0.2 MTok × $0.50 = **$5**

基本単価はOpus 5の2倍なのに、**キャッシュ読み取りの部分だけを見るとFable 5.1のほうがOpus 5より安い**という逆転が起きます。

**ふたつめ。キャッシュミスの相対コストが跳ね上がります。** Fable 5ではミス（$10）とヒット（$1）の差は10倍でした。5.1では$10対$0.25で40倍です。つまり**キャッシュを温かく保つことの価値が4倍になった**ということです。

追加機能のうち2つが、まさにこの点に効いていることに注目してください。per-message effortは「effortを変えたいがキャッシュは壊したくない」ための機能であり、turn-scoped system messageは「毎ターン指示を出したいがキャッシュは壊したくない」ための機能です。破壊的変更3の回避策であると同時に、キャッシュ設計の一部でもあります。

## Claude CodeのCHANGELOGが記録している追随過程

「キャッシュを温かく保つことの価値が上がった」という話が抽象論でないことは、Anthropic自身のハーネスであるClaude Codeの変更履歴を見るとわかります。実際に取得してみます。

```bash
gh api repos/anthropics/claude-code/contents/CHANGELOG.md --jq '.content' | base64 -d | grep -n -i 'fable'
```

Fable 5.1に関係する行を、バージョンと日付（`feed.xml` の `updated` より）に紐付けるとこうなります。

**v2.1.257（2026-09-01）** ——モデル追加と同日です。

> Added Claude Fable 5.1 (`claude-fable-5-1`), now the default Fable model — 1M context, $10/$50 per Mtok with $0.25/Mtok cache reads

同じバージョンには、こういう行もあります。

> Changed `fable` and `best` in Claude apps gateway sessions to keep resolving to Fable 5 for now, since gateways not yet configured for Fable 5.1 reject it; pick Fable 5.1 in `/model` to use it

gateway経由のセッションでは、エイリアス `fable` / `best` は当面Fable 5に解決され続けます。5.1を使うには `/model` で明示的に選ぶ必要があった、ということです。

そして**v2.1.260（2026-09-03）**、リリースから2日後です。

> Fixed prompt caching on Claude Fable 5.1 not covering the context attached after tool results, so it was re-sent as uncached input on every tool-call turn

> Improved `/effort` on Claude Fable 5.1 so changing effort mid-session no longer invalidates the prompt cache

1行目は、ツール結果の後ろに付く文脈がキャッシュ範囲に入っておらず、**ツール呼び出しのターンごとに未キャッシュ入力として再送されていた**という不具合の修正です。キャッシュミスがヒットの40倍になったモデルで、毎ツールターンにミスが発生していたわけです。

2行目は、セッション中のeffort変更がプロンプトキャッシュを無効化していた問題の改善で、これはまさに前述のper-message effortが解決する課題そのものです。

つまり**公式ハーネスですら、5.1のキャッシュ設計に追いつくのに数日かかっています**。自作のエージェントループを5.1に載せ替えるなら、`usage.cache_read_input_tokens` を実際に見て、想定どおりキャッシュに乗っているか確認する価値があります。

## コード変更なしに現れる振る舞いの差

公式は「コードを一切変えなくても現れる差」も列挙しています。これも移行時に踏みやすい落とし穴です。

- **並列ツール呼び出しが不安定になる**。Fable 5がまとめて投げていた場面で、1ターン1呼び出しになることがあります。次に読むべき独立したファイルが「明示されておらず暗黙的」な長いエージェントループ——自作のコーディングエージェント、bashとエディタだけのハーネス、computer use——で顕在化します。答えの品質は落ちませんが、ラウンドトリップとトークンと実時間が増えます。「複数のものを取ってこい」と明示したリクエストは従来どおり並列に走ります
- **長時間実行中の進捗表明が減る**。特にeffortが高いときに顕著です。前述の `display: "updates"` で拾えます。あわせて、旧モデル向けに書いた「findingsは最終応答までまとめて保持せよ」のような指示は削除すべきです
- **low effortで検索を撃たなくなる**。記憶から答える傾向が強まります。特に「名前は知っているが情報が古い」固有名詞——AIモデル名や開発ツール名——で目立ちます
- **散文が密になる**。一文が長く、段落の区切りが減ります
- **チャットでの装飾が減る**。太字・見出し・箇条書きの使用が旧モデルより減るため、旧モデル向けに書いた「箇条書きを使うな」系の指示が過剰に効いて、必要な構造まで潰れます
- **要約時に引用を引用として示さないことがある**。原文をそのまま再現しつつ引用符を付けない、という挙動です
- **小さな変更でもファイル全体を書き直す**傾向があります。結果は同じですが、出力トークンと時間を余分に使います

最後の3つは、いずれも「モデルを上げたのに遅くなった／出力が増えた」という体験として現れます。原因が能力ではなく振る舞いにあるので、プロンプト側で対処する類のものです。

なお多言語性能については、公式は「Multilingual performance is on par with Claude Fable 5.」としています。日本語での使用に関して、5.1で特別に改善したという主張はありません。

## 移行時に確認すること

Fable 5からの移行で確認すべき点を、優先度順に整理します。

1. **モデルIDを `claude-fable-5-1` に変更する**
2. **`tool_choice` の `any` / `tool` をすべて削除する**。スキーマ保証は `strict: true` へ、JSON抽出はstructured outputsへ移す。「ツールが呼ばれなかったらリトライ」ループも削除する
3. **thinkingブロックはそのまま返し続ける**。空のものも `redacted_thinking` も含めて、手で剥がさない
4. **履歴をappend-onlyにする**。毎ターンのリマインダはturn-scoped system messageへ、`system` / `tools` の変更はmid-conversation system messageとtool changeへ、履歴の刈り取りはサーバサイドのcontext editing / compactionへ。`prefix_mismatch_behavior: "drop_block"` を指定して `input_transformations` をログに出し、どこで履歴を編集しているか洗い出す
5. **effortを再チューニングする**。レベル名が示す思考量はモデルごとに違うため、Fable 5で行ったスイープはそのまま使えません
6. **エージェントループの並列度を計測する**。1ターンあたりのツール呼び出し数が1に張り付いていないか確認する
7. **キャッシュヒット率を確認する**。`usage.cache_read_input_tokens` が想定どおり出ているか
8. **Priority Tierを使っていた場合は代替を検討する**。5.1では使えません

## まとめ

- Claude Fable 5.1は2026年9月1日発表。コンテキスト1M、最大出力128K、トークナイザ、入出力単価のいずれもFable 5と同一です
- ベンチマークの伸びは長時間・多段のエージェントタスクに集中しています。単発推論の伸びは限定的です。またFable 5は、いくつかの評価軸ではすでに半額のOpus 5に抜かれていました
- 破壊的変更は3件。forced tool useの400、thinkingブロックのモデル束縛、履歴編集によるthinking無効化です。後者2つは自分で `messages` を組むコードの前提を壊します
- 履歴編集チェックは**2026年8月31日以降に作成されたアカウントで既定で強制**されます。ツールを配布しているなら、自分の組織より先にユーザーが強制される点に注意が必要です
- 追加機能5件のうち2件（turn-scoped system message、per-message effort）は、破壊的変更の回避策であると同時にキャッシュ維持の道具です
- キャッシュ読み取りは $1 → $0.25。恩恵は長いエージェントセッションに集中し、代わりにキャッシュミスの相対コストが10倍から40倍に上がりました
- Claude Code自身、リリース2日後にキャッシュ範囲の不具合を修正しています。載せ替えたら実測で確認するのが安全です

「マイナーバージョンアップだからモデルIDを差し替えるだけ」で済むかどうかは、そのコードが履歴をどう扱っているかで決まります。Claude CodeやAgent SDKに乗っているなら差し替えるだけです。自分で `messages` を組んでいるなら、まず履歴編集の棚卸しから始めるのがよさそうです。

## 参考リンク

- [Introducing Claude Fable 5.1 and Claude Mythos 5.1（Anthropic）](https://www.anthropic.com/claude-fable-and-mythos-5-1)
- [What's new in Claude Fable 5.1（Claude Platform Docs）](https://platform.claude.com/docs/en/models/fable-5-1/whats-new-fable-5-1)
- [Migrating to Claude Fable 5.1 and Claude Mythos 5.1（Claude Platform Docs）](https://platform.claude.com/docs/en/models/fable-5-1/migration-guide)
- [Models overview（Claude Platform Docs）](https://platform.claude.com/docs/en/about-claude/models/overview)
- [Pricing（Claude Platform Docs）](https://platform.claude.com/docs/en/about-claude/pricing)
- [Claude Fable 5 and Claude Mythos 5（Anthropic）](https://www.anthropic.com/news/claude-fable-5-mythos-5)
- [Claude Fable 5.1 is now available on AWS](https://aws.amazon.com/about-aws/whats-new/2026/09/claude-fable-5-1-aws/)
- [anthropics/claude-code CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
