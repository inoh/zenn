---
title: "Prompt APIを実用にする2つの条件——出力を閉じる、セッションを複製する"
emoji: "🧩"
type: "tech"
topics: ["chrome", "javascript", "ai", "gemini", "webapi"]
published: true
---

## はじめに

Chrome の Prompt API がWebページから使えるようになり、`LanguageModel.create()` でオンデバイスのモデルを呼べるようになりました。ただ「動かしてみた」記事は多い一方で、**何に使うと実用になるのか**の議論はあまり見かけません。

Gemini Nano は小型モデルです。ChatGPT や Claude と同じ感覚で使うと、遅さと出力のブレに悩まされます。そこで手元の Chrome 150 でベンチマークを取り、実用になるタスクの形を絞り込みました。

結論から書くと、条件は2つです。

1. **`responseConstraint` で出力を閉じる**
2. **`create()` ではなく `clone()` を使う**

どちらも実測で効果を確認しました。順に見ていきます。

## 前提：モデルの準備

Prompt API は初回にモデルのダウンロードが必要です。`availability()` で状態を確認します。

```js
await LanguageModel.availability({});
// 'available' | 'downloadable' | 'downloading' | 'unavailable'
```

`downloadable` が返った場合、ダウンロードは**ユーザー操作を起点にしないと開始できません**。DevTools のコンソールから叩いても始まらないので、ボタンのハンドラ内で呼ぶ必要があります。

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

手元では数GB規模のダウンロードに数分かかりました。Chrome の[公式ドキュメント](https://developer.chrome.com/docs/ai/prompt-api)によると、空きストレージ22GB、GPUのVRAM 4GB以上またはCPU 16GB RAM以上・4コア以上が要件とされています。

## 条件1：`responseConstraint` で出力を閉じる

LLM の処理時間は出力トークン数にほぼ比例します。これを確かめるため、同じ入力（約240文字の技術記事）に対して**出力の長さだけを変えた3パターン**を各3回計測しました。

### A. enum分類 — 出力を実質1トークンに

記事の種別を2択で判定させます。`responseConstraint` に JSON Schema を渡すと、モデルの出力がスキーマに拘束されます。

```js
const SCHEMA_TYPE = { type: 'string', enum: ['tech', 'idea'] };

const result = await session.prompt(
  `次の記事は tech（技術解説）と idea（考察）のどちらですか。\n\n${text}`,
  { responseConstraint: SCHEMA_TYPE }
);
console.log(JSON.parse(result)); // 'tech'
```

戻り値は**JSON文字列**なので `JSON.parse()` が必要です。ここは素の値が返ってくると勘違いしやすいポイントです。

### B. 構造化抽出 — 配列を取る

Zenn の `topics` 候補を出させます。

```js
const SCHEMA_TOPICS = {
  type: 'object',
  properties: {
    topics: { type: 'array', items: { type: 'string' }, minItems: 3, maxItems: 5 },
  },
  required: ['topics'],
  additionalProperties: false,
};

const result = await session.prompt(
  `次の記事に付ける topics を3〜5個挙げてください。\n\n${text}`,
  { responseConstraint: SCHEMA_TOPICS }
);
console.log(JSON.parse(result).topics);
```

### C. 自由生成 — 制約なし（対照群）

```js
const result = await session.prompt(`次の記事を日本語2文で要約してください。\n\n${text}`);
```

### 結果

| ベンチ | 中央値 | 最小 | 最大 | 出力文字数 |
|---|---:|---:|---:|---:|
| A. enum分類 | **147ms** | 147 | 923 | 4 |
| B. 構造化抽出 | **973ms** | 904 | 1146 | 73 |
| C. 自由生成 | **1985ms** | 1888 | 2292 | 129 |

**入力が同じでも、出力を短くするだけで13.5倍速くなりました。** 出力4文字→73文字→129文字に対して147ms→973ms→1985msと、ほぼ出力長に比例しています。

A の最大値923msは初回のウォームアップです。2回目以降は147msに落ちるので、実運用では最初の1回を捨てるか、起動時に空打ちしておくと安定します。

147msなら、入力欄の `blur` やフォーム送信の直前に挟んでもユーザーは待たされたと感じません。逆に2秒かかる自由生成をインタラクションの同期パスに置くのは無理があります。

## 条件2：`create()` ではなく `clone()` を使う

分類器のように同じシステムプロンプトで何度も呼ぶ場合、セッションの作り方でコストが変わります。`clone()` は初期プロンプトと対話履歴を引き継いだ複製を作ります。

```js
// テンプレートを1つだけ作る
const base = await LanguageModel.create({
  initialPrompts: [{
    role: 'system',
    content: 'あなたは日本語の技術記事を分類するアシスタントです。指示された値だけを返してください。',
  }],
});

// リクエストごとに複製する
const session = await base.clone();
const result = await session.prompt(input, { responseConstraint: SCHEMA_TYPE });
session.destroy();
```

計測結果です。

| 処理 | 中央値 | 最小 | 最大 |
|---|---:|---:|---:|
| `create()`（system prompt付き） | 147ms | 147 | 164 |
| `clone()` | **0ms** | 0 | 0 |

`clone()` は**計測不能なほど速い**という結果でした。`create()` の147msは、システムプロンプトを毎回読み直すコストです。

分類のたびに `create()` を呼ぶと、A の推論時間147msに対して同じだけのセッション構築コストが乗り、**単純に倍の時間**がかかります。テンプレートを1つ保持して複製する形にすれば、これはまるごと消えます。

なお `clone()` は履歴も引き継ぐので、リクエスト間で文脈を分離したい場合はベースセッションに履歴を溜めないよう注意が必要です。使い終わったクローンは `destroy()` で捨てます。

コンテキストの消費量は確認できます。

```js
console.log(`${session.contextUsage}/${session.contextWindow}`);
```

## 落とし穴：JSON Schema が保証するのは構造だけ

ここが実務で一番刺さった点です。構造化抽出（B）を3回実行した結果を並べます。

```
1回目: ["css","layout","anchor positioning","web development","position-anchor"]
2回目: ["css","layout","anchor-positioning","web development","browser compatibility"]
3回目: ["css","layout","anchor-positioning","web-development"]
```

3回とも JSON としては正しく、スキーマにも適合しています。失敗はゼロです。しかし**値が毎回ぶれています**。

- `anchor positioning` と `anchor-positioning` が混在
- `web development` と `web-development` が混在
- 3回目は4個しか返っていない（`minItems: 3` なので仕様上は正しい）

つまり `responseConstraint` は「パースできる形で返ること」を保証しますが、「同じ値が返ること」は保証しません。タグ候補として使うなら、**既存タグ集合へのマッピング層が別途必要**になります。

一方 enum分類（A）は3回とも `tech` で完全に一致しました。**選択肢を閉じきったときだけ、小型モデルの出力は信頼できます。** 自由文字列を含んだ瞬間に揺らぎが入る、と考えておくのが安全です。

## では何に使うか

以上を踏まえると、用途は3つに絞られます。

### 1. enum分類

問い合わせフォームのルーティング、通報の一次振り分け、コンテンツの種別判定。出力が閉じているので速く、安定します。147msなら同期的な処理に組み込めます。

### 2. 構造化抽出

自由記述から日付・金額・カテゴリを取り出す用途。ただし前述の通り値は揺れるので、後段でのバリデーションと正規化が前提です。

### 3. 送信前チェック

**ここが Prompt API でしかできない領域です。** 投稿前の本文に個人情報が混ざっていないか、攻撃的な表現になっていないかを、**サーバーに送る前に**判定する用途です。

チェック対象のデータを外部に出せないことが要件なので、オンデバイスである必然性があります。逆に言うと、サーバーに送ってよいデータであれば、素直にサーバー側で高性能なモデルを呼んだ方が速くて確実です。

### 使うべきでない用途

翻訳・要約・校正には専用APIがあります。実測では Translator が90文字を26〜44msで処理したのに対し、Prompt API の自由生成は出力1文字あたり約15msでした。**専用APIがある領域で Prompt API を使う理由は速度面では見当たりません。**

専用APIとの比較は別記事「[Chromeの組み込みAIを実測したら、速いのはLLMじゃない方だった](https://zenn.dev/ino_h/articles/2026-08-11-chrome-builtin-ai-benchmark)」に詳しくまとめています。

## 標準化のリスクは織り込んでおく

実装を検討するうえで無視できないのが、他エンジンの姿勢です。

- **Mozilla**: [standards-positions #1213](https://github.com/mozilla/standards-positions/issues/1213) に `position: negative` と `concerns: interoperability` のラベル（2025年4月28日起票）
- **WebKit**: standards-positions の "ML Prompt API" に `position: oppose`、`concerns: interoperability` / `privacy` / `portability` のラベル（2025年5月14日起票）

相互運用性が争点になっているのは、API の性質上ある意味で当然です。プロンプトはモデルごとに最適化されるため、Gemini Nano で狙い通り動くプロンプトが、別のブラウザの別のモデルで同じ品質を返す保証がありません。CSS や DOM API のように「仕様通りに書けば同じ結果になる」という前提が成立しないのです。

したがって Prompt API は、**現時点では Chrome 限定の拡張機能として設計する**べきです。必ずフォールバック経路を用意し、機能が無い環境でも成立するUIにしておく必要があります。

```js
if ('LanguageModel' in self && await LanguageModel.availability({}) === 'available') {
  // オンデバイスで処理
} else {
  // サーバー側にフォールバック、または機能自体を出さない
}
```

## まとめ

- Prompt API の処理時間は出力長にほぼ比例する。実測で enum分類147ms、構造化抽出973ms、自由生成1985ms と13.5倍の差が出た
- `responseConstraint` に JSON Schema を渡して出力を閉じるのが最大の高速化手段。戻り値は JSON 文字列なので `JSON.parse()` が必要
- `create()` 147ms に対し `clone()` は0ms。同じシステムプロンプトを使い回すならテンプレートを複製する
- JSON Schema は構造しか保証しない。自由文字列を含むと値は毎回ぶれる。enum で閉じたときだけ安定した
- 本領は「送信前チェック」のようにデータを外に出せない用途。翻訳・要約は専用APIの方が速い
- Mozilla・WebKit が公式に反対を表明しているため、Chrome 限定機能として設計しフォールバックを用意する
