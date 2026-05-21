---
title: "招待されないClaude Mythosの技術仕様をAWS Bedrockモデルカードから読み解く"
emoji: "🔍"
type: "tech"
topics: ["claude", "bedrock", "vertexai", "anthropic", "ai"]
published: true
---

## はじめに

2026年4月7日、Anthropicは新フロンティアモデル「Claude Mythos Preview」を発表しました。性能はFirefoxに対する制御フロー乗っ取り181件（Opus 4.6は2件）など派手な数字が並びますが、一般公開はなく、12社連合「Project Glasswing」経由でのみ提供される「招待されないAI」です。

その一方で、Anthropic公式の発表blog（[red.anthropic.com](https://red.anthropic.com/2026/mythos-preview/)）には、いつもなら必ず書かれているはずの技術仕様（コンテキストウィンドウ、APIの形、リージョン、推論パラメータ）が一切記載されていません。

ところが、AWS Bedrock の[公式モデルカード](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-mythos-preview.html)には、しっかりと仕様の決定版が掲載されています。本記事ではこのモデルカードを一次ソースとして、Claude Mythos の技術的輪郭を「触れない一般エンジニア」目線で逆解析していきます。

## 公式blogが「触れない」もの

まず確認しておきたいのは、公式blog `red.anthropic.com/2026/mythos-preview/` が何を語り、何を語らないかです。

語られていること：

- セキュリティタスクでの圧倒的性能（Firefox 181件のexploit、OSS-Fuzz 595件のクラッシュ）
- OpenBSD 27年もののSACK脆弱性、FFmpeg 16年もののH.264脆弱性の発見
- 数千件の高/クリティカル脆弱性を発見したこと
- Project Glasswing 経由でのみ提供すること

語られていないこと：

- コンテキストウィンドウ
- 最大出力トークン
- Knowledge cutoff
- API/エンドポイントの仕様
- 推論（thinking）の設定可能なオプション
- 利用可能リージョン

普段のClaude発表（Opus 4.7 など）であれば、ブログ末尾に必ず仕様一覧があったはずです。今回それがない理由は推測でしかありませんが、ゲート付き先行公開という性格と整合的に、「触りにくる人に対しては別ルートで情報を渡す」という設計に見えます。

そして、その「別ルート」がクラウドベンダのモデルカードです。

## AWS Bedrock モデルカードに書かれている決定版仕様

Bedrock の[Claude Mythos Preview モデルカード](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-mythos-preview.html)から、技術スペックを順に拾っていきます。

### 基本スペック

| 項目 | 値 |
|---|---|
| モデルID | `anthropic.claude-mythos-preview` |
| Model launch date | 2026-04-07 |
| ライフサイクル | Preview |
| コンテキストウィンドウ | 1M tokens |
| 最大出力トークン | 128K tokens |
| Knowledge cutoff | 2025年12月 |
| Reasoning | `thinking.type: "adaptive"` のみサポート |

コンテキスト1M tokens は、Anthropicのフロンティアモデルの最新値と揃っており、長時間動作するエージェント用途（Anthropic自身が公言している方向性）と整合的です。

### 入出力モダリティ・APIサーフェス

| 入力 | テキスト、画像 |
|---|---|
| 出力 | テキストのみ |
| 対応API | Messages のみ |

Converse API・Chat Completions API・Invoke API は非対応です。Bedrockで Claude を使うときによく使われている `Converse` API が使えない点はハマりどころになりそうです。

### エンドポイント

ここが今回の記事で一番注目すべき点です。

```
| Endpoint        | Model ID                        | URL                                            |
| bedrock-mantle  | anthropic.claude-mythos-preview | https://bedrock-mantle.{region}.api.aws        |
```

通常の Bedrock モデルは `bedrock-runtime` エンドポイントを使いますが、Mythos Preview は **`bedrock-mantle` という新設エンドポイント** に乗っています。詳細は次節で考察します。

### リージョン

| Region | In-Region | Geo Cross-Region | Global Cross-Region |
|---|---|---|---|
| us-east-1 (N. Virginia) | ✅ | ❌ | ❌ |

us-east-1 の In-Region のみ。Geo / Global のクロスリージョンルーティングは無効化されています。データ越境を発生させない設計です。

### Service Tier

| Standard | Priority | Flex | Reserved |
|---|---|---|---|
| ✅ | ❌ | ❌ | ❌ |

Standard のみで、Priority / Flex / Reserved は使えません。スループット重視の長期コミットや、コスト優先のFlex運用といった「本番向け」のオプションが意図的に外されています。

### プロンプトキャッシュ

| 項目 | 値 |
|---|---|
| 対応 | あり |
| 最小トークン数 / チェックポイント | 4,096 |
| 最大チェックポイント数 / リクエスト | 4 |
| TTL | 5分 / 1時間 |
| 対応フィールド | `system`、`messages`、`tools` |

`tools` フィールドまでキャッシュ対象になっているのは、大量のツール定義を抱えるエージェント運用を想定している証拠です。

## 考察: なぜ `bedrock-mantle` という新エンドポイントなのか

`bedrock-mantle` は今回モデルカードに初登場した名前で、命名から推測する限りですが、地球科学のメタファ（"mantle" = マントル）を借りた「Bedrockの内側にあるもう一層」という構造を意図しているように見えます。

公式ドキュメントには `bedrock-mantle` の独立した解説はまだありません（2026年5月時点）。観測できる事実だけ列挙すると：

- URLは `https://bedrock-mantle.{region}.api.aws`（`bedrock-runtime` とは別ホスト）
- Mythos Preview のサンプルコードでは `AnthropicBedrockMantle` という専用クライアントクラスを利用

```python
from anthropic import AnthropicBedrockMantle

client = AnthropicBedrockMantle(aws_region="us-east-1")

message = client.messages.create(
    model="anthropic.claude-mythos-preview",
    max_tokens=1024,
    messages=[{"role": "user", "content": "..."}],
)
```

クライアントSDK側でも `AnthropicBedrock` ではなく `AnthropicBedrockMantle` と完全に別クラスで分離されています。コードレベルでも、通常のBedrock経路と物理的に混ぜないという意思表示と読めます。

この分離は、Project Glasswing のアクセス制御を「IAMポリシー+モデルID」ではなく「そもそも別エンドポイント・別SDKクライアント」というレイヤで担保している、と解釈すると整合します。間違って一般アプリから呼ばれないように、トラフィック経路ごと隔離している、というイメージです。

## 考察: `adaptive` only の意味

Claude 4.x 系で導入された `thinking` パラメータには、本来 `enabled`（有効化）や `disabled`（無効化）といったタイプが選べますが、Mythos Preview では **`adaptive` のみ** がサポートされています（Bedrock モデルカードの "Reasoning" 欄に明記）。

`adaptive` は、入力タスクの難易度に応じてモデル側が推論の深さを動的に決めるモードです。これがonlyということは、

- 呼び出し側で「軽く返してほしい」と推論を切ることができない
- 逆に「絶対深く考えさせる」と固定もできない

つまり、Mythos の運用方針として「タスクをきちんと見て、必要な深さの推論をモデル自身に判断させる」ことを前提にしているということです。長時間ジョブで `thinking` を切って高速化、というよくある最適化は使えません。

## Vertex AI ではどう提供されているか

Google Cloudの[公式blog](https://cloud.google.com/blog/products/ai-machine-learning/claude-mythos-preview-on-vertex-ai)によれば、Vertex AI でも Mythos Preview を提供していますが、こちらは **Private Preview** で、Google Cloud側で選定された顧客のみが対象です。

ブログ内ではリージョンや価格・固有の制限などの仕様詳細は明示されていません。「同じく Vertex AI で既に提供されている Opus 4.6 / Sonnet 4.6 と並列で扱える」という記述に留まっています。

つまり、現時点で技術仕様の決定版が読めるのは AWS Bedrock 側だけ、という状態です。Bedrock のモデルカードがデファクトのスペックシートとして機能しているのは、Anthropic 公式の沈黙と対照的で興味深い構図です。

## プロンプトキャッシュ仕様から推測する想定ワークロード

最後にプロンプトキャッシュの仕様を見ながら、Anthropic が Mythos に何を期待しているかを推測します。

| 項目 | Mythos Preview |
|---|---|
| 最小4,096 tokens / チェックポイント | 長いシステムプロンプト前提 |
| 最大4チェックポイント | 多層キャッシュで段階的にコンテキストを積む運用を想定 |
| TTL 5分 / 1時間 | 5分は短期インタラクティブ、1時間は長時間ジョブ向け |
| `tools` もキャッシュ対象 | 大量のツールスキーマを抱えるエージェント運用 |

4チェックポイント・1時間TTL・`tools` キャッシュという組み合わせは、以下のような使われ方を強く示唆しています。

1. 巨大なシステムプロンプト（例: コードベース全体の要約、セキュリティポリシー）をキャッシュ
2. その上にツール定義群（例: 数百種のセキュリティスキャナを呼ぶwrapper）をキャッシュ
3. その上に対話履歴のチェックポイントを積み増し
4. 1時間オーダーで動き続ける長時間エージェントが、何度もモデルを叩く

これは、Anthropic blog が掲げる「ambitious projects focusing on cybersecurity, autonomous coding, and long-running agents」という運用像と非常によく整合します。仕様の作り方からも「長時間動かす自律エージェント」が主用途であることが透けて見えます。

## まとめ: モデルカードが示す「ゲート付き先行公開」のアーキテクチャ

公式blogが意図的に技術仕様を伏せている一方で、Bedrock のモデルカードを読めば、Claude Mythos Preview の運用設計がかなり立体的に見えてきます。

- **新エンドポイント `bedrock-mantle`** + **専用SDKクラス `AnthropicBedrockMantle`**: 経路ごと隔離された別レイヤの存在
- **us-east-1 In-Region限定**: データ越境の物理的制限
- **Standard tier限定**: スループット予約や本番運用を排除
- **`adaptive` only thinking**: 推論深度の制御権をAnthropic側が保持
- **4チェックポイント・1時間TTL・toolsキャッシュ**: 長時間ジョブ向けエージェント運用に最適化

「招待されないAI」と言われると遠い話に聞こえますが、こうしてモデルカード越しに眺めると、Anthropic と AWS がプロトコル層・SDK層・IAM層・リージョン層のすべてで多重に「Mythosは別物」と区切っていることがわかります。

Project Glasswing に招待されていなくても、モデルカードと SDK のリポジトリは誰でも読めます。フロンティアモデルの「先行公開フレームワーク」がどう設計されているか、というメタな観察対象として、Mythos Preview のモデルカードは一読する価値があります。
