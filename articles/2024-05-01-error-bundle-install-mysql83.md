---
title: "MySQL が 8.3 になってしまって rails が起動しなくなった"
emoji: "💀"
type: "tech"
topics: ["Ruby"]
published: true
---

意図せず MySQL が 8.0 から 8.3 にあがってしまって、Rails が起動しなくなったので、そのときの対応メモ。

Rails を起動をするとこんなエラーがでたり

```shell
Library not loaded: '/opt/homebrew/opt/mysql/lib/libmysqlclient.22.dylib'
```

mysql2 の gem を入れ直そうと bundle install でこんなエラーが出始めた。

```shell
client.c:1438:3: error: implicit declaration of function 'mysql_ssl_set' is invalid in C99 [-Werror,-Wimplicit-function-declaration]
```

色々ネットを探していると MySQL を 8.3 にあげたけど mysql-client が 8.3 だとうまくいかないらしい。
https://github.com/brianmario/mysql2/issues/1346#issuecomment-1925565106
なので mysql-client だけバージョンを下げてみました。


```shell
brew uninstall mysql-client
brew install mysql-client@8.0
bundle config --local build.mysql2 -- --with-mysql-dir=$(brew --prefix mysql-client@8.0)
bundle install
```

これでいちを mysql2 もインストールできて、Rails も無事起動できたとさ。
しばらくは mysql-client のバージョンが上がるのを待つしかないのかな？
