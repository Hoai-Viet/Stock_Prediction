import argparse
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import bindparam, create_engine, text


PIPELINE_NAME = "features_calculation"
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Recover daily stock features from staging intraday raw data."
    )
    parser.add_argument("--start-date", help="Optional YYYY-MM-DD lower bound.")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD upper bound.")
    parser.add_argument(
        "--pipeline-name",
        default=PIPELINE_NAME,
        help="Checkpoint key in dwh.fact_feature_checkpoint.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Exit 0 when recovery is needed; exit 99 when no missing dates exist.",
    )
    return parser.parse_args()


def load_env(project_root):
    env_candidates = [
        project_root / ".env",
        Path.cwd() / ".env",
        project_root / "scripts" / "crawling" / ".env",
    ]
    for env_path in env_candidates:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded env from {env_path}")
            return
    raise FileNotFoundError("Could not find .env for feature recovery")


def parse_date(value, name):
    try:
        return pd.Timestamp(value).date()
    except Exception as exc:
        raise ValueError(f"{name} must be a valid YYYY-MM-DD date") from exc


def get_required_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_engine():
    db_user = get_required_env("DB_USER")
    db_password = get_required_env("DB_PASSWORD")
    db_host = get_required_env("DB_HOST")
    db_port = get_required_env("DB_PORT")
    db_name = get_required_env("DB_NAME")
    return create_engine(
        f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )


def ensure_checkpoint_table(engine, dwh_schema):
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {dwh_schema}"))
        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {dwh_schema}.fact_feature_checkpoint (
                    pipeline_name VARCHAR(100) PRIMARY KEY,
                    last_processed_date DATE,
                    last_successful_run_id VARCHAR(255),
                    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    error_message TEXT
                )
                """
            )
        )


def get_checkpoint(engine, dwh_schema, pipeline_name):
    query = text(
        f"""
        SELECT last_processed_date, status
        FROM {dwh_schema}.fact_feature_checkpoint
        WHERE pipeline_name = :pipeline_name
        """
    )
    with engine.connect() as conn:
        row = conn.execute(query, {"pipeline_name": pipeline_name}).fetchone()
    if row is None:
        return None
    return {"last_processed_date": row[0], "status": row[1]}


def mark_checkpoint_running(engine, dwh_schema, pipeline_name, run_id):
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                INSERT INTO {dwh_schema}.fact_feature_checkpoint (
                    pipeline_name,
                    last_successful_run_id,
                    status,
                    updated_at,
                    error_message
                )
                VALUES (:pipeline_name, :run_id, 'RUNNING', now(), NULL)
                ON CONFLICT (pipeline_name) DO UPDATE
                SET status = 'RUNNING',
                    updated_at = now(),
                    error_message = NULL
                """
            ),
            {"pipeline_name": pipeline_name, "run_id": run_id},
        )


def mark_checkpoint_success(engine, dwh_schema, pipeline_name, run_id, last_date):
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                INSERT INTO {dwh_schema}.fact_feature_checkpoint (
                    pipeline_name,
                    last_processed_date,
                    last_successful_run_id,
                    status,
                    updated_at,
                    error_message
                )
                VALUES (:pipeline_name, :last_date, :run_id, 'SUCCESS', now(), NULL)
                ON CONFLICT (pipeline_name) DO UPDATE
                SET last_processed_date = EXCLUDED.last_processed_date,
                    last_successful_run_id = EXCLUDED.last_successful_run_id,
                    status = 'SUCCESS',
                    updated_at = now(),
                    error_message = NULL
                """
            ),
            {
                "pipeline_name": pipeline_name,
                "run_id": run_id,
                "last_date": last_date,
            },
        )


def mark_checkpoint_failed(engine, dwh_schema, pipeline_name, error_message):
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                INSERT INTO {dwh_schema}.fact_feature_checkpoint (
                    pipeline_name,
                    status,
                    updated_at,
                    error_message
                )
                VALUES (:pipeline_name, 'FAILED', now(), :error_message)
                ON CONFLICT (pipeline_name) DO UPDATE
                SET status = 'FAILED',
                    updated_at = now(),
                    error_message = EXCLUDED.error_message
                """
            ),
            {"pipeline_name": pipeline_name, "error_message": error_message[:2000]},
        )


def get_missing_dates(engine, staging_schema, dwh_schema, start_date, end_date):
    params = {"end_date": end_date}
    start_filter = ""
    if start_date:
        params["start_date"] = start_date
        start_filter = "AND raw_dates.trade_date >= :start_date"

    query = text(
        f"""
        WITH raw_dates AS (
            SELECT DISTINCT trade_date
            FROM {staging_schema}.fact_stock_price_intraday
            WHERE trade_date <= :end_date
        ),
        metric_dates AS (
            SELECT DISTINCT period_date
            FROM {dwh_schema}.fact_metric
            WHERE period_type = 'daily'
        ),
        cleaned_dates AS (
            SELECT DISTINCT period_date
            FROM {dwh_schema}.fact_cleaned_metric
            WHERE period_type = 'daily'
        )
        SELECT raw_dates.trade_date
        FROM raw_dates
        LEFT JOIN metric_dates
          ON metric_dates.period_date = raw_dates.trade_date
        LEFT JOIN cleaned_dates
          ON cleaned_dates.period_date = raw_dates.trade_date
        WHERE raw_dates.trade_date <= :end_date
          {start_filter}
          AND (
              metric_dates.period_date IS NULL
              OR cleaned_dates.period_date IS NULL
          )
        ORDER BY raw_dates.trade_date
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [row[0] for row in rows]


def get_max_ready_raw_date(engine, staging_schema, dwh_schema, start_date, end_date):
    params = {"end_date": end_date}
    start_filter = ""
    if start_date:
        params["start_date"] = start_date
        start_filter = "AND raw_dates.trade_date >= :start_date"

    query = text(
        f"""
        WITH raw_dates AS (
            SELECT DISTINCT trade_date
            FROM {staging_schema}.fact_stock_price_intraday
            WHERE trade_date <= :end_date
        ),
        metric_dates AS (
            SELECT DISTINCT period_date
            FROM {dwh_schema}.fact_metric
            WHERE period_type = 'daily'
        ),
        cleaned_dates AS (
            SELECT DISTINCT period_date
            FROM {dwh_schema}.fact_cleaned_metric
            WHERE period_type = 'daily'
        )
        SELECT max(raw_dates.trade_date)
        FROM raw_dates
        JOIN metric_dates
          ON metric_dates.period_date = raw_dates.trade_date
        JOIN cleaned_dates
          ON cleaned_dates.period_date = raw_dates.trade_date
        WHERE raw_dates.trade_date <= :end_date
          {start_filter}
        """
    )
    with engine.connect() as conn:
        return conn.execute(query, params).scalar()


def get_latest_cleaned_date(engine, dwh_schema, end_date):
    query = text(
        f"""
        SELECT max(period_date)
        FROM {dwh_schema}.fact_cleaned_metric
        WHERE period_type = 'daily'
          AND period_date <= :end_date
        """
    )
    with engine.connect() as conn:
        return conn.execute(query, {"end_date": end_date}).scalar()


def resolve_recovery_start_date(engine, dwh_schema, end_date, user_start_date, checkpoint):
    if user_start_date:
        return user_start_date

    if checkpoint and checkpoint["last_processed_date"]:
        start_date = checkpoint["last_processed_date"] + timedelta(days=1)
        print(
            "Using checkpoint start date: "
            f"{start_date} (last_processed_date={checkpoint['last_processed_date']})."
        )
        return start_date

    latest_cleaned_date = get_latest_cleaned_date(engine, dwh_schema, end_date)
    if latest_cleaned_date:
        start_date = latest_cleaned_date + timedelta(days=1)
        print(
            "No checkpoint date found. "
            f"Using fact_cleaned_metric start date: {start_date} "
            f"(latest_cleaned_date={latest_cleaned_date})."
        )
        return start_date

    return None


def compress_ranges(dates):
    if not dates:
        return []

    ranges = []
    start = dates[0]
    previous = dates[0]
    for current in dates[1:]:
        if current == previous + timedelta(days=1):
            previous = current
            continue
        ranges.append((start, previous))
        start = current
        previous = current
    ranges.append((start, previous))
    return ranges


def run_command(command, cwd):
    print(f"Running: {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def get_dbt_bin():
    configured = os.getenv("DBT_BIN")
    if configured:
        return configured
    linux_default = Path("/root/dbt_venv/bin/dbt")
    if linux_default.exists():
        return str(linux_default)
    return "dbt"


def run_dbt_fact_metric(project_root, start_date, end_date):
    dbt_project_dir = Path(os.getenv("DBT_PROJECT_DIR", project_root / "dbt"))
    dbt_vars = {
        "feature_start_date": start_date.isoformat(),
        "feature_end_date": end_date.isoformat(),
        "intraday_feature_only": True,
    }
    run_command(
        [
            get_dbt_bin(),
            "run",
            "--select",
            "dim_metric",
            "int_price_daily",
            "int_price_with_return",
            "int_technical_indicator",
            "fact_metric",
            "--vars",
            json.dumps(dbt_vars),
        ],
        cwd=dbt_project_dir,
    )


def run_cleaned_metric_backfill(project_root, start_date, end_date):
    script_path = project_root / "scripts" / "backfill" / "backfill_eda.py"
    run_command(
        [
            sys.executable,
            str(script_path),
            "--start-date",
            start_date.isoformat(),
            "--end-date",
            end_date.isoformat(),
        ],
        cwd=script_path.parent,
    )


def validate_processed_dates(engine, dwh_schema, dates):
    if not dates:
        return

    metric_query = text(
        f"""
        SELECT DISTINCT period_date
        FROM {dwh_schema}.fact_metric
        WHERE period_type = 'daily'
          AND period_date IN :dates
        """
    ).bindparams(bindparam("dates", expanding=True))
    cleaned_query = text(
        f"""
        SELECT DISTINCT period_date
        FROM {dwh_schema}.fact_cleaned_metric
        WHERE period_type = 'daily'
          AND period_date IN :dates
        """
    ).bindparams(bindparam("dates", expanding=True))
    params = {"dates": dates}
    with engine.connect() as conn:
        metric_dates = {row[0] for row in conn.execute(metric_query, params).fetchall()}
        cleaned_dates = {row[0] for row in conn.execute(cleaned_query, params).fetchall()}

    missing_metric = sorted(set(dates) - metric_dates)
    missing_cleaned = sorted(set(dates) - cleaned_dates)
    if missing_metric or missing_cleaned:
        raise RuntimeError(
            "Recovery validation failed. "
            f"Missing fact_metric dates={missing_metric}; "
            f"missing fact_cleaned_metric dates={missing_cleaned}"
        )


def main():
    args = parse_args()
    project_root = DEFAULT_PROJECT_ROOT
    load_env(project_root)

    staging_schema = os.getenv("DB_SCHEMA_STAGING") or os.getenv("DB_SCHEMA", "staging")
    dwh_schema = os.getenv("DB_SCHEMA_DWH", "dwh")
    end_date = parse_date(args.end_date, "--end-date")
    user_start_date = parse_date(args.start_date, "--start-date") if args.start_date else None
    run_id = os.getenv("AIRFLOW_CTX_DAG_RUN_ID") or f"manual__{pd.Timestamp.utcnow().isoformat()}"

    engine = get_engine()
    ensure_checkpoint_table(engine, dwh_schema)
    checkpoint = get_checkpoint(engine, dwh_schema, args.pipeline_name)
    start_date = resolve_recovery_start_date(
        engine,
        dwh_schema=dwh_schema,
        end_date=end_date,
        user_start_date=user_start_date,
        checkpoint=checkpoint,
    )

    missing_dates = get_missing_dates(
        engine,
        staging_schema=staging_schema,
        dwh_schema=dwh_schema,
        start_date=start_date,
        end_date=end_date,
    )

    if args.check_only:
        if missing_dates:
            print(
                f"Recovery needed for {len(missing_dates)} dates "
                f"from {missing_dates[0]} to {missing_dates[-1]}."
            )
            return
        print("No recovery needed.")
        return

    if not missing_dates:
        print("No missing daily feature dates found.")
        max_ready_date = get_max_ready_raw_date(
            engine,
            staging_schema=staging_schema,
            dwh_schema=dwh_schema,
            start_date=start_date,
            end_date=end_date,
        )
        if max_ready_date:
            last_date = max(
                checkpoint["last_processed_date"]
                if checkpoint and checkpoint.get("last_processed_date")
                else date(1900, 1, 1),
                max_ready_date,
            )
            mark_checkpoint_success(engine, dwh_schema, args.pipeline_name, run_id, last_date)
        return

    print(
        f"Found {len(missing_dates)} missing daily feature dates "
        f"from {missing_dates[0]} to {missing_dates[-1]}."
    )

    try:
        mark_checkpoint_running(engine, dwh_schema, args.pipeline_name, run_id)
        for range_start, range_end in compress_ranges(missing_dates):
            print(f"Recovering range {range_start} to {range_end}")
            range_dates = [
                current.date()
                for current in pd.date_range(range_start, range_end, freq="D")
                if current.date() in missing_dates
            ]
            run_dbt_fact_metric(project_root, range_start, range_end)
            run_cleaned_metric_backfill(project_root, range_start, range_end)
            validate_processed_dates(engine, dwh_schema, range_dates)

        success_date = max(
            checkpoint["last_processed_date"]
            if checkpoint and checkpoint.get("last_processed_date")
            else date(1900, 1, 1),
            max(missing_dates),
        )
        mark_checkpoint_success(
            engine,
            dwh_schema,
            args.pipeline_name,
            run_id,
            success_date,
        )
        print(f"Feature recovery completed through {success_date}.")
    except Exception as exc:
        mark_checkpoint_failed(engine, dwh_schema, args.pipeline_name, str(exc))
        raise


if __name__ == "__main__":
    main()
