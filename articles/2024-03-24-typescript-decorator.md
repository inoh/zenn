---
title: "Typescript で Decorator を使ってみよう！"
emoji: "🚀"
type: "teck"
topics: ["node"]
published: true
---

Node で Decorator の機能があることをご存知でしょうか？
実は Java や Python でもあるようなアノテーションで書けるんです。
https://www.typescriptlang.org/docs/handbook/decorators.html

早速書いてみましょう。

## 初期ロード

```typescript
const decorate = () => {
  console.log("decorate");
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    console.log('initial')
    target.value = 1
  };
}

class ExampleClass {
  @decorate()
}
```

上記でデコレータを実行すると、、、

```typescript
decorate
initial
```

と表示されます。
実際に定義したクラスを使ってみましょう。

```typescript
const example1 = new ExampleClass()
console.log(example1.value) // => 1
example1.value = 2
console.log(example1.value) // => 2

const example2 = new ExampleClass()
console.log(example2.value) // => 1
```

上記の通り実行してみると、インスタンスごとに初期値が設定され、独立していることが確認できます。
