---
title: "LangChain を使用してヘルプセンターをスクレイピングしてみる"
emoji: "🤖"
type: "tech"
topics: ["AI"]
published: true
---

今回は LangChain を使用して [Brushup](https://help.brushup.net/) のヘルプセンターをスプレイピングしてみようと思います。

ヘルプセンターをスクレイピングするために、[SitemapLoader](https://python.langchain.com/v0.1/docs/integrations/document_loaders/sitemap/) を使用したいと思います。
SitemapLoader を使用すると sitemap.xml を自動で解釈して、ページをスクレイピングできます。

Python は事前に入っていることが前提になりますが早速コードは下記になります。

requirements.txt

```txt
langchain-community==0.2.1
lxml==5.2.2
beautifulsoup4==4.12.3
tqdm==4.66.4
```

index.py

```python
from langchain_community.document_loaders.sitemap import SitemapLoader

sitemap_loader = SitemapLoader(web_path="https://help.brushup.net/hc/sitemap.xml")

docs = sitemap_loader.load()
print(docs)
```

実行してみるとインジゲーターが表示され sitemap にあるページが取得されることがわかります。
ただ今回のヘルプセンターは zendesk で作成されている関係かすべて
「Just a moment...Enable JavaScript and cookies to continue」
となっていました。

今回は失敗してしまいましたが、javascript で構成されているサイトの場合は [PlaywrightWebBaseLoader](https://js.langchain.com/v0.1/docs/integrations/document_loaders/web_loaders/web_playwright/) を使用するとよさそうなので、次回以降で試してみようと思います。
