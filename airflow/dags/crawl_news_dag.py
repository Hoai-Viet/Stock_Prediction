"""
DAG for crawling Vietnamese stock news.
Runs daily at 01:30 and writes raw data to staging tables.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["[EMAIL_ADDRESS]"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=10),
}


dag = DAG(
    "stock_crawl_news",
    default_args=default_args,
    description="Daily crawl of Vietnamese news sources for sentiment",
    schedule_interval="30 1 * * *",
    start_date=datetime(2026, 2, 12),
    catchup=False,
    tags=["stock", "crawling", "news", "sentiment"],
)


crawl_news_task = BashOperator(
    task_id="crawl_news_data",
    bash_command="""
    cd /opt/stock_project/scripts/crawling && \
    /opt/stock_project/scripts/crawling/cr_venv/bin/python crawl_news.py
    """,
    execution_timeout=timedelta(minutes=20),
    dag=dag,
)

build_news_features_task = BashOperator(
    task_id="build_news_features",
    bash_command="""
    cd /opt/stock_project/scripts/crawling && \
    /opt/stock_project/scripts/crawling/cr_venv/bin/python build_news_features.py
    """,
    execution_timeout=timedelta(minutes=15),
    dag=dag,
)


crawl_news_task >> build_news_features_task
