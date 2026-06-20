"""
DAG: Data Quality Report
Runs Mon-Fri at 09:00 ICT (after ml_evaluate finishes at 08:00).

Single task: checks data quality across all crawlers and ML pipeline,
outputs a formatted console report.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_ROOT = "/opt/stock_project"
CRAWL_VENV = f"{PROJECT_ROOT}/scripts/crawling/cr_venv/bin/python"

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

dag = DAG(
    "data_quality_report",
    default_args=default_args,
    description="Daily data quality report: crawl logs, data gaps, coverage, ML health",
    schedule_interval="0 2 * * 1-5",  # 09:00 ICT (UTC+7) = 02:00 UTC
    start_date=datetime(2026, 3, 1),
    catchup=False,
    tags=["stock", "monitoring", "data-quality"],
)

run_report = BashOperator(
    task_id="run_data_quality_report",
    bash_command=f"""
    cd {PROJECT_ROOT}/scripts && \
    {CRAWL_VENV} data_quality_report.py
    """,
    execution_timeout=timedelta(minutes=5),
    dag=dag,
)
