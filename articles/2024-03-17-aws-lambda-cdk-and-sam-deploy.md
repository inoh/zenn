---
title: "AWS と SAM を掛け合わせて開発する方法について検討してみる"
emoji: "🤔"
type: "teck"
topics: ["node","aws"]
published: true
---

※ SAM はインストールされている前提になります

公式に CDK から吐き出した template を使用して SAM で開発を行う方法が記載されています。
https://docs.aws.amazon.com/ja_jp/serverless-application-model/latest/developerguide/serverless-cdk-getting-started.html

今回はこれを試してみようと思います。

## とりあえず CDK の土台作る

```shell
$ npx cdk init app --language typescript
```

## template を吐き出して実行してみる

CDK でデプロイする lambda の template を cdk.out フォルダに吐き出します。

```shell
$ npx cdk synth --no-staging
```

そのまま実行するとテレメトリーを収集することの警告が表示されます。
実行するため無効にする場合は環境変数を設定します。

```shell
$ export SAM_CLI_TELEMETRY=0
```

sam 実行すると

```
$ sam local invoke MyFunction --no-event -t ./cdk.out/SamTemplateStack.template.json
Error: Running AWS SAM projects locally requires Docker. Have you got it installed and running?
```

のエラーが出るので docker のリンクを修正。

```shell
$ sudo ln -s "$HOME/.docker/run/docker.sock" /var/run/docker.sock
```

実行リベンジ！

```shell
$ sam local invoke MyFunction --no-event -t ./cdk.out/SamTemplateStack.template.json
Error: Error building docker image: pull access denied for public.ecr.aws/lambda/nodejs, repository does not exist or may require 'docker login': denied: Your authorization token has expired. Reauthenticate and try again.
```

古いセッションが残りっぱなしになることがあるみたいなので、ログアウトする。
https://docs.aws.amazon.com/ja_jp/AmazonECR/latest/public/public-troubleshooting.html#public-troubleshooting-authentication

```shell
$ docker logout public.ecr.aws
```

もう一回実行！
```shell
$ sam local invoke MyFunction --no-event -t ./cdk.out/SamTemplateStack.template.json
INFO    Hello, world! {}
```

正常終了やっとしました。

## まとめ
端末固有の問題も含まれていそうですが、そのまま写経してもうまくいかないところがいくつかありました。
CDK と SAM を掛け合わせて開発する一歩踏み出せたので、Typescript のビルドとか含めて SAM いけるのか今後の模索していきたいです。
