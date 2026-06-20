import os
from pathlib import Path

import matplotlib.pyplot as plt
import missingno as msno
import pandas as pd
import seaborn as sns
from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, create_engine, text

env_candidates = [
    Path("../../.env"),
]
loaded_env_path = None
for env_candidate in env_candidates:
    if env_candidate.exists():
        load_dotenv(env_candidate)
        loaded_env_path = env_candidate.resolve()
        break

if loaded_env_path is None:
    raise FileNotFoundError("Could not find .env for EDA notebook")

# DB config
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Schema
DWH = os.getenv("DB_SCHEMA_DWH")

# Incremental EDA settings
ROLLING_OBV_WINDOW = 20
TAIL_DAILY_PERIODS = 40


def get_db_engine():
    return create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )


"Load recent fact_metric window"
engine = get_db_engine()

query = f"""
    with ranked_daily as (
        select
            symbol_key,
            period_date,
            period_type,
            metric_code,
            metric_value,
            dense_rank() over (
                partition by symbol_key
                order by period_date desc
            ) as period_rank
        from {DWH}.fact_metric
        where period_type = 'daily'
    )
    select symbol_key, period_date, period_type, metric_code, metric_value
    from ranked_daily
    where period_rank <= {TAIL_DAILY_PERIODS}
"""
print(f"Querying trailing {TAIL_DAILY_PERIODS} daily periods per symbol via SQLAlchemy...")
df = pd.read_sql(text(query), engine)

df_copy = df.copy()
df = df_copy

df.info()

# Pivot daily table
df_daily = df[df["period_type"] == 'daily']
df_daily = df_daily.drop(columns=['period_type'])
df_daily = df_daily.pivot_table(
    index=["symbol_key", "period_date"],
    columns="metric_code",
    values="metric_value",
    aggfunc="first"
).reset_index()
df_daily["period_date"] = pd.to_datetime(df_daily["period_date"])
df_daily.columns.name = None
df_daily.info()

msno.bar(df_daily)
plt.show()

latest_period_date = df_daily["period_date"].max()
print(f"Loaded {len(df_daily):,} pivoted daily rows from the last {TAIL_DAILY_PERIODS} periods per symbol")
if pd.notna(latest_period_date):
    latest_symbol_count = int(df_daily[df_daily["period_date"] == latest_period_date]["symbol_key"].nunique())
    print(f"Latest period_date in fact_metric: {latest_period_date.date()} ({latest_symbol_count:,} symbols)")
if "return_next_3d" in df_daily.columns:
    null_label_rows = int(df_daily["return_next_3d"].isna().sum())
    print(f"Rows with null return_next_3d retained for inference: {null_label_rows:,}")

df_daily = df_daily.sort_values(by=["symbol_key", "period_date"]).reset_index(drop=True)

df_daily.info()

df_daily.isna().sum()

df_daily["ma_5_norm"] = df_daily["ma_5"] / (df_daily["close_price"] - 1)
df_daily["ma_9_norm"] = df_daily["ma_9"] / (df_daily["close_price"] - 1)
df_daily["ma_15_norm"] = df_daily["ma_15"] / (df_daily["close_price"] - 1)
df_daily["ma_20_norm"] = df_daily["ma_20"] / (df_daily["close_price"] - 1)
df_daily["ema_12_norm"] = df_daily["ema_12"] / (df_daily["close_price"] - 1)
df_daily["ema_26_norm"] = df_daily["ema_26"] / (df_daily["close_price"] - 1)
df_daily["macd_line_norm"] = df_daily["macd_line"] / df_daily["close_price"]
df_daily["signal_line_norm"] = df_daily["signal_line"] / df_daily["close_price"]
df_daily["macd_hist_norm"] = df_daily["macd_hist"] / df_daily["close_price"]
df_daily["bb_width_norm"] = df_daily["bb_width_20"] / df_daily["close_price"]

obv_roll_mean = df_daily.groupby("symbol_key")["obv"].transform(
    lambda series: series.rolling(ROLLING_OBV_WINDOW, min_periods=ROLLING_OBV_WINDOW).mean()
)
obv_roll_std = df_daily.groupby("symbol_key")["obv"].transform(
    lambda series: series.rolling(ROLLING_OBV_WINDOW, min_periods=ROLLING_OBV_WINDOW).std()
)
df_daily["obv_zscore"] = (df_daily["obv"] - obv_roll_mean) / obv_roll_std
df_daily["ma5_vs_ma20"] = df_daily["ma_5"] / df_daily["ma_20"] - 1

df_daily = df_daily.dropna(subset=["obv_zscore"]).copy()
print(f"Rows remaining after {ROLLING_OBV_WINDOW}-period OBV z-score filter: {len(df_daily):,}")

df_daily.info()

df_daily = df_daily.drop(columns=[
    'close_price',
    'ma_5', 'ma_9', 'ma_15', 'ma_20',
    'ema_12', 'ema_26',
    'macd_line', 'signal_line', 'macd_hist',
    'bb_upper_20', 'bb_lower_20', 'bb_width_20',
    'volume', 'vol_ma_5', 'vol_ma_20',
    'obv',
])

df_daily.info()

from sqlalchemy.dialects.postgresql import insert

df_daily_latest = df_daily[df_daily["period_date"] == latest_period_date].copy()
print(f"Preparing latest-only cleaned metrics for {latest_period_date.date()}: {len(df_daily_latest):,} rows")

df_daily_long = (
    df_daily_latest.melt(
        id_vars=["symbol_key", "period_date"],
        var_name="metric_code",
        value_name="metric_value",
    )
    .dropna(subset=["metric_value"])
    .assign(period_type="daily")
)
df_daily_long["inserted_at"] = pd.Timestamp.now(tz="UTC").floor("s")

records = df_daily_long.to_dict(orient="records")
table = Table("fact_cleaned_metric", MetaData(), schema=DWH, autoload_with=engine)

chunksize = 5000
inserted = 0

with engine.begin() as conn:
    for i in range(0, len(records), chunksize):
        chunk = records[i : i + chunksize]
        stmt = insert(table).values(chunk).on_conflict_do_nothing(
            index_elements=["symbol_key", "period_date", "period_type", "metric_code"]
        )
        result = conn.execute(stmt)
        inserted += result.rowcount

print(f"Inserted {inserted:,} new rows / {len(records):,} latest-date rows attempted")
