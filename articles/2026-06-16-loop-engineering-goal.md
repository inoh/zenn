---
title: "Loop Engineeringの組み方：Claude Code /goal で「自走するループ」を設計する"
emoji: "🔁"
type: "tech"
topics: ["claudecode", "ai", "llm", "agent", "loopengineering"]
published: true
---

## はじめに

2026年6月、AIコーディング界隈で「Loop Engineering（ループエンジニアリング）」という言葉が一気に広がりました。発端は、OpenClaw の作者として知られる Peter Steinberger 氏が6月7日に投稿した、たった2文のポストです。

> You shouldn't be prompting coding agents anymore. You should be designing loops that prompt your agents.

（もうコーディングエージェントにプロンプトを書くのはやめましょう。エージェントにプロンプトを書く「ループ」を設計すべきです）

翌日には Google の Addy Osmani 氏がこの概念を整理したブログ記事 [Loop Engineering](https://addyosmani.com/blog/loop-engineering/) を公開し、考え方が一気に体系化されました。さらに、Anthropic で Claude Code を率いる Boris Cherny 氏の次の発言が、この潮流を象徴するものとして繰り返し引用されています。

> I don't prompt Claude anymore. I have loops running that prompt Claude and figuring out what to do. My job is to write loops

（私はもう Claude にプロンプトを書きません。Claude にプロンプトを書き、何をすべきか判断するループを動かしています。私の仕事はループを書くことです）

この記事では、Loop Engineering とは何かという思想的な背景を押さえたうえで、**実際に「自走するループ」をどう組むのか**を、Claude Code の公式機能 `/goal` を題材にハンズオン形式で解説します。`/goal` の挙動は[公式ドキュメント](https://code.claude.com/docs/en/goal)で確認した内容に基づいています。

## Loop Engineering とは何か

Addy Osmani 氏のブログでは、Loop Engineering を次のように定義しています。

> Loop engineering is replacing yourself as the person who prompts the agent. You design the system that does it instead.

（ループエンジニアリングとは、エージェントにプロンプトを書く「あなた自身」を置き換えることです。代わりにそれを行うシステムを設計するのです）

これまでの「プロンプトエンジニアリング」は、人間が1ターンごとに指示を考え、結果を見て、また次の指示を打つ、という単発・人間駆動のスタイルでした。Loop Engineering はそこから一歩進んで、**プロンプトを生成し、実行し、結果を検証し、ゴールに達するまで繰り返すシステムそのものを設計する**という発想です。

この変化は、AIに任せるほど人間の仕事が減るのではなく、むしろ「設計」の比重が増すことを意味します。コードを書く仕事から、ループを書く仕事へのシフトです。

## ループの最小要件

複数の解説で共通して語られているのは、ループが成立するには次の2つが必須だという点です。

1. **トリガー（起動条件）** — 何がループを開始させるのか
2. **検証可能なゴール（終了状態）** — どうなったら完了とみなすのか

ポイントは、エージェントが**あなたの次のメッセージを待たない**ことです。ループは起動し、自分で作業を進め、ゴールに達したかをチェックし、達していなければまた回る——これを停止条件が満たされるまで自走します。

特に重要なのが「検証可能なゴール」です。「いい感じにして」のような曖昧なゴールでは、いつ止まればよいのか機械が判断できません。「全テストが通る」「ビルドが exit 0 になる」「キューが空になる」といった、**機械が真偽を判定できる終了状態**を設計することが、ループ設計の肝になります。

## ループを組む5つの構成要素

Addy Osmani 氏は、実際にループを組み上げるための構成要素を整理しています。本文で挙げられているのは次の5つ＋外部メモリです。

### 1. Automations（自動化）

スケジュール実行によって「発見と分類（トリアージ）」を自動で回します。たとえば、新しい Issue や問い合わせを定期的に拾い上げ、ラベル付けや優先度判定までを人手を介さず行わせる、といった使い方です。

### 2. Worktrees（作業ツリーの隔離）

複数のエージェントを並行して走らせると、同じファイルを同時に編集して衝突します。これを git の worktree で隔離し、エージェントごとに独立した作業領域を持たせます。並列度を上げたいときの基盤になります。

### 3. Skills（スキル）

プロジェクト固有の知識を `SKILL.md` 形式でコード化します。「このリポジトリではこう作業する」というルールを毎回プロンプトに書く代わりに、再利用可能なスキルとして外出しします。

### 4. Plugins / Connectors（連携）

MCP（Model Context Protocol）経由で GitHub や Slack などの既存ツールと接続します。ループが現実の情報源から入力を受け取り、現実の場所に成果を反映するための接続点です。

### 5. Sub-agents（サブエージェント）

**実装者と検証者を分離する**のが重要なポイントです。同じエージェントに「作業」と「その作業の合否判定」を兼ねさせると、自分に甘い採点になりがちです。役割を分けることで、検証の独立性を確保します。

### ＋ 外部メモリ（External Memory）

そして見落とされがちなのが外部メモリです。Osmani 氏は、エージェントは実行と実行のあいだでコンテキストを忘れるため、**ディスク上に状態を残すことが必須**だと指摘しています。具体的にはマークダウンファイルや Linear のボードなどに、進捗や決定事項を書き出しておきます。

## ハンズオン：Claude Code `/goal` で自走ループを組む

ここからは、上記の「検証可能なゴールまで自走する」ループを、Claude Code の `/goal` コマンドで実際に組んでみます。`/goal` はループを製品として実装した分かりやすい例です。

:::message
`/goal` は Claude Code v2.1.139 以降で利用できます。
:::

### `/goal` の基本

`/goal` は完了条件を1度だけ書くと、Claude がターンをまたいで自走し続ける仕組みです。公式ドキュメントには次のように書かれています。

> The `/goal` command sets a completion condition and Claude keeps working toward it without you prompting each step. After each turn, a small fast model checks whether the condition holds. If not, Claude starts another turn instead of returning control to you. The goal clears automatically once the condition is met.

ポイントを整理すると次のとおりです。

- 完了条件を1回設定するだけで、毎ターンごとに人間がプロンプトを打つ必要がなくなる
- **毎ターン後に、別の小型・高速モデル（既定は Haiku）が条件を満たしたかを判定する**
- 条件が満たされれば自動でゴールが解除され、通常のターンごとのモードに戻る

ここで効いているのが「作業するモデル」と「採点するモデル」の分離です。前述の構成要素で言う**実装者と検証者の分離**が、`/goal` では仕組みとして組み込まれています。

### ゴールを設定する

使い方はシンプルで、`/goal` の後に満たしたい条件を書くだけです。

```text
/goal all tests in test/auth pass and the lint step is clean
```

これは「`test/auth` の全テストが通り、lint がクリーンになるまで作業を続けて」という意味になります。ゴールを設定した瞬間に、その条件自体を指示として1ターン目が始まります。別途プロンプトを送る必要はありません。実行中は `◎ /goal active` というインジケータで、ゴールがどれくらい走っているかが表示されます。

### 評価器の「重要な制約」を理解する

ここが `/goal` を使ううえで最も重要な注意点です。公式ドキュメントは次のように説明しています。

> The evaluator judges your condition against what Claude has surfaced in the conversation. It doesn't run commands or read files independently, so write the condition as something Claude's own output can demonstrate.

つまり、**評価器（採点するモデル）はコマンドを実行したりファイルを独立して読んだりしません**。会話のなかに Claude が出力した内容だけを見て判定します。

したがって、条件は「Claude 自身の出力で証明できる形」で書く必要があります。たとえば「`test/auth` の全テストが通る」が機能するのは、Claude がテストを実行し、その結果がトランスクリプトに出力され、それを評価器が読めるからです。逆に、Claude が一度も実行・出力していないことは、評価器には判定できません。

### 良い条件の3要素

公式ドキュメントは、長いターンにわたって成立する条件には次の3つの要素があるとしています。

- **測定可能な1つの終了状態**：テスト結果、ビルドの exit code、ファイル数、空のキューなど
- **証明方法の明示**：どう証明するか。たとえば「`npm test` が exit 0 になる」「`git status` がクリーンになる」
- **守るべき制約**：途中で変えてはいけないもの。たとえば「他のテストファイルは変更しない」

また、暴走を防ぐためにターン数や時間の上限を条件に含めることもできます。

```text
/goal CHANGELOG.md に今週マージされた全PRのエントリがある or stop after 20 turns
```

`or stop after 20 turns`（20ターンで停止）のような節を入れると、Claude は毎ターンその上限に対する進捗を報告し、評価器が会話から判断します。条件は最大4,000文字まで書けます。

### 状態確認・早期解除・非対話実行

引数なしで `/goal` を実行すると、現在の条件・経過時間・評価済みターン数・トークン消費量・評価器の直近の判定理由が確認できます。

途中で止めたい場合は `/goal clear` です（`stop` / `off` / `reset` / `none` / `cancel` がエイリアスとして使えます）。`/clear` で新しい会話を始めても、アクティブなゴールは解除されます。

CI やバッチで使いたい場合は、非対話モード（`-p`）でループを最後まで一気に実行できます。

```bash
claude -p "/goal CHANGELOG.md has an entry for every PR merged this week"
```

### `/goal` と `/loop` と Stop hook の使い分け

セッションを動かし続ける手段は `/goal` だけではありません。公式ドキュメントでは、次のターンが「何によって始まるか」で使い分けるよう整理されています。

| 手段 | 次のターンが始まる条件 | 停止する条件 |
|---|---|---|
| `/goal` | 前のターンが終わったとき | モデルが条件達成を確認したとき |
| `/loop` | 一定の時間間隔が経過したとき | 自分で止めるか、Claudeが完了と判断したとき |
| Stop hook | 前のターンが終わったとき | 自前のスクリプト／プロンプトが判断したとき |

`/goal` はセッション限定の手軽なショートカット、Stop hook は設定ファイルに書いて全セッションに適用する仕組み、`/loop` は時間間隔で再実行する仕組み、という棲み分けです。条件達成まで自走させたいなら `/goal`、定期的に回したいなら `/loop` が基本になります。

## ループが壊れる3つの本番問題

Loop Engineering は強力ですが、ガードレールなしのループは簡単に壊れます。複数の解説で共通して挙げられているのが、次の3つです。これらは「めったに起きないエッジケース」ではなく、**常態として向き合うべき本番問題**だと位置づけられています。

1. **無限ループ** — ゴールに永遠に到達せず回り続ける
2. **ゴールドリフト** — 目的が少しずつズレて、当初と違うものを作り始める
3. **トークンコストの爆発** — 自走するぶん、消費が一気に膨らむ

Addy Osmani 氏もトークンコストについて、はっきり警告しています。

> you absolutely _have_ to be careful about token costs (usage patterns can vary wildly if you are token rich or poor)

（トークンコストには絶対に注意しなければなりません。使い方によって消費パターンは大きく変わります）

これらに対する設計上の打ち手は、これまで見てきた要素のなかにあります。

- **無限ループ対策**：ゴール条件に `or stop after N turns` のような上限を必ず入れる
- **ゴールドリフト対策**：実装者と検証者を分け、「守るべき制約」を条件に明記する
- **コスト爆発対策**：`/goal` で消費トークンを随時確認し、評価には小型モデル（Haiku）を使う

なお `/goal` の評価コストについて、公式ドキュメントは「評価のトークンは小型・高速モデルで課金され、メインターンの消費と比べれば通常はごくわずか」としています。コストの主役はあくまで作業を行うメインターン側なので、ループを回す前にゴールと上限をきちんと設計しておくことが、そのまま請求額の管理につながります。

## どこまで自動化されているのか

「ループを書くのが仕事」という言葉は誇張ではありません。Boris Cherny 氏のセットアップについては、すでに**数百の Claude インスタンスが Twitter のフィードバック・GitHub の Issue・Slack を監視し、プロダクトのアイデアを生成している**と報じられています（WorkOS によるインタビューまとめ）。

もちろん、これはツールと組織を成熟させた先端事例です。Addy Osmani 氏自身も、この働き方は「まだ早期段階」であり、トークンコストには十分注意が必要だと述べています。いきなり数百インスタンスを目指す必要はありません。まずは1本、`/goal` で「検証可能なゴールまで自走するループ」を組んでみるところから始めるのが現実的です。

## まとめ

- **Loop Engineering** は、エージェントに手でプロンプトを打つのをやめ、プロンプトを生成・実行・検証して繰り返す「ループ」そのものを設計する考え方です
- ループには **トリガー** と **検証可能なゴール** が必須です。機械が真偽を判定できる終了状態を設計することが肝になります
- 組み上げる要素は **Automations / Worktrees / Skills / Plugins / Sub-agents ＋ 外部メモリ**。特に**実装者と検証者の分離**が品質を支えます
- Claude Code の **`/goal`** は、この「自走ループ」を製品化した分かりやすい入口です。完了条件を1度書けば、毎ターン小型モデルが判定し、達成まで自走します
- 評価器は**会話に出力された内容しか見ない**ため、条件は「Claude の出力で証明できる形」で書きます
- ガードレールなしのループは**無限ループ・ゴールドリフト・コスト爆発**で壊れます。ターン上限・守るべき制約・トークン監視で防ぎます

「プロンプトを書く」から「ループを書く」へ。まずは手元のリポジトリで `/goal` を1本回してみるところから、Loop Engineering を体験してみてください。

### 参考リンク

- [Addy Osmani — Loop Engineering](https://addyosmani.com/blog/loop-engineering/)
- [Claude Code 公式ドキュメント — Keep Claude working toward a goal（`/goal`）](https://code.claude.com/docs/en/goal)
- [WorkOS — Key takeaways from Boris Cherny on building Claude Code](https://workos.com/blog/boris-cherny-claude-code-acquired-interview-takeaways)
