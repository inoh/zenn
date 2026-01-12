---
title: "Terraform 完全ガイド：IaCの基礎から実践まで"
emoji: "🏗️"
type: "tech"
topics: ["Terraform", "IaC", "AWS", "HCL", "DevOps"]
published: true
---

Terraform は HashiCorp が開発した Infrastructure as Code（IaC）ツールで、宣言的な構成ファイルを使用してインフラストラクチャを管理できます。
Terraform を改めて１から学んだときのメモをもとに本記事を作成しました。

## Terraform とは

Terraform は HashiCorp（Vagrant の開発元としても知られる）が開発したオープンソースの IaC ツールです。
独自の設定言語である HCL2（HashiCorp Configuration Language 2）を使用して、クラウドリソースやその他のインフラストラクチャを宣言的に定義・管理できます。

### Terraform の主な特徴

- **宣言的な記述**: 「何を」作りたいかを記述すれば、「どうやって」は Terraform が自動で判断
- **マルチクラウド対応**: AWS、Azure、GCP など多数のプロバイダーをサポート
- **状態管理**: tfstate ファイルで現在のインフラ状態を管理
- **プランニング機能**: 変更内容を事前に確認できる

## 環境構築

### tfenv のインストール

Terraform のバージョン管理には tfenv を使用するのがベストプラクティスです。

```bash
# Homebrew でインストール
brew install tfenv

# PATH を通す
echo 'export PATH="$HOME/.tfenv/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Terraform をインストール
tfenv install
tfenv use 1.14.3

# バージョン確認
terraform version
```

### 開発環境の準備

VS Code を使用している場合は、以下の拡張機能をインストールすることをおすすめします。

- **HashiCorp Terraform**: シンタックスハイライト、コード補完、フォーマット機能を提供

### セキュリティ設定（git-secrets）

Terraform では自動でクレデンシャル情報が作成されるため、クレデンシャル情報を誤って Git にコミットしないように、git-secrets をインストールしましょう。

```bash
# インストール
brew install git-secrets

# リポジトリに設定
git secrets --install

# AWS のクレデンシャルパターンを登録
git secrets --register-aws
```

## HCL2 の基本構文

HCL2 は Terraform で使用される独自の設定言語です。主要なブロックタイプを理解することが、Terraform マスターへの第一歩です。

### 基本的なブロック構造

```hcl
# ローカル変数（ファイル内でのみ使用）
locals {
  common_tags = {
    Project     = "MyProject"
    Environment = "Production"
  }
}

# 変数定義（外部から値を注入可能）
variable "region" {
  type        = string
  default     = "ap-northeast-1"
  description = "AWS region"
}

# Terraform 自体の設定
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# プロバイダー設定
provider "aws" {
  region  = var.region
  profile = "default"
}

# リソース定義
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  
  tags = {
    Name = "main-vpc"
  }
}

# データソース（既存リソースの参照）
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }
}

# 出力値
output "vpc_id" {
  value       = aws_vpc.main.id
  description = "The ID of the VPC"
}
```

## 基本的なワークフロー

Terraform の基本的な操作フローは以下の通りです。

```bash
# 1. 初期化（プロバイダーのダウンロード）
terraform init

# 2. フォーマット（コードの整形）
terraform fmt

# 3. バリデーション（構文チェック）
terraform validate

# 4. プラン（変更内容の確認）
terraform plan

# 5. 適用（リソースの作成・更新）
terraform apply

# 6. 破棄（リソースの削除）
terraform destroy
```

### 状態管理コマンド

```bash
# リソース一覧の表示
terraform state list

# 特定リソースの詳細表示
terraform state show aws_instance.example

# リソース名の変更
terraform state mv aws_instance.old aws_instance.new

# リソースの削除（tfstate から削除、実リソースは残る）
terraform state rm aws_instance.example

# 既存リソースのインポート
terraform import aws_instance.example i-0f1f545a97c98bc88

# 状態の最新化
terraform refresh
```

### インタラクティブコンソール

Terraform には、式や関数をテストできるインタラクティブコンソールがあります。

```bash
terraform console
```

```hcl
# コンソール内での操作例
> floor(4.9)
4
> substr("hello world", 1, 4)
"ello"
> join(", ", ["a", "b", "c"])
"a, b, c"
```

## variable と locals の使い分け

### variable（変数）

`variable` は外部から値を注入できる変数です。環境や状況に応じて値を変更したい場合に使用します。

```hcl
variable "region" {
  type        = string
  default     = "ap-northeast-1"
  description = "AWS region"
}

variable "instance_count" {
  type    = number
  default = 2
}

variable "tags" {
  type = map(string)
  default = {
    Environment = "dev"
  }
}
```

### データ型

HCL2 でサポートされる主なデータ型：

- **プリミティブ型**: `string`, `number`, `boolean`, `null`
- **コレクション型**: `list`, `map`, `set`
- **構造型**: `object`, `tuple`

### variable の値の設定方法（優先順位：下ほど高い）

1. **デフォルト値**（variable ブロック内の `default`）
2. **環境変数**（鍵情報、環境依存の値に適している）
   ```bash
   export TF_VAR_region="us-west-2"
   ```

3. **変数ファイル**（Git 管理、ロジックのデータに適している）
   ```hcl
   # terraform.tfvars または *.auto.tfvars
   region = "ap-northeast-1"
   instance_count = 3
   ```

4. **コマンド引数**（実行ログに残る。一時的に変更したい場合）
   ```bash
   terraform apply -var="region=eu-west-1"
   ```

### locals（ローカル変数）

`locals` はファイル内でのみ使用できる変数で、複雑な式の結果を保存したり、共通値を定義する際に使用します。

```hcl
locals {
  # 環境名の決定
  environment = terraform.workspace == "production" ? "prod" : "dev"
  
  # 共通タグの定義
  common_tags = {
    Project     = "MyApp"
    Environment = local.environment
    ManagedBy   = "Terraform"
  }
  
  # 計算結果の保存
  subnet_count = length(data.aws_availability_zones.available.names)
}

resource "aws_instance" "web" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.micro"
  
  tags = merge(
    local.common_tags,
    {
      Name = "web-server"
    }
  )
}
```

**使い分けのポイント**：
- 外部から変更する可能性がある → `variable`
- 内部でのみ使用する計算結果や共通値 → `locals`

## 主要ブロックの詳細

### terraform ブロック

Terraform 自体の設定を行います。主にバージョンの固定に使用します。

```hcl
terraform {
  # Terraform のバージョン指定
  required_version = ">= 1.0.0, < 2.0.0"
  
  # プロバイダーのバージョン指定
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # バックエンド設定（状態ファイルの保存場所）
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "ap-northeast-1"
  }
}
```

### provider ブロック

クラウドプロバイダーやサービスへの接続設定を行います。

```hcl
provider "aws" {
  region  = var.region
  profile = "default"  # AWS CLI のプロファイル名
  
  default_tags {
    tags = {
      ManagedBy = "Terraform"
      Project   = "MyProject"
    }
  }
}
```

プロバイダーの一覧は [Terraform Registry](https://registry.terraform.io/browse/providers) で確認できます。

### resource ブロック

実際に作成・管理するリソースを定義します。

```hcl
resource "aws_instance" "web" {
  ami           = "ami-03d1820163e6b9f5d"
  instance_type = "t2.micro"
  
  tags = {
    Name = "web-server"
  }
}
```

### data ブロック

既存のリソースや外部データを参照します。Terraform の管理対象外だが利用したいリソースに使用します。

```hcl
# 最新の Ubuntu AMI を取得
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }
}

# 既存の VPC を参照
data "aws_vpc" "existing" {
  id = "vpc-12345678"
}

# 参照方法
resource "aws_instance" "web" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.micro"
}
```

### output ブロック

作成したリソースの情報を外部に公開します。モジュール化や他のツールとの連携に便利です。

```hcl
output "instance_id" {
  value       = aws_instance.web.id
  description = "The ID of the EC2 instance"
}

output "instance_public_ip" {
  value       = aws_instance.web.public_ip
  description = "The public IP of the EC2 instance"
  sensitive   = false
}

output "db_password" {
  value       = aws_db_instance.main.password
  description = "Database password"
  sensitive   = true  # 機密情報は sensitive = true にする
}
```

出力値の確認：
```bash
terraform output
terraform output instance_id
terraform output -json  # JSON 形式で出力
```

## リソース間の参照

Terraform では、リソース間で値を参照できます。

### 参照の構文

```
<BLOCK_TYPE>.<RESOURCE_NAME>.<ATTRIBUTE_NAME>
```

- **BLOCK_TYPE**: ブロックの種類（`resource`, `data`, `var`, `local` など）
- **RESOURCE_NAME**: リソースの名前
- **ATTRIBUTE_NAME**: 属性の名前（オプション）

### 実践例

```hcl
# VPC の作成
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  
  tags = {
    Name = "main-vpc"
  }
}

# サブネットの作成（VPC の ID を参照）
resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id  # VPC リソースを参照
  cidr_block        = "10.0.1.0/24"
  availability_zone = "ap-northeast-1a"
  
  tags = {
    Name = "public-subnet"
  }
}

# セキュリティグループの作成
resource "aws_security_group" "web" {
  name        = "web-sg"
  description = "Security group for web servers"
  vpc_id      = aws_vpc.main.id  # VPC リソースを参照
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# EC2 インスタンスの作成
resource "aws_instance" "web" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t2.micro"
  subnet_id              = aws_subnet.public.id           # サブネットを参照
  vpc_security_group_ids = [aws_security_group.web.id]   # セキュリティグループを参照
  
  tags = {
    Name = "web-server"
  }
}
```

この参照により、Terraform は自動的に依存関係を理解し、正しい順序でリソースを作成します。

## 組み込み関数

Terraform には多数の組み込み関数があります。

### リファレンス

詳細は [公式ドキュメント](https://www.terraform.io/language/functions) を参照してください。

### よく使う関数

```hcl
locals {
  # 文字列操作
  upper_name    = upper("hello")           # "HELLO"
  lower_name    = lower("WORLD")           # "world"
  trimmed       = trim("  hello  ")        # "hello"
  substring     = substr("hello world", 1, 4)  # "ello"
  replaced      = replace("hello", "l", "r")   # "herro"
  
  # リスト操作
  list_length   = length(["a", "b", "c"])      # 3
  first_item    = element(["a", "b", "c"], 0)  # "a"
  joined        = join(", ", ["a", "b", "c"])  # "a, b, c"
  list_concat   = concat(["a", "b"], ["c"])    # ["a", "b", "c"]
  
  # マップ操作
  map_keys      = keys({a = 1, b = 2})         # ["a", "b"]
  map_values    = values({a = 1, b = 2})       # [1, 2]
  merged_map    = merge({a = 1}, {b = 2})      # {a = 1, b = 2}
  
  # 数値操作
  max_value     = max(1, 2, 3)                 # 3
  min_value     = min(1, 2, 3)                 # 1
  floored       = floor(4.9)                   # 4
  
  # 条件分岐
  env           = var.environment == "prod" ? "production" : "development"
  
  # ファイル操作
  file_content  = file("${path.module}/config.json")
  template      = templatefile("${path.module}/script.tpl", {
    var1 = "value1"
  })
}
```

### 実践例：複数の AZ にサブネットを作成

```hcl
data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_subnet" "public" {
  count = 3
  
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone = element(data.aws_availability_zones.available.names, count.index)
  
  tags = {
    Name = "public-subnet-${count.index + 1}"
  }
}
```

## ファイル分割とプロジェクト構成

Terraform は、カレントディレクトリ内のすべての `.tf` ファイルを自動的に読み込みます（サブディレクトリは読み込まない）。

### 推奨されるファイル構成

```
terraform-project/
├── .gitignore           # Git 除外設定
├── terraform.tfvars     # 変数の値（環境依存、Git に含めない場合も）
├── variables.tf         # 変数定義
├── locals.tf            # ローカル変数
├── provider.tf          # プロバイダー設定
├── versions.tf          # Terraform とプロバイダーのバージョン指定
├── main.tf              # メインのリソース定義
├── network.tf           # ネットワーク関連のリソース
├── compute.tf           # コンピュートリソース
├── database.tf          # データベース関連
├── outputs.tf           # 出力値
└── README.md            # ドキュメント
```

### .gitignore の設定

[gitignore.io](https://www.toptal.com/developers/gitignore) を参考に、以下を除外します。

```gitignore
# Terraform
**/.terraform/*
*.tfstate
*.tfstate.*
crash.log
crash.*.log
override.tf
override.tf.json
*_override.tf
*_override.tf.json
.terraformrc
terraform.rc

# Sensitive files
*.pem
*.key
secrets.tfvars
```

### terraform.tfvars について

`terraform.tfvars` ファイルは、変数の値を定義するファイルです。Terraform は自動的にこのファイルを読み込みます。

```hcl
# terraform.tfvars
region         = "ap-northeast-1"
instance_type  = "t2.micro"
instance_count = 3

tags = {
  Environment = "production"
  Project     = "MyApp"
}
```

環境ごとに異なる値を使用する場合：

```bash
# 開発環境
terraform apply -var-file="dev.tfvars"

# 本番環境
terraform apply -var-file="prod.tfvars"
```

## AWS 実践例

### VPC とサブネットの構築

```hcl
# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "main-vpc"
  }
}

# インターネットゲートウェイ
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = {
    Name = "main-igw"
  }
}

# パブリックサブネット
resource "aws_subnet" "public" {
  count = 2
  
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  
  tags = {
    Name = "public-subnet-${count.index + 1}"
  }
}

# ルートテーブル
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  
  tags = {
    Name = "public-route-table"
  }
}

# ルートテーブルの関連付け
resource "aws_route_table_association" "public" {
  count = 2
  
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}
```

### RDS の構築

RDS を構築する際に理解すべき概念：

- **サブネットグループ**: 複数のサブネットを指定して冗長化
- **パラメータグループ**: データベースエンジンの動作設定
- **オプショングループ**: 追加機能の有効化

```hcl
# DB サブネットグループ
resource "aws_db_subnet_group" "main" {
  name       = "main-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
  
  tags = {
    Name = "Main DB subnet group"
  }
}

# DB パラメータグループ
resource "aws_db_parameter_group" "main" {
  name   = "main-db-params"
  family = "mysql8.0"
  
  parameter {
    name  = "character_set_server"
    value = "utf8mb4"
  }
  
  parameter {
    name  = "character_set_client"
    value = "utf8mb4"
  }
}

# セキュリティグループ
resource "aws_security_group" "rds" {
  name        = "rds-sg"
  description = "Security group for RDS"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
  
  tags = {
    Name = "rds-sg"
  }
}

# RDS インスタンス
resource "aws_db_instance" "main" {
  identifier     = "main-db"
  engine         = "mysql"
  engine_version = "8.0"
  instance_class = "db.t3.micro"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  
  db_name  = "myapp"
  username = var.db_username
  password = var.db_password
  
  db_subnet_group_name   = aws_db_subnet_group.main.name
  parameter_group_name   = aws_db_parameter_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"
  
  skip_final_snapshot = false
  final_snapshot_identifier = "main-db-final-snapshot"
  
  tags = {
    Name = "main-database"
  }
}
```

### プレフィックスリストの活用

プレフィックスリストは、複数の CIDR ブロックをまとめて管理できる機能です。例えば、S3 や DynamoDB などの AWS サービスのエンドポイント群を指定する際に便利です。

```hcl
# VPC エンドポイント用のプレフィックスリスト
data "aws_prefix_list" "s3" {
  name = "com.amazonaws.ap-northeast-1.s3"
}

resource "aws_security_group_rule" "allow_s3" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  prefix_list_ids   = [data.aws_prefix_list.s3.id]
  security_group_id = aws_security_group.app.id
}
```

## 実践的な Tips

### 1. ワークスペースの活用

環境ごとに状態ファイルを分離できます。

```bash
# ワークスペースの作成
terraform workspace new dev
terraform workspace new prod

# ワークスペースの切り替え
terraform workspace select dev

# 現在のワークスペース確認
terraform workspace show

# ワークスペース一覧
terraform workspace list
```

設定での活用：

```hcl
locals {
  environment = terraform.workspace
  
  instance_type = {
    dev  = "t2.micro"
    prod = "t3.medium"
  }
}

resource "aws_instance" "web" {
  instance_type = local.instance_type[local.environment]
  # ...
}
```

### 2. count と for_each の使い分け

**count**: 同じリソースを複数作成する場合

```hcl
resource "aws_instance" "web" {
  count = 3
  
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.micro"
  
  tags = {
    Name = "web-${count.index + 1}"
  }
}
```

**for_each**: 名前付きのリソースを作成する場合

```hcl
locals {
  environments = {
    dev  = "t2.micro"
    staging = "t2.small"
    prod = "t3.medium"
  }
}

resource "aws_instance" "web" {
  for_each = local.environments
  
  ami           = data.aws_ami.ubuntu.id
  instance_type = each.value
  
  tags = {
    Name        = "web-${each.key}"
    Environment = each.key
  }
}
```

### 3. dynamic ブロックの活用

繰り返しの設定を動的に生成できます。

```hcl
variable "ingress_rules" {
  type = list(object({
    port        = number
    protocol    = string
    cidr_blocks = list(string)
    description = string
  }))
  
  default = [
    {
      port        = 80
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTP"
    },
    {
      port        = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTPS"
    }
  ]
}

resource "aws_security_group" "web" {
  name   = "web-sg"
  vpc_id = aws_vpc.main.id
  
  dynamic "ingress" {
    for_each = var.ingress_rules
    
    content {
      from_port   = ingress.value.port
      to_port     = ingress.value.port
      protocol    = ingress.value.protocol
      cidr_blocks = ingress.value.cidr_blocks
      description = ingress.value.description
    }
  }
}
```

### 4. ライフサイクルの制御

リソースのライフサイクルを細かく制御できます。

```hcl
resource "aws_instance" "web" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.micro"
  
  lifecycle {
    # 作成前に削除（デフォルトは削除後に作成）
    create_before_destroy = true
    
    # 削除を防止
    prevent_destroy = true
    
    # 特定の属性の変更を無視
    ignore_changes = [
      tags,
      user_data,
    ]
  }
}
```

### 5. 依存関係の明示的な指定

暗黙的な依存関係が機能しない場合に使用します。

```hcl
resource "aws_instance" "web" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.micro"
  
  # このリソースより先に作成すべきリソースを指定
  depends_on = [
    aws_iam_role_policy_attachment.example
  ]
}
```

## トラブルシューティング

### よくあるエラーと対処法

1. **Provider のダウンロードエラー**
   ```bash
   terraform init -upgrade
   ```

2. **State ファイルのロック**
   ```bash
   terraform force-unlock <LOCK_ID>
   ```

3. **リソースの drift（差分）確認**
   ```bash
   terraform plan -refresh-only
   terraform apply -refresh-only
   ```

4. **デバッグモード**
   ```bash
   export TF_LOG=DEBUG
   terraform apply
   ```

## まとめ

本記事では、Terraform の基礎から実践的な使い方まで解説しました。

### 重要なポイント

1. **環境構築**: tfenv でバージョン管理
2. **セキュリティ**: git-secrets でクレデンシャル保護
3. **ベストプラクティス**: ファイル分割、変数の適切な使用、状態管理
4. **AWS リソース**: VPC、EC2、RDS などの構築パターン

### 次のステップ

- **モジュール化**: 再利用可能なモジュールの作成
- **リモートバックエンド**: S3 + DynamoDB での状態管理
- **CI/CD 統合**: GitHub Actions や GitLab CI との連携
- **Terraform Cloud**: チーム開発での活用

### 参考リンク

- [Terraform 公式ドキュメント](https://www.terraform.io/docs)
- [HCL2 言語仕様](https://www.terraform.io/language)
- [Terraform Registry](https://registry.terraform.io/)
- [AWS Provider ドキュメント](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

Terraform を使えば、インフラストラクチャをコードとして管理し、再現性の高い環境構築が可能になります。ぜひ実際に手を動かして、IaC の世界を体験してみてください。
