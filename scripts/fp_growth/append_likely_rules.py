import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from pyspark.ml.fpm import FPGrowth
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    array,
    array_compact,
    array_contains,
    col,
    concat_ws,
    lit,
    size,
    when,
)


LOW_CONFIDENCE = 0.6
HIGH_CONFIDENCE = 0.7


def build_spark():
    spark = (
        SparkSession.builder
        .appName("FP-Growth Likely Rules")
        .master("local[*]")
        .config("spark.driver.memory", "4g")
        .config("spark.driver.extraJavaOptions", "-Duser.timezone=Asia/Ho_Chi_Minh")
        .config("spark.executor.extraJavaOptions", "-Duser.timezone=Asia/Ho_Chi_Minh")
        .config("spark.jars.packages", "org.postgresql:postgresql:42.7.4")
        .config("spark.sql.session.timeZone", "Asia/Ho_Chi_Minh")
        .getOrCreate()
    )
    spark._jvm.java.util.TimeZone.setDefault(
        spark._jvm.java.util.TimeZone.getTimeZone("Asia/Ho_Chi_Minh")
    )
    return spark


def load_config():
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")

    cfg = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "name": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "dwh": os.getenv("DB_SCHEMA_DWH"),
    }
    jdbc_url = (
        f"jdbc:postgresql://{cfg['host']}:{cfg['port']}/{cfg['name']}"
        "?options=-c%20TimeZone=Asia/Ho_Chi_Minh"
    )
    props = {
        "user": cfg["user"],
        "password": cfg["password"],
        "driver": "org.postgresql.Driver",
    }
    engine = create_engine(
        "postgresql+psycopg2://"
        f"{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['name']}"
    )
    return root, cfg["dwh"], jdbc_url, props, engine


def clean_existing_likely(engine, dwh):
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                DELETE FROM {dwh}.fact_cal_rules_fp_growth_buy
                WHERE confidence >= :low_confidence
                  AND confidence < :high_confidence
                """
            ),
            {"low_confidence": LOW_CONFIDENCE, "high_confidence": HIGH_CONFIDENCE},
        )
        conn.execute(
            text(
                f"""
                DELETE FROM {dwh}.fact_cal_rules_fp_growth_sell
                WHERE confidence >= :low_confidence
                  AND confidence < :high_confidence
                """
            ),
            {"low_confidence": LOW_CONFIDENCE, "high_confidence": HIGH_CONFIDENCE},
        )


def append_buy_likely_rules(spark, root, dwh, jdbc_url, props, engine):
    df_metric = pd.read_csv(root / "scripts" / "EDA" / "outputs" / "fact_metric_wide_format.csv")
    dim_weight_buy = pd.read_sql(
        text(
            f"""
            SELECT id, rank_no, rule_col, rule_name, weight, indicator_family
            FROM {dwh}.dim_weight_buy
            ORDER BY rank_no
            """
        ),
        engine,
    )

    pdf = df_metric.copy()
    pdf["period_date"] = pd.to_datetime(pdf["period_date"])
    pdf = pdf.sort_values(["symbol_key", "period_date"]).reset_index(drop=True)

    grouped = pdf.groupby("symbol_key", sort=False)
    prev1 = grouped.shift(1)
    prev2 = grouped.shift(2)

    feature_exprs = {
        "obv_lt_obv_ma_20": pdf["obv"] < pdf["obv_ma_20"],
        "rsi_14_gt_70": pdf["rsi_14"] > 70,
        "bb_percent_b_20_gt_1_0": pdf["bb_percent_b_20"] > 1.0,
        "close_price_gt_bb_upper_20": pdf["close_price"] > pdf["bb_upper_20"],
        "vol_ratio_20_gt_2_and_return_1d_gt_0": (pdf["vol_ratio_20"] > 2) & (pdf["return_1d"] > 0),
        "atr_14_gt_atr_ma_14": pdf["atr_14"] > pdf["atr_ma_14"],
        "return_5d_gt_0_08": pdf["return_5d"] > 0.08,
        "return_3d_gt_0_05": pdf["return_3d"] > 0.05,
        "close_price_gte_high_10d_mul_0_98": pdf["close_price"] >= pdf["high_10d"] * 0.98,
        "volume_gt_vol_ma_5_mul_1_5": pdf["volume"] > pdf["vol_ma_5"] * 1.5,
        "bb_width_20_increasing": pdf["bb_width_20"] > prev1["bb_width_20"],
        "rsi_14_decreasing_3_days": (pdf["rsi_14"] < prev1["rsi_14"]) & (prev1["rsi_14"] < prev2["rsi_14"]),
        "obv_decreasing_3_days": (pdf["obv"] < prev1["obv"]) & (prev1["obv"] < prev2["obv"]),
        "macd_hist_decreasing_3_days": (pdf["macd_hist"] < prev1["macd_hist"]) & (prev1["macd_hist"] < prev2["macd_hist"]),
        "return_1d_gt_0_04": pdf["return_1d"] > 0.04,
        "close_price_increasing_3_days": (pdf["close_price"] > prev1["close_price"]) & (prev1["close_price"] > prev2["close_price"]),
    }

    for rule in dim_weight_buy.itertuples(index=False):
        pdf[rule.rule_col] = feature_exprs[rule.id].fillna(False).astype(int)

    rule_cols = dim_weight_buy["rule_col"].tolist()
    weights = dim_weight_buy.set_index("rule_col").loc[rule_cols, "weight"].astype(float)
    pdf["rule_weight_total"] = pdf[rule_cols].mul(weights, axis=1).sum(axis=1)
    pdf["prediction"] = np.where(pdf["rule_weight_total"] >= 0.75, "sell", "buy")
    pdf = pdf.dropna(subset=["return_next_3d"]).copy()
    pdf["tomorrow_up"] = (pdf["return_next_3d"] > 0).astype(int)
    pdf["actual_signal"] = np.where(pdf["tomorrow_up"] == 1, "buy", "sell")
    pdf["actual"] = (pdf["actual_signal"] == "buy").astype(int)

    model_cols = [
        "period_date",
        "symbol_key",
        "close_price",
        "rule_weight_total",
        "prediction",
        "tomorrow_up",
        "actual",
        "actual_signal",
    ] + rule_cols
    df = spark.createDataFrame(pdf[model_cols])
    df_buy = df.filter(col("prediction") == "buy")
    df_buy = df_buy.withColumn("Buy", when(col("actual_signal") == "buy", 1).otherwise(0))

    item_exprs = [when(col(c) == 1, lit(c)).otherwise(None) for c in rule_cols]
    target_expr = when(col("Buy") == 1, lit("Buy")).otherwise(None)
    df_items_buy = df_buy.withColumn(
        "items",
        array_compact(array(*item_exprs, target_expr)),
    ).select("items")

    count_buy = df_items_buy.count()
    model_buy = FPGrowth(
        itemsCol="items",
        minSupport=5 / count_buy,
        minConfidence=LOW_CONFIDENCE,
    ).fit(df_items_buy)

    rule_buy = (
        model_buy.associationRules
        .filter(size(col("antecedent")) >= 3)
        .filter(array_contains(col("consequent"), "Buy"))
        .filter(~array_contains(col("antecedent"), "Buy"))
        .filter(col("confidence") >= LOW_CONFIDENCE)
        .filter(col("confidence") < HIGH_CONFIDENCE)
    )
    rules_buy_out = rule_buy.select(
        concat_ws(",", col("antecedent")).alias("antecedents"),
        concat_ws(",", col("consequent")).alias("consequents"),
        col("confidence"),
        col("lift"),
    )
    rules_buy_out.write.jdbc(
        url=jdbc_url,
        table=f"{dwh}.fact_cal_rules_fp_growth_buy",
        mode="append",
        properties=props,
    )
    return rules_buy_out.count()


def append_sell_likely_rules(spark, dwh, jdbc_url, props):
    df = spark.read.jdbc(
        url=jdbc_url,
        table=f"{dwh}.fact_txn_fp_growth_metrics",
        properties=props,
    )

    cols = df.columns
    new_cols = cols[:8] + [f"X{i}" for i in range(1, len(cols[8:]) + 1)]
    df = df.toDF(*new_cols)
    df = df.drop("close_price", "rule_weight_total", "actual_signal", "tomorrow_up")
    df = df.withColumn("prediction", when(col("prediction") == "buy", 1).otherwise(0))
    df_sell = df.filter(col("prediction") == 0)
    df_sell = df_sell.withColumn("Sell", when(col("actual") == 1, 1).otherwise(0))

    rule_cols = [c for c in df_sell.columns if c.startswith("X")]
    item_exprs = [when(col(c) == 1, lit(c)).otherwise(None) for c in rule_cols]
    target_expr = when(col("Sell") == 1, lit("Sell")).otherwise(None)
    df_items = df_sell.withColumn(
        "items",
        array_compact(array(*item_exprs, target_expr)),
    ).select("items")

    count = df_items.count()
    model = FPGrowth(
        itemsCol="items",
        minSupport=10 / count,
        minConfidence=LOW_CONFIDENCE,
    ).fit(df_items)

    rule_sell = (
        model.associationRules
        .filter(size(col("antecedent")) >= 3)
        .filter(array_contains(col("consequent"), "Sell"))
        .filter(~array_contains(col("antecedent"), "Sell"))
        .filter(col("confidence") >= LOW_CONFIDENCE)
        .filter(col("confidence") < HIGH_CONFIDENCE)
    )
    rules_out = rule_sell.select(
        concat_ws(",", col("antecedent")).alias("antecedents"),
        concat_ws(",", col("consequent")).alias("consequents"),
        col("confidence"),
        col("lift"),
    )
    rules_out.write.jdbc(
        url=jdbc_url,
        table=f"{dwh}.fact_cal_rules_fp_growth_sell",
        mode="append",
        properties=props,
    )
    return rules_out.count()


def main():
    spark = build_spark()
    root, dwh, jdbc_url, props, engine = load_config()
    clean_existing_likely(engine, dwh)
    buy_count = append_buy_likely_rules(spark, root, dwh, jdbc_url, props, engine)
    sell_count = append_sell_likely_rules(spark, dwh, jdbc_url, props)
    with engine.begin() as conn:
        conn.execute(text(f"call {dwh}.update_fact_cal_rules_fp_growth_prc();"))
    print(f"Appended likely buy rules : {buy_count}")
    print(f"Appended likely sell rules: {sell_count}")


if __name__ == "__main__":
    main()
