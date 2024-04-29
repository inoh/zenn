---
title: "PHP Composer を使って Cake PHP を動かしてみる"
emoji: "🎼"
type: "tech"
topics: ["PHP"]
published: true
---

Composer を使用して Cake PHP を動かしてみたいと思います。

## まずは動かしてみる

### Composer インストール

まずは [Composer](https://getcomposer.org/download/) をインストールします。

```bash
php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
php -r "if (hash_file('sha384', 'composer-setup.php') === 'dac665fdc30fdd8ec78b38b9800061b4150413ff2e3b6f88543c636f7cd84f6db9189d43a81e5503cda447da73c7e5b6') { echo 'Installer verified'; } else { echo 'Installer corrupt'; unlink('composer-setup.php'); } echo PHP_EOL;"
php composer-setup.php
php -r "unlink('composer-setup.php');"
```

### Cake PHP インストール

※ 2024/4/29 時点で v5 の CakePHP が出ていますが、v5 の公式ドキュメントがまだ v4 になっていたため、v4 のインストールで進めます

```bash
php composer.phar create-project --prefer-dist cakephp/app:"4.*" hello-cake
```

### サーバー起動

最後はサーバーを起動してみます。

```bash
cd hello-cake
bin/cake server
```

http://localhost:8765/ にアクセスすると Welcome ページが表示されます。

今後はこの composer.phar を使ってインストールするため bin フォルダに移動しておきます。

```
mv composer.phar hello-cake/bin/composer
```

## パッケージを追加する

パッケージを追加する場合は、コマンドラインからインストールすることができます。

### aws-sdk をインストールしてみる

パッケージを追加する場合は `bin/composer require` を使用します。

```bash
bin/composer require aws/aws-sdk-php
```

### 確認する

確認するために psysh をインストールして REPL を起動します。

```bash
bin/composer require psy/psysh:@stable
vendor/bin/psysh
```

下記のコードを実行します。
※ AWS の設定がデフォルトで設定されている前提になっています

```php
require 'vendor/autoload.php';

use Aws\S3\S3Client;

$s3Client = new S3Client([]);

$buckets = $s3Client->listBuckets();
foreach ($buckets['Buckets'] as $bucket) {
    echo $bucket['Name'] . "\n";
}
```

コンソールにバッケットが表示されることが確認できます。
