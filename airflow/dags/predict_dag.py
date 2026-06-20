"""Generate daily FP-growth predictions and send Telegram notifications."""
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
    "prediction_dag",
    default_args=default_args,
    description="Generate next-session FP-growth BUY/SELL/HOLD predictions",
    schedule_interval="30 21 * * 1-5",
    start_date=datetime(2026, 4, 1),
    catchup=False,
    tags=["prediction", "fp-growth"]
)

prediction_task = BashOperator(
    task_id="prediction",
    bash_command="""
    cd /opt/stock_project/scripts/fp_growth && \
    /opt/stock_project/scripts/ml/ml_venv/bin/python \
      /opt/stock_project/scripts/fp_growth/predict.py \
      --write-db \
      --update-actuals \
      --signals-only
    """,
    dag=dag
)

telegram_notify_task = BashOperator(
    task_id="telegram_notify",
    bash_command="""
    cd /opt/stock_project/scripts/notifications && \
    /opt/stock_project/scripts/ml/ml_venv/bin/python /opt/stock_project/scripts/notifications/notify_telegram.py
    """,
    dag=dag
)

prediction_task >> telegram_notify_task
