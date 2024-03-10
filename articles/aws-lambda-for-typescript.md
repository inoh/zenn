---
title: "AWS を CDK+Typescript で開発する方法まとめ"
emoji: "😄"
type: "teck"
topics: ["aws"]
published: false
---

Typescript で開発したものを AWS Lambda としてデプロイする方法をまとめます。
開発する上で CDK を使用することを前提で記載しますが、開発資源が 1 つまたは複数かどうかによってまず分岐します。

- [CDK の NodejsFunction を使用する](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_lambda_nodejs.NodejsFunction.html)
- [AWS SAM の eslint を使用する](https://docs.aws.amazon.com/ja_jp/serverless-application-model/latest/developerguide/serverless-sam-cli-using-build-typescript.html)

## 考えたいこと

- test をどうやってローカルで行うか
- ビルドをどうやって行うか
- Link をどうやって定義して共有するか

