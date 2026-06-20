"""
DAG for crawling financial statements (BCTC) for bank stocks
Runs daily at 2 AM to fetch balance sheet, income statement, cash flow, and ratios
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=10),
}

# Define the DAG
dag = DAG(
    'stock_crawl_financial_statements',
    default_args=default_args,
    description='Crawl financial statements (BCTC) for bank stocks',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    start_date=datetime(2026, 1, 22),
    catchup=False,
    tags=['stock', 'crawling', 'financial-statements', 'bctc'],
)

# Task to run the crawl_bctc.py script
# Task to run the crawl_bctc.py script using airflow_venv's python
crawl_task = BashOperator(
    task_id='crawl_financial_statements',
    bash_command="""
    cd /opt/stock_project/scripts/crawling && \
    /opt/stock_project/scripts/crawling/cr_venv/bin/python crawl_bctc.py
    """,
    execution_timeout=timedelta(hours=2),
    dag=dag,
)

crawl_task
