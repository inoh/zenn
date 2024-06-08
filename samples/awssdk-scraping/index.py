import requests
from bs4 import BeautifulSoup
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import HTMLHeaderTextSplitter

embedding_function = HuggingFaceEmbeddings(
    model_name="oshizo/sbert-jsnli-luke-japanese-base-lite",
    # model_name="sentence-transformers/all-mpnet-base-v2",
)

def scrape_awsdocs(locale):
    sitemap = requests.get(f"https://docs.aws.amazon.com/{locale}/mediaconvert/latest/ug/sitemap.xml").text
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

    return Chroma.from_documents(texts, embedding_function, persist_directory=f"./db/mediaconvert_{locale}")



db = scrape_awsdocs("en_us")
# db = Chroma(persist_directory="./db/mediaconvert_ja_jp", embedding_function=embedding_function)

result = db.similarity_search("Role", k=10)
for val in result:
    print("---")
    print(val.page_content)

# ---
# AWSドキュメントMediaConvertユーザーガイド  
# 複数キューとパフォーマンステストオンデマンドキューでのトランスコードの支払い方法 オンデマンドキューを作成するオンデマンドキューを一時停止または再有効化オンデマンドキューのリストオンデマンドキューを削除  
# AWS Elemental でのオンデマンドキューの使用 MediaConvert リソースの管理とパフォーマンスのテスト リソース割り当てとジョブ優先度付け パフォーマンステスト オンデマンドキューでのトランスコードの支払い方法 オンデマンドキューを作成する Console AWS CLI aws mediaconvert create-queue \ --region region-name-1 \ --name Queue1 \ --description "Example queue description." \ --tags "KeyName1=string1,KeyName2=string2" オンデマンドキューを一時停止または再有効化 Console AWS CLI aws mediaconvert update-queue \ --name Queue1 \ --status PAUSED aws mediaconvert update-queue \ --name Queue1 \ --status ACTIVE オンデマンドキューの一覧表示 Console AWS CLI aws mediaconvert list-queues { "Queues": [ { "Arn": "arn:aws:mediaconvert:us-west-2:111122223333:queues/Example", "CreatedAt": "2023-06-19T09:34:25-07:00", "LastUpdated": "2023-06-19T09:34:25-07:00", "Name": "Example", "PricingPlan": "ON_DEMAND", "ProgressingJobsCount": 0, "Status": "ACTIVE", "SubmittedJobsCount": 0, "Type": "CUSTOM" }, { "Arn": "arn:aws:mediaconvert:us-west-2:111122223333:queues/Default", "CreatedAt": "2018-05-16T09:13:08-07:00", "LastUpdated": "2021-05-14T15:39:23-07:00", "Name": "Default", "PricingPlan": "ON_DEMAND", "ProgressingJobsCount": 0, "Status": "ACTIVE", "SubmittedJobsCount": 0, "Type": "SYSTEM" } ] } オンデマンドキューを削除 Console AWS CLI aws mediaconvert delete-queue \ --name Queue1  
# 翻訳は機械翻訳により提供されています。提供された翻訳内容と英語版の間で齟齬、不一致または矛盾がある場合、英語版が優先します。
# ---
# AWSドキュメントMediaConvertユーザーガイド  
# Dolby Atmos パススルーに対する機能制限  
# AWS Elemental MediaConvert で Dolby Atmos パススルーの使用 Dolby Atmos パススルーに対する機能制限  
# 翻訳は機械翻訳により提供されています。提供された翻訳内容と英語版の間で齟齬、不一致または矛盾がある場合、英語版が優先します。
# ---
# デフォルトのキューはオンデマンドキューです。オンデマンドキューは、AWS Elemental MediaConvert がトランスコーディングリソースをジョブに割り当てる方法と支払い方法がリザーブドキューとは異なります。詳細については、「料金表」を参照してください。MediaConvert このセクションは複数のキューの使用、追加のキューの作成、キューの表示、キューの一時停止と有効化、キューの削除に関するものです。  
# トピック  
# 複数キューとパフォーマンステストオンデマンドキューでのトランスコードの支払い方法 オンデマンドキューを作成するオンデマンドキューを一時停止または再有効化オンデマンドキューのリストオンデマンドキューを削除
# ---
# iam:PassRole アクションを実行する権限がないというエラーが表示された場合は、ポリシーを更新して にロールを渡すことができるようにする必要があります MediaConvert。  
# 一部の AWS のサービス では、新しいサービスロールまたはサービスにリンクされたロールを作成する代わりに、そのサービスに既存のロールを渡すことができます。そのためには、サービスにロールを渡す権限が必要です。  
# 次の例のエラーは、 という IAM marymajor ユーザーがコンソールを使用して でアクションを実行しようする場合に発生します MediaConvert。ただし、このアクションをサービスが実行するには、サービスロールから付与された権限が必要です。Mary には、ロールをサービスに渡す権限がありません。  
# この場合、Mary のポリシーを更新してメアリーに iam:PassRole アクションの実行を許可する必要があります。  
# サポートが必要な場合は、 AWS 管理者にお問い合わせください。サインイン資格情報を提供した担当者が管理者です。
# ---
# AWSドキュメントMediaConvertユーザーガイド  
# MediaConvert ノンリニアウォーターマーキング用のジョブ設定  
# 翻訳は機械翻訳により提供されています。提供された翻訳内容と英語版の間で齟齬、不一致または矛盾がある場合、英語版が優先します。
# ---
# AWSドキュメントMediaConvertユーザーガイド  
# デフォルト (パディングありのフィット)引き伸ばし出力へFitアップスケーリングせずにフィットFill  
# ビデオスケーリングの動作とアスペクト比 デフォルト (パディングありのフィット) 引き伸ばし出力へ Fit アップスケーリングせずにフィット Fill  
# 翻訳は機械翻訳により提供されています。提供された翻訳内容と英語版の間で齟齬、不一致または矛盾がある場合、英語版が優先します。
# ---
# 次の情報は、 と IAM の使用時に発生する可能性がある一般的な問題の診断 MediaConvert と修正に役立ちます。  
# トピック  
# でアクションを実行する権限がない MediaConvertiam を実行する権限がありません。PassRole自分の 以外のユーザーに自分の MediaConvert リソース AWS アカウント へのアクセスを許可したい
# ---
# この機能を使用するには、まず Nielsen との関係を築き、クラウドに Nielsen SID/TIC サーバーをセットアップする必要があります。 AWS Nielsen に連絡して SID/TIC サーバーソフトウェアをダウンロードし、WRR ライセンスファイルを生成して、インストールとセットアップの指示を受けてください。インフラストラクチャの仕組みについては、「AWS Elemental がクラウド内のニールセン SID/TIC MediaConvert サーバーとどのように相互作用するか AWS」をご覧ください。  
# Nielsen 非線形ウォーターマークを設定するには (コンソール)  
# Nielsen SID/TIC サーバーシステムをクラウドにセットアップします。 AWS 詳細については、Nielsen にお問い合わせください。  
# ニールセンメタデータの.zip ファイルを格納する Amazon S3 バケットを設定します。 MediaConvertメタデータをこのバケットに書き込みます。  
# MediaConvert でのジョブの設定 で説明したように、ジョブの入力と出力を設定します。  
# [Create job] (ジョブの作成) ページでは、左の [Job] (ジョブ) ペインで、[Job settings] (ジョブ設定) の [Settings] (設定) を選択します。  
# 右側の [Partner integrations] (パートナー統合) セクションで、[Nielsen non-linear watermarking] (ニールセン非線形ウォーターマーク) を選択します。  
# [Nielsen non-linear watermarking] (Nielsen 非線形ウォーターマーク) を有効にしたときに表示される設定値を指定します。各設定の手順とガイダンスについては、設定ラベルの横にある [Info] (情報) を選択します。  
# ページの下部にある [Create] (作成) を選択して、ジョブを実行します。  
# メタデータの Amazon S3 バケットにあるデータを、Nielsen の指示に従って転送します。  
# Nielsen 非線形ウォーターマーク (API、CLI、および SDK) を設定するには  
# API、CLI、または SDK を使用する場合は、JSON ジョブ仕様で関連する設定を指定し、ジョブとともにプログラムで送信します。プログラムによるジョブの送信の詳細については、『AWS Elemental API リファレンス』の入門トピックのいずれかを参照してください。 MediaConvert  
# AWS SDK または AWS CLI MediaConvert を使用して AWS Elemental を使い始める  
# API を使用して AWS Elemental MediaConvert を使い始める  
# MediaConvert コンソールを使用して JSON ジョブ仕様を生成します。コンソールはジョブスキーマに対するインタラクティブなバリデーターとして機能するため、この方法をお勧めします。 MediaConvert 以下の手順で、コンソールを使って JSON ジョブ仕様書を生成します。  
# コンソールで、前の手順に従います。  
# 左側の [Job] (ジョブ) ペインの [Job settings (ジョブ設定)]で、[Show job JSON (ジョブの JSON を表示)] を選択します。  
# 各設定がジョブ設定構造のどこにあるかなどの追加情報については、AWS Elemental MediaConvert API リファレンスをご覧ください。このリストのリンクは、そのドキュメントの設定に関する情報に移動します。  
# Nielsen non-linear watermarking (ニールセン非線形ウォーターマーク) (nielsenNonLinearWatermark)  
# Source watermark status (ソースウォーターマークステータス) (sourceWatermarkStatus)  
# Watermark types (ウォーターマークのタイプ) (activeWatermarkProcess)  
# SID (sourceId)  
# [CSID] (cbetSourceId)  
# Asset ID (アセット ID) (assetId)  
# [Asset name] (アセット名) (assetName)  
# Episode ID (エピソード ID) (episodeId)  
# TIC server REST endpoint (TIC サーバー REST エンドポイント) (ticServerUrl)  
# [ADI file] (ADI ファイル) (adiFilename)  
# Metadata destination (メタデータの送信先) (metadataDestination)  
# Share TICs across tracks (トラック間でTICを共有する) (uniqueTicPerAudioTrack)
# ---
# AWS Elemental は、トランスコードジョブの実行時に、ジョブの完了を妨げない問題が発生した場合に警告コード MediaConvert を返します。Amazon を使用して EventBridge 、サービスが返す警告コードを追跡できます。詳細については、「 EventBridge で を使用する AWS Elemental MediaConvert」を参照してください。  
# この表は、 が返す MediaConvert警告コードの詳細と、考えられる原因と解決策を示しています。  
# 警告コード メッセージ 詳細 100000 220000 230001 230002 230004 230005 230006 MediaConvert は入力オーディオの一部をデコードできません。 240000 240001 250001 250002 Dolby CBI 入力に対応していないビットレートが含まれています。 270000 MediaConvert は、出力を送信先バケットに書き込むときにAmazon S3 S3 から 503 スローダウンエラーコードを受信しました。  
# 実行したジョブが最初の送信キューから送信先キューにホップできませんでした。  
# 実行したジョブが指定した待機時間よりも長い時間、元の送信キューで待機していましたが、新しい送信先キューに移動できませんでした。送信先キューがまだ存在するかどうか確認してください。必要となるアクションはありませんが、完了を予期した時間より長くジョブが実行されることがあります。  
# Wait minutes と Destination queue を含むホップの挙動は、[ジョブ管理キューホッピング]設定で操作できます。  
# 詳細については、API リファレンスの HopDestination を参照してください。  
# 入力ファイルは切り捨てられます。  
# 入力ファイルにはデータがないため、出力の所要時間が予想よりも短くなる可能性があります。  
# トラブルシューティングを行うには、入力内容に欠落がないかどうかを確認してください。  
# 入力の色メタデータが欠落しているか不完全です。  
# MediaConvert は、入力の色メタデータが欠落しているか不完全なため、入力の色空間をたどれませんでした。カラーメタデータには、カラープライマリ、転送関数、マトリックス係数が含まれます。  
# 出力の色メタデータが欠落しているか不完全な可能性があり、これによりプレーヤーがビデオコンテンツを不完全に表示する原因になります。  
# 出力 Color space conversionで を指定した場合Color corrector、 MediaConvert は色空間を変換できず、不正確な色メタデータが書き込まれた可能性があることに注意してください。  
# 解決するには、入力の Color space を指定し、Color space usage を Force に設定します。  
# 詳細については、API リファレンスの ColorSpace を参照してください。  
# MediaConvert は入力にオーディオ継続時間補正を適用できません。  
# 入力ファイルコンテナのオーディオトラックの'stts' time-to-sample テーブルに問題があり、オーディオ時間補正を適用 MediaConvert できません。  
# オーディオ継続時間補正に関する詳細については、「API リファレンス」を参照してください。  
# オーディオとビデオの同期に関する問題がないか、出力を確認してください。  
# 入力の 'mdhd' メディアヘッダー Atom の情報に欠落があります。  
# 入力の'mdhd'メディアヘッダーアトムが不完全であるか、データがありません。 は、ア'mdhd'トムが 32 バイトまたは 20 バイトであると MediaConvert 想定します。  
# MediaConvert は入力を正しく読み取れない可能性があります。ファイルの総所要時間と言語コード (該当する場合) を含む、出力の正確さと品質を確認してください。  
# MediaConvert は、入力で色サンプル範囲メタデータを見つけることができません。  
# MediaConvert は、入力の色サンプル範囲メタデータが欠落しているか不完全であるため、入力の色サンプル範囲をフォローできませんでした。  
# 出力の色サンプル範囲メタデータが欠落しているか不正確な可能性があり、それがプレーヤーがビデオコンテンツを正確に表示できない原因になっています。  
# 出力Color corrector で Color space conversion または Sample range conversion を指定すると、出力のサンプル範囲が不正確になる可能性があるという点にご留意ください。  
# 解決するには、入力の Sample range を指定します。  
# 詳細については、API リファレンスの SampleRange を参照してください。  
# 入力のファイル構造またはオーディオストリームに問題があります。  
# 入力に破損やその他のオーディオエンコードの問題がないか確認します。  
# 出力にデコード MediaConvert できないオーディオコンテンツがない可能性があります。  
# MediaConvert は、オーディオとビデオの同期を維持するために、少なくとも 100 ミリ秒のオーディオサイレンスを追加しました。  
# 入力オーディオトラックに欠落、破損、または予期しないデータが含まれています。オーディオとビデオの同期に関する問題がないか、出力を確認してください。  
# MediaConvert は、オーディオとビデオを整列させるために、少なくとも 100 ミリ秒のオーディオを削除しました。  
# オーディオとビデオの同期に関する問題がないか、出力を確認してください。  
# 入力のキャプションにサポートされていないフォントが含まれています。  
# サポートされていないフォントの付いた入力キャプションを送信しました。 MediaConvert は代わりに汎用フォントを使用します。  
# サポートされていないビットレートでDolby CBI入力を送信しました。 は、サポートされるビットレートに増加 MediaConvert します。  
# DOLBY CBI 入力を生成するアプリケーションが最新版かどうかを確認してください。  
# MediaConvert が出力ファイルをレプリケート先バケットに書き込んでいる間に、Amazon S3 によってスロットリングされました。ジョブが停止するか、想定より完了に時間がかかる可能性があります。  
# Amazon S3 へのリクエストレート制限を超過したときには 503 Slow Down エラー応答を受信します。同時にリクエストを行ってジョブを制限する原因となっている他のアプリケーションがないか、確認してください。  
# 詳細については、「Amazon S3 のトラブルシューティング」を参照してください。
# ---
# AWSドキュメントMediaConvertユーザーガイド  
# AWS Elemental アウトプットのオーディオウォーターマーキングに Kantar を使用する MediaConvert  
# 翻訳は機械翻訳により提供されています。提供された翻訳内容と英語版の間で齟齬、不一致または矛盾がある場合、英語版が優先します。
