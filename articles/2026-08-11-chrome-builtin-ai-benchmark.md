---
title: "Chromeの組み込みAIを実測したら、速いのはLLMじゃない方だった"
emoji: "⚡"
type: "tech"
topics: ["chrome", "javascript", "ai", "webapi", "frontend"]
published: true
---

## はじめに

ブラウザに AI が組み込まれる、という話題では Prompt API（Gemini Nano）ばかりが注目されます。任意のプロンプトを投げられるので、たしかに一番派手です。

ただ、実際に自分のマシンで全部のAPIを叩いて時間を測ってみたところ、評価が逆転しました。**実用速度で圧倒的に優れていたのは、LLMではない専用APIの方**でした。

この記事では Chrome 150 上で組み込みAI各APIの可用性とレイテンシを実測し、どのAPIをどう選ぶべきかを整理します。すべて手元で再現できるコードを載せています。

## 検証環境

| 項目 | 値 |
|---|---|
| ブラウザ | Chrome 150.0.0.0 |
| OS | macOS |
| 計測方法 | `performance.now()` の差分、各3回 |

Chrome の[公式ドキュメント](https://developer.chrome.com/docs/ai/prompt-api)によると、組み込みAIの利用には空きストレージ22GB、GPUのVRAM 4GB以上またはCPU 16GB RAM以上・4コア以上が必要とされています。要件を満たさない環境では以降のコードが `unavailable` を返します。

## まず可用性を調べる

各APIはグローバルオブジェクトとして生えています。存在確認と `availability()` を一気に回します。

```js
const names = [
  'LanguageModel', 'Translator', 'LanguageDetector',
  'Summarizer', 'Writer', 'Rewriter', 'Proofreader',
];

for (const n of names) {
  if (!(n in self)) {
    console.log(n, 'グローバルなし');
    continue;
  }
  try {
    console.log(n, await self[n].availability({}));
  } catch (e) {
    console.log(n, `ERR ${e.name}: ${e.message}`);
  }
}
```

手元の Chrome 150 での結果です。

| API | 結果 |
|---|---|
| `LanguageDetector` | `available` |
| `Translator` | 引数必須のため `TypeError`（後述） |
| `Summarizer` | `downloadable` |
| `LanguageModel` | `downloadable` |
| `Writer` | グローバルなし |
| `Rewriter` | グローバルなし |
| `Proofreader` | グローバルなし |

いきなり3つ躓きました。

Chrome の[ドキュメント](https://developer.chrome.com/docs/ai/built-in-apis)上では Writer / Rewriter / Proofreader は origin trial 段階とされていますが、トライアルに登録していない状態では**グローバルすら生えていません**。`'Writer' in self` が `false` なので、機能検出は素直に書けば足ります。

`Translator.availability({})` は空オブジェクトだと落ちます。

```
TypeError: Failed to execute 'availability' on 'Translator':
Failed to read the 'sourceLanguage' property from 'TranslatorCreateCoreOptions':
Required member is undefined.
```

翻訳は言語ペアごとにモデルが違うので、可用性の判定にも言語指定が要る、という設計です。他のAPIと引数の扱いが揃っていないので、共通ループで回すときは個別対応が必要になります。

```js
await Translator.availability({ sourceLanguage: 'en', targetLanguage: 'ja' });
// → 'available'
```

## 実測① LanguageDetector — ほぼコストゼロ

言語判定から測ります。

```js
const t0 = performance.now();
const detector = await LanguageDetector.create();
console.log('create:', Math.round(performance.now() - t0), 'ms');

for (const s of samples) {
  const t = performance.now();
  const r = await detector.detect(s);
  console.log(Math.round(performance.now() - t), 'ms', r[0].detectedLanguage, r[0].confidence);
}
```

結果です。

| 処理 | 時間 |
|---|---|
| `create()` | **2ms** |
| 英文93文字の判定 | **1ms**（`en` 100.0%） |
| 和文27文字の判定 | **1ms**（`ja` 99.7%） |
| コード片の判定 | **0ms**（`en` 99.9%） |

`create()` が2ms、判定が0〜1msです。これは実質コストゼロで、UIのイベントハンドラ内で同期的に呼んでも問題にならない水準です。

`detect()` は候補の配列を信頼度つきで返します。判定できないときは `und`（undetermined）が返るので、閾値を決めて切り捨てる運用になります。

## 実測② Translator — 90文字を26〜44ms

翻訳です。en→ja のモデルはすでに `available` でした。

```js
const t0 = performance.now();
const translator = await Translator.create({
  sourceLanguage: 'en',
  targetLanguage: 'ja',
  monitor(m) {
    m.addEventListener('downloadprogress', (e) => {
      console.log(`Downloaded ${(e.loaded * 100).toFixed(1)}%`);
    });
  },
});
console.log('create:', Math.round(performance.now() - t0), 'ms');

const t = performance.now();
const out = await translator.translate(text);
console.log(Math.round(performance.now() - t), 'ms', out);
```

| 処理 | 時間 |
|---|---|
| `create()` | **109ms** |
| 93文字の翻訳 | **44ms** |
| 92文字の翻訳 | **26ms** |
| ウォーム後の短文（`Hello world.`） | **8ms** |

訳文も実物を載せます。入力と出力は次の通りです。

入力:

```
Anchor positioning is a new layout mechanism for anchoring one element to another on the web.
```

出力:

```
アンカー ポジショニングは、Web 上で要素を別の要素に固定するための新しいレイアウト メカニズムです。
```

用語がカタカナで分かち書きされる癖はありますが、意味は正確です。**90文字前後で26〜44ms、ウォーム後の短文なら8ms**というのは、入力中のリアルタイム翻訳にも耐える速度です。

なお `create()` の109msは、初回のみ発生するセッション構築コストです。翻訳のたびに `create()` を呼ぶと毎回これが乗るので、言語ペアごとにインスタンスを保持するのが正解になります。

## 実測③ Prompt API と比べる

ここからが本題です。同じ「文章を生成する」処理を Prompt API（Gemini Nano）でやらせて比較します。

Prompt API は `downloadable` 状態だったので、まずモデルを落とす必要がありました。この初回ダウンロードは**ユーザー操作が必須**で、DevTools のコンソールから直接は開始できません。ボタンのクリックハンドラ内で `create()` を呼ぶ必要があります。

```html
<button id="prep">モデルを準備する</button>
<script>
document.querySelector('#prep').addEventListener('click', async () => {
  const session = await LanguageModel.create({
    monitor(m) {
      m.addEventListener('downloadprogress', (e) => {
        console.log(`${(e.loaded * 100).toFixed(1)}%`);
      });
    },
  });
  session.destroy();
});
</script>
```

手元では数GB規模のダウンロードに数分かかりました。完了すると `availability()` が `available` に変わります。

そのうえで、同じ記事本文（約240文字）を要約させた結果がこちらです。

| API | 処理 | 出力 | 時間 |
|---|---|---|---|
| Translator | 93文字を翻訳 | 48文字 | **44ms** |
| Prompt API | 240文字を要約 | 129文字 | **1985ms** |

出力1文字あたりに直すと、Translator が約0.35ms、Prompt API が約15msです。**40倍以上の差**があります。

要約の品質自体は悪くありません。実際の出力です。

```
CSS Anchor Positioningは、CSSだけで要素を紐付けて配置する新しいレイアウト機構で、
従来のJavaScriptライブラリの必要をなくします。全ブラウザで実装が完了し実戦投入が
可能になった一方、APIの学習コストや満足度の低さが課題です。
```

読める日本語ですし、内容も入力に忠実です。ただ**2秒かかります**。そして Chrome には要約専用の Summarizer API が別に存在します。

つまり、翻訳・要約・校正といった「タスクが決まっている処理」において、Prompt API を選ぶ理由は速度面では見当たりません。専用APIの方が速く、モデルのダウンロードも軽く、出力も安定します。

## ハマりどころ

実際に触って踏んだものをまとめます。

### `LanguageModel.params()` は存在しない

温度や topK のデフォルト値を取ろうとして呼ぶと落ちます。

```
TypeError: LanguageModel.params is not a function
```

そもそも `temperature` と `topK` は Chrome 拡張機能か origin trial 経由でのみ指定でき、通常のWebページからは触れません。パラメータ調整前提の設計はできないと考えた方が安全です。

### モデルのダウンロードはユーザー操作が必須

前述の通りです。自動テストやコンソールから叩こうとすると、ここで止まります。E2Eテストに組み込むなら、実際のクリックを発生させる必要があります。

### `requestAnimationFrame` はバックグラウンドタブで止まる

これは組み込みAIの話ではありませんが、計測ページを書くときに踏みました。rAF はタブが非アクティブだと発火しないので、自動計測するページでは `setTimeout` を併用しておかないと結果が空のままになります。

```js
let measured = false;
function measure() {
  if (measured) return;
  measured = true;
  // 計測処理
}
requestAnimationFrame(() => requestAnimationFrame(measure));
setTimeout(measure, 300); // バックグラウンドタブ用の保険
```

## 標準化の状況は楽観できない

速度以前の問題として、Prompt API はクロスブラウザ機能として設計できません。他エンジンが公式に反対を表明しています。

- **Mozilla**: [standards-positions #1213](https://github.com/mozilla/standards-positions/issues/1213) に `position: negative` と `concerns: interoperability` のラベルが付いています（2025年4月28日起票）
- **WebKit**: standards-positions の "ML Prompt API" に `position: oppose`、`concerns: interoperability` / `privacy` / `portability` のラベルが付いています（2025年5月14日起票）

一方 Translator / LanguageDetector / Summarizer は[Chrome 138 で stable](https://developer.chrome.com/docs/ai/built-in-apis) になっていますが、これらも現時点では Chrome 独自です。いずれにせよフォールバック経路は必須になります。

## 結論：APIの選び方

実測から導かれる優先順位はシンプルです。

1. **タスクが決まっているなら専用APIを使う。** 翻訳は Translator、言語判定は LanguageDetector、要約は Summarizer。速度が桁違いで、出力も安定します
2. **言語判定は今すぐ使える。** モデルサイズが小さく `create()` 2ms・判定1msなので、フォールバックを書く手間の方が大きいくらいです
3. **Prompt API は「専用APIがない、かつ出力が短い」タスクに限定する。** 分類・抽出のように出力を閉じられる用途でなければ、2秒待たされます
4. **どれを使うにしてもフォールバックは必須。** Chrome 独自であることに加え、ハードウェア要件を満たさない端末では軒並み `unavailable` になります

「ブラウザに LLM が載った」という切り口だと Prompt API に目が行きますが、**いま実務で効くのは地味な専用APIの方**でした。まずそちらから検討することをおすすめします。

Prompt API を実際に使う場合の設計については、別記事「[Prompt APIを実用にする2つの条件——出力を閉じる、セッションを複製する](https://zenn.dev/ino_h/articles/2026-08-11-prompt-api-practical)」で条件を整理しています。

## まとめ

- Chrome 150 の実測で、LanguageDetector は `create()` 2ms・判定0〜1ms、Translator は90文字を26〜44msで処理した
- 同じ生成処理で Prompt API は出力1文字あたり約15msかかり、Translator の40倍以上遅い
- `Translator.availability()` は言語指定が必須、`LanguageModel.params()` は存在しない、Writer / Rewriter / Proofreader はグローバルすら生えていない
- Prompt API のモデルダウンロードはユーザー操作必須
- Mozilla は `position: negative`、WebKit は `position: oppose` を表明しており、クロスブラウザ前提には置けない
