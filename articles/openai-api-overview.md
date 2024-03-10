---
title: "OpenAI の API とはなんなのか"
emoji: "😄"
type: "teck"
topics: ["zenn"]
published: false
---

OpenAI の [OpenAI developer platform](https://platform.openai.com/docs/overview) をとりあえず読んでみると。
まず最初に該当ページを見ると大きく「アシスタント作成」と「API」に大きく２分されています。
ただ現時点でベータになっている「アシスタント作成」が将来的に OpenAI らしい機能を作成する上では、こちらを使うことになりそうに感じます。

## アシスタント作成をとりあえず使ってみる

Node.js を使用して inoh アシスタントを作成してみようと思います。

とりあえずパッケージをインストールします。

```shell
npm install --save openai
```

[公式の API ドキュメント](https://platform.openai.com/docs/api-reference/introduction)を参考に動かしてみます。

```node
import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env['OPENAI_API_KEY'], // This is the default and can be omitted
});

// アシスタント作成
const assistant = await openai.beta.assistants.create({
  name: "inoh",
  instructions: "井上裕之風のアシスタント",
  tools: [{ type: "code_interpreter" }],
  model: "gpt-4-turbo-preview"
});
```
