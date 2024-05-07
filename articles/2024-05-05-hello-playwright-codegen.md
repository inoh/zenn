---
title: ""
emoji: "🚀"
type: "tech"
topics: ["E2E"]
published: false
---

Playwright のテストを非エンジニアに任せたいってことありますよね？
実際にどこまでブラウザ操作だけでテストが書けるか試してみようと思います。

Playwright のコードをブラウザ操作で書くためには generator を使用します。

## generator を使用してみる

基本てな手順はこちらを参考にしてみてください。
https://playwright.dev/docs/codegen

手順要約：

- [VS Code プラグイン](https://marketplace.visualstudio.com/items?itemName=ms-playwright.playwright) をインストール
- VS Code で操作
  - サイドメニューでテストを開く
  - 「Recode new」をクリック -> ブラウザが開く
    - テストしたいサイトの URL を入力
    - 画面操作をすると VS Code にコードが生成される

## 使用してみて

公式の手順通りにやってみると簡単にコードが作成できます。
ただし、繰り返し実行する場合は動的に生成される要素に対してテストを書くとうまくいかないことがあります。
