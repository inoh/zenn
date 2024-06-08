---
title: "AWS SDK のドキュメントをデータベースにしてみたよ"
emoji: "📜"
type: "tech"
topics: ["AWS", "AI"]
published: true
---
今回は AWS SDK の MediaConvert のドキュメントをスクレイピングしてみました。
スクレイピングしたデータは加工して ChromeDB に保存しています。

## データベース作成

AWS のドキュメントには sitemap があるため、そこから url を抜き出してスクレイピングしています。

事前に必要なパッケージをインストールします。

```
requests==2.32.3
beautifulsoup4==4.12.3
lxml==5.2.2
langchain==0.2.3
langchain-community==0.2.3
langchain-chroma==0.1.1
langchain-text-splitters==0.2.1
langchain-huggingface==0.0.3
sentencepiece==0.2.0
sentence-transformers==3.0.1
```

スクレイピングするプログラムです。

```python
import requests
from bs4 import BeautifulSoup
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import HTMLHeaderTextSplitter

embedding_function = HuggingFaceEmbeddings(
    model_name="oshizo/sbert-jsnli-luke-japanese-base-lite",
)

def scrape_awsdocs():
    # 日本語ドキュメント
    sitemap = requests.get('https://docs.aws.amazon.com/ja_jp/mediaconvert/latest/ug/sitemap.xml').text
    # 英語ドキュメント
    # sitemap = requests.get('https://docs.aws.amazon.com/en_us/mediaconvert/latest/ug/sitemap.xml').text
    soup = BeautifulSoup(sitemap, 'xml')
    urls = [url.find('loc').string.strip() for url in soup.find_all('url')]

    splitter = HTMLHeaderTextSplitter(
        headers_to_split_on=[
            ("h1", "Header 1"),
            ("h2", "Header 2"),
            ("h3", "Header 3"),
        ]
    )

    texts = []
    for url in urls:
        print(f"Now scraping... {url}")
        response = requests.get(url)
        response.encoding = 'utf-8'
        html = BeautifulSoup(response.text, 'html.parser')
        main = html.find(id="main")
        texts.extend(splitter.split_text(str(main)))

    return Chroma.from_documents(texts, embedding_function, persist_directory="./db/mediaconvert_ja") # 日本語
    # return Chroma.from_documents(texts, embedding_function, persist_directory="./db/mediaconvert_us") # 英語


db = scrape_awsdocs()
# 2 回目以降はロードするだけでよい
# db = Chroma(persist_directory="./db/mediaconvert_ja", embedding_function=embedding_function)
```

## 検索してみる
作成した ChromaDB から検索してみます。

まずは日本語

```python
db = Chroma(persist_directory="./db/mediaconvert_ja", embedding_function=embedding_function)

result = db.similarity_search("Role", k=10)
for val in result:
    print("---")
    print(val.page_content)
```

結果

```
---
AWSドキュメントMediaConvertユーザーガイド  
AWS Elemental の高速トランスコード JSON ジョブの例 MediaConvert{ "Role": "arn:aws:iam::123456789012:role/MediaConvert_Role", "AccelerationSettings" : { "Mode" : "ENABLED" }, "UserMetadata": { "job" : "Acceleration" }, "Settings": { "TimecodeConfig": { "Source": "ZEROBASED" }, "OutputGroups": [ { "Name": "File Group", "Outputs": [ { "ContainerSettings": { "Container": "MP4", "Mp4Settings": { "CslgAtom": "EXCLUDE", "FreeSpaceBox": "EXCLUDE", "MoovPlacement": "NORMAL" } }, "VideoDescription": { "Width": 1280, "ScalingBehavior": "DEFAULT", "Height": 720, "VideoPreprocessors": { "TimecodeBurnin": { "FontSize": 32, "Position": "TOP_CENTER" } }, "TimecodeInsertion": "DISABLED", "AntiAlias": "ENABLED", "Sharpness": 50, "CodecSettings": { "Codec": "H_265", "H265Settings": { "InterlaceMode": "PROGRESSIVE", "ParNumerator": 1, "NumberReferenceFrames": 3, "FramerateDenominator": 1001, "GopClosedCadence": 1, "AlternateTransferFunctionSei": "DISABLED", "HrdBufferInitialFillPercentage": 90, "GopSize": 48, "Slices": 4, "GopBReference": "ENABLED", "HrdBufferSize": 20000000, "SlowPal": "DISABLED", "ParDenominator": 1, "SpatialAdaptiveQuantization": "ENABLED", "TemporalAdaptiveQuantization": "ENABLED", "FlickerAdaptiveQuantization": "DISABLED", "Bitrate": 10000000, "FramerateControl": "INITIALIZE_FROM_SOURCE", "RateControlMode": "CBR", "CodecProfile": "MAIN_MAIN", "Tiles": "ENABLED", "Telecine": "NONE", "FramerateNumerator": 24000, "MinIInterval": 0, "AdaptiveQuantization": "HIGH", "CodecLevel": "LEVEL_5", "SceneChangeDetect": "ENABLED", "QualityTuningLevel": "SINGLE_PASS_HQ", "FramerateConversionAlgorithm": "DUPLICATE_DROP", "UnregisteredSeiTimecode": "DISABLED", "GopSizeUnits": "FRAMES", "ParControl": "SPECIFIED", "NumberBFramesBetweenReferenceFrames": 3, "TemporalIds": "DISABLED", "SampleAdaptiveOffsetFilterMode": "ADAPTIVE" } }, "AfdSignaling": "NONE", "DropFrameTimecode": "ENABLED", "RespondToAfd": "NONE", "ColorMetadata": "INSERT" }, "AudioDescriptions": [ { "AudioTypeControl": "FOLLOW_INPUT", "CodecSettings": { "Codec": "AAC", "AacSettings": { "AudioDescriptionBroadcasterMix": "NORMAL", "Bitrate": 160000, "RateControlMode": "CBR", "CodecProfile": "LC", "CodingMode": "CODING_MODE_2_0", "RawFormat": "NONE", "SampleRate": 48000, "Specification": "MPEG4" } }, "LanguageCodeControl": "FOLLOW_INPUT", "AudioType": 0 } ], "Extension": "mp4", "NameModifier": "1280x720" } ], "OutputGroupSettings": { "Type": "FILE_GROUP_SETTINGS", "FileGroupSettings": { "Destination": "s3://mediaconvert-outputs/accelerated/" } } } ], "AdAvailOffset": 0, "Inputs": [ { "InputClippings": [ { "EndTimecode": "01:00:00:00", "StartTimecode": "00:00:00:00" } ], "AudioSelectors": { "Audio Selector 1": { "Offset": 0, "DefaultSelection": "DEFAULT", "ProgramSelection": 1 } }, "VideoSelector": { "ColorSpace": "FOLLOW" }, "FilterEnable": "AUTO", "PsiControl": "USE_PSI", "FilterStrength": 0, "DeblockFilter": "DISABLED", "DenoiseFilter": "DISABLED", "TimecodeSource": "ZEROBASED", "FileInput": "s3://mediaconvert-inputs/SampleVideo_h264_StereoAudio.mp4" } ] } }  
翻訳は機械翻訳により提供されています。提供された翻訳内容と英語版の間で齟齬、不一致または矛盾がある場合、英語版が優先します。
---
AWSドキュメントMediaConvertユーザーガイド  
複数キューとパフォーマンステストオンデマンドキューでのトランスコードの支払い方法 オンデマンドキューを作成するオンデマンドキューを一時停止または再有効化オンデマンドキューのリストオンデマンドキューを削除  
AWS Elemental でのオンデマンドキューの使用 MediaConvert リソースの管理とパフォーマンスのテスト リソース割り当てとジョブ優先度付け パフォーマンステスト オンデマンドキューでのトランスコードの支払い方法 オンデマンドキューを作成する Console AWS CLI aws mediaconvert create-queue \ --region region-name-1 \ --name Queue1 \ --description "Example queue description." \ --tags "KeyName1=string1,KeyName2=string2" オンデマンドキューを一時停止または再有効化 Console AWS CLI aws mediaconvert update-queue \ --name Queue1 \ --status PAUSED aws mediaconvert update-queue \ --name Queue1 \ --status ACTIVE オンデマンドキューの一覧表示 Console AWS CLI aws mediaconvert list-queues { "Queues": [ { "Arn": "arn:aws:mediaconvert:us-west-2:111122223333:queues/Example", "CreatedAt": "2023-06-19T09:34:25-07:00", "LastUpdated": "2023-06-19T09:34:25-07:00", "Name": "Example", "PricingPlan": "ON_DEMAND", "ProgressingJobsCount": 0, "Status": "ACTIVE", "SubmittedJobsCount": 0, "Type": "CUSTOM" }, { "Arn": "arn:aws:mediaconvert:us-west-2:111122223333:queues/Default", "CreatedAt": "2018-05-16T09:13:08-07:00", "LastUpdated": "2021-05-14T15:39:23-07:00", "Name": "Default", "PricingPlan": "ON_DEMAND", "ProgressingJobsCount": 0, "Status": "ACTIVE", "SubmittedJobsCount": 0, "Type": "SYSTEM" } ] } オンデマンドキューを削除 Console AWS CLI aws mediaconvert delete-queue \ --name Queue1  
翻訳は機械翻訳により提供されています。提供された翻訳内容と英語版の間で齟齬、不一致または矛盾がある場合、英語版が優先します。
---
AWSドキュメントMediaConvertユーザーガイド  
Dolby Atmos パススルーに対する機能制限  
AWS Elemental MediaConvert で Dolby Atmos パススルーの使用 Dolby Atmos パススルーに対する機能制限  
翻訳は機械翻訳により提供されています。提供された翻訳内容と英語版の間で齟齬、不一致または矛盾がある場合、英語版が優先します。
---
このステップでは、 EventBridge ルールでイベントパターンを指定する方法を示します。このルールは、ジョブのステータスが に変わった MediaConvert ときに によって送信されたイベントをキャプチャしますERROR。  
EventBridge ルールでイベントパターンを設定するには  
{ "source": ["aws.mediaconvert"], "detail-type": ["MediaConvert Job State Change"], "detail": { "status": ["ERROR"] } }  
https://console.aws.amazon.com/events/ で Amazon EventBridge コンソールを開きます。  
ナビゲーションペインで [Rules (ルール)] を選択します。デフォルトのイベントバスを維持し、次に [ルールを作成] を選択します。  
[名前] に「MediaConvertJobStateError」と入力し、[次へ] を選択します。  
[イベントソース] から始まる [イベントパターン] セクションで、以下の設定を選択します。  
イベントソース: AWS services  
AWS サービス： MediaConvert  
イベントタイプ: MediaConvert Job State Change  
イベントタイプ、特定の状態：ERROR  
[イベントパターン] ボックスは以下の例のようになります。  
このコードは、ジョブのステータスが に変わるイベントに一致するイベント EventBridge ルールを定義しますERROR。イベントパターンの詳細については、「Amazon ユーザーガイド」の「イベントとイベントパターン」を参照してください。 CloudWatch  
[次へ] をクリックします。
---
デフォルトのキューはオンデマンドキューです。オンデマンドキューは、AWS Elemental MediaConvert がトランスコーディングリソースをジョブに割り当てる方法と支払い方法がリザーブドキューとは異なります。詳細については、「料金表」を参照してください。MediaConvert このセクションは複数のキューの使用、追加のキューの作成、キューの表示、キューの一時停止と有効化、キューの削除に関するものです。  
トピック  
複数キューとパフォーマンステストオンデマンドキューでのトランスコードの支払い方法 オンデマンドキューを作成するオンデマンドキューを一時停止または再有効化オンデマンドキューのリストオンデマンドキューを削除
---
iam:PassRole アクションを実行する権限がないというエラーが表示された場合は、ポリシーを更新して にロールを渡すことができるようにする必要があります MediaConvert。  
一部の AWS のサービス では、新しいサービスロールまたはサービスにリンクされたロールを作成する代わりに、そのサービスに既存のロールを渡すことができます。そのためには、サービスにロールを渡す権限が必要です。  
次の例のエラーは、 という IAM marymajor ユーザーがコンソールを使用して でアクションを実行しようする場合に発生します MediaConvert。ただし、このアクションをサービスが実行するには、サービスロールから付与された権限が必要です。Mary には、ロールをサービスに渡す権限がありません。  
この場合、Mary のポリシーを更新してメアリーに iam:PassRole アクションの実行を許可する必要があります。  
サポートが必要な場合は、 AWS 管理者にお問い合わせください。サインイン資格情報を提供した担当者が管理者です。
---
次の情報は、 と IAM の使用時に発生する可能性がある一般的な問題の診断 MediaConvert と修正に役立ちます。  
トピック  
でアクションを実行する権限がない MediaConvertiam を実行する権限がありません。PassRole自分の 以外のユーザーに自分の MediaConvert リソース AWS アカウント へのアクセスを許可したい
---
この機能を使用するには、まず Nielsen との関係を築き、クラウドに Nielsen SID/TIC サーバーをセットアップする必要があります。 AWS Nielsen に連絡して SID/TIC サーバーソフトウェアをダウンロードし、WRR ライセンスファイルを生成して、インストールとセットアップの指示を受けてください。インフラストラクチャの仕組みについては、「AWS Elemental がクラウド内のニールセン SID/TIC MediaConvert サーバーとどのように相互作用するか AWS」をご覧ください。  
Nielsen 非線形ウォーターマークを設定するには (コンソール)  
Nielsen SID/TIC サーバーシステムをクラウドにセットアップします。 AWS 詳細については、Nielsen にお問い合わせください。  
ニールセンメタデータの.zip ファイルを格納する Amazon S3 バケットを設定します。 MediaConvertメタデータをこのバケットに書き込みます。  
MediaConvert でのジョブの設定 で説明したように、ジョブの入力と出力を設定します。  
[Create job] (ジョブの作成) ページでは、左の [Job] (ジョブ) ペインで、[Job settings] (ジョブ設定) の [Settings] (設定) を選択します。  
右側の [Partner integrations] (パートナー統合) セクションで、[Nielsen non-linear watermarking] (ニールセン非線形ウォーターマーク) を選択します。  
[Nielsen non-linear watermarking] (Nielsen 非線形ウォーターマーク) を有効にしたときに表示される設定値を指定します。各設定の手順とガイダンスについては、設定ラベルの横にある [Info] (情報) を選択します。  
ページの下部にある [Create] (作成) を選択して、ジョブを実行します。  
メタデータの Amazon S3 バケットにあるデータを、Nielsen の指示に従って転送します。  
Nielsen 非線形ウォーターマーク (API、CLI、および SDK) を設定するには  
API、CLI、または SDK を使用する場合は、JSON ジョブ仕様で関連する設定を指定し、ジョブとともにプログラムで送信します。プログラムによるジョブの送信の詳細については、『AWS Elemental API リファレンス』の入門トピックのいずれかを参照してください。 MediaConvert  
AWS SDK または AWS CLI MediaConvert を使用して AWS Elemental を使い始める  
API を使用して AWS Elemental MediaConvert を使い始める  
MediaConvert コンソールを使用して JSON ジョブ仕様を生成します。コンソールはジョブスキーマに対するインタラクティブなバリデーターとして機能するため、この方法をお勧めします。 MediaConvert 以下の手順で、コンソールを使って JSON ジョブ仕様書を生成します。  
コンソールで、前の手順に従います。  
左側の [Job] (ジョブ) ペインの [Job settings (ジョブ設定)]で、[Show job JSON (ジョブの JSON を表示)] を選択します。  
各設定がジョブ設定構造のどこにあるかなどの追加情報については、AWS Elemental MediaConvert API リファレンスをご覧ください。このリストのリンクは、そのドキュメントの設定に関する情報に移動します。  
Nielsen non-linear watermarking (ニールセン非線形ウォーターマーク) (nielsenNonLinearWatermark)  
Source watermark status (ソースウォーターマークステータス) (sourceWatermarkStatus)  
Watermark types (ウォーターマークのタイプ) (activeWatermarkProcess)  
SID (sourceId)  
[CSID] (cbetSourceId)  
Asset ID (アセット ID) (assetId)  
[Asset name] (アセット名) (assetName)  
Episode ID (エピソード ID) (episodeId)  
TIC server REST endpoint (TIC サーバー REST エンドポイント) (ticServerUrl)  
[ADI file] (ADI ファイル) (adiFilename)  
Metadata destination (メタデータの送信先) (metadataDestination)  
Share TICs across tracks (トラック間でTICを共有する) (uniqueTicPerAudioTrack)
---
AWS Elemental は、トランスコードジョブの実行時に、ジョブの完了を妨げない問題が発生した場合に警告コード MediaConvert を返します。Amazon を使用して EventBridge 、サービスが返す警告コードを追跡できます。詳細については、「 EventBridge で を使用する AWS Elemental MediaConvert」を参照してください。  
この表は、 が返す MediaConvert警告コードの詳細と、考えられる原因と解決策を示しています。  
警告コード メッセージ 詳細 100000 220000 230001 230002 230004 230005 230006 MediaConvert は入力オーディオの一部をデコードできません。 240000 240001 250001 250002 Dolby CBI 入力に対応していないビットレートが含まれています。 270000 MediaConvert は、出力を送信先バケットに書き込むときにAmazon S3 S3 から 503 スローダウンエラーコードを受信しました。  
実行したジョブが最初の送信キューから送信先キューにホップできませんでした。  
実行したジョブが指定した待機時間よりも長い時間、元の送信キューで待機していましたが、新しい送信先キューに移動できませんでした。送信先キューがまだ存在するかどうか確認してください。必要となるアクションはありませんが、完了を予期した時間より長くジョブが実行されることがあります。  
Wait minutes と Destination queue を含むホップの挙動は、[ジョブ管理キューホッピング]設定で操作できます。  
詳細については、API リファレンスの HopDestination を参照してください。  
入力ファイルは切り捨てられます。  
入力ファイルにはデータがないため、出力の所要時間が予想よりも短くなる可能性があります。  
トラブルシューティングを行うには、入力内容に欠落がないかどうかを確認してください。  
入力の色メタデータが欠落しているか不完全です。  
MediaConvert は、入力の色メタデータが欠落しているか不完全なため、入力の色空間をたどれませんでした。カラーメタデータには、カラープライマリ、転送関数、マトリックス係数が含まれます。  
出力の色メタデータが欠落しているか不完全な可能性があり、これによりプレーヤーがビデオコンテンツを不完全に表示する原因になります。  
出力 Color space conversionで を指定した場合Color corrector、 MediaConvert は色空間を変換できず、不正確な色メタデータが書き込まれた可能性があることに注意してください。  
解決するには、入力の Color space を指定し、Color space usage を Force に設定します。  
詳細については、API リファレンスの ColorSpace を参照してください。  
MediaConvert は入力にオーディオ継続時間補正を適用できません。  
入力ファイルコンテナのオーディオトラックの'stts' time-to-sample テーブルに問題があり、オーディオ時間補正を適用 MediaConvert できません。  
オーディオ継続時間補正に関する詳細については、「API リファレンス」を参照してください。  
オーディオとビデオの同期に関する問題がないか、出力を確認してください。  
入力の 'mdhd' メディアヘッダー Atom の情報に欠落があります。  
入力の'mdhd'メディアヘッダーアトムが不完全であるか、データがありません。 は、ア'mdhd'トムが 32 バイトまたは 20 バイトであると MediaConvert 想定します。  
MediaConvert は入力を正しく読み取れない可能性があります。ファイルの総所要時間と言語コード (該当する場合) を含む、出力の正確さと品質を確認してください。  
MediaConvert は、入力で色サンプル範囲メタデータを見つけることができません。  
MediaConvert は、入力の色サンプル範囲メタデータが欠落しているか不完全であるため、入力の色サンプル範囲をフォローできませんでした。  
出力の色サンプル範囲メタデータが欠落しているか不正確な可能性があり、それがプレーヤーがビデオコンテンツを正確に表示できない原因になっています。  
出力Color corrector で Color space conversion または Sample range conversion を指定すると、出力のサンプル範囲が不正確になる可能性があるという点にご留意ください。  
解決するには、入力の Sample range を指定します。  
詳細については、API リファレンスの SampleRange を参照してください。  
入力のファイル構造またはオーディオストリームに問題があります。  
入力に破損やその他のオーディオエンコードの問題がないか確認します。  
出力にデコード MediaConvert できないオーディオコンテンツがない可能性があります。  
MediaConvert は、オーディオとビデオの同期を維持するために、少なくとも 100 ミリ秒のオーディオサイレンスを追加しました。  
入力オーディオトラックに欠落、破損、または予期しないデータが含まれています。オーディオとビデオの同期に関する問題がないか、出力を確認してください。  
MediaConvert は、オーディオとビデオを整列させるために、少なくとも 100 ミリ秒のオーディオを削除しました。  
オーディオとビデオの同期に関する問題がないか、出力を確認してください。  
入力のキャプションにサポートされていないフォントが含まれています。  
サポートされていないフォントの付いた入力キャプションを送信しました。 MediaConvert は代わりに汎用フォントを使用します。  
サポートされていないビットレートでDolby CBI入力を送信しました。 は、サポートされるビットレートに増加 MediaConvert します。  
DOLBY CBI 入力を生成するアプリケーションが最新版かどうかを確認してください。  
MediaConvert が出力ファイルをレプリケート先バケットに書き込んでいる間に、Amazon S3 によってスロットリングされました。ジョブが停止するか、想定より完了に時間がかかる可能性があります。  
Amazon S3 へのリクエストレート制限を超過したときには 503 Slow Down エラー応答を受信します。同時にリクエストを行ってジョブを制限する原因となっている他のアプリケーションがないか、確認してください。  
詳細については、「Amazon S3 のトラブルシューティング」を参照してください。
---
IAM ロールは、特定のアクセス許可 AWS アカウント を持つ 内のアイデンティティです。これは IAM ユーザーに似ていますが、特定のユーザーには関連付けられていません。ロール を切り替える AWS Management Console ことで、 で IAM ロールを一時的に引き受けることができます。ロールを引き受けるには、 または AWS API AWS CLI オペレーションを呼び出すか、カスタム URL を使用します。ロールを使用する方法の詳細については、「IAM ユーザーガイド」の「IAM ロールの使用」を参照してください。  
IAM ロールと一時的な認証情報は、次の状況で役立ちます:  
フェデレーションユーザーアクセス – フェデレーティッドアイデンティティに権限を割り当てるには、ロールを作成してそのロールの権限を定義します。フェデレーティッドアイデンティティが認証されると、そのアイデンティティはロールに関連付けられ、ロールで定義されている権限が付与されます。フェデレーションの詳細については、『IAM ユーザーガイド』の「サードパーティーアイデンティティプロバイダー向けロールの作成」 を参照してください。IAM アイデンティティセンターを使用する場合、権限セットを設定します。アイデンティティが認証後にアクセスできるものを制御するため、IAM Identity Center は、権限セットを IAM のロールに関連付けます。権限セットの詳細については、『AWS IAM Identity Center ユーザーガイド』の「権限セット」を参照してください。  
一時的な IAM ユーザー権限 - IAM ユーザーまたはロールは、特定のタスクに対して複数の異なる権限を一時的に IAM ロールで引き受けることができます。  
クロスアカウントアクセス - IAM ロールを使用して、自分のアカウントのリソースにアクセスすることを、別のアカウントの人物 (信頼済みプリンシパル) に許可できます。クロスアカウントアクセス権を付与する主な方法は、ロールを使用することです。ただし、一部の では AWS のサービス、 (ロールをプロキシとして使用する代わりに) リソースに直接ポリシーをアタッチできます。クロスアカウントアクセスにおけるロールとリソースベースのポリシーの違いについては、『IAM ユーザーガイド』の「IAM ロールとリソースベースのポリシーとの相違点」を参照してください。  
クロスサービスアクセス — 一部の は、他の の機能 AWS のサービス を使用します AWS のサービス。例えば、あるサービスで呼び出しを行うと、通常そのサービスによって Amazon EC2 でアプリケーションが実行されたり、Amazon S3 にオブジェクトが保存されたりします。サービスでは、呼び出し元プリンシパルの権限、サービスロール、またはサービスにリンクされたロールを使用してこれを行う場合があります。  
転送アクセスセッション (FAS) — IAM ユーザーまたはロールを使用して でアクションを実行する場合 AWS、ユーザーはプリンシパルと見なされます。一部のサービスを使用する際に、アクションを実行することで、別のサービスの別のアクションがトリガーされることがあります。FAS は、 を呼び出すプリンシパルのアクセス許可を AWS のサービス、ダウンストリームサービス AWS のサービス へのリクエストのリクエストと組み合わせて使用します。FAS リクエストは、サービスが他の AWS のサービス またはリソースとのやり取りを完了する必要があるリクエストを受け取った場合にのみ行われます。この場合、両方のアクションを実行するためのアクセス許可が必要です。FAS リクエストを行う際のポリシーの詳細については、「転送アクセスセッション」を参照してください。  
サービスロール - サービスがユーザーに代わってアクションを実行するために引き受ける IAM ロールです。IAM 管理者は、IAM 内からサービスロールを作成、変更、削除できます。詳細については、「IAM ユーザーガイド」の「AWS のサービスに権限を委任するロールの作成」を参照してください。  
サービスにリンクされたロール – サービスにリンクされたロールは、 にリンクされたサービスロールの一種です AWS のサービス。サービスは、ユーザーに代わってアクションを実行するロールを引き受けることができます。サービスにリンクされたロールは に表示され AWS アカウント 、サービスによって所有されます。IAM 管理者は、サービスにリンクされたロールの権限を表示できますが、編集することはできません。  
Amazon EC2 で実行されているアプリケーション – IAM ロールを使用して、EC2 インスタンスで実行され、 AWS CLI または AWS API リクエストを行うアプリケーションの一時的な認証情報を管理できます。これは、EC2 インスタンス内でのアクセスキーの保存に推奨されます。 AWS ロールを EC2 インスタンスに割り当て、そのすべてのアプリケーションで使用できるようにするには、インスタンスにアタッチされたインスタンスプロファイルを作成します。インスタンスプロファイルにはロールが含まれ、EC2 インスタンスで実行されるプログラムは一時的な認証情報を取得できます。詳細については、『IAM ユーザーガイド』の「Amazon EC2 インスタンスで実行されるアプリケーションに IAM ロールを使用して権限を付与する」を参照してください。  
IAM ロールと IAM ユーザーのどちらを使用するかについては、『IAM ユーザーガイド』の「(IAM ユーザーではなく) IAM ロールをいつ作成したら良いのか?」を参照してください。
```

英語で試してみる。

```python
db = scrape_awsdocs("en_us")
```

結果

```
---
By default, AWS Elemental MediaConvert sets your color space to Follow, which means that your output color space is the same as your input color space, even if the color space changes over the course of the video. Also by default, MediaConvert sets the output setting Color metadata to Insert, so that any color metadata is included in the output. If you want your output HDR to be the same as your input video, keep this setting and make sure that you choose HEVC for your codec and a 10-bit profile.  
To pass through HDR content  
Set up your transcoding job as usual. For more information, see Configuring jobs in MediaConvert.  
Make sure that the input Color space is set to the default value Follow.  
On the Create job page, in the Job pane on the left, choose Input 1.  
In the Video selector section on the right, for Color space, choose Follow.  
For each HDR output, choose an appropriate codec and profile and make sure that Color metadata is set to the default value Insert.  
On the Create job page, in the Job pane on the left, choose the output, such as Output 1.  
In the Encoding settings section on the right, specify these video settings as follows:  
Tip  
The simplest way to find specific encoding settings in the console is to use your web browser’s search on page function. For many browsers, this search is case sensitive.  
Video codec – Choose HEVC (H.265).  
Profile – Choose one of the 10-bit profiles: Main10/Main, Main10/High, Main 4:2:2 10-bit/Main, or Main 4:2:2 10-bit/High.  
Color metadata – Choose Insert.
---
The Layer setting specifies how overlapping image overlays appear in the video. The service overlays images with higher values for Layer on top of overlays with lower values for Layer. Each overlay must have a unique value for Layer; you can't assign the same layer number to more than one overlay.  
The following illustration shows how the value for Layer affects how a image overlay appears in relation to other overlays. The triangle has the highest value for Layer and appears on top, obscuring the video frame and all image overlays with lower values of Layer.  
To specify a value for the Layer setting  
Set up your image overlay as described in Image insertion.  
For Layer, enter a whole number from 0 to 99.  
Note  
You can use each number only once. Each image overlay must have its own layer.
---
When you convert a video from one color space to another, AWS Elemental MediaConvert automatically maps colors from your input color space to your output color space. To optionally specify your own custom color mapping, use 3D LUTs (3D lookup tables).  
3D LUTs contain color mapping information for a specific input or set of inputs. You receive 3D LUTs as .cube files from your color grader as part of your video production workflow.
---
AWS Elemental MediaConvert supports the following combinations of AAC settings when your output Bitrate control mode is CBR.  
To use this table, choose a profile from the Profile column. Then read across to find a valid combination of Coding mode, Sample rate, and Bitrate:  
Profile Coding mode(s) Sample rate(s) (Hz) Bitrate(s) (bit/s) LC 1.0 LC 1.0 16000 LC 1.0 LC 1.0 32000 LC 1.0 44100 LC 1.0 48000 LC 1.0 88200 LC 1.0 96000 LC 2.0 LC 2.0 16000 LC 2.0 LC 2.0 32000 LC 2.0 44100 LC 2.0 48000 LC 2.0 88200 LC 2.0 96000 LC 5.1 32000 LC 5.1 44100 LC 5.1 48000 LC 5.1 96000 HEV1 1.0 HEV1 1.0 32000 HEV1 1.0 HEV1 2.0 32000 HEV1 2.0 44100 HEV1 2.0 48000 HEV1 2.0 96000 HEV1 5.1 32000 HEV1 5.1 44100 HEV1 5.1 48000 HEV1 5.1 96000 HEV2 2.0 HEV2 2.0 32000 HEV2 2.0  
8000, 12000  
8000, 10000, 12000, 14000  
8000, 10000, 12000, 14000, 16000, 20000, 24000, 28000  
22050, 24000  
24000, 28000  
32000, 40000, 48000, 56000, 64000, 80000, 96000, 112000, 128000, 160000, 192000  
56000, 64000, 80000, 96000, 112000, 128000, 160000, 192000, 224000, 256000  
56000, 64000, 80000, 96000, 112000, 128000, 160000, 192000, 224000, 256000, 288000  
288000  
128000, 160000, 192000, 224000, 256000, 288000  
8000, 12000  
16000, 20000  
16000, 20000, 24000, 28000, 32000  
22050, 24000  
32000  
40000, 48000, 56000, 64000, 80000, 96000, 112000, 128000, 160000, 192000, 224000, 256000, 288000, 320000, 384000  
64000, 80000, 96000, 112000, 128000, 160000, 192000, 224000, 256000, 288000, 320000, 384000, 448000, 512000  
64000, 80000, 96000, 112000, 128000, 160000, 192000, 224000, 256000, 288000, 320000, 384000, 448000, 512000, 576000  
576000  
256000, 288000, 320000, 384000, 448000, 512000, 576000  
160000, 192000, 224000, 256000, 288000, 320000, 384000, 448000, 512000, 576000, 640000, 768000  
256000, 288000, 320000, 384000, 448000, 512000, 576000, 640000  
256000, 288000, 320000, 384000, 448000, 512000, 576000, 640000, 768000  
640000, 768000  
22050, 24000  
8000, 10000  
12000, 14000, 16000, 20000, 24000, 28000, 32000, 40000, 48000, 56000, 64000  
44100, 48000  
20000, 24000, 28000, 32000, 40000, 48000, 56000, 64000  
16000, 20000, 24000, 28000, 32000, 40000, 48000, 56000, 64000, 80000, 96000, 112000, 128000  
16000, 20000, 24000, 28000, 32000, 40000, 48000, 56000, 64000, 80000, 96000  
16000, 20000, 24000, 28000, 32000, 40000, 48000, 56000, 64000, 80000, 96000, 112000, 128000  
96000, 112000, 128000  
64000, 80000, 96000, 112000, 128000, 160000, 192000, 224000, 256000, 288000, 320000  
64000, 80000, 96000, 112000, 128000, 160000, 192000, 224000  
64000, 80000, 96000, 112000, 128000, 160000, 192000, 224000, 256000, 288000, 320000  
256000, 288000, 320000  
22050, 24000  
8000, 10000  
12000, 14000, 16000, 20000, 24000, 28000, 32000, 40000, 48000, 56000, 64000  
44100, 48000  
20000, 24000, 28000, 32000, 40000, 48000, 56000, 64000
---
When you specify the rotation for your input, AWS Elemental MediaConvert rotates the video from your input clockwise the amount that you specify. This rotation applies to all outputs in the job. You can rotate clockwise by 90, 180, or 270 degrees. The following image shows a video output from a job that specifies a 90-degree rotation.  
Note  
AWS Elemental MediaConvert doesn't pass through rotation metadata. Regardless of how you set Rotate, job outputs don't have rotation metadata.  
To specify the rotation of your video  
On the Create job page, in the Job pane on the left, in the Inputs section, choose the input that you want to rotate.  
In the Video selector section on the left, for Rotate, choose the amount of clockwise rotation that you want.  
If you use the API or an SDK, you can find this setting in the JSON file of your job. The setting name is rotate. Find the rotate property in the AWS Elemental MediaConvert API Reference.  
Note  
AWS Elemental MediaConvert doesn't rotate images and motion images that you overlay. If you use the image inserter feature or the motion image inserter feature with the rotate feature, rotate your overlay before you upload it. Specify the position of your overlays as you want them to appear on the video after rotation.
---
When you set Fragment length, check your values for Closed GOP cadence, GOP size, and Frame rate.
---
If you want your output video to use a different color space than your input video, use color space conversion. Set up color space conversion in the output Color corrector settings.  
MediaConvert supports the following input color spaces: Rec. 601, Rec. 709, HDR10, HLG 2020, P3DCI, and P3D65.  
To convert the color space  
Confirm that MediaConvert supports the conversion that you want to do. See Supported color space conversions.  
Set up your transcoding job as usual. For more information, see Configuring jobs in MediaConvert.  
On the Create job page, in the Job pane on the left, choose your HDR output.  
At the bottom of the Encoding settings section on the right, choose Preprocessors.  
Choose Color corrector to display the color correction settings.  
For Color space conversion, choose the color space that you want for your output.  
If you are converting to HDR 10, specify values for the HDR master display information settings.  
These values don't affect the pixel values that are encoded in the video stream. They are intended to help the downstream video player display content in a way that reflects the intentions of the content creator.
---
The following examples show a CloudTrail event for the CreateJob, CreateQueue, DeleteQueue, and TagResource operations. CloudTrail also records all other MediaConvert operations, though they are not shown here.  
Example event: CreateJob  
Example event: CreateQueue  
Example event: DeleteQueue  
Example event: TagResource
---
For all ABR streaming output groups other than HLS (CMAF, DASH, and Microsoft Smooth Streaming), the value that you specify for Fragment length (FragmentLength) must work with the other output settings that you specify. If you set Fragment length incorrectly, when viewers watch the output video, their player might crash. This can happen because the player expects additional segments at the end of the video and requests segments that don't exist.  
Fragment length is constrained by your values for Closed GOP cadence (GopClosedCadence), GOP size (GopSize), and Frame rate (FramerateNumerator, FramerateDenominator). For information about finding these settings on the console and in your JSON job specification, see Finding the settings related to fragment length.  
Note  
When you set your output Frame rate to Follow source, make sure that the frame rate of your input video file works with the value that you specify for the output Fragment length. The frame rate of your input video file functions as your output frame rate.  
Topics  
Rule for fragment lengthFragment length examplesFinding the settings related to fragment length
---
The following example policy grants the basic permissions to operate AWS Elemental MediaConvert. In this example, the account number is 111122223333 and the role name is MediaConvertRole. If you are using encryption, or if your Amazon S3 buckets have default encryption enabled, you need additional permissions. For more information, see Protecting your media assets with encryption and DRM using AWS Elemental MediaConvert.
```

## さいご
ぱっと見分量も多く人間が見た感じでは何が書いてあるかさっぱりですね。。
今後はこのデータを LLM に渡して質問をしてみて、想定している回答が返ってくるか試してみたいと思います。
