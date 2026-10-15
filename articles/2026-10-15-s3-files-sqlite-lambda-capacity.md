---
title: "S3 Files に SQLite を置いた Lambda はどこまで耐えるか — 天井・コストと代替案の比較"
emoji: "🪣"
type: "tech"
topics: ["aws", "lambda", "sqlite", "htmx", "serverless"]
published: true
---

## はじめに

ここ1〜2年、AWS で「とりあえず立ち上げるだけなら一瞬」というサービスが目に見えて増えています。公式の発表で日付を確認できたものだけでも、次のとおりです。

| 時期 | サービス | 何が手軽になったか |
|---|---|---|
| 2024-11 | [Aurora Serverless v2 の 0 ACU 対応](https://aws.amazon.com/about-aws/whats-new/2024/11/amazon-aurora-serverless-v2-scaling-zero-capacity/) | 使っていない間は自動で一時停止する |
| 2025-10 | [Amazon Bedrock AgentCore GA](https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available) | AI エージェントの実行基盤をインフラ管理なしで使える |
| 2025-11 | [Amazon ECS Express Mode](https://aws.amazon.com/about-aws/whats-new/2025/11/announcing-amazon-ecs-express-mode/) | コンテナイメージを渡すだけで URL・ALB・スケーリングまで用意される |
| 2025-12 | [Amazon S3 Vectors GA](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-s3-vectors-generally-available/) | S3 にベクトルを置いてそのまま検索できる |
| 2026-04 | [Lambda × Amazon S3 Files](https://aws.amazon.com/about-aws/whats-new/2026/04/aws-lambda-amazon-s3/) | S3 バケットを Lambda にファイルシステムとしてマウントできる |

「サーバーレス化・従量課金化」自体は Lambda（2014年）以来の AWS の一貫した方向性で、生成 AI が始めた流れではありません。ただ、S3 Files の発表文が「エージェントがメモリを永続化し、パイプラインの段階間で状態を共有する」用途を挙げているように、**AI エージェント向けの用途を前面に出した手軽なサービス**が増えているのは確かだと思います。さらに CDK や Terraform を AI に書かせれば、面倒な構成でも数分で揃います。「手軽になった」という感覚は、サービス側と作業側の両方から来ているのでしょう。

そこで気になったのが、この組み合わせです。

- 画面は **htmx** でサーバーから HTML 断片を返す
- サーバーは **Lambda**
- DB は **SQLite** のファイルを **S3 Files** に置く

DB サーバーを持たず、全部従量課金で、構成も単純です。ではこの構成で、ウェブサービスはどこまで耐えるのでしょうか。

本記事では、**AWS 公式ドキュメントの仕様**と **AWS Price List API から取得した公式単価**をもとに、性能の天井とコストを見積もります。あわせて Aurora DSQL・DynamoDB・「1台 SQLite + Litestream」と比較します。

:::message
本記事では負荷試験を行っていません。性能の天井は仕様からの**推論**、コストは公式単価と明示した仮定からの**試算**です。推論や仮定の箇所はその都度書いています。
:::

## 先に結論

- 動かすことはできます。ただし天井を決めるのは Lambda ではなく、**NFS 越しの SQLite で書き込みが同時に1つしかできないこと**です。
- コストは Lambda 代より、**S3 Files の「1操作 32KiB 最低課金」**と、**DB ファイルの S3 バージョンが増え続けること**が先に効いてきます。
- 本番のウェブサービスなら、サーバーレスのままにしたいときは **Aurora DSQL か DynamoDB**、SQLite を活かしたいときは **Lambda をやめて1台 + Litestream** がおすすめです。

## S3 Files の仕組みをおさらい

S3 Files は、S3 バケット（またはプレフィックス）にひもづく共有ファイルシステムです。公式ドキュメントによると、中身は Amazon EFS ベースで NFSv4.1 / 4.2 に対応しています。

https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-files.html

SQLite を載せるうえで押さえたいのは、次の**2層構造**です。

```
Lambda ──NFS(2049)──▶ 高性能ストレージ層（低レイテンシ・課金対象）
                            │  約60秒、書き込みが止まったら export
                            ▼
                        S3 バケット（正のデータ・バージョニング必須）
```

- **書き込みはまず高性能ストレージに入り、その時点で永続化されます。** ドキュメントには "Writes go to the high-performance storage and are durable immediately." とあります。
- **S3 への反映（export）は、書き込みが約60秒止まってから**行われます。30秒おきに5分間追記し続けた場合、export が始まるのは6分目、という例が載っています。
- **S3 バケットのバージョニングが必須です。** 変更は新しいオブジェクトバージョンとして書き戻されます。
- **読み取りは2経路あります。** 小さいファイル（初期値 128KiB 未満）は高性能ストレージから低レイテンシで返ります。閾値を超えるファイルや 1MiB 以上の大きな読み取りは、S3 から直接ストリームされます。
- **競合時は S3 側が正になります。** S3 の API で同じオブジェクトを書き換えると、ファイルシステム側の変更は lost+found ディレクトリに移されます。

Lambda から使うには、関数をマウントターゲットと同じ VPC に置き、NFS（TCP 2049）を通すセキュリティグループが必要です。

https://docs.aws.amazon.com/lambda/latest/dg/configuration-filesystem-s3files.html

## SQLite を載せるときの前提

### WAL モードは使えない

SQLite 公式は、ネットワークファイルシステム上での利用をそもそも推奨していません。

https://sqlite.org/useovernet.html

特に効くのが WAL モードです。WAL は複数プロセスが共有メモリを使う仕組みのため、同じホスト上のプロセスからしか使えず、ネットワークファイルシステムでは動かないと明記されています。

https://sqlite.org/wal.html

Lambda の実行環境はそれぞれ別ホストなので、WAL は使えず、**rollback journal モード（DELETE / TRUNCATE / PERSIST）**になります。rollback journal では、書き込みのコミット中は読み取りもブロックされます。

### ロックは advisory、1ファイル512個まで

S3 Files はファイルロックに対応しています。ただし制限一覧には、次のような記載があります。

- ロックはすべて advisory（Mandatory locking は非対応）
- **1ファイルあたりのロックは、接続している全インスタンス合計で 512 まで**
- 1マウントあたり 8,192 ロック、1ファイルシステムあたり接続 25,000 まで

https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-files-quotas.html

SQLite は読み取り中も共有ロックを取ります。同時に動く Lambda 実行環境が DB ファイルにロックをかけるので、**512 という上限が同時実行数の天井になりうる**点は覚えておきたいところです。何同時実行で当たるかは未検証です。

## 天井の見立て（推論）

ここからは仕様と既存の実測値から推論した見立てです。

### 参考になる実測値

- **S3 Files 単体（Lambda）**: [Ryotaro Harada 氏の計測](https://builder.aws.com/content/2zfBu6Br5Z46ZaFsNrGfPtswmsX/testing-read-and-write-performance-with-s3-files-from-aws-lambda)（2026-07、東京、512MB、arm64）では、64KiB の読み取りが p50 2.0ms、書き込みが p50 13.4ms でした。
- **SQLite on EFS（Lambda）**: S3 Files 以前からある構成で、[2020年の検証記事](https://www.lambrospetrou.com/articles/aws-lambda-and-sqlite-over-efs/)では、テスト一式でローカル 30〜40ms に対して Lambda + EFS が約140ms でした。書き込みが1つずつしかできないことがボトルネックになる、という結論です。

### 見立て

| 観点 | 天井を決めるもの | 目安（推論） |
|---|---|---|
| 書き込み | 書き込みは1つずつ × rollback journal × NFS 上の fsync | 1件が数十ms かかるなら、**秒間数十件程度**で頭打ち |
| 読み取り | 1回 ms 級の NFS 読み取り × ロック取得 | 読み取り中心なら秒間数百〜数千件。ただし 512 ロックの壁がある |
| ファイルシステムの上限 | 書き込み 50,000 IOPS / 読み取り 250,000 IOPS（1ファイルシステムあたり） | SQLite の書き込みの1本道より先に当たることはまずない |

htmx は、ページ全体ではなく HTML 断片を返すリクエストを細かく飛ばす作りなので、**1画面あたりのリクエスト数は増えがち**です。読み取りが多い管理画面や社内ツールなら問題になりにくいですが、「いいね」や「既読」のように細かい書き込みを多発する UI だと、書き込みの1本道にすぐ当たります。

### 128KiB の閾値の罠

S3 Files は、`sizeLessThan`（初期値 128KiB）より大きいファイルのデータを高性能ストレージに自動では取り込まず、**S3 から直接読みます**。SQLite の DB ファイルはすぐ 128KiB を超えるので、初期設定のままだと、SQLite のページ読み取りが S3 からの直接読み取りに回る可能性があります。そうなると、1回数十ms のレイテンシと S3 GET の課金がかかります。

`sizeLessThan` は最大 48TiB まで上げられるので、**DB ファイルのあるプレフィックスだけ閾値を DB サイズより大きくする**インポートルールを作っておくのが安全です。

https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-files-synchronization-customizing.html

| prefix | trigger | sizeLessThan |
|---|---|---|
| `""`（ルート、必須） | `ON_FILE_ACCESS` | 131,072（128KiB、初期値のまま） |
| `db/` | `ON_FILE_ACCESS` | 10,737,418,240（10GiB） |

（`db/` 配下だけ 10GiB 未満のファイルを取り込む設定例です。インポートルールはコンソールか `PutSynchronizationConfiguration` API で設定します。）

なお Lambda では、メモリ 512MB 以上の関数で S3 からの直接読み取り（`DirectS3Read: AUTO`）が初期値で有効になります。

## コスト試算

### 公式単価（東京リージョン）

AWS Price List API（`https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/{サービス}/current/ap-northeast-1/index.json`）から取得した単価です（2026年9〜10月公開分）。

| 項目 | 単価 |
|---|---|
| S3 Files 高性能ストレージ | $0.36 / GB-月 |
| S3 Files 読み取り | $0.04 / GB |
| S3 Files 書き込み | $0.07 / GB |
| S3 Standard ストレージ | $0.025 / GB-月 |
| Lambda リクエスト | $0.20 / 100万件 |
| Lambda 実行時間（arm64） | $0.0000133334 / GB-秒 |

ちなみに、同じ Price List で比べると、この S3 Files の3つの単価は **EFS Standard と EFS Elastic Throughput（読み取り / 書き込み）の単価とまったく同じ**でした。

### 課金の要点：1操作あたり 32KiB の最低課金

課金の仕組みのドキュメントを読むと、効いてくるのは次の点です。

https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-files-metering.html

- 高性能ストレージへの読み書きは、**1操作あたり最低 32KiB** として課金される
- メタデータ操作（ファイル作成・削除・リネーム・`fsync` など）は最低 4KiB として課金される
- S3 への export は、高性能ストレージからの読み取り＋S3 PUT として課金される

SQLite のページは初期値 4KiB です。つまり**4KiB のページを1枚読むだけで 32KiB 分の課金**になります。

### 100万リクエストあたりの試算

仮定は次のとおりです。

- Lambda：arm64、512MB、平均 50ms
- 読み取りリクエスト：S3 Files への読み取り 6回（ヘッダー確認＋ページ5枚）×（32KiB＋メタデータ 4KiB）
- 書き込みトランザクション：journal 作成・書き込み・DB ページ 2枚・fsync 2回・journal 削除で、計約 112KiB

| 項目 | 100万件あたり |
|---|---|
| Lambda（リクエスト＋実行時間） | **約 $0.53** |
| S3 Files 読み取り（読み取りリクエスト） | **約 $8.2** |
| S3 Files 書き込み（書き込みトランザクション） | **約 $7.5** |

**S3 Files のアクセス料金が Lambda 代の10倍以上**になる、という逆転が起きます。ただし、Linux の NFS クライアントのページキャッシュが効けば読み取りの課金は減ります。逆に、ロックを取るたびにキャッシュが無効化されるなら、この試算に近づきます。ここは実測が必要です。

### もう一つの罠：DB ファイルのバージョンが増え続ける

S3 Files は、書き込みが60秒止まるたびに、変更されたファイルを S3 に**新しいバージョンとして**書き戻します。バージョニングは必須なので、古いバージョンは残り続けます。

| DB サイズ | 1日24回 export された場合の旧バージョン（30日） | S3 Standard 料金 |
|---|---|---|
| 100MB | 約 72GB | 約 $1.8 / 月 |
| 1GB | 約 720GB | 約 $18 / 月 |
| 10GB | 約 7.2TB | 約 $180 / 月 |

「昼は数分おきに書き込みがあり、合間に1分以上の静かな時間ができる」程度のトラフィックで、簡単に起きる数字です。高性能ストレージ料金（1GB で $0.36 / 月）より、こちらのほうがずっと大きくなります。**S3 ライフサイクルルールで `NoncurrentVersionExpiration` を設定するのは必須**と考えてください。

逆に、書き込みが途切れずに続く DB は、60秒の空白ができないため **S3 への export が始まらない**ことになります。高性能ストレージ上では永続化されていますが、「S3 にバックアップがある」状態にはなりません。

## 代替案との比較

では、Lambda + htmx の永続化層として、ほかに何があるでしょうか。

| 案 | 向いているケース | 東京の単価 | 弱いところ |
|---|---|---|---|
| **S3 Files + SQLite** | 書き込みがまれ・DB が小さい個人ツール | 前述のとおり | 書き込みは1つずつ、32KiB 最低課金、バージョン増殖 |
| **Aurora DSQL** | SQL を使いたい、サーバーレスのままにしたい | $0.00001 / DPU、ストレージ $0.40 / GB-月（毎月 10万 DPU・1GB まで無料） | 1トランザクションで変更できるのは3,000行まで、楽観ロックのためリトライ実装が必要 |
| **DynamoDB オンデマンド** | 安く、どこまでも伸ばしたい | 読み取り $0.1425 / 100万 RRU、書き込み $0.715 / 100万 WRU、ストレージ $0.285 / GB-月 | SQL・JOIN がなく、アクセスパターンを先に設計する必要がある |
| **1台 SQLite + Litestream** | SQLite の性能と単純さを活かしたい | 小さいサーバー1台＋S3 代 | Lambda をやめることになる。基本1台なので可用性は復旧の速さで補う |
| **読み取り専用 SQLite ＋ 書き込みは別 DB** | ほぼ読み取りだけのコンテンツサイト | 読み取りはほぼ Lambda 代だけ | 書いた内容がすぐ反映されない。データ同期の仕組みが必要 |

### Aurora DSQL：サーバーレスのまま SQL を使いたいなら

Aurora DSQL は、PostgreSQL 16 互換のサーバーレス分散 SQL データベースで、東京リージョンでも使えます。

https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html

- 接続は IAM で発行する一時的な認証トークンで行い、パスワード管理が要りません
- ロックで待たせるのではなく、コミット時に競合を検出する**楽観的同時実行制御**です。競合するとシリアライゼーションエラーが返るので、アプリ側でリトライします
- 分離レベルは Repeatable Read 固定、1トランザクションで変更できるのは3,000行まで、PL/pgSQL・トリガー・一時テーブルは非対応です

課金単位の DPU は、SQL の実行・読み取り・書き込みにかかった処理量を表します。[料金ページ](https://aws.amazon.com/rds/aurora/dsql/pricing/)には「無料枠の 10万 DPU が、TPC-C で約70万トランザクション相当だった」という AWS の計測例が載っています。単純に割ると 1トランザクションあたり約 0.14 DPU で、東京の単価なら **100万トランザクションで約 $1.4** の計算です。TPC-C は比較的軽いトランザクションなので、実際のクエリでは上下すると考えてください。

**SQLite の「書き込みは1つずつ」がなくなり、S3 Files の VPC・マウント・32KiB 課金の悩みも消える**ので、今回の構成に一番近い代替案だと思います。

### DynamoDB：最安で伸ばしたいなら

DynamoDB オンデマンドは、強い整合性の読み取りが 4KB ごとに 1 RRU、結果整合性の読み取りが 0.5 RRU、標準の書き込みが 1KB ごとに 1 WRU です。

https://aws.amazon.com/dynamodb/pricing/on-demand/

1KB 以下の書き込みなら **100万件で $0.715**、4KB 以下の強い整合性の読み取りなら **100万件で約 $0.14** です。先ほどの S3 Files の試算（読み取りだけで100万件あたり約 $8）よりかなり安くなります。そのかわり、SQL も JOIN もないので、画面ごとのアクセスパターンからテーブル設計を逆算する必要があります。

### 1台 SQLite + Litestream：SQLite を活かしたいなら

SQLite は本来、アプリとデータが同じマシンにある前提で設計されています。それなら、Lambda をやめて**小さなサーバー1台**にアプリと SQLite を同居させるのが一番素直です。

- ローカルディスクなので **WAL モード**が使え、読み取りと書き込みが互いにブロックしません
- [Litestream](https://litestream.io/)（現行 v0.5 系）は、アプリとは別のプロセスとして SQLite の変更を S3 などに流し続けるレプリケーションツールです。アプリのコードを変えずにバックアップと復旧の仕組みを足せます
- htmx はサーバー側で HTML を描画するモノリスと相性がよく、「1台の Web サーバー + SQLite + htmx」は構成としてとても単純です

冒頭で挙げた ECS Express Mode のように、コンテナを渡すだけで動く選択肢も増えています。ただ、ECS で SQLite を使う場合は、タスクのローカルディスクが消えうる前提で Litestream からの復元手順まで設計しておく必要があります。

## どれを選ぶか

```
書き込みはまれ？ DB は小さい？ 個人ツール？
  └─ Yes → S3 Files + SQLite でも可（閾値設定とライフサイクルルールを忘れずに）
  └─ No
      ├─ サーバーレスは譲れない
      │   ├─ SQL・JOIN が欲しい → Aurora DSQL
      │   └─ アクセスパターンが決まっている → DynamoDB
      └─ サーバー1台でもよい → SQLite（WAL）+ Litestream
```

## 未検証の項目

本記事では次の点を実測していません。

- S3 Files 上で rollback journal（DELETE / TRUNCATE / PERSIST）の SQLite を動かしたときの、実際の書き込みレイテンシと長時間動かしたときの安定性
- Lambda 上の NFS クライアントキャッシュがどこまで効くか（課金額に直結します）
- 512 ロック上限に、同時実行数いくつで当たるか
- 一部だけ変わった DB ファイルを export するとき、全体を PUT するのか、変わった部分だけで済むのか（ドキュメントで確認できたのは「追記」時に `UploadPartCopy` を使うという例だけです）
- Aurora DSQL の、実際のアプリのクエリでの DPU 消費量

## まとめ

- S3 Files で、Lambda からも SQLite ファイルを「普通のファイル」として扱えるようになりました。ただ、中身は EFS ベースの NFS なので、**WAL が使えず、書き込みが1つずつしかできない**という SQLite on EFS 時代と同じ天井があります。
- コスト面では、**1操作 32KiB の最低課金**で Lambda 代を上回りやすく、さらに**60秒ごとの export で DB ファイルの旧バージョンが増え続ける**点に注意が必要です。
- 本番のウェブサービスなら、サーバーレスのまま行きたいときは Aurora DSQL か DynamoDB、SQLite を活かしたいときは1台 + Litestream のほうが、性能・コスト・運用のバランスがよいと考えます。

「手軽に立ち上がる」サービスは増えましたが、「手軽に運用できる・安い」とは限りません。新しいサービスを組み合わせるときこそ、課金の仕組みと制限一覧のページまで読んでおくのがおすすめです。
