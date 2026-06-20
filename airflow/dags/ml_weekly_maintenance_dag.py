"""
DAG: ML Weekly Maintenance
Runs Sunday at 3:00 AM.

Pipeline: train_model → mine_feature_pairs

Consolidates ml_model_training and ml_feature_pair_mining DAGs.
Training runs first so that FP-Growth mining uses the latest model.
"""
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
    description="Weekly ML maintenance: retrain model then mine feature pairs",
    schedule_interval="0 3 * * 0",  # Sunday at 3:00 AM
    start_date=datetime(2026, 2, 5),
    catchup=False,
    tags=["ml", "training", "fp-growth", "weekly", "maintenance"],
)

# --- Step 1: Retrain the trading model ---
train_model = BashOperator(
    task_id="train_trading_model",
    bash_command=f"""
    cd {PROJECT_ROOT}/scripts/ml && \
    {ML_VENV} train_model.py
    """,
    retry_delay=timedelta(minutes=30),
    execution_timeout=timedelta(hours=3),
    dag=dag,
)

# --- Step 2: FP-Growth feature pair mining ---
mine_feature_pairs = BashOperator(
    task_id="mine_feature_pairs",
    bash_command=f"""
    cd {PROJECT_ROOT}/scripts/fp_growth && \
    {ML_VENV} mine_feature_pairs.py
    """,
    retries=1,
    execution_timeout=timedelta(minutes=60),
    dag=dag,
)

train_model >> mine_feature_pairs
