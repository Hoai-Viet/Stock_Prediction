"""Build daily feature metrics used by FP-growth prediction."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "yashinwoo",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=10)
}

dag = DAG(
    "features_calculation",
    default_args=default_args,
    description="Build dwh.fact_metric from staging intraday prices for FP-growth prediction",
    schedule_interval="30 20 * * 1-5",
    start_date=datetime(2026, 3, 29),
    catchup=False,
    max_active_runs=1,
    tags=["feature", "metric", "fp-growth"]
)

build_fact_metric = BashOperator(
    task_id="build_fact_metric",
    bash_command="""
    cd /opt/stock_project/dbt && \
    /root/dbt_venv/bin/dbt run \
      --select dim_metric int_price_daily int_price_with_return int_technical_indicator fact_metric \
      --vars '{"intraday_feature_only": true}'
    """,
    dag=dag
)