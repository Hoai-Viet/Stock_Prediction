"""
Daily crawl intraday stock price of 22 symbols at 7:00pm
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

# Default arguments for dag
default_args = {
    "owner": "yashinwoo",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=10)
}

# Define the dag
dag = DAG(
    "stock_crawl_intraday",
    default_args=default_args,
    description="crawl minute candles intraday for bank stock",
    schedule_interval="0 19 * * 1-5",
    start_date=datetime(2026, 3, 29),
    catchup=False,
    tags=['stock', 'crawling', 'intraday', 'bctc']
)

# Task to run script crawl intraday
crawl_task = BashOperator(
    task_id="crawl_stock_intraday",
    bash_command="""
    cd /opt/stock_project/scripts/crawling && \
    /opt/stock_project/scripts/crawling/cr_venv/bin/python crawl_intraday.py
    """,
    dag=dag
)

