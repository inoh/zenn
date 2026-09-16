---
title: "React 以外の選択肢を地図にする — htmx 4.0 時代の HTML over the wire 全 3 系統"
emoji: "🗺️"
type: "tech"
topics: ["htmx", "hotwire", "frontend", "architecture", "webdev"]
published: true
---

## はじめに

2026 年 8 月 28 日に htmx 4.0.0 がリリースされました。Hacker News のスレッドは 830 ポイント・252 コメントに達し、「サーバーが HTML をそのまま返す」設計が改めて注目を集めています。

一方で、この分野には htmx のほかにも Turbo、Datastar、Unpoly、LiveView、Livewire、Inertia……と名前ばかりが並び、「どれが何と競合していて、どれが併用できるのか」が整理されていないまま語られがちです。

この記事では、これらを **3 つの系統** に分けて地図を描きます。各ライブラリの数字は、執筆日（2026 年 9 月 16 日）に GitHub API（`gh api repos/<owner>/<repo>`）で取得した Stars と最終 push 日だけを使い、二次記事のベンチマーク数値やインストール数は載せていません。

想定読者は「React（あるいは SPA 一般）が今のプロジェクトには重すぎると感じているが、代替の全体像がつかめていない」Web エンジニアです。

なお、このブログでは最近 Claude Code や AI エージェントの記事が続いていましたが、今回は久しぶりに AI そのものではなく Web アーキテクチャの話です。ただし、この分野が 2026 年に再評価されている背景には AI コーディングの普及が深く関わっているため、最後の節でその接点にも触れます。

## 共通する思想：JSON ではなく HTML を返す

SPA では、サーバーは JSON を返し、クライアントの JavaScript がそれを DOM に変換します。状態（state）はブラウザ側に置かれ、その同期のために React や Vue のようなランタイムと、状態管理ライブラリが必要になります。

これに対して HTML over the wire と呼ばれるアプローチでは、サーバーが **描画済みの HTML 断片** を返し、クライアントはそれを DOM の該当箇所に差し込むだけです。Hotwire の公式サイトはこれを次のように定義しています。

> An alternative approach to building modern web applications without using much JavaScript by sending HTML instead of JSON over the wire.
>
> — [hotwired.dev](https://hotwired.dev/)

ポイントは「クライアントに状態を持たせない」という一点にあります。テンプレートはサーバー側に一本化され、フロントエンドのビルドパイプラインも最小化できます。

### 用語の整理：SPA でも SSR でもなく「HDA」

「HTML over the wire」は Hotwire が広めた、**通信内容**（JSON ではなく HTML を送る）に着目した呼び方です。一方、htmx 側はこのアーキテクチャ自体を **Hypermedia-Driven Application（HDA）** と名付けています。

> The Hypermedia Driven Application (HDA) architecture is a new/old approach to building web applications. It combines the simplicity & flexibility of traditional Multi-Page Applications (MPAs) with the better user experience of Single-Page Applications (SPAs).
>
> — [Hypermedia-Driven Applications — htmx](https://htmx.org/essays/hypermedia-driven-applications/)

同エッセイは MPA を thesis、SPA を antithesis、HDA を synthesis と位置づけています。SPA / MPA は「ページ遷移の単位」、SSR / CSR は「HTML をどこで描画するか」の分類であり、HDA はそのどちらとも軸が違います。「htmx は SSR です」は誤りではないものの、SSR は初回描画の場所しか表さないため、「以降のやり取りも HTML で行う」という本質を取りこぼします。

理論的な背景は REST の HATEOAS（Hypermedia As The Engine of Application State）で、同エッセイは次のように述べています。

> HDAs continue to use Hypermedia As The Engine of Application State (HATEOAS), whereas most SPAs abandon HATEOAS in favor of a client-side model and data (rather than hypermedia) APIs.
>
> — [Hypermedia-Driven Applications — htmx](https://htmx.org/essays/hypermedia-driven-applications/)

本記事では横断的な総称として「HTML over the wire」を使いますが、htmx の文脈で HDA という語が出てきたら同じものを指していると読んでください。

ただし、「クライアントが持たない状態をどこで持つか」で 2 つの流派に分かれ、さらにその周辺に「思想は近いが HTML は送らない」隣接領域があります。それが以下の 3 系統です。

## 系統 1：ステートレスな HTML 断片差し込み型

もっとも単純な系統です。クライアントは HTTP リクエストを投げ、返ってきた HTML を指定要素に swap します。**サーバーは通常の HTTP リクエスト/レスポンスで完結し、接続状態を保持しません**。したがって、バックエンドの言語やフレームワークを問わず使えます。

| ライブラリ | Stars | 最終 push | 一言で |
| --- | --- | --- | --- |
| [htmx](https://github.com/bigskysoftware/htmx) | 49,450 | 2026-09-12 | 本流。4.0 で fetch() ベースに刷新 |
| [Turbo](https://github.com/hotwired/turbo) | 7,394 | 2026-09-09 | Hotwire の中核。Rails の既定フロントエンド |
| [Datastar](https://github.com/starfederation/datastar) | 5,060 | 2026-09-12 | htmx + Alpine.js 相当を 1 本に統合 |
| [Unpoly](https://github.com/unpoly/unpoly) | 2,786 | 2026-09-16 | 老舗。オーバーレイ（レイヤー）管理が強い |
| [fixi.js](https://github.com/bigskysoftware/fixi) | 1,324 | 2026-09-06 | htmx 作者による実験的な極小実装 |
| [Alpine AJAX](https://github.com/imacrayon/alpine-ajax) | 1,146 | 2026-03-17 | Alpine.js のプラグインとして同じことを行う |

### htmx 4.0 で何が変わったか

htmx 4 は、作者 Carson Gross が 2025 年 11 月のエッセイ「[The fetch()ening](https://htmx.org/essays/the-fetchening/)」で予告した大型版です。主な変更は次のとおりです。

- 通信層を `XMLHttpRequest` から `fetch()` に置き換え
- 属性の暗黙的な継承（CSS のように親から子へ効く挙動）を **デフォルト無効** にし、`hx-target:inherited="#div"` のように `:inherited` 修飾子で明示する方式へ
- 複数箇所を一度に更新する `<hx-partial>` 要素の追加
- DOM モーフィング（`innerMorph` / `outerMorph`）のコア対応
- SSE と WebSocket を拡張（extension）として分離

特徴的なのは、破壊的変更を出しながら **旧版を切らない** 方針を明文化している点です。

> htmx 2.0 (like htmx 1.0 & intercooler.js 1.0) will be supported _in perpetuity_, so there is absolutely _no_ pressure to upgrade your application.
>
> — [The fetch()ening](https://htmx.org/essays/the-fetchening/)

実際、htmx.org のトップページでは次のように案内されており、npm の `latest` タグは 2.x のまま維持されています。

> htmx 4.0 has been released! It is not currently marked as `latest` in NPM so that people using the 2.x line are not accidentally upgraded.
>
> — [htmx.org](https://htmx.org/)

GitHub のリリース一覧でも、4.0.0（2026-08-28）の後に 2.x 系の v2.0.10（2026-09-06）が出ており、両系統が並走していることが確認できます。

### Turbo：Rails 既定の実装

Turbo は 37signals が開発する Hotwire の中核ライブラリで、Drive（ページ遷移の高速化）、Frames（部分更新）、Streams（複数箇所の同時更新）の 3 要素からなります。Rails では `rails new` 時に `--skip-hotwire` を付けない限り `turbo-rails` と `stimulus-rails` が Gemfile に入ります（rails/rails の `railties/lib/rails/generators/app_base.rb` の `hotwire_gemfile_entry` で確認できます）。

htmx とは解いている問題が同じで、機能はほぼ 1 対 1 に対応します。htmx 公式が [Hotwire/Turbo からの移行ガイド](https://htmx.org/migration-guide-hotwire-turbo/) を用意しているのはそのためです。

| Turbo | htmx |
| --- | --- |
| Turbo Drive | `hx-boost="true"` |
| Turbo Frames | `hx-get` + `hx-target`（専用要素は不要） |
| Turbo Streams | `hx-swap-oob` / `hx-select-oob` |
| `data-turbo="false"` | `hx-boost="false"` |

なお、Turbo 8 のモーフィングは htmx 作者が公開している [Idiomorph](https://github.com/bigskysoftware/idiomorph) に依存しています（hotwired/turbo の `package.json` に `"idiomorph": "~0.7.4"` があり、`src/core/morphing.js` で import されています）。競合しつつ、根っこでは同じ部品を共有している関係です。

最新リリースは v8.0.23（2026-01-29）で、執筆時点でそれ以降のリリースはありません。

### Datastar・Unpoly・fixi

**Datastar** は自身を次のように位置づけています。

> Datastar provides backend reactivity like htmx and frontend reactivity like Alpine.js in a lightweight frontend framework that doesn't require any npm packages or other dependencies.
>
> — [Datastar Getting Started](https://data-star.dev/guide/getting_started)

`data-bind` や `data-on:click` といった `data-*` 属性でクライアント側のリアクティビティを書き、バックエンドからの応答には `text/event-stream`（SSE）も受け付けます。後述する「htmx + Alpine.js」の組み合わせを 1 ライブラリで済ませたい人向けで、最新版は v1.0.3（2026-08-27）です。

**Unpoly** は「Works with any language. Gracefully degrades without JavaScript.」を掲げる老舗で、モーダルやドロワーをレイヤーとして扱い、サブインタラクションを分岐させて元のページに戻る、という設計が特徴です。

**fixi.js** は htmx 作者による「6 属性・9 イベント・2 プロパティ」だけの極小実装で、README 自身が experimental と明記しています。htmx の思想を最小構成で学ぶ教材、あるいは後述の MCP Apps のような特殊環境向けと考えるとよいでしょう。

## 系統 2：サーバーが状態を持つ LiveView 型

系統 1 との決定的な違いは、**WebSocket を常時接続し、サーバー側がコンポーネントの状態を保持する** ことです。ユーザーの操作はイベントとしてサーバーに送られ、サーバーが再描画した結果の差分だけが push されます。

| フレームワーク | 母体 | Stars | 最終 push |
| --- | --- | --- | --- |
| [Phoenix LiveView](https://github.com/phoenixframework/phoenix_live_view) | Elixir / Phoenix | 6,826 | 2026-09-15 |
| [Livewire](https://github.com/livewire/livewire) | Laravel（PHP） | 23,576 | 2026-09-15 |
| Blazor Server | ASP.NET Core（C#） | — | — |
| [StimulusReflex](https://github.com/stimulusreflex/stimulus_reflex) | Rails | 2,334 | 2026-09-13 |
| [django-unicorn](https://github.com/django-commons/django-unicorn) | Django | 2,664 | 2026-05-22 |

（Blazor Server は dotnet/aspnetcore リポジトリの一部のため、単独の Stars は記載していません）

この系統の源流は Phoenix LiveView（リポジトリ作成は 2018 年 9 月）で、Livewire や StimulusReflex、django-unicorn は、その考え方を各言語のフレームワークに持ち込んだものです。

系統 1 より書けることが多く、フォームのリアルタイムバリデーションや共同編集のような「状態が頻繁に変わる UI」を、クライアント JavaScript をほとんど書かずに実現できます。引き換えに、**接続ユーザー数に比例してサーバーのメモリと WebSocket 接続を消費** し、フレームワーク専用（Elixir なら LiveView、Laravel なら Livewire）になります。Elixir/Erlang の軽量プロセスと相性がよいのは偶然ではありません。

## 系統 3：隣接するが HTML は送らないもの

「SPA のルーティングやデータ取得をサーバーに戻す」という問題意識は共有しつつ、送るものが HTML ではない領域です。

- **[Inertia.js](https://github.com/inertiajs/inertia)**（8,115 Stars、最終 push 2026-09-15）— サーバー側のルーティングとコントローラをそのまま使い、ページコンポーネント（React / Vue / Svelte）に props を **JSON で** 渡します。GitHub の説明にある「build modern single-page React, Vue and Svelte apps using classic server-side routing」がそのまま本質です。Laravel や Rails のコミュニティで人気があります
- **React Server Components / Next.js App Router** — サーバーで描画した結果をクライアントに流す点は近いものの、送るのは RSC ペイロードで、クライアント側に React ランタイムが必要です

これらは「フロントエンドは React のまま、バックエンド主導に寄せたい」ときの選択肢で、HTML over the wire とは別の答えです。

## 補助役の位置づけ：Stimulus と Alpine.js

系統 1 のライブラリは「サーバーとの往復」しか担当しません。ドロップダウンの開閉やタブ切り替えのような、サーバーに聞く必要のない小さな振る舞いには別の道具が要ります。

- **[Stimulus](https://github.com/hotwired/stimulus)**（13,103 Stars）— Hotwire 側の公式ペア。Turbo + Stimulus が Rails の既定構成です
- **[Alpine.js](https://github.com/alpinejs/alpine)**（31,932 Stars）— htmx と組む定番。htmx 4 には Alpine との共存を助ける `alpine-compat` 拡張が同梱されています

ここで注意したいのは、**htmx と Turbo は併用しない** という点です。両者はともにリンククリックとフォーム送信を横取りして履歴を管理するため、同時に読み込むと同じクリックを二重に処理してしまいます。「htmx か Turbo かを 1 つ選び、Alpine か Stimulus を足す」が基本形です。

## 選び方の分岐

3 系統を踏まえると、選択は次の順で絞れます。

1. **使っているバックエンドに一級の統合があるか**
   Rails なら Turbo、Laravel なら Livewire（または Inertia）、Elixir なら LiveView が既定の道です。フレームワーク側が整備した統合（Rails の ActionCable と Turbo Streams、Laravel の Livewire コンポーネントなど）を捨てて別の系統を持ち込む合理性は、多くの場合ありません
2. **リアルタイム性と状態の複雑さ**
   「保存したら一覧が更新される」程度なら系統 1 で十分です。入力のたびにサーバー側で検証し、他ユーザーの操作も即時反映したい、となれば系統 2 が向きます。ただし接続コストを受け入れる必要があります
3. **フレームワークに依存せず学びたいか**
   htmx の公式 [Server-Side Examples](https://htmx.org/server-examples/) には Python、Java、C#、Rust、PHP、Ruby、Clojure、OCaml など 20 を超える言語・フレームワークの例が並んでいます。どのバックエンドでも同じ書き方ができることが、htmx を「まず学ぶ 1 本」にする理由になります

## AI コーディング時代の視点

最後に、この分野が 2026 年に再評価されている背景として、AI コーディングとの関係に触れておきます。

htmx の作者 Carson Gross は 2026 年 6 月のエッセイ「[Code is Cheap(er)](https://htmx.org/essays/code-is-cheap/)」で次のように述べています。

> The LLM can produce code far faster than you, or anyone else, can understand it.
>
> — [Code is Cheap(er)](https://htmx.org/essays/code-is-cheap/)

LLM がコードを量産できるようになった結果、ボトルネックは「書く速さ」から「理解し検証する速さ」へ移った、という主張です。この観点で系統 1 を見直すと、**クライアントに状態がない** ということは、LLM が生成したコードを検証すべき面積がサーバー側のテンプレートとハンドラに集約される、ということでもあります。同エッセイは、コードを足すことより層を減らすことに価値を置く「subtractive, constraining engineer」という像を提示しています。

Hacker News の htmx 4.0 スレッドでも、「Claude などの LLM が htmx をよく理解し、うまく生成する」「HTML ベースのテストはヘッドレスブラウザより速く回せる」といった声が複数見られました。これらはコメント由来の定性的な報告であり、定量的な検証結果ではない点は割り引いて読む必要があります。

また、同じ htmx.org には、MCP Apps（LLM ホスト内の iframe に UI を描く仕様拡張）の画面を React ではなく fixi.js で組んだ事例「[Hypermedia Friendly Model Context Protocol App Architecture](https://htmx.org/essays/mcp-apps-hypermedia/)」も掲載されています。LLM に向けた UI という新しい領域でも、HTML over the wire の設計が選択肢に上がっていることがわかります。

## まとめ

- HTML over the wire 系のライブラリは **3 系統** に分けると整理できます
  - 系統 1：ステートレスな HTML 断片差し込み型（htmx / Turbo / Datastar / Unpoly / fixi）
  - 系統 2：サーバーが状態を持つ LiveView 型（LiveView / Livewire / Blazor Server / StimulusReflex）
  - 系統 3：隣接するが HTML は送らないもの（Inertia.js / RSC）
- 系統 1 の中では htmx と Turbo が同じ問題を解く競合関係にあり、**併用はしません**。補助役の Alpine.js / Stimulus と組むのが基本形です
- 選択の第一基準は「使っているバックエンドに一級統合があるか」で、なければフレームワーク非依存の htmx が学びやすい入口になります
- htmx 4.0 は fetch() 化と明示継承という破壊的変更を入れつつ、2.x を「in perpetuity」でサポートすると明文化しています
- AI がコードを量産する時代には、「クライアントに状態を持たない」設計が検証コストの面から再評価されています

React を使わない、という選択は「古い作り方に戻る」ことではなく、状態をどこに置くかを設計し直すことです。まずは自分のバックエンドに一級統合がある系統から試してみてください。

## 参考リンク

- [hotwired.dev](https://hotwired.dev/)
- [htmx.org](https://htmx.org/)
- [The fetch()ening — htmx](https://htmx.org/essays/the-fetchening/)
- [Hotwire / Turbo → htmx Migration Guide](https://htmx.org/migration-guide-hotwire-turbo/)
- [Hypermedia-Driven Applications — htmx](https://htmx.org/essays/hypermedia-driven-applications/)
- [Code is Cheap(er) — htmx](https://htmx.org/essays/code-is-cheap/)
- [Hypermedia Friendly MCP App Architecture — htmx](https://htmx.org/essays/mcp-apps-hypermedia/)
- [Datastar Getting Started](https://data-star.dev/guide/getting_started)
- [Unpoly](https://unpoly.com/)
- [Htmx 4.0 — Hacker News](https://news.ycombinator.com/item?id=49478178)
