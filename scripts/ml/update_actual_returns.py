import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


BUY_THRESHOLD = 0.02
SELL_THRESHOLD = -0.02
FORWARD_HORIZON = 3
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]


def load_environment():
    env_candidates = [
        SCRIPT_DIR / ".env",
        REPO_ROOT / ".env",
    ]
    for env_path in env_candidates:
        if env_path.exists():
            load_dotenv(env_path)
            return env_path
    raise FileNotFoundError("Could not find .env for update_actual_returns.py")


def get_db_engine():
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")
    return create_engine(
        f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}",
        pool_pre_ping=True,
    )


def get_trading_dates(engine):
    query = text(
        """
        select distinct period_date
        from dwh.fact_metric
        where period_type = 'daily'
        order by period_date
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()
    return [row[0] for row in rows]


def resolve_prediction_and_evaluation_dates(engine, target_date=None):
    trading_dates = get_trading_dates(engine)
    if not trading_dates:
        return None, None, "No trading dates found in dwh.fact_metric."

    if target_date:
        try:
            prediction_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            return None, None, f"Invalid --date format: {target_date}. Expected YYYY-MM-DD."

        if prediction_date_obj not in trading_dates:
            return None, None, f"Prediction date {target_date} is not in trading calendar."

        pred_idx = trading_dates.index(prediction_date_obj)
        eval_idx = pred_idx + FORWARD_HORIZON
        if eval_idx >= len(trading_dates):
            return None, None, (
                f"Not enough future trading days after {target_date} "
                f"for T+{FORWARD_HORIZON} evaluation."
            )

        evaluation_date_obj = trading_dates[eval_idx]
        return prediction_date_obj.strftime("%Y-%m-%d"), evaluation_date_obj.strftime("%Y-%m-%d"), None

    if len(trading_dates) <= FORWARD_HORIZON:
        return None, None, "Not enough trading history to resolve evaluation window."

    evaluation_date_obj = trading_dates[-1]
    prediction_date_obj = trading_dates[-(FORWARD_HORIZON + 1)]
    return prediction_date_obj.strftime("%Y-%m-%d"), evaluation_date_obj.strftime("%Y-%m-%d"), None


def print_existing_summary(engine, prediction_date):
    status_query = text(
        """
        select
            count(*) as total_predictions,
            count(*) filter (where actual_direction is not null) as evaluated_predictions
        from dwh.fact_decision
        where trade_date = :pred_date
        """
    )
    with engine.connect() as conn:
        status = conn.execute(status_query, {"pred_date": prediction_date}).fetchone()

    total_predictions = int(status[0] or 0)
    evaluated_predictions = int(status[1] or 0)

    if total_predictions == 0:
        print(f"No predictions found for {prediction_date}")
        return

    if evaluated_predictions == 0:
        print(f"No pending rows could be updated for {prediction_date}")
        print("Likely missing return_3d for the evaluation date, or predictions were not generated yet.")
        return

    print(f"Predictions for {prediction_date} were already evaluated.")
    print(f"Total: {total_predictions}, Evaluated: {evaluated_predictions}")


def update_actual_returns(target_date=None):
    env_path = load_environment()
    engine = get_db_engine()

    prediction_date, evaluation_date, err = resolve_prediction_and_evaluation_dates(
        engine, target_date=target_date
    )
    if err:
        print(err)
        return 0

    print(f"Loaded environment from: {env_path}")
    print("=" * 70)
    print("UPDATING ACTUAL RETURNS")
    print("=" * 70)
    print(f"Prediction Date: {prediction_date}")
    print(f"Evaluation Date: {evaluation_date} (using return_3d at T+{FORWARD_HORIZON})")
    print(f"Thresholds: BUY > {BUY_THRESHOLD:.2%}, SELL < {SELL_THRESHOLD:.2%}")
    print()

    update_query = text(
        """
        with actuals as (
            select
                d.id,
                d.symbol_key,
                d.predicted_label,
                m.metric_value::float as actual_return
            from dwh.fact_decision d
            join dwh.fact_metric m
              on m.symbol_key = d.symbol_key
             and m.period_date = :eval_date
             and m.period_type = 'daily'
             and m.metric_code = 'return_3d'
            where d.trade_date = :pred_date
              and d.actual_direction is null
        )
        update dwh.fact_decision d
        set
            actual_direction = case
                when a.actual_return > :buy_threshold then 'BUY'
                when a.actual_return < :sell_threshold then 'SELL'
                else 'SILENT'
            end,
            is_correct = d.predicted_label = case
                when a.actual_return > :buy_threshold then 'BUY'
                when a.actual_return < :sell_threshold then 'SELL'
                else 'SILENT'
            end,
            evaluated_at = current_timestamp
        from actuals a
        where d.id = a.id
        returning
            d.symbol_key,
            d.predicted_label,
            d.actual_direction,
            a.actual_return
        """
    )

    with engine.begin() as conn:
        rows = conn.execute(
            update_query,
            {
                "pred_date": prediction_date,
                "eval_date": evaluation_date,
                "buy_threshold": BUY_THRESHOLD,
                "sell_threshold": SELL_THRESHOLD,
            },
        ).fetchall()

    if not rows:
        print_existing_summary(engine, prediction_date)
        return 0

    print(f"Updated {len(rows)} predictions")
    print("Sample:")
    for row in rows[:5]:
        symbol_key, predicted_label, actual_direction, actual_return = row
        status = "OK" if predicted_label == actual_direction else "NG"
        print(
            f"  symbol_key={symbol_key} | predicted={predicted_label} | "
            f"actual={actual_direction} | return_3d={actual_return:+.2%} {status}"
        )

    summary_query = text(
        """
        select
            predicted_label,
            count(*) as total,
            count(*) filter (where is_correct = true) as correct,
            round(avg(case when is_correct = true then 1.0 else 0.0 end) * 100, 1) as accuracy_pct
        from dwh.fact_decision
        where trade_date = :pred_date
          and actual_direction is not null
        group by predicted_label
        order by predicted_label
        """
    )
    with engine.connect() as conn:
        summary_rows = conn.execute(summary_query, {"pred_date": prediction_date}).fetchall()

    print("\nAccuracy summary:")
    for predicted_label, total, correct, accuracy_pct in summary_rows:
        print(f"  {predicted_label:6} | {correct}/{total} correct | {accuracy_pct}%")

    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update actual returns for predictions")
    parser.add_argument(
        "--date",
        type=str,
        required=False,
        help=(
            "Prediction date to evaluate (YYYY-MM-DD). "
            "If not provided, evaluates predictions from FORWARD_HORIZON trading days ago."
        ),
    )
    args = parser.parse_args()

    try:
        count = update_actual_returns(args.date)
        print(f"\nSuccessfully updated {count} predictions")
    except Exception as exc:
        print(f"\nError: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
