---
title: "Fastify で JWT 認証をどう実現するか"
emoji: "🚀"
type: "teck"
topics: ["node"]
published: true
---

Fastify で JWT 認証をするための選択肢として [fastify-jwt](https://github.com/fastify/fastify-jwt) というエコシステムがあります。
今回はこれを使用してみようと思います。

## fastify-jwt について

最初に余談にはなりますが公式にこう書いてあるんですね

https://fastify.dev/docs/latest/Guides/Getting-Started/#your-first-plugin
> As with JavaScript, where everything is an object, with Fastify everything is a plugin.

JavaScript はすべてがオブジェクトだけど、Fastify は全てプラグインということらしいです。（知らなかった）

ということで、fastify-jwt もプラグインとして Fastify に追加します。

```typescript
import fastify from 'fastify'
import jwt from '@fastify/jwt'

const server = fastify()
server.register(jwt, { secret: 'supersecret' })
```

これによって `supersecret` という共通キーで JWT を作成することができます。

## 使ってみる

プラグインを追加すると fastify に jwt が追加されるため、あとは好きなペイロードで sign したり verify したりできます。

```typescript
server.post('/login', () => {
  return server.jwt.sign({ name: 'inoh' })
})
```

サーバーを起動して実行してみると JWT が返却されることが確認できます。

```typescript
server.listen({ port: 9999 })
```

※ 9999 ポートで起動してる前提になります

```shell
curl --request POST --url http://localhost:9999/login
# eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiaW5vaCIsImlhdCI6MTcxMjQ2NDc2Nn0.MK4j6nXFBneArlfjWE1j0ipmMi-N_8Cee0fKZ5m5lrU
```

次に認証してみます。
request に jwtVerify が拡張されているため、このメソッドを使用して認証します。

```typescript
server.get('/me', async (request) => {
  return await request.jwtVerify()
})
```

API をリクエストしてみると正常に Payload が取得されることが確認できました。

```shell
curl --request GET --url http://localhost:9999/me \
  --header 'authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiaW5vaCIsImlhdCI6MTcxMjQ2NDc2Nn0.MK4j6nXFBneArlfjWE1j0ipmMi-N_8Cee0fKZ5m5lrU'
# { "name": "inoh", "iat": 1712464766 }
```
デフォルトでは exp が設定されていないため有効期限はなさそうです。
当然 JWT を指定しないとエラーになります。

```shell
curl --request GET --url http://localhost:9999/me
# {"statusCode":401,"code":"FST_JWT_NO_AUTHORIZATION_IN_HEADER","error":"Unauthorized","message":"No Authorization was found in request.headers"}
```

HS256 前提で今回試していますが、register を使用してプラグインを追加するだけで簡単に JWT 認証が実現できるため、認証のサービスを作るためのハードルはかなり下がっている感じがしますね。
RS256 前提でサンプルコードも書いてみたので参考にしてみてください！
https://github.com/inoh/zenn/tree/main/samples/fastify
