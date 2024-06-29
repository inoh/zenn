---
title: "Anthropic のプロンプトジェネレータを使ってみた"
emoji: "📜"
type: "tech"
topics: ["LLM"]
published: true
---

Anthropic のプロンプトエンジニアリングを重点に学ぶため https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview を読んでみようと思います。

## ガイドラインの前提

参考のサイトは下記を前提としたドキュメントになっています。
- ユースケースの成功基準を明確に定義する
- これらの基準を経験的にテストする方法
- 改善したい最初のドラフトプロンプト

もし前提に満たない場合は [成功基準の定義](https://docs.anthropic.com/en/docs/build-with-claude/define-success) や [強力な実証的評価の作成](https://docs.anthropic.com/en/docs/build-with-claude/develop-tests) を読むとよいとのこと。

## プロンプトエンジニアリング手法

プロンプトエンジニアリングの手法がいくつか紹介されており、これらの手法を順番に試すことをお勧めします。
各手法の実際の影響は使用事例によって異なっています。

1. [プロンプトジェネレータ](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prompt-generator)
2. [明確かつ直接的であること](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/be-clear-and-direct)
3. [使用例（マルチショット）](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/multishot-prompting)
4. [クロードに考えさせる（思考の連鎖）](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/chain-of-thought)
5. [XMLタグを使用する](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags)
6. [クロードに役割を与える（システムプロンプト）](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/system-prompts)
7. [クロードの回答を事前に入力する](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prefill-claudes-response)
8. [複雑なプロンプトを連鎖させる](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/chain-complex-prompts)
9. [長いコンテキストのヒント](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/long-context-tips)

### 1. プロンプトジェネレータ

今回は最初にやるべきプロンプトジェネレータを使用してみようと思います。
効果的なプロンプト方法を見つけるため、最初に簡単に質問をするとプロンプトのテンプレートを生成してくれます。

例えば

```
雑誌出版社が書いた文章を校正した内容を提示する
```

のように指示を出すと

```
You are an AI assistant tasked with analyzing and presenting the corrections made to a text originally written by a magazine publisher. Your goal is to clearly show what changes were made during the proofreading process.

Here is the original text:
<original_text>
{{ORIGINAL_TEXT}}
</original_text>

Here is the corrected text:
<corrected_text>
{{CORRECTED_TEXT}}
</corrected_text>

Compare the original text with the corrected text and identify all changes made during the proofreading process. These changes may include corrections to grammar, spelling, punctuation, word choice, or sentence structure.

Present your findings in the following format:
1. List each correction made, showing the original text and the corrected version.
2. Provide a brief explanation for each correction, stating why the change was likely made.

Use the following structure for each correction:
<correction>
Original: [Insert original text here]
Corrected: [Insert corrected text here]
Explanation: [Provide a brief explanation for the correction]
</correction>

Additional guidelines:
- Present the corrections in the order they appear in the text.
- If a single sentence or paragraph has multiple corrections, group them together.
- For minor changes like punctuation or spelling, you can group several related corrections together if they are in close proximity.
- If no changes were made to the original text, state that no corrections were necessary.

Begin your analysis with an introductory sentence, and end with a brief summary of the types of corrections made. Present your entire response within <analysis> tags.
```

のようなテンプレートを生成してくれました。
私のような初学者にはすごいありがたい機能、かつ Claude を初めて使って XML で指示するのになれていないときとかすごい便利に感じました。

次回以降は生成されたテンプレートをどうブラッシュアップしていくかを考えていければと思います。
