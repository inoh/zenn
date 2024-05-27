from langchain_community.document_loaders.sitemap import SitemapLoader

sitemap_loader = SitemapLoader(web_path="https://help.brushup.net/hc/sitemap.xml")

docs = sitemap_loader.load()
print(docs)
