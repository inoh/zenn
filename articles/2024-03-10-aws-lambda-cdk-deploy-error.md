---
title: "AWS の node を CDK deploy する 403 が出たので解決した"
emoji: "😄"
type: "teck"
topics: ["aws"]
published: true
---

CDK で nodejs をデプロイするとこんなエラーが発生した。

```
ERROR: failed to solve: public.ecr.aws/sam/build-nodejs20.x: pulling from host public.ecr.aws failed with status code [manifests latest]: 403 Forbidden
```

自分の環境は M1 mac を使用していたので好例のおまじないの `--platform="linux/amd64` をつけて、Lambda の node をインストールして無事解決。

```shell
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
docker pull public.ecr.aws/lambda/nodejs:20 --platform="linux/amd64"
```
