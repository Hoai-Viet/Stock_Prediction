"""Refresh FP-Growth BUY/SELL combo rules every Sunday at 3:00 AM."""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_ROOT = "/opt/stock_project"
ML_VENV = f"{PROJECT_ROOT}/scripts/ml/ml_venv/bin/python"

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}

dag = DAG(
    "ml_weekly_maintenance",
    default_args=default_args,
    description="Weekly FP-Growth combo-rule refresh",
    schedule_interval="0 3 * * 0",  # Sunday at 3:00 AM
    start_date=datetime(2026, 2, 5),
    catchup=False,
    tags=["fp-growth", "rules", "weekly", "maintenance"],
)

refresh_combo_rules = BashOperator(
    task_id="refresh_combo_rules",
    bash_command=f"""
    cd {PROJECT_ROOT}/scripts/fp_growth && \
    {ML_VENV} append_likely_rules.py
    """,
    retries=1,
    execution_timeout=timedelta(hours=2),
    dag=dag,
)
