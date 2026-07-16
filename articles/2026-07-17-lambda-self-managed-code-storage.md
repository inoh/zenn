---
title: "Lambdaのコードストレージ制限が実質撤廃。Self-Managed Code Storage（Referenceモード）を試す"
emoji: "🗄️"
type: "tech"
topics: ["aws", "lambda", "s3", "serverless"]
published: true
---

## はじめに

2026年7月15日、AWS Lambda に **Self-Managed Code Storage**（自己管理型コードストレージ）という新機能が発表されました。

https://aws.amazon.com/about-aws/whats-new/2026/07/lambda-self-managed-code-storage/

一言でいうと「**自分の S3 バケットをそのまま Lambda のコード置き場にできる**」機能です。これまで Lambda は、S3 経由でデプロイしても必ず Lambda 管理ストレージに zip の**コピー**を作っていました。このコピーがリージョンあたり 75GB の上限にカウントされるため、関数バージョンやレイヤーが溜まると `CodeStorageExceededException` でデプロイが止まる——CI/CD を回している方なら一度は見たことがあるのではないでしょうか。

今回の発表のポイントは2つです。

- 新しい **Reference モード**を使うと、Lambda はコピーを作らず自分の S3 バケットを直接参照する。Lambda 管理ストレージを**一切消費しない**
- あわせて Lambda 管理ストレージのデフォルト上限が **75GB → 300GB** に引き上げ

本記事では実際に AWS アカウント上で Reference モードの関数を作成・実行し、ドキュメントに書かれた「落とし穴」も再現して確かめました。実行ログ付きで紹介します。

## COPYモードとREFERENCEモードの違い

新機能は `S3ObjectStorageMode` というパラメータで制御します。値は2つです。

| モード | 動き | ストレージ消費 |
|---|---|---|
| `COPY`（デフォルト） | 従来どおり Lambda 管理ストレージにコピーを保存 | Lambda 管理ストレージを消費（上限 300GB/リージョン） |
| `REFERENCE` | 自分の S3 バケットのオブジェクトを直接参照 | Lambda 側の消費ゼロ。S3 バケットの容量まで実質無制限 |

公式ドキュメントには次のように書かれています。

> With self-managed S3 code storage, you can configure Lambda to reference your code directly from an S3 bucket in your account. Lambda does not store a copy of your code, so the code does not count against your Lambda-managed storage quota.

https://docs.aws.amazon.com/lambda/latest/dg/configuration-self-managed-storage.html

料金面の追加コストはなく、S3 の標準ストレージ料金だけがかかります（同一リージョン内のオブジェクト取得に Lambda 側の課金はありません。リージョンを跨ぐ参照は S3 のデータ転送料が発生します）。

なお、対象は **zip パッケージの関数とレイヤーのみ**です。コンテナイメージ関数は従来どおり ECR を使います。また、zip の上限サイズ（解凍後 250MB）は変わりません。

## 上限300GBを実機で確認する

まず「デフォルト上限が 300GB になった」という発表内容を、利用実績ゼロのアカウントで確認してみます。

```bash
$ aws lambda get-account-settings --query AccountLimit --output json
{
    "AccountLimit": {
        "TotalCodeSize": 322122547200,
        ...
    }
}
```

`322122547200` バイト = ちょうど **300GiB** です。上限緩和の申請をしていないアカウントでこの値なので、デフォルトが引き上げられたことが確認できます。

:::message
手元の AWS CLI が古いと `--s3-object-storage-mode` オプション自体が存在しません。筆者の環境（aws-cli 2.34.19）にはまだ入っておらず、最新版への更新が必要でした。発表直後に試す場合は最初に CLI を更新してください。
:::

## セットアップ手順

Reference モードを使うには、事前準備が3つ必要です。

1. S3 バケットで**バージョニングを有効化**する（必須。Lambda がどのバージョンのオブジェクトを使うか追跡するため）
2. zip をアップロードする
3. Lambda のサービスプリンシパルにオブジェクトの読み取りを許可する**バケットポリシー**を設定する

### 1. バケット作成とバージョニング有効化

```bash
aws s3api create-bucket \
  --bucket my-lambda-code-bucket \
  --create-bucket-configuration LocationConstraint=ap-northeast-1

aws s3api put-bucket-versioning \
  --bucket my-lambda-code-bucket \
  --versioning-configuration Status=Enabled
```

### 2. zipのアップロード

アップロード時に返ってくる `VersionId` を控えておきます。関数作成時に使います。

```bash
$ aws s3api put-object \
  --bucket my-lambda-code-bucket \
  --key my-function.zip \
  --body my-function.zip \
  --query VersionId --output text
JhMp_gq7EWQJId_jzvZObBt_1.oWsABT
```

### 3. バケットポリシーの設定

`lambda.amazonaws.com` に `s3:GetObject` と `s3:GetObjectVersion` を許可します。`aws:SourceArn` の条件で対象の関数を絞るのが公式推奨の形です。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaSelfManagedCodeAccess",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetObjectVersion"],
      "Resource": "arn:aws:s3:::my-lambda-code-bucket/my-function.zip",
      "Principal": { "Service": "lambda.amazonaws.com" },
      "Condition": {
        "ArnLike": {
          "aws:SourceArn": "arn:aws:lambda:ap-northeast-1:123456789012:function:my-function"
        }
      }
    }
  ]
}
```

## Referenceモードで関数を作成する

`--code` に `S3ObjectStorageMode=REFERENCE` を追加するだけです。

```bash
aws lambda create-function \
  --function-name my-function \
  --runtime python3.12 \
  --role arn:aws:iam::123456789012:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --code "S3Bucket=my-lambda-code-bucket,S3Key=my-function.zip,S3ObjectVersion=JhMp_gq7EWQJId_jzvZObBt_1.oWsABT,S3ObjectStorageMode=REFERENCE"
```

作成後に `get-function` で確認すると、`Code` セクションに `ResolvedS3Object` として**自分のバケットへの参照**が表示されます。

```bash
$ aws lambda get-function --function-name my-function --query Code --output json
{
    "RepositoryType": "S3",
    "ResolvedS3Object": {
        "S3Bucket": "my-lambda-code-bucket",
        "S3Key": "my-function.zip",
        "S3ObjectVersion": "JhMp_gq7EWQJId_jzvZObBt_1.oWsABT"
    }
}
```

invoke も問題なく動きます。

```bash
$ aws lambda invoke --function-name my-function out.json
{
    "StatusCode": 200,
    "ExecutedVersion": "$LATEST"
}
$ cat out.json
{"message": "hello from self-managed code storage"}
```

### 本当にストレージを消費していないのか

ここが一番おもしろいポイントです。関数が1個 Active で動いている状態で `get-account-settings` を見ると——

```bash
$ aws lambda get-account-settings --query AccountUsage --output json
{
    "TotalCodeSize": 0,
    "FunctionCount": 1
}
```

**関数は存在するのに `TotalCodeSize` は 0** です。Reference モードの関数は Lambda 管理ストレージをまったく消費しないことが実機で確認できました。

CloudFormation の場合は `Code` プロパティに同じキーを書きます。

```yaml
Resources:
  MyFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: my-function
      Runtime: python3.12
      Handler: lambda_function.lambda_handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Code:
        S3Bucket: my-lambda-code-bucket
        S3Key: my-function.zip
        S3ObjectVersion: abc123def456
        S3ObjectStorageMode: REFERENCE
```

レイヤーも同様に `publish-layer-version` の `--content` で `S3ObjectStorageMode=REFERENCE` を指定できます。

## 落とし穴3選

便利な機能ですが、実際に触ってみると注意点がいくつかあります。

### 罠1: コード更新時にモード指定を忘れると黙ってCOPYに戻る

これは実際に再現できました。Reference モードで動いている関数に対して、`--s3-object-storage-mode` を**付けずに** `update-function-code` を実行してみます。

```bash
aws lambda update-function-code \
  --function-name my-function \
  --s3-bucket my-lambda-code-bucket \
  --s3-key my-function.zip \
  --s3-object-version JhMp_gq7EWQJId_jzvZObBt_1.oWsABT
```

更新は**エラーなく成功**します。しかし `Code` セクションを見ると、`ResolvedS3Object` が消えて Lambda 管理のスナップショット用バケット（`awslambda-ap-ne-1-tasks`）への署名付き URL に変わっていました。ストレージ使用量もゼロではなくなっています。

```bash
$ aws lambda get-account-settings --query AccountUsage --output json
{
    "TotalCodeSize": 223,
    "FunctionCount": 1
}
```

`S3ObjectStorageMode` を省略するとデフォルトの `COPY` が適用されるためです。公式ドキュメントにも Important として明記されています。

> You must specify `S3ObjectStorageMode=REFERENCE` on every call to `update-function-code`. If you omit `S3ObjectStorageMode`, it defaults to `COPY` and Lambda stores your code in Lambda-managed storage.

警告もエラーも出ないので、CI/CD のデプロイスクリプトに指定を入れ忘れると、気づかないうちに全関数が COPY モードへ戻っていた、ということが起こり得ます。

なお `REFERENCE` を付けて更新し直せば、Lambda 管理側のコピーは削除されて `TotalCodeSize` も 0 に戻ることを確認しました。モードの行き来は自由にできます。

### 罠2: S3オブジェクトを消すと関数がInactiveになる

Reference モードでは、S3 のオブジェクトが「デプロイ時に一度読まれて終わり」ではありません。Lambda はコードの再最適化のために**定期的にソースオブジェクトへアクセスし続けます**。

公式ドキュメントによると、Lambda が関数のソースオブジェクトにアクセスできなくなると、関数は `Inactive` 状態に遷移します。復旧するにはアクセスを回復したうえで関数を更新する必要があります。

つまり、以下のような操作が事故につながります。

- 参照先のオブジェクト（またはバージョン）を削除する
- S3 ライフサイクルポリシーで古いバージョンを自動削除する
- バケットポリシーから Lambda の許可を外す

「デプロイが終わったから古い zip は掃除しよう」が通用しない点は、運用設計に組み込んでおく必要があります。ライフサイクルポリシーを使う場合は、現役の関数が参照しているバージョンを消さない設計にしましょう。

（この挙動は Lambda の再最適化のタイミングに依存し短時間では再現できないため、本記事ではドキュメントの記載の紹介にとどめます）

### 罠3: Lambdaコンソールのコードエディタが使えない

Reference モードの関数では、マネジメントコンソール上のコードエディタが無効になります。コードを直したいときは、S3 の zip を更新して関数を更新するのが唯一の手段です。

「コンソールでちょっと print デバッグ」という運用をしているチームは注意してください。逆に言えば、コンソールからの手編集を防げるので、IaC 徹底の観点ではメリットと捉えることもできます。

## まとめ

実機検証の結果をまとめます。

- Reference モード（`S3ObjectStorageMode=REFERENCE`）の関数は、動作中でも **`TotalCodeSize: 0`**。Lambda 管理ストレージを消費しない
- Lambda 管理ストレージのデフォルト上限は **300GiB**（`322122547200` バイト）に引き上げ済み
- `update-function-code` で**モード指定を省略すると黙って COPY に戻る**（エラーなし・再現済み）
- 参照先の S3 オブジェクトは消してはいけない。アクセスを失うと関数が `Inactive` になる
- コンソールのコードエディタは使用不可

`CodeStorageExceededException` に悩まされてきたヘビーユーザーにとっては待望の機能ですし、「デプロイアーティファクトの単一ソースを自分の S3 で管理する」という設計がそのまま Lambda に通用するようになったのは大きな変化です。一方で、S3 オブジェクトが関数の生存に直結するようになるため、バケットの管理ポリシーはこれまで以上に慎重に設計する必要があります。

## 参考リンク

- [AWS Lambda announces self-managed code storage（What's New）](https://aws.amazon.com/about-aws/whats-new/2026/07/lambda-self-managed-code-storage/)
- [Self-managed S3 code storage（公式ドキュメント）](https://docs.aws.amazon.com/lambda/latest/dg/configuration-self-managed-storage.html)
