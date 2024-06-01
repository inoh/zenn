---
title: "LangChain の Introduction をとりあえず読んでみる (v0.2)"
emoji: "🤖"
type: "tech"
topics: ["AI"]
published: true
---

## はじめに

LangChain をやっていてプロンプト以外の機能がかなり豊富なことを知ったので、とりあえず導入のページを読んでみました。
https://python.langchain.com/v0.2/docs/introduction/

## LangChain の全体構成

LangChain は LLM アプリケーションを構築するために必要なライフサイクルを簡素化するためのフレームワークです。

大枠としては 3 つに分類されていそうです。

### Development

開発用です。
便利なテンプレートやサードパーティとの統合ですぐに LLM を実行することができます。

### Productionization

LangSmith を使用して開発したアプリケーションを検査、監視、評価し、最適化して継続的にデプロイを可能にします。

### Deployment

LangServe を使用して開発したものを API として提供します。

## オープンソースのライブラリ一覧

### langchain-core

LangChain の言語が抽象化された基礎となるライブラリです。

### langchain

アプリケーションのアーキテクチャとして、Chains、Agents、Retrieval Strategies の機能が提供されます。

### langchain-community

サードパーティと統合されたライブラリになります。
元々 LangChain の v0.0 のときには langchain-core、langchain、langchain-community が 1 つのパッケージにまとまっていましたが、v0.1 で分解されています。
OpenAI や Anthropic などのサードパーティについて、langchain-core に依存する独自の軽量パッケージとして提供されています。

### langgraph

これが一番自分で馴染みがなかったのですが、AWS でいうところの StepFunction みたいな位置づけだと理解しています。
ステートフルの multi-actor なアプリケーションでそれぞれのステップの状態によりワークフローを作成します。

### langserve

LangChain で構築したアプリケーションをデプロイし、REST API として提供します。

### LangSmith

LLM アプリケーションのデバッグ、テスト、評価、監視を行うための開発者プラットフォームです。

## さいごに

LangChain の勉強を始めたときは単純にプロンプトを作るだけだと思いきや、かなり広範囲の機能を提供していることを知りました。
まだ登場して１年半ですが、すでにここまでの機能を提供しており、今後もどんどんと進化していきそうですね。
