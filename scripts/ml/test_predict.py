import argparse
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


BUY_THRESHOLD = 0.02
SELL_THRESHOLD = -0.02
FORWARD_HORIZON = 3
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_environment():
    env_candidates = [
        SCRIPT_DIR / ".env",
        REPO_ROOT / ".env",
    ]
    for env_path in env_candidates:
        if env_path.exists():
            load_dotenv(env_path)
            return env_path
    raise FileNotFoundError("Could not find .env for test_predict.py")


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


def sql_identifier(name, label):
    if not name or not IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid {label}: {name!r}")
    return name


def get_table_config(args):
    schema = sql_identifier(args.schema or os.getenv("DB_SCHEMA_DWH", "dwh"), "schema")
    decision_table = sql_identifier(
        args.decision_table or os.getenv("FACT_DECISION_TABLE", "fact_decision"),
        "decision table",
    )
    metric_table = sql_identifier(
        args.metric_table or os.getenv("FACT_METRIC_TABLE", "fact_metric"),
        "metric table",
    )
    return schema, decision_table, metric_table


def build_filters(args):
    labels = ("BUY", "SELL", "SILENT") if args.include_silent else ("BUY", "SELL")
    label_placeholders = ", ".join(f":label_{idx}" for idx, _ in enumerate(labels))
    filters = [f"d.predicted_label in ({label_placeholders})"]
    params = {
        "buy_threshold": args.buy_threshold,
        "sell_threshold": args.sell_threshold,
        "forward_horizon": args.forward_horizon,
    }
    params.update({f"label_{idx}": label for idx, label in enumerate(labels)})

    if args.date:
        filters.append("d.trade_date = :trade_date")
        params["trade_date"] = args.date
    if args.start_date:
        filters.append("d.trade_date >= :start_date")
        params["start_date"] = args.start_date
    if args.end_date:
        filters.append("d.trade_date <= :end_date")
        params["end_date"] = args.end_date
    if args.model_version:
        filters.append("d.model_version = :model_version")
        params["model_version"] = args.model_version

    return " and ".join(filters), params


def fetch_accuracy_rows(engine, schema, decision_table, metric_table, args):
    where_clause, params = build_filters(args)

    query = text(
        f"""
        with trading_dates as (
            select
                period_date,
                row_number() over (order by period_date) as rn
            from (
                select distinct period_date
                from {schema}.{metric_table}
                where period_type = 'daily'
            ) x
        ),
        decisions as (
            select
                d.id,
                d.symbol_key,
                d.trade_date,
                d.predicted_label,
                d.actual_direction as stored_actual_direction,
                d.is_correct as stored_is_correct,
                d.model_version,
                eval_dates.period_date as evaluation_date
            from {schema}.{decision_table} d
            join trading_dates pred_dates
              on pred_dates.period_date = d.trade_date
            left join trading_dates eval_dates
              on eval_dates.rn = pred_dates.rn + :forward_horizon
            where {where_clause}
        ),
        scored as (
            select
                d.id,
                d.symbol_key,
                d.trade_date,
                d.evaluation_date,
                d.predicted_label,
                d.model_version,
                d.stored_actual_direction,
                d.stored_is_correct,
                m.metric_value::float as actual_return,
                case
                    when m.metric_value::float > :buy_threshold then 'BUY'
                    when m.metric_value::float < :sell_threshold then 'SELL'
                    when m.metric_value is not null then 'SILENT'
                    else null
                end as computed_actual_direction
            from decisions d
            left join {schema}.{metric_table} m
              on m.symbol_key = d.symbol_key
             and m.period_date = d.evaluation_date
             and m.period_type = 'daily'
             and m.metric_code = 'return_3d'
        )
        select
            id,
            symbol_key,
            trade_date,
            evaluation_date,
            predicted_label,
            coalesce(computed_actual_direction, stored_actual_direction) as actual_direction,
            actual_return,
            model_version,
            case
                when coalesce(computed_actual_direction, stored_actual_direction) is null then null
                else predicted_label = coalesce(computed_actual_direction, stored_actual_direction)
            end as is_correct
        from scored
        order by trade_date, predicted_label, symbol_key
        """
    )

    with engine.connect() as conn:
        return conn.execute(query, params).mappings().all()


def pct(correct, total):
    if not total:
        return 0.0
    return correct / total * 100


def print_summary(rows, args):
    total_predictions = len(rows)
    evaluated_rows = [row for row in rows if row["actual_direction"] is not None]
    pending_rows = total_predictions - len(evaluated_rows)

    if not rows:
        print("No BUY/SELL predictions found for the selected filters.")
        return 1

    total_correct = sum(1 for row in evaluated_rows if row["is_correct"])
    print("=" * 70)
    title = "ALL PREDICTION ACCURACY" if args.include_silent else "BUY/SELL PREDICTION ACCURACY"
    print(title)
    print("=" * 70)
    total_label = "Total predictions" if args.include_silent else "Total BUY/SELL predictions"
    print(f"{total_label}: {total_predictions:,}")
    print(f"Evaluated predictions:      {len(evaluated_rows):,}")
    print(f"Pending/no actual data:     {pending_rows:,}")
    print(f"Overall accuracy:           {total_correct:,}/{len(evaluated_rows):,} = {pct(total_correct, len(evaluated_rows)):.2f}%")

    print("\nBy predicted label:")
    print(f"{'Label':<8} {'Correct':>10} {'Total':>10} {'Accuracy':>10}")
    print("-" * 42)
    labels = ("BUY", "SELL", "SILENT") if args.include_silent else ("BUY", "SELL")
    for label in labels:
        label_rows = [row for row in evaluated_rows if row["predicted_label"] == label]
        label_correct = sum(1 for row in label_rows if row["is_correct"])
        print(f"{label:<8} {label_correct:>10,} {len(label_rows):>10,} {pct(label_correct, len(label_rows)):>9.2f}%")

    print("\nConfusion matrix (predicted -> actual):")
    print(f"{'Predicted':<10} {'BUY':>8} {'SELL':>8} {'SILENT':>8}")
    print("-" * 38)
    for predicted in labels:
        counts = {
            actual: sum(
                1
                for row in evaluated_rows
                if row["predicted_label"] == predicted and row["actual_direction"] == actual
            )
            for actual in ("BUY", "SELL", "SILENT")
        }
        print(f"{predicted:<10} {counts['BUY']:>8,} {counts['SELL']:>8,} {counts['SILENT']:>8,}")

    if args.by_date:
        print("\nBy trade_date:")
        print(f"{'Date':<12} {'Correct':>10} {'Total':>10} {'Accuracy':>10}")
        print("-" * 46)
        dates = sorted({row["trade_date"] for row in evaluated_rows})
        for trade_date in dates:
            date_rows = [row for row in evaluated_rows if row["trade_date"] == trade_date]
            date_correct = sum(1 for row in date_rows if row["is_correct"])
            print(f"{str(trade_date):<12} {date_correct:>10,} {len(date_rows):>10,} {pct(date_correct, len(date_rows)):>9.2f}%")

    if args.show_wrong:
        wrong_rows = [row for row in evaluated_rows if not row["is_correct"]]
        print(f"\nWrong samples (first {args.show_wrong}):")
        print(f"{'Date':<12} {'Symbol':>8} {'Pred':<6} {'Actual':<6} {'Return':>10} {'Model':<20}")
        print("-" * 72)
        for row in wrong_rows[: args.show_wrong]:
            actual_return = row["actual_return"]
            actual_return_text = "N/A" if actual_return is None else f"{actual_return:+.2%}"
            print(
                f"{str(row['trade_date']):<12} "
                f"{row['symbol_key']:>8} "
                f"{row['predicted_label']:<6} "
                f"{row['actual_direction']:<6} "
                f"{actual_return_text:>10} "
                f"{row['model_version']:<20}"
            )

    return 0


def parse_args():
    parser = argparse.ArgumentParser(
        description="Test BUY/SELL prediction accuracy from the prediction table without updating DB."
    )
    parser.add_argument("--date", help="Only one prediction trade date (YYYY-MM-DD)")
    parser.add_argument("--start-date", help="Start prediction trade date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End prediction trade date (YYYY-MM-DD)")
    parser.add_argument("--model-version", help="Filter one model_version")
    parser.add_argument("--schema", help="DWH schema. Default: DB_SCHEMA_DWH or dwh")
    parser.add_argument("--decision-table", help="Prediction table. Default: FACT_DECISION_TABLE or fact_decision")
    parser.add_argument("--metric-table", help="Metric table. Default: FACT_METRIC_TABLE or fact_metric")
    parser.add_argument("--forward-horizon", type=int, default=FORWARD_HORIZON)
    parser.add_argument("--buy-threshold", type=float, default=BUY_THRESHOLD)
    parser.add_argument("--sell-threshold", type=float, default=SELL_THRESHOLD)
    parser.add_argument("--by-date", action="store_true", help="Print accuracy grouped by trade_date")
    parser.add_argument("--show-wrong", type=int, default=10, help="Show first N wrong rows. Use 0 to hide.")
    parser.add_argument("--include-silent", action="store_true", help="Include predicted SILENT rows in accuracy.")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.date and (args.start_date or args.end_date):
        raise ValueError("--date cannot be combined with --start-date or --end-date")

    env_path = load_environment()
    schema, decision_table, metric_table = get_table_config(args)
    engine = get_db_engine()

    print(f"Loaded environment from: {env_path}")
    print(f"Using prediction table: {schema}.{decision_table}")
    print(f"Using metric table:     {schema}.{metric_table}")
    print(f"Evaluation rule: BUY > {args.buy_threshold:.2%}, SELL < {args.sell_threshold:.2%}, horizon T+{args.forward_horizon}")
    print(f"Predicted labels:       {'BUY, SELL, SILENT' if args.include_silent else 'BUY, SELL'}")

    rows = fetch_accuracy_rows(engine, schema, decision_table, metric_table, args)
    return print_summary(rows, args)


if __name__ == "__main__":
    raise SystemExit(main())
