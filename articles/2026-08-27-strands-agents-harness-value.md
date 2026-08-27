---
title: "AWS Strands Agentsは何が嬉しいのか——「ハーネス」再ポジショニングとAgentCore Harnessの二層構造"
emoji: "🧵"
type: "tech"
topics: ["aws", "strandsagents", "bedrock", "aiagent", "llm"]
published: true
---

## はじめに

AWS が2025年5月に公開したオープンソースのAIエージェントSDK「Strands Agents」は、公開から1年以上が経ち、単なる「AWS製のエージェントSDK」から立ち位置を大きく変えつつあります。

その変化を象徴するのが、GitHubリポジトリの改名です。かつて `strands-agents/sdk-python` だったリポジトリは、現在 **`strands-agents/harness-sdk`** に改名され、READMEの冒頭にはこう書かれています。

> Build an agent harness. Control it end-to-end.

さらに2026年6月には、Strands Agents を基盤とするマネージドサービス **Amazon Bedrock AgentCore Harness** がGAになりました。「SDK」ではなく「ハーネス」という言葉を軸に、AWSのエージェント戦略が二層構造に再編されたわけです。

本記事では、実際に SDK をインストールして検証した結果と一次ソース（公式ブログ・GitHub・公式ドキュメント）をもとに、Strands Agents が提供する価値を「ハーネスへの再ポジショニング」という観点から整理します。

:::message
本記事の情報は2026年8月27日時点のものです。バージョンは Python SDK v1.53.0 で検証しています。
:::

## Strands Agentsとは——model-drivenという設計思想

Strands Agents は AWS が開発したオープンソース（Apache-2.0）のAIエージェントSDKです。2025年5月16日に[AWS Open Source Blog で発表](https://aws.amazon.com/blogs/opensource/introducing-strands-agents-an-open-source-ai-agents-sdk/)され、AWS社内では Amazon Q Developer、AWS Glue、VPC Reachability Analyzer などのチームが本番利用していることが公式に明かされています。

最大の特徴は **model-driven（モデル駆動）** と呼ばれるアプローチです。エージェントを「モデル」「ツール」「プロンプト」の3要素だけで定義し、どのツールをいつ呼ぶか・どんな順序でタスクを進めるかという**オーケストレーションの判断をLLM自身に委ねます**。

コードにするとこれだけです。

```python
from strands import Agent, tool

@tool
def word_count(text: str) -> int:
    """テキストの単語数を数えます"""
    return len(text.split())

agent = Agent(tools=[word_count])
agent("次の文章の単語数を教えてください: Hello world from Strands")
```

LangGraph のようにノードとエッジでグラフを明示的に設計するフレームワークと比べると、思想の違いは明確です。

| | グラフ駆動（LangGraph等） | model-driven（Strands） |
|---|---|---|
| 実行パスの決定者 | 開発者がグラフとして設計 | LLMが実行時に推論 |
| 得意な場面 | 決定的な実行パスが必要な業務フロー | ツールを渡して自律的に解かせるタスク |
| コード量 | 状態・ノード・エッジの定義が必要 | エージェント定義は数行 |
| モデル性能への依存 | 低い（パスは固定） | 高い（推論力がそのまま品質になる） |

「モデルが賢くなるほどフレームワーク側の制御は薄くていい」という賭けが model-driven の本質です。この賭けは、ツール利用に強いモデルが標準になった2026年時点では、かなり分がよくなっています。

## リポジトリ改名に表れた「ハーネス」再ポジショニング

冒頭で触れたとおり、Strands のリポジトリは `sdk-python` から `harness-sdk` へ改名され、Python SDK と TypeScript SDK を束ねるモノレポになっています。リポジトリの説明文も次のように変わりました。

> Build an agent harness and control it end-to-end. Open-source SDK for production AI agents in Python & TypeScript - any model, any cloud.

「ハーネス（harness）」とは、エージェント本体（モデルの推論ループ）の周囲に必要な**実行環境一式**——コンテキスト管理、実行制限、オブザーバビリティ、ガードレール、フックによる介入——を指す言葉です。READMEの「Why Strands」セクションでは、次の4点が価値として挙げられています。

- **Build your way**: どのモデル・どのクラウドでも動き、バックエンドを差し替えてもコードは変わらない
- **Model agnostic**: Amazon Bedrock、Anthropic、OpenAI、Gemini などをファーストクラスでサポート
- **Stay in control**: エージェントループは全決定をデフォルトでトレースし、フックであらゆるステップに介入できる
- **Deliver outcomes that work**: ガードレールが実行前にミスを捕捉し、ステアリングハンドラでエージェント自身に軌道修正させる

つまり「数行でエージェントが作れるSDK」という初期のメッセージから、**「エージェントの実行系を端から端まで自分の制御下に置くためのハーネス」**へと、訴求の重心が移っています。単発のデモエージェントではなく、本番運用時の可視性と介入可能性が主戦場になったということです。

### フックによる介入の例

「Stay in control」を支えるのがフック機構です。ツール実行の前後、モデル呼び出しの前後など、ループの各ステップにイベントとして割り込めます。

```python
from strands import Agent
from strands.hooks import BeforeToolCallEvent

def ツール実行前の検証(event: BeforeToolCallEvent) -> None:
    # 危険なツール呼び出しをここでブロック・書き換えできます
    print(f"実行しようとしているツール: {event.tool_use['name']}")

agent = Agent(hooks=[ツール実行前の検証])
```

`BeforeToolCallEvent` / `AfterModelCallEvent` / `BeforeMultiAgentInvocationEvent` など、マルチエージェント実行まで含めた粒度でイベントが定義されていることを実機で確認しました。

## AgentCore Harnessとの二層構造——設定で始めて、コードに卒業する

2026年6月18日、AWS は [Amazon Bedrock AgentCore Harness の一般提供](https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-agentcore-harness-is-now-generally-available-go-from-idea-to-production-grade-agent-in-minutes/)を発表しました（2026年4月にプレビュー開始）。公式ブログはハーネスをこう定義しています。

> A harness is everything an agent needs to run in production, wrapped behind two API calls.

`CreateHarness` と `InvokeHarness` の2つのAPIだけで、エージェントの定義から実行までを完結させるマネージドサービスです。モデル・ツール・スキル・指示を**設定として宣言**すると、サンドボックス環境・メモリ・ストレージ・アイデンティティ・オブザーバビリティをAWS側が引き受けます。コードを書く必要はありません。

そして重要なのが、この AgentCore Harness が **Strands Agents を基盤としている**ことと、両者の間に「卒業パス」が用意されていることです。公式ブログから引用します。

> One CLI command exports the harness as Strands-based code that can host on AgentCore Runtime or anywhere else

つまり、AWSのエージェント提供形態は次の二層構造になっています。

```
┌─────────────────────────────────────────────┐
│ Amazon Bedrock AgentCore Harness（マネージド層）│
│ 設定だけでエージェントを定義・実行               │
│ CreateHarness / InvokeHarness の2API           │
└──────────────────┬──────────────────────────┘
                   │ CLI 1コマンドで
                   │ Strandsコードにエクスポート（卒業）
                   ▼
┌─────────────────────────────────────────────┐
│ Strands Agents SDK（コード層・OSS）            │
│ ループ・フック・ガードレールを全て自分で制御      │
│ AgentCore Runtime でもどこでもホスト可能        │
└─────────────────────────────────────────────┘
```

「まず設定ベースのマネージドハーネスで検証し、カスタムオーケストレーションが必要になったらStrandsコードとしてエクスポートして深掘りする」——プロトタイプから本番カスタマイズまでの移行コストを下げる設計です。マネージド側とOSS側が同じ基盤を共有しているため、卒業してもランタイム（AgentCore Runtime）はそのまま使えます。

AgentCore Runtime 側も Strands のデプロイ先として公式ドキュメントで案内されており、セッションごとのマイクロVM分離や Amazon Cognito / Microsoft Entra ID / Okta との認証統合が特徴です（[公式デプロイガイド](https://strandsagents.com/docs/user-guide/deploy/deploy_to_bedrock_agentcore/)）。

## 実機検証——インストールして分かる「ハーネスの中身」

言葉だけでは実態が掴みにくいので、実際にインストールして中身を確認しました。

```bash
pip install strands-agents strands-agents-tools
```

検証環境は Python SDK v1.53.0（2026年8月21日リリース）です。

### モデルプロバイダ: 12種を同梱、AWS専用ではない

`strands.models` パッケージには以下のプロバイダモジュールが同梱されていることを確認しました。

```
anthropic, bedrock, gemini, litellm, llamaapi, llamacpp,
mistral, ollama, openai, openai_responses, sagemaker, writer
```

デフォルトは Amazon Bedrock ですが、Anthropic・OpenAI・Gemini の直接利用から、Ollama や llama.cpp によるローカル実行まで揃っています。「AWSが作ったからAWS専用」ではなく、モデルとクラウドを差し替えてもエージェントコードが変わらないことが、公式の言う「Any model, any cloud」の実体です。

### 標準ツール: 49個を実測

別パッケージ `strands-agents-tools` には49個のツールモジュールが含まれていました。一部を挙げると次のとおりです。

- `browser` / `code_interpreter`: ブラウザ操作・コード実行
- `a2a_client`: A2Aプロトコルで他のエージェントを呼び出し
- `agent_core_memory`: AgentCore Memory との連携
- `diagram` / `editor` / `calculator` / `current_time`: 汎用ユーティリティ

ツールを自作しなくても、ある程度のエージェントは同梱ツールの組み合わせで構築できます。

### マルチエージェント: Graph / Swarm をSDK本体に内蔵

```python
from strands.multiagent import GraphBuilder, Swarm
```

決定的な実行順序を定義する `GraphBuilder` と、エージェント同士が自律的にハンドオフする `Swarm` が、追加パッケージなしでSDK本体からインポートできます。「単発エージェントはmodel-drivenで、マルチエージェントの骨格は必要なら明示的に組む」という使い分けが1つのSDKで完結します。

### 開発の勢い

GitHubのリリース履歴を確認すると、Python 1.0.0 が2025年7月15日、その後2026年8月時点で v1.53.0 まで、ほぼ週次でリリースが続いています。TypeScript SDK も v1.14.0 まで到達しており、二言語体制での開発が定着しています。

なお、ダウンロード数について AWS 公式ブログ（[2025年9月15日のWeekly Roundup](https://aws.amazon.com/blogs/aws/aws-weekly-roundup-strands-agents-1m-downloads-cloud-club-captain-ai-agent-hackathon-and-more-september-15-2025)）は次のように述べています。

> Strands Agents just hit 1 million downloads and earned 3,000+ GitHub Stars less than 4 months since launching as a preview in May 2025

## どちらをいつ選ぶか——判断基準

二層構造を踏まえると、選択の指針は次のように整理できます。

| 状況 | 推奨 |
|---|---|
| とにかく速くエージェントを立ち上げて検証したい | AgentCore Harness（設定のみ・2API） |
| ツール選択やループに独自の制御・検証を入れたい | Strands SDK（フック・ガードレール） |
| AWS以外のクラウドやローカルでも動かしたい | Strands SDK（model agnostic） |
| Harnessで始めたが要件が複雑化してきた | CLIエクスポートでStrandsコードに卒業 |
| 決定的な実行パスが業務要件（監査等）で必須 | Strands の GraphBuilder、または LangGraph 等のグラフ駆動 |

ポイントは、**この二層が対立ではなく連続している**ことです。マネージドで始めてもロックインで行き止まりにならず、OSSコードとして手元に引き出せる。逆にStrandsで書いたエージェントは AgentCore Runtime にそのままデプロイして、マイクロVM分離やマネージド認証の恩恵を受けられる。この「行き来できること」自体が、単体のフレームワーク比較では見えてこない Strands の価値だと言えます。

## まとめ

- Strands Agents は「モデル・ツール・プロンプト」の3要素でオーケストレーションをLLMに委ねる model-driven なOSSエージェントSDKで、Amazon Q Developer などAWS社内の本番利用が公表されています
- リポジトリは `sdk-python` から `harness-sdk` に改名され、「数行で作れるSDK」から「実行系を端から端まで制御するハーネス」へ訴求が再ポジショニングされました
- 2026年6月GAの Amazon Bedrock AgentCore Harness は Strands を基盤とする設定ベースのマネージド層で、CLI 1コマンドでStrandsコードにエクスポートする「卒業パス」を持ちます
- 実機検証では、12種のモデルプロバイダ・49個の標準ツール・Graph/Swarm のマルチエージェントパターンがSDKに同梱されていることを確認しました
- 「設定で始めて、コードに卒業する」二層構造の行き来のしやすさが、2026年時点の Strands の最大の価値です

## 参考リンク

- [Introducing Strands Agents, an Open Source AI Agents SDK（AWS Open Source Blog）](https://aws.amazon.com/blogs/opensource/introducing-strands-agents-an-open-source-ai-agents-sdk/)
- [strands-agents/harness-sdk（GitHub）](https://github.com/strands-agents/harness-sdk)
- [Strands Agents 公式ドキュメント](https://strandsagents.com/)
- [Amazon Bedrock AgentCore harness is now generally available（AWS Machine Learning Blog）](https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-agentcore-harness-is-now-generally-available-go-from-idea-to-production-grade-agent-in-minutes/)
- [Deploying Strands Agents to Amazon Bedrock AgentCore Runtime（公式デプロイガイド）](https://strandsagents.com/docs/user-guide/deploy/deploy_to_bedrock_agentcore/)
