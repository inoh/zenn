---
title: "LLMで作った理想のアプリをAWS本番に載せて、修正で壊さない2026年の作り方"
emoji: "🛟"
type: "tech"
topics: ["aws", "ai", "claude", "テスト", "spec"]
published: true
---

## はじめに

プロダクトオーナーがLLMを使って「これが理想だ」というアプリを作り上げる——2026年の今、これはもう珍しい光景ではありません。プロトタイプは驚くほど速く立ち上がります。

問題はその次です。「動くものができた。これをAWSの本番に載せて、これからも改修していきたい。でも、修正するたびに別のところが壊れるのは困る」。本記事はまさにこのフェーズ、**「動くプロトタイプ」を「壊れない本番システム」に変えるための作り方**を、2026年のトレンドと一次ソースに基づいて整理します。

結論を先に言うと、鍵は3つです。

1. **コードより先に「仕様（spec）」を固める**
2. **AWSのマネージドな経路に載せる**
3. **CI上の自動ガードレールで回帰を止める**

なぜこの3つなのか。まずは「動くアプリをそのまま育てると何が起きるか」をデータで見ていきましょう。

## 1. 「できた」と「壊れない」は別物——4つのデータが同じ方向を指している

LLM生成コードの品質については、2025年後半〜2026年にかけて独立した複数の調査が出そろいました。手法も調査主体もバラバラなのに、**結論の方向が一致している**のが重要なポイントです。

### セキュリティ：モデルが進化しても改善していない

Veracodeの「Spring 2026 GenAI Code Security Update」によると、AIコーディングアシスタントが生成したコードのセキュリティ合格率は**約55%で、ここ2年間ほぼ横ばい**でした[^veracode]。裏を返すと、**約45%のケースで既知の脆弱性が混入**しています。

注目すべきは「OpenAI・Google・Anthropicの2年間のモデル進化で、針は55%から55%にしか動いていない」という指摘です。SQLインジェクション（合格率82%）のような定番の脆弱性は得意になった一方、深いコード解析を要する複雑な型では合格率が落ちます。**最新モデルに乗り換えれば安全になる、という期待は裏切られている**わけです。

[^veracode]: [Spring 2026 GenAI Code Security Update: Despite Claims, AI Models Are Still Failing Security - Veracode](https://www.veracode.com/blog/spring-2026-genai-code-security/)。検証対象はSQLi(CWE-89)、XSS(CWE-80)、Log Injection(CWE-117)、脆弱な暗号(CWE-327)。セキュリティ特化のプロンプトを与えない「素のまま」の挙動を測定。

### 欠陥密度：AIコードのPRは問題が多い（ただし留保あり）

コードレビューツールのCodeRabbitが2025年12月に公開した「State of AI vs Human Code Generation」レポートでは、OSSのGitHub PR 470本（AI共同執筆320本・人間のみ150本）を解析し、次の結果を報告しています[^coderabbit]。

| 指標 | AI | 人間 |
|---|---|---|
| 1PRあたりの問題数 | 10.83 | 6.45（**約1.7倍**） |

カテゴリ別では、ロジック・正確性が+75%、可読性が3倍超、セキュリティ脆弱性が最大2.74倍、性能（過剰なI/O等）に至っては約8倍という数字が並びます。

ただし、この数字を引用するときは**前提を必ずセットにする**べきです。CodeRabbit自身がレポート中で重要な限界を認めています。「大規模OSSデータセットで各PRの著者を直接確認するのは不可能だったため、**AI共同執筆の"シグナル"があるものをAI、無いものを人間と仮定した**」「人間執筆とラベルしたものに、実際は人間だけで書かれていないものが混じっている可能性は否定できない」。つまり著者判定は推定であり、さらにAIレビューを販売する企業による測定でもあります。「AIコードは1.7倍バグる」と断定するのではなく、「**CodeRabbitの470PR分析では1.7倍多かった（著者判定は推定）**」という温度感が正確です。

[^coderabbit]: [State of AI vs Human Code Generation Report - CodeRabbit](https://www.coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report)（2025年12月17日公開）。

### 保守性：「貼り付け」が増え「リファクタリング」が消える

GitClearは2020年1月〜2024年12月の**2.11億行**の変更を分析し、コードの「貼り付け方」の変化を追っています[^gitclear]。

- コピペ（クローン）コード：**8.3% → 12.3%**（2021→2024）
- リファクタリング（Moved）行：**25% → 10%未満**

レポートは「初めて、開発者がリファクタリングよりコピペを多用するようになった」と表現しています。数年スパンで開発速度を保つにはDRY（Don't Repeat Yourself）でモジュラーな設計が要るのに、AI支援開発はその逆の傾向を生んでいる、という指摘です。**目先は速いが、貼り付けの蓄積がボディブローのように効いてくる**構図です。

[^gitclear]: [AI Copilot Code Quality: 2025 Data Suggests 4x Growth in Code Clones - GitClear](https://www.gitclear.com/ai_assistant_code_quality_2025_research)

### 生産性のパラドックス：熟練者ほど「速くなった気がして遅くなる」

最後に、最も示唆的なデータです。METR（Model Evaluation & Threat Research）のランダム化比較試験（RCT）では、**16名の経験豊富なOSS開発者・246タスク**を対象に、AIツールの使用可否をランダムに割り当てて完了時間を測りました[^metr]。

結果は、AI許可時に完了時間が**19%増加（=遅くなった）**。しかも開発者は事前に24%の短縮を予測し、タスクを終えた後でも「20%速くなった」と自己評価していました。**体感と実測の差は約39ポイント**です。

遅くなった要因として、プロンプトの記述、AI出力のレビューや待機、そして**AI生成コードの手直し**に時間が流れたことが挙げられています。

[^metr]: [Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity - METR (arXiv:2507.09089)](https://arxiv.org/abs/2507.09089)。使用ツールは主にCursor Pro + Claude 3.5/3.7 Sonnet。

### この章の含意

4つのデータは、調査主体も手法も異なります。だからこそ「セキュリティで劣る」「欠陥が多い」「保守性が落ちる」「体感ほど速くない」が**独立して同じ方向を指している**ことに意味があります。

ここから導かれる行動はシンプルです。**「動いた」を信用しすぎないための仕組みを、本番化と同時に組み込む**こと。次章から、その具体策を見ていきます。

## 2. 第一歩はコードではなく「仕様」——spec駆動開発

「壊れない仕組み」と聞くとテストやCIを思い浮かべますが、実はその前段にもっと効くものがあります。**仕様（spec）を明文化すること**です。

LLMで作ったアプリの最大の弱点は、「何を作りたかったのか」が自然言語のプロンプト履歴とコードの中に溶けてしまい、**正解（ground truth）がどこにも残らない**ことです。正解が無ければ、修正が「直したつもりで壊した」のか判定できません。

### AWS Kiroが示す「要件→設計→タスク」

この課題に対するAWSの回答が、agentic IDEの**Kiro**です。Kiroは「Bring engineering rigor to agentic development（エージェント開発にエンジニアリングの厳密さを持ち込む）」を掲げ、プロンプトからいきなりコードを書くのではなく、**3段階の仕様**を先に固めます[^kiro]。

1. **要件（Requirements）**：自然言語の要望を、受け入れ基準つきの明確な要件に変換する。ここで**EARS（Easy Approach to Requirements Syntax）**という記法を使い、`WHEN` / `IF-THEN` / `WHILE` といったパターンで「テスト可能な要件」を書く
2. **設計（Design）**：コードベースを解析し、アーキテクチャ・技術選定を提案する
3. **タスク（Tasks）**：要件に紐づいた実装タスクへ分解し、テストも含めて順序立てる

ポイントは、**この仕様がそのままリポジトリに残り、修正時のsingle source of truth（唯一の正解）になる**ことです。次の改修も「仕様→差分」で進むので、何を壊してはいけないかが常に明示されます。

[^kiro]: [Kiro](https://kiro.dev/)。AWSが提供するagentic開発プラットフォーム（IDE / CLI / Web）。ログインにAWS Builder IDやIAM Identity Centerが使えますが、利用にAWSアカウントは必須ではありません。

### AWSの答えは「もっとAI」ではなく「形式手法」だった

2026年5月、Kiroに**Requirements Analysis**という機能が加わりました。これが象徴的です。AIの間違いを別のAIに直させるのではなく、**50年以上の歴史を持つ自動推論（formal verification）**を持ち込んだのです。

Requirements Analysisは、LLMと自動推論エンジンを組み合わせた**neuro-symbolic（ニューロシンボリック）な3段パイプライン**で動きます[^kiro-blog]。

1. **精緻化**：曖昧な要件を、成功状態から逆算してテスト可能な受け入れ基準に書き直す
2. **自動形式化**：自然言語をSMT-lib形式の論理式に翻訳する。複数の形式化をサンプリングして「意味のブレ（semantic entropy）」を測り、曖昧さを検出する
3. **論理解析**：**SMTソルバ**と自動推論エンジンが、矛盾・抜け漏れ・未定義の振る舞いを洗い出す

要するに、**コードを1行も書く前に、要件の論理的な矛盾を数学的に検出する**わけです。複数のメディアは「AWSは要件のかなりの割合にバグを見つけた」と報じていますが、公式ブログが明示的に引用している数字は別の研究（Larbi et al., 2025）で、「要件が曖昧・不完全になると、構文的には正しい生成コードの60〜90%が意味的に誤りになる」というものです。仕様の質が、生成コードの質を支配しているという実証です。

[^kiro-blog]: [Requirements Analysis: catching requirement bugs before they become code - Kiro Blog](https://kiro.dev/blog/deep-spec-analysis/)

### Kiroを使わなくてもよい

ツールはKiroでなくても構いません。本質は「**修正前に、変えてよいもの・変えてはいけないものを仕様として書き出しておく**」ことです。`docs/spec/` にEARS風の要件を置き、PRごとに仕様との差分を意識する——これだけでも、LLM生成アプリの「正解が無い」問題は大きく緩和されます。

## 3. AWSへ載せる——アプリの正体で経路は変わる

仕様が固まったら本番化です。「LLMで作った理想のアプリ」と一口に言っても中身は様々なので、まず**アプリの正体で経路を分けます**。

### パターンA：LLMは一機能（フルスタックWebアプリ）

業務アプリやSaaSで、生成AIはその一機能、という最も多いケースです。

| レイヤー | 選択肢 |
|---|---|
| フロントエンド | Amplify Hosting、または S3 + CloudFront |
| API | API Gateway + Lambda（**AWS SAM** か **AWS CDK** で定義） |
| 生成AI部分 | **Amazon Bedrock**（基盤モデルをAPIで利用） |
| シークレット | AWS Secrets Manager |

LLMを呼ぶ部分だけBedrockに寄せ、残りは普通のサーバーレス構成にするのが堅実です。インフラは後述の通り**必ずIaC（SAM/CDK）で定義**します。

### パターンB：アプリ自体がAIエージェント／チャット

アプリの本体がエージェントやRAGチャットの場合、AWSは専用ソリューションを用意しています。**Generative AI Application Builder on AWS（GAAB）**です[^gaab]。

- バージョン4.1.14、**2026年5月リリース**
- MCP（Model Context Protocol）サーバー、エージェント、マルチエージェントのオーケストレーションを統合
- 基盤は**Amazon Bedrock AgentCore Runtime** + Lambda + API Gateway + Cognito + DynamoDB + CloudWatch
- **AWS Well-Architected**の設計原則に準拠し、CloudFormationテンプレートで（公称）約10分でデプロイ可能
- オープンソースで、StrandsやLangChainのオーケストレーション層を同梱

「エージェントの土台を自前で組むのは大変」という場合、GAABか、その基盤である**Bedrock AgentCore**を直接使うのが2026年の定石です。

[^gaab]: [Generative AI Application Builder on AWS - AWS Solutions](https://docs.aws.amazon.com/solutions/generative-ai-application-builder-on-aws/)

### どちらの経路でも共通する「壊れない土台」

経路が違っても、本番化で共通して入れるべき土台があります。

- **IaC**（CDK / SAM）：環境を再現可能にする。手作業のコンソール操作を残さない
- **Secrets Manager**：APIキーをコードやenvに直書きしない（前章のVeracodeが示した脆弱性の典型はここ）
- **CloudWatch**：メトリクス・ログ・ダッシュボードで観測可能にする

そして、ここまでが「載せる」話。次が本題の「壊れないようにする」話です。

## 4. 壊れない仕組み——テストがエージェント時代の唯一の防壁

修正で壊れないシステムの核心は、**「壊れたことを機械が自動で検知して止める」**ことに尽きます。人間のレビューだけでは、AIがコードを書く速度に追いつけません。

### Golden / characterizationテストで「今の正しい挙動」を固定する

LLM生成アプリは、仕様書が後付けになりがちで、内部実装も人間が完全には把握していないことが多いです。こういうコードに有効なのが**characterizationテスト（特性化テスト）**、別名**Golden Master**です。

考え方はシンプルで、「**今、現に動いている入出力のペアを"正解"として固定し、以後の変更がそこからズレたら失敗にする**」というものです。仕様が曖昧でも、「少なくとも現状の振る舞いは変えない」という防壁を即座に張れます。

```python
# tests/test_golden.py（イメージ）
import json
from app import generate_summary

def test_summary_matches_golden(snapshot):
    inputs = json.load(open("tests/golden/inputs.json"))
    for case in inputs:
        result = generate_summary(case["text"])
        # 保存済みの「正解」と差分があれば失敗
        snapshot.assert_match(result, f"golden/{case['id']}.txt")
```

LLM応答のように出力が完全一致しない部分は、スキーマ検証（JSON構造が崩れていないか）や主要フィールドの存在チェックなど、**決定的に判定できる軸**でゴールデンセットを作るのがコツです。

### カバレッジ・ラチェットで「後退」を物理的に禁止する

**カバレッジ・ラチェット（coverage ratchet）**は、テストカバレッジを「一方通行のラチェット（爪車）」にする仕組みです。現在のカバレッジ率を下限としてCIに記録し、**それを下回るPRはマージできなくする**。AIが大量のコードを足してもテストが伴わなければ率が下がるので、自動的にブロックされます。

### CIゲート：レポートをガードレールに変える

テストやカバレッジは、ただ実行するだけでは「レポート」止まりです。**閾値で不合格ならマージを止める**ところまで噛ませて初めて「ガードレール」になります。GitHub Actionsでの最小例を示します。

```yaml
# .github/workflows/guardrail.yml
name: guardrail
on:
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: 依存関係のインストール
        run: pip install -r requirements.txt
      - name: ゴールデンテスト＋カバレッジ下限ゲート
        run: pytest --cov=app --cov-fail-under=80   # 80%を下回ったら失敗
      - name: セキュリティ静的解析
        run: pip install bandit && bandit -r app -ll  # 中以上の指摘で失敗
```

このゲートを通過したPRだけが、別ワークフローで**SAM / CDKによる本番デプロイ**へ進む構成にします。「テストが通ったものしか本番に出ない」を機械で保証するわけです。

```bash
# デプロイ側ワークフローのコア（mainマージ時のみ実行）
sam build && sam deploy --no-confirm-changeset --no-fail-on-empty-changeset
# または CDK の場合
cdk deploy --require-approval never
```

CIに専用ゲートを足すとフィードバックループは数分伸びますが、それは「壊れたものを本番に出してから気づく」コストに比べれば桁違いに安い投資です。

### 観測性：壊れたときに即わかるように

最後に、デプロイ後も壊れを検知できるようにします。CloudWatchのアラーム（エラー率・レイテンシ・Bedrockの呼び出し失敗など）と、生成AI特有の評価（出力品質のオフライン評価＝eval）を組み合わせます。エージェント系ならGAABが標準でCloudWatchメトリクスを集約してくれるので、それを土台にダッシュボードを組むとよいでしょう。

## 5. まとめ——速さの前に、仕様・テスト・IaC

LLMで理想のアプリを作るところまでは、もう誰でも速くたどり着けます。差がつくのは、**それを壊れない本番システムに変える工程**です。

本記事の要点を3つに畳むと、次のようになります。

1. **コードより先に仕様（spec）を固める**：何を変えてはいけないかを明文化する。AWS Kiroの要件→設計→タスク、Requirements Analysisのような形式手法の流れが2026年のトレンド
2. **AWSのマネージドな経路に載せる**：フルスタックなら Amplify + SAM/CDK + Bedrock、エージェントなら GAAB / Bedrock AgentCore。インフラは必ずIaCで
3. **CI上の自動ガードレールで回帰を止める**：characterization/Goldenテスト＋カバレッジ・ラチェット＋CIゲート＋観測性

Veracode・CodeRabbit・GitClear・METRのデータが口を揃えて示すのは、「**AIは加速装置だが、ブレーキは別途つけないと事故る**」ということです。理想のアプリを長く育てたいなら、まず仕様とテストというブレーキから組みましょう。

:::message
本記事のデータは、各社の一次ソース（公式ブログ・レポート・arXiv論文・AWS公式ドキュメント）を確認して記載しています。数値はいずれも調査時期・サンプル・方法論の前提とセットで読んでください。特にCodeRabbitのレポートは著者判定が推定ベースである点に留意が必要です。
:::
