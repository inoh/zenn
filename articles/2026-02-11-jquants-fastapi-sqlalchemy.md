---
title: "J-Quants API を FastAPI + SQLAlchemy で実運用する際のハマりどころと設計パターン"
emoji: "📈"
type: "tech"
topics: ["jquants", "fastapi", "sqlalchemy", "python", "株式投資"]
published: true
---

## はじめに

J-Quants API は東証上場銘柄の株価・財務データを取得できる API です。個人開発で日本株分析サービスを構築する際、非常に便利なデータソースですが、**実際にプロダクションレベルで運用しようとすると意外なハマりどころが多い**です。

本記事では、FastAPI + SQLAlchemy (async) + PostgreSQL の構成で J-Quants API を実運用してきた中で得た知見を、以下の4つのテーマに絞って紹介します。

1. **レート制限とリトライ戦略**
2. **差分更新とバックフィル** — 効率的なデータ同期パイプライン
3. **PostgreSQL upsert パターン** — 冪等なデータ取り込み
4. **株式分割調整** — per-share 財務指標の正確な処理

## 1. レート制限とリトライ戦略

### J-Quants API のレート制限

J-Quants API（Light）のレート制限は **1分あたり60リクエスト** です。これを超えると `429 Too Many Requests` が返ってきます。全銘柄のデータを一括取得する場合はあまり問題になりませんが、銘柄個別のバックフィル処理では簡単に上限に達します。

### クライアントラッパーの実装

```python
import threading
import time

class JQuantsClient:
    def __init__(self) -> None:
        self._client = None
        self._last_call_time: float = 0.0
        self._lock = threading.Lock()

    def _wait_for_rate_limit(self) -> None:
        """API呼び出し間隔を制御する"""
        interval = 2.0  # 2秒間隔 ≒ 30回/分
        with self._lock:
            now = time.time()
            elapsed = now - self._last_call_time
            if elapsed < interval:
                time.sleep(interval - elapsed)
            self._last_call_time = time.time()

    def _call_with_retry(self, fn, label="", max_retries=3):
        """429エラー時はリトライする"""
        for attempt in range(max_retries):
            self._wait_for_rate_limit()
            try:
                return fn()
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    wait = 30 * (attempt + 1)  # 30秒, 60秒, 90秒
                    time.sleep(wait)
                else:
                    raise
```

**ポイント:**

- `threading.Lock` で前回呼び出し時刻を排他制御。`asyncio.to_thread()` で別スレッドから呼ばれるため、スレッドセーフにしておく必要がある
- 429 発生時のバックオフは30秒刻みの線形増加。J-Quants のレート制限は比較的長めにリセットされるため、短い Exponential Backoff では不十分なことが多い
- `"429" in str(e)` という雑な判定だが、`jquants-api-client` ライブラリが投げる例外が標準化されていないため、文字列マッチが実用的

### asyncio.to_thread() で非同期化

`jquants-api-client` は同期ライブラリなので、FastAPI の async ハンドラからそのまま呼ぶとイベントループをブロックします。`asyncio.to_thread()` でワーカースレッドに逃がすのが定石です。

```python
df = await asyncio.to_thread(
    jquants_client.get_daily_prices,
    code=code, from_date=from_date, to_date=to_date,
)
```

## 2. 差分更新とバックフィル — 効率的なデータ同期パイプライン

### 2段階の同期戦略

データ同期を「差分更新」と「バックフィル」の2段階に分けることで、通常の日次更新は高速に、新規銘柄や過去データの補完は段階的に行えます。

```python
async def sync_daily_prices(db, valid_codes, target_date=None, backfill=True):
    TARGET_YEARS = 5
    full_start = date.today() - timedelta(days=365 * TARGET_YEARS)

    # ステップ1: DB内の最新日付から差分開始日を決定
    max_date = (await db.execute(
        select(func.max(DailyPrice.date))
    )).scalar()

    if max_date:
        from_date = max_date + timedelta(days=1)
    else:
        from_date = full_start  # 初回: 5年前から

    # メインの差分取得（全銘柄一括）
    df = await asyncio.to_thread(
        jquants_client.get_daily_prices,
        from_date=from_date, to_date=date.today(),
    )
    await _process_and_upsert_prices(db, df)

    # ステップ2: カバー不足の銘柄を個別補完
    if backfill:
        coverage_map = await _get_coverage_map(db)
        backfill_codes = [
            c for c in valid_codes
            if coverage_map.get(c, 0) < 365 * (TARGET_YEARS - 1)
        ]
        for code in backfill_codes:
            bc_df = await asyncio.to_thread(
                jquants_client.get_daily_prices,
                code=code, from_date=full_start, to_date=date.today(),
            )
            await _process_and_upsert_prices(db, bc_df)
```

**ポイント:**

- `code` 指定なしの API は「指定日の全銘柄データ」を返すため、差分更新は日付単位で効率的に行える
- 新規上場銘柄や途中からウォッチ対象に追加した銘柄は、差分更新だけでは過去データが不足する。バックフィルで個別に補完する
- カバー範囲の判定は `(max_date - min_date).days` で算出し、4年未満なら再取得対象にする

### 財務データの差分更新

財務データも同様の2段階戦略ですが、判定基準が異なります。

```python
# 通期決算の年数でカバー範囲を判定
fin_coverage = (
    select(FinancialStatement.code,
           func.count(func.distinct(FinancialStatement.fiscal_year)))
    .where(FinancialStatement.fiscal_quarter == "4")
    .group_by(FinancialStatement.code)
)
# 5年分の通期データがなければバックフィル対象
backfill_codes = [c for c in codes if coverage.get(c, 0) < 5]
```

## 3. PostgreSQL upsert パターン — 冪等なデータ取り込み

### バッチ upsert の実装

J-Quants API から取得したデータを PostgreSQL に取り込む際、`ON CONFLICT DO UPDATE`（upsert）を使うことで冪等な処理を実現します。

```python
async def _batch_upsert(db, records, columns, batch_size=1000):
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        stmt = insert(DailyPrice).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=["code", "date"],  # ユニーク制約
            set_={
                col: stmt.excluded[col]
                for col in columns
                if col not in ("code", "date")  # キー列は除外
            },
        )
        await db.execute(stmt)
    await db.commit()
```

**ポイント:**

- `stmt.excluded` は `INSERT` しようとした値（= 新しい値）を参照する PostgreSQL の `EXCLUDED` テーブルに対応
- `index_elements` で衝突検出に使うカラムを指定。テーブルにユニーク制約が必要
- 1,000件ずつのバッチ処理で、メモリ使用量と DB 負荷を制御
- この処理は **冪等** なので、同じデータを何度投入しても結果が同じになる。障害時のリトライが安全

### 財務データの upsert: 完全性スコアによる重複制御

財務データは同じ決算期のデータが複数回発表されることがあります（速報→修正）。より完全なデータで上書きするため、完全性スコアを基準に重複を制御します。

```python
# 完全性スコアでソートし、最も完全なレコードを残す
df = df.sort_values("completeness_score")
df = df.drop_duplicates(
    subset=["code", "fiscal_year", "fiscal_quarter"],
    keep="last",  # completeness が高いものが最後に来る
)
```

## 4. 株式分割調整 — per-share 財務指標の正確な処理

### 問題: 分割前後で EPS/BPS/配当の比較ができない

株式分割が行われると、1株あたりの指標が不連続になります。例えば3:1分割があると、分割前の EPS 300円は分割後ベースでは 100円相当です。J-Quants の株価データは `adjustment_close`（調整後終値）を提供していますが、**財務データには分割調整が入っていません**。

### 解決: 株価データから累積分割比率を算出し、財務指標に適用

```
adjustment_close / close = 累積分割比率
```

例: 3:1分割の場合
- 分割前: close=3000, adjustment_close=1000 → 比率 0.333
- 分割後: close=1000, adjustment_close=1000 → 比率 1.0

```python
import bisect

async def _fetch_split_adjustments(db, grouped):
    """株式分割の調整係数を取得する"""
    # 1. 分割のある銘柄を特定（close != adjustment_close）
    split_codes = await _find_split_codes(db, list(grouped.keys()))

    # 2. 株価データから日付ごとの分割比率を取得
    price_data = {}
    for code in split_codes:
        rows = await db.execute(
            select(DailyPrice.date,
                   (DailyPrice.adjustment_close / DailyPrice.close).label("ratio"))
            .where(DailyPrice.code == code)
            .order_by(DailyPrice.date)
        )
        price_data[code] = [(r.date, float(r.ratio)) for r in rows]

    # 3. 各決算年度の調整係数を算出
    for code in split_codes:
        dates = [d for d, _ in price_data[code]]
        ratios = [r for _, r in price_data[code]]

        for fs in grouped[code]:
            fy_end = fs.fiscal_year_end

            # EPS/BPS用: 決算末日時点の比率
            idx = bisect.bisect_right(dates, fy_end) - 1
            end_ratio = ratios[idx] if idx >= 0 else 1.0

            # 配当用: 年度内の最小比率
            fy_start = date(fy_end.year - 1, fy_end.month, fy_end.day)
            start_idx = bisect.bisect_left(dates, fy_start)
            end_idx = bisect.bisect_right(dates, fy_end)
            min_ratio = min(ratios[start_idx:end_idx])
```

### なぜ EPS と配当で調整ロジックが異なるのか？

ここが最もハマったポイントです。

**EPS/BPS** は決算時点の株数ベースで報告されます。決算末日に有効な分割比率で調整すれば正確になります。

**配当** は四半期ごとに支払われ、各支払い時点の株数ベースで金額が決まります。年度途中に分割があった場合、分割前の四半期配当は分割前の株数ベースです。年間配当を分割後ベースで統一するには、年度内の最小比率（= 分割前の比率）で調整する必要があります。最小比率 = 分割前の比率 = 0.333 を掛けることで、分割後ベースに統一できます。

```python
# 調整の適用
def _adjust(value, factor):
    if value is None or factor == 1.0:
        return value
    return round(value * factor, 2)

# EPS: 決算末日の比率で調整
adjusted_eps = _adjust(raw_eps, fy_end_ratio.get(fiscal_year, 1.0))

# 配当: 年度内最小比率で調整
adjusted_div = _adjust(raw_div, min_ratio.get(fiscal_year, 1.0))
```

### 四半期配当からの年間配当復元

J-Quants の `DivAnn`（年間配当）が NaN の場合、四半期配当（`Div1Q` 〜 `DivFY`）から復元する必要があります。この際も各四半期の分割比率を個別に適用します。

```python
def _compute_annual_dividend(fs, date_ratios):
    """四半期配当から年間配当を計算する（分割調整込み）"""
    quarters = [fs.dividend_q1, fs.dividend_q2,
                fs.dividend_q3, fs.dividend_q4]

    # 各四半期の配当に対応する分割比率を適用
    total = 0.0
    for i, q_val in enumerate(quarters):
        if q_val is None or q_val == 0:
            continue
        lookup_date = _quarter_end_date(fs.fiscal_year_end, i + 1)
        dates = [d for d, _ in date_ratios]
        ratios = [r for _, r in date_ratios]
        idx = bisect.bisect_right(dates, lookup_date) - 1
        ratio = ratios[idx] if idx >= 0 else 1.0
        total += q_val * ratio

    return round(total, 2)
```

## J-Quants API のカラム名マッピング

記事の最後に、実装時に困りがちな J-Quants V2 のカラム名マッピングをまとめておきます。

| J-Quants カラム | 意味 | 備考 |
|---|---|---|
| `Code` | 銘柄コード | 末尾の `0` を含む5桁。4桁に切り詰めて使う |
| `CurPerType` | 決算期種別 | `FY`=通期, `3Q`, `2Q`, `1Q` |
| `CurFYEnd` | 決算期末日 | `YYYY-MM-DD` 形式。fiscal_year の導出に使う |
| `Sales` | 売上高 | — |
| `OP` | 営業利益 | — |
| `NP` | 当期純利益 | ROE/ROA の計算に使う |
| `EPS` | 1株あたり利益 | 分割未調整 |
| `BPS` | 1株あたり純資産 | 分割未調整 |
| `DivAnn` | 年間配当 | NaN の場合あり。四半期配当から復元が必要 |
| `Div1Q`〜`DivFY` | 四半期配当 | — |
| `Eq` | 自己資本 | ROE = NP / Eq * 100 |
| `TA` | 総資産 | ROA = NP / TA * 100 |

## まとめ

| 課題 | 解決策 |
|---|---|
| レート制限 | スレッドセーフな間隔制御 + 線形バックオフ |
| データ同期 | 差分更新 + バックフィルの2段階戦略 |
| 冪等な取り込み | PostgreSQL `ON CONFLICT DO UPDATE` |
| 株式分割 | `adjustment_close / close` で累積比率を算出し、EPS/配当で異なるロジックを適用 |

特に**株式分割調整**は、一見シンプルに見えて EPS と配当で異なるロジックが必要になる点が最大の落とし穴でした。J-Quants API を使って財務データの時系列比較を行う際は、この点を意識した設計をお勧めします。

---

本記事で紹介したコードは、FastAPI + Next.js 15 でテクニカル指標表示・ML 騰落予測・銘柄スクリーニングまで実装しています。
