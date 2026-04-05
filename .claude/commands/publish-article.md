---
name: publish-article
description: Zennに新しい技術記事を作成して投稿する
arguments:
  - name: topic
    description: 記事のテーマや内容の概要
    required: true
---

Zennの技術記事を作成してください。

## 手順

### 1. 記事の企画

ユーザーが指定したテーマ「$ARGUMENTS.topic」について、以下を決定してください：

- **タイトル**: 具体的で検索されやすいタイトル
- **emoji**: 記事の内容に合った絵文字1つ
- **topics**: 関連する技術タグ（最大5つ、小文字英数字）
- **スラッグ**: `YYYY-MM-DD-slug-name` 形式（今日の日付を使用）

企画内容をユーザーに提示し、承認を得てから次のステップに進んでください。

### 2. 記事の執筆

以下のフォーマットで記事ファイルを作成してください：

**ファイルパス**: `articles/{スラッグ}.md`

```markdown
---
title: "タイトル"
emoji: "絵文字"
type: "tech"
topics: ["topic1", "topic2"]
published: false
---

## はじめに

（導入文）

## 本文セクション

（内容）

## まとめ

（まとめ）
```

執筆のガイドライン：
- 実践的で具体的なコード例を含める
- ハマりどころや注意点を共有する
- 読者が再現できるように手順を明確に書く
- 見出しで構造化し、読みやすくする

### 3. レビューと公開

記事を書き終えたら、ユーザーに内容を確認してもらいます。

- 修正が必要な場合は対応する
- ユーザーの承認後、frontmatterの `published: false` を `published: true` に変更する
- git commitを作成する（コミットメッセージ例: `Zennに「{タイトル}」の記事を追加`）

### 4. デプロイ

ユーザーに確認の上、以下を実行：
```bash
git push origin main
```

Zenn連携により、mainブランチへのpushで自動的に記事が公開されます。
