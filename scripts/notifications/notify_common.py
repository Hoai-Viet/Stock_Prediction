import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

SIGNAL_NOTIFICATION_TYPE = "ml_decision_signal"
EVALUATION_NOTIFICATION_TYPE = "ml_decision_evaluation"
EVALUATION_PENDING_NOTIFICATION_TYPE = "ml_decision_evaluation_pending"
CORRECTNESS_NOTIFICATION_TYPE = "ml_decision_correctness"
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]


@dataclass(frozen=True)
class NotificationBatch:
    trade_date: date
    model_version: str


@dataclass(frozen=True)
class Recipient:
    recipient_id: int
    recipient_name: str
    chat_id: str


@dataclass(frozen=True)
class EvaluationSummary:
    total_evaluated: int
    total_correct: int
    buy_correct: tuple[str, ...]
    buy_incorrect: tuple[str, ...]
    sell_correct: tuple[str, ...]
    sell_incorrect: tuple[str, ...]


@dataclass(frozen=True)
class CorrectnessSummary:
    total_checked: int
    total_correct: int
    buy_checked: int
    buy_correct: int
    sell_checked: int
    sell_correct: int
    correct_predictions: tuple[str, ...]
    incorrect_predictions: tuple[str, ...]


def load_environment():
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        raise FileNotFoundError(f"Could not find environment file at {env_path}")
    load_dotenv(env_path)
    return env_path


def get_db_connection():
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")

    missing = [
        name
        for name, value in {
            "DB_HOST": host,
            "DB_PORT": port,
            "DB_USER": user,
            "DB_PASSWORD": password,
            "DB_NAME": db_name,
        }.items()
        if not value
    ]
    if missing:
        missing_list = ", ".join(missing)
        raise ValueError(f"Missing required database settings: {missing_list}")

    return create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}",
        pool_pre_ping=True,
    )


def get_schema_names():
    dwh_schema = os.getenv("DB_SCHEMA_DWH", "dwh")
    staging_schema = os.getenv("DB_SCHEMA_STAGING", "staging")
    return dwh_schema, staging_schema


def get_latest_batch(engine, dwh_schema):
    query = text(
        f"""
        select trade_date, model_version
        from {dwh_schema}.fact_decision
        order by trade_date desc, generated_at desc nulls last, id desc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(query).mappings().first()
    if not row:
        return None
    return NotificationBatch(
        trade_date=row["trade_date"],
        model_version=row["model_version"],
    )


def get_latest_evaluated_batch(engine, dwh_schema):
    query = text(
        f"""
        select trade_date, model_version
        from {dwh_schema}.fact_decision
        where actual_direction is not null
          and predicted_label in ('BUY', 'SELL')
        group by trade_date, model_version
        order by trade_date desc, max(evaluated_at) desc nulls last, model_version desc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(query).mappings().first()
    if not row:
        return None
    return NotificationBatch(
        trade_date=row["trade_date"],
        model_version=row["model_version"],
    )


def get_latest_correctness_batch(engine, dwh_schema):
    query = text(
        f"""
        select trade_date, model_version
        from {dwh_schema}.fact_decision
        where is_correct is not null
          and predicted_label in ('BUY', 'SELL')
        group by trade_date, model_version
        order by trade_date desc, max(evaluated_at) desc nulls last, model_version desc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(query).mappings().first()
    if not row:
        return None
    return NotificationBatch(
        trade_date=row["trade_date"],
        model_version=row["model_version"],
    )


def get_batches_for_dates(engine, dwh_schema, start_date=None, end_date=None):
    filters = []
    params = {}
    if start_date:
        filters.append("trade_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        filters.append("trade_date <= :end_date")
        params["end_date"] = end_date

    where_clause = f"where {' and '.join(filters)}" if filters else ""
    query = text(
        f"""
        select trade_date, model_version
        from {dwh_schema}.fact_decision
        {where_clause}
        group by trade_date, model_version
        order by trade_date, model_version
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query, params).mappings().all()

    return [
        NotificationBatch(
            trade_date=row["trade_date"],
            model_version=row["model_version"],
        )
        for row in rows
    ]


def batch_has_evaluation(engine, dwh_schema, batch):
    query = text(
        f"""
        select count(*) as evaluated_count
        from {dwh_schema}.fact_decision
        where trade_date = :trade_date
          and model_version = :model_version
          and actual_direction is not null
          and predicted_label in ('BUY', 'SELL')
        """
    )
    with engine.connect() as conn:
        row = conn.execute(
            query,
            {
                "trade_date": batch.trade_date,
                "model_version": batch.model_version,
            },
        ).mappings().first()
    return bool(row and row["evaluated_count"])


def fetch_actionable_signals(engine, dwh_schema, staging_schema, batch):
    query = text(
        f"""
        select ds.symbol_code, d.predicted_label
        from {dwh_schema}.fact_decision d
        join {staging_schema}.dim_symbol ds
          on ds.symbol_key = d.symbol_key
        where d.trade_date = :trade_date
          and d.model_version = :model_version
          and d.predicted_label in ('BUY', 'SELL')
        order by d.predicted_label, ds.symbol_code
        """
    )
    signals = {"BUY": [], "SELL": []}
    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {
                "trade_date": batch.trade_date,
                "model_version": batch.model_version,
            },
        ).mappings()
        for row in rows:
            label = row["predicted_label"]
            symbol_code = row["symbol_code"]
            if label in signals and symbol_code:
                signals[label].append(str(symbol_code))
    return signals


def fetch_active_recipients(engine, staging_schema):
    query = text(
        f"""
        select recipient_id, recipient_name, chat_id
        from {staging_schema}.dim_telegram_recipient
        where is_active = true
        order by recipient_id
        """
    )
    recipients = []
    with engine.connect() as conn:
        rows = conn.execute(query).mappings()
        for row in rows:
            recipients.append(
                Recipient(
                    recipient_id=int(row["recipient_id"]),
                    recipient_name=row["recipient_name"] or "",
                    chat_id=str(row["chat_id"]),
                )
            )
    return recipients


def fetch_sent_recipient_ids(engine, dwh_schema, batch, notification_type):
    query = text(
        f"""
        select recipient_id
        from {dwh_schema}.fact_telegram_notification_log
        where trade_date = :trade_date
          and model_version = :model_version
          and notification_type = :notification_type
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {
                "trade_date": batch.trade_date,
                "model_version": batch.model_version,
                "notification_type": notification_type,
            },
        )
        return {int(row[0]) for row in rows}


def insert_notification_log(
    engine,
    dwh_schema,
    batch,
    recipient_id,
    telegram_message_id,
    notification_type,
):
    stmt = text(
        f"""
        insert into {dwh_schema}.fact_telegram_notification_log (
            recipient_id,
            trade_date,
            model_version,
            notification_type,
            telegram_message_id,
            sent_at
        )
        values (
            :recipient_id,
            :trade_date,
            :model_version,
            :notification_type,
            :telegram_message_id,
            current_timestamp
        )
        on conflict (recipient_id, trade_date, model_version, notification_type) do nothing
        """
    )
    with engine.begin() as conn:
        conn.execute(
            stmt,
            {
                "recipient_id": recipient_id,
                "trade_date": batch.trade_date,
                "model_version": batch.model_version,
                "notification_type": notification_type,
                "telegram_message_id": str(telegram_message_id),
            },
        )


def build_notification_message(batch, signals):
    buy_symbols = sorted(set(signals.get("BUY", [])))
    sell_symbols = sorted(set(signals.get("SELL", [])))

    sections = [
        "TÍN HIỆU DỰ ĐOÁN FP-GROWTH",
        f"Ngày giao dịch: {batch.trade_date}",
        f"Phiên bản mô hình: {batch.model_version}",
        "",
    ]

    if buy_symbols:
        sections.extend(
            [
                f"MUA - BUY ({len(buy_symbols)}):",
                ", ".join(buy_symbols),
                "",
            ]
        )

    if sell_symbols:
        sections.extend(
            [
                f"BÁN - SELL ({len(sell_symbols)}):",
                ", ".join(sell_symbols),
            ]
        )

    return "\n".join(sections).strip()


def fetch_evaluation_summary(engine, dwh_schema, staging_schema, batch):
    summary_query = text(
        f"""
        select
            count(*) as total_evaluated,
            count(*) filter (where is_correct = true) as total_correct
        from {dwh_schema}.fact_decision
        where trade_date = :trade_date
          and model_version = :model_version
          and actual_direction is not null
          and predicted_label in ('BUY', 'SELL')
        """
    )
    details_query = text(
        f"""
        select
            ds.symbol_code,
            d.predicted_label,
            d.actual_direction,
            coalesce(d.is_correct, false) as is_correct
        from {dwh_schema}.fact_decision d
        join {staging_schema}.dim_symbol ds
          on ds.symbol_key = d.symbol_key
        where d.trade_date = :trade_date
          and d.model_version = :model_version
          and d.actual_direction is not null
          and d.predicted_label in ('BUY', 'SELL')
        order by d.predicted_label, ds.symbol_code
        """
    )

    params = {
        "trade_date": batch.trade_date,
        "model_version": batch.model_version,
    }

    with engine.connect() as conn:
        summary_row = conn.execute(summary_query, params).mappings().first()
        detail_rows = conn.execute(details_query, params).mappings()

        buy_correct = []
        buy_incorrect = []
        sell_correct = []
        sell_incorrect = []

        for row in detail_rows:
            symbol_code = str(row["symbol_code"])
            predicted_label = row["predicted_label"]
            actual_direction = row["actual_direction"]
            is_correct = bool(row["is_correct"])

            if predicted_label == "BUY":
                if is_correct:
                    buy_correct.append(symbol_code)
                else:
                    buy_incorrect.append(
                        f"{symbol_code}: dự đoán BUY → thực tế {actual_direction}"
                    )
            elif predicted_label == "SELL":
                if is_correct:
                    sell_correct.append(symbol_code)
                else:
                    sell_incorrect.append(
                        f"{symbol_code}: dự đoán SELL → thực tế {actual_direction}"
                    )

    if not summary_row or not summary_row["total_evaluated"]:
        return None

    return EvaluationSummary(
        total_evaluated=int(summary_row["total_evaluated"] or 0),
        total_correct=int(summary_row["total_correct"] or 0),
        buy_correct=tuple(buy_correct),
        buy_incorrect=tuple(buy_incorrect),
        sell_correct=tuple(sell_correct),
        sell_incorrect=tuple(sell_incorrect),
    )


def build_evaluation_message(batch, summary):
    accuracy_pct = (summary.total_correct / summary.total_evaluated * 100) if summary.total_evaluated else 0.0
    buy_total = len(summary.buy_correct) + len(summary.buy_incorrect)
    sell_total = len(summary.sell_correct) + len(summary.sell_incorrect)
    buy_accuracy_pct = len(summary.buy_correct) / buy_total * 100 if buy_total else 0.0
    sell_accuracy_pct = len(summary.sell_correct) / sell_total * 100 if sell_total else 0.0

    sections = [
        "KẾT QUẢ ĐÁNH GIÁ DỰ ĐOÁN",
        f"Ngày giao dịch: {batch.trade_date}",
        f"Phiên bản mô hình: {batch.model_version}",
        "Cách đánh giá: giá đóng cửa của phiên kế tiếp so với phiên trước đó",
        f"Độ chính xác chung: {summary.total_correct}/{summary.total_evaluated} ({accuracy_pct:.1f}%)",
        (
            f"Độ chính xác BUY: {len(summary.buy_correct)}/{buy_total} "
            f"({buy_accuracy_pct:.1f}%)"
            if buy_total
            else "Độ chính xác BUY: Không có dự đoán"
        ),
        (
            f"Độ chính xác SELL: {len(summary.sell_correct)}/{sell_total} "
            f"({sell_accuracy_pct:.1f}%)"
            if sell_total
            else "Độ chính xác SELL: Không có dự đoán"
        ),
        "",
    ]

    if summary.buy_correct:
        sections.extend(
            [
                f"BUY đúng ({len(summary.buy_correct)}):",
                ", ".join(summary.buy_correct),
                "",
            ]
        )

    if summary.buy_incorrect:
        sections.extend(
            [
                f"BUY sai ({len(summary.buy_incorrect)}):",
                ", ".join(summary.buy_incorrect),
                "",
            ]
        )

    if summary.sell_correct:
        sections.extend(
            [
                f"SELL đúng ({len(summary.sell_correct)}):",
                ", ".join(summary.sell_correct),
                "",
            ]
        )

    if summary.sell_incorrect:
        sections.extend(
            [
                f"SELL sai ({len(summary.sell_incorrect)}):",
                ", ".join(summary.sell_incorrect),
            ]
        )

    return "\n".join(sections).strip()


def fetch_correctness_summary(engine, dwh_schema, staging_schema, batch):
    summary_query = text(
        f"""
        select
            count(*) as total_checked,
            count(*) filter (where is_correct = true) as total_correct,
            count(*) filter (where predicted_label = 'BUY') as buy_checked,
            count(*) filter (
                where predicted_label = 'BUY' and is_correct = true
            ) as buy_correct,
            count(*) filter (where predicted_label = 'SELL') as sell_checked,
            count(*) filter (
                where predicted_label = 'SELL' and is_correct = true
            ) as sell_correct
        from {dwh_schema}.fact_decision
        where trade_date = :trade_date
          and model_version = :model_version
          and is_correct is not null
          and predicted_label in ('BUY', 'SELL')
        """
    )
    details_query = text(
        f"""
        select
            ds.symbol_code,
            d.predicted_label,
            d.is_correct
        from {dwh_schema}.fact_decision d
        join {staging_schema}.dim_symbol ds
          on ds.symbol_key = d.symbol_key
        where d.trade_date = :trade_date
          and d.model_version = :model_version
          and d.is_correct is not null
          and d.predicted_label in ('BUY', 'SELL')
        order by d.is_correct desc, d.predicted_label, ds.symbol_code
        """
    )

    params = {
        "trade_date": batch.trade_date,
        "model_version": batch.model_version,
    }

    with engine.connect() as conn:
        summary_row = conn.execute(summary_query, params).mappings().first()
        detail_rows = conn.execute(details_query, params).mappings()

        correct_predictions = []
        incorrect_predictions = []
        for row in detail_rows:
            symbol_code = str(row["symbol_code"])
            predicted_label = row["predicted_label"]
            item = f"{symbol_code}({predicted_label})"
            if row["is_correct"]:
                correct_predictions.append(item)
            else:
                incorrect_predictions.append(item)

    if not summary_row or not summary_row["total_checked"]:
        return None

    return CorrectnessSummary(
        total_checked=int(summary_row["total_checked"] or 0),
        total_correct=int(summary_row["total_correct"] or 0),
        buy_checked=int(summary_row["buy_checked"] or 0),
        buy_correct=int(summary_row["buy_correct"] or 0),
        sell_checked=int(summary_row["sell_checked"] or 0),
        sell_correct=int(summary_row["sell_correct"] or 0),
        correct_predictions=tuple(correct_predictions),
        incorrect_predictions=tuple(incorrect_predictions),
    )


def build_correctness_message(batch, summary):
    accuracy_pct = (summary.total_correct / summary.total_checked * 100) if summary.total_checked else 0.0
    buy_accuracy_pct = (
        summary.buy_correct / summary.buy_checked * 100
        if summary.buy_checked
        else 0.0
    )
    sell_accuracy_pct = (
        summary.sell_correct / summary.sell_checked * 100
        if summary.sell_checked
        else 0.0
    )
    sections = [
        "Prediction correctness (BUY/SELL only)",
        f"Trade date: {batch.trade_date}",
        f"Model version: {batch.model_version}",
        f"Overall BUY/SELL: {summary.total_correct}/{summary.total_checked} ({accuracy_pct:.1f}%)",
        (
            f"BUY accuracy: {summary.buy_correct}/{summary.buy_checked} "
            f"({buy_accuracy_pct:.1f}%)"
            if summary.buy_checked
            else "BUY accuracy: N/A (0 predictions)"
        ),
        (
            f"SELL accuracy: {summary.sell_correct}/{summary.sell_checked} "
            f"({sell_accuracy_pct:.1f}%)"
            if summary.sell_checked
            else "SELL accuracy: N/A (0 predictions)"
        ),
        "",
    ]

    if summary.correct_predictions:
        sections.extend(
            [
                f"Correct predictions ({len(summary.correct_predictions)}):",
                ", ".join(summary.correct_predictions),
                "",
            ]
        )

    if summary.incorrect_predictions:
        sections.extend(
            [
                f"Incorrect predictions ({len(summary.incorrect_predictions)}):",
                ", ".join(summary.incorrect_predictions),
            ]
        )

    return "\n".join(sections).strip()


def build_evaluation_pending_message(batch):
    sections = [
        "TRẠNG THÁI ĐÁNH GIÁ",
        f"Ngày giao dịch: {batch.trade_date}",
        f"Phiên bản mô hình: {batch.model_version}",
        "Trạng thái: Chưa có kết quả đánh giá.",
        "Lý do: Chưa có giá đóng cửa của ngày dự đoán để tính biến động phiên kế tiếp.",
    ]
    return "\n".join(sections).strip()


def build_consolidated_message(messages):
    non_empty_messages = [message.strip() for message in messages if message and message.strip()]
    if not non_empty_messages:
        return ""

    return "\n\n────────────\n\n".join(
        ["BÁO CÁO DỰ ĐOÁN CỔ PHIẾU", *non_empty_messages]
    )
