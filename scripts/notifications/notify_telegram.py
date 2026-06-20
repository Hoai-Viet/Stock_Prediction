import argparse
import logging
import os

import requests

from notify_common import (
    EVALUATION_PENDING_NOTIFICATION_TYPE,
    EVALUATION_NOTIFICATION_TYPE,
    SIGNAL_NOTIFICATION_TYPE,
    build_consolidated_message,
    build_evaluation_message,
    build_evaluation_pending_message,
    build_notification_message,
    fetch_active_recipients,
    fetch_actionable_signals,
    fetch_evaluation_summary,
    fetch_sent_recipient_ids,
    get_batches_for_dates,
    get_db_connection,
    get_latest_batch,
    get_latest_evaluated_batch,
    get_schema_names,
    insert_notification_log,
    load_environment,
)
from telegram_client import send_telegram_message


def collect_batch_notifications(engine, dwh_schema, staging_schema, batch):
    notifications = []
    signals = fetch_actionable_signals(engine, dwh_schema, staging_schema, batch)

    if signals["BUY"] or signals["SELL"]:
        notifications.append(
            (
                batch,
                SIGNAL_NOTIFICATION_TYPE,
                build_notification_message(batch, signals),
            )
        )
    else:
        logging.info(
            "No BUY/SELL signals found for trade_date=%s model_version=%s.",
            batch.trade_date,
            batch.model_version,
        )

    evaluation_summary = fetch_evaluation_summary(
        engine=engine,
        dwh_schema=dwh_schema,
        staging_schema=staging_schema,
        batch=batch,
    )
    if evaluation_summary:
        notifications.append(
            (
                batch,
                EVALUATION_NOTIFICATION_TYPE,
                build_evaluation_message(batch, evaluation_summary),
            )
        )
    else:
        notifications.append(
            (
                batch,
                EVALUATION_PENDING_NOTIFICATION_TYPE,
                build_evaluation_pending_message(batch),
            )
        )

    return notifications


def send_consolidated_notifications(
    *,
    engine,
    dwh_schema,
    recipients,
    bot_token,
    notifications,
    force=False,
):
    if not notifications:
        logging.info("No notification content to send.")
        return

    sent_by_notification = {}
    if not force:
        for batch, notification_type, _message in notifications:
            key = (batch, notification_type)
            sent_by_notification[key] = fetch_sent_recipient_ids(
                engine=engine,
                dwh_schema=dwh_schema,
                batch=batch,
                notification_type=notification_type,
            )

    sent_count = 0
    skipped_count = 0
    failed_count = 0

    for recipient in recipients:
        pending_notifications = notifications
        if not force:
            pending_notifications = [
                item
                for item in notifications
                if recipient.recipient_id not in sent_by_notification[(item[0], item[1])]
            ]
        if not pending_notifications:
            skipped_count += 1
            logging.info(
                "Skipping recipient_id=%s chat_id=%s because all report sections were already sent.",
                recipient.recipient_id,
                recipient.chat_id,
            )
            continue

        message = build_consolidated_message(
            [item[2] for item in pending_notifications]
        )

        try:
            telegram_message_id = send_telegram_message(
                bot_token=bot_token,
                chat_id=recipient.chat_id,
                message=message,
            )
            for batch, notification_type, _section in pending_notifications:
                insert_notification_log(
                    engine=engine,
                    dwh_schema=dwh_schema,
                    batch=batch,
                    recipient_id=recipient.recipient_id,
                    telegram_message_id=telegram_message_id,
                    notification_type=notification_type,
                )
            sent_count += 1
            logging.info(
                "Consolidated report with %s sections sent to recipient_id=%s chat_id=%s.",
                len(pending_notifications),
                recipient.recipient_id,
                recipient.chat_id,
            )
        except (requests.RequestException, RuntimeError) as exc:
            failed_count += 1
            logging.warning(
                "Failed to send consolidated report to recipient_id=%s chat_id=%s: %s",
                recipient.recipient_id,
                recipient.chat_id,
                exc,
            )

    logging.info(
        "Consolidated notification run finished: sent=%s skipped=%s failed=%s.",
        sent_count,
        skipped_count,
        failed_count,
    )


def main():
    parser = argparse.ArgumentParser(description="Send Telegram prediction notifications")
    parser.add_argument("--date", help="Notify one prediction trade date (YYYY-MM-DD)")
    parser.add_argument("--start-date", help="Start trade date for notification range")
    parser.add_argument("--end-date", help="End trade date for notification range")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Send again even when the notification log says it was already sent",
    )
    args = parser.parse_args()

    if args.date and (args.start_date or args.end_date):
        raise ValueError("--date cannot be combined with --start-date or --end-date")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    env_path = load_environment()
    logging.info("Loaded environment from: %s", env_path)

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logging.warning("TELEGRAM_BOT_TOKEN is not configured. Skipping notification.")
        return

    engine = get_db_connection()
    dwh_schema, staging_schema = get_schema_names()

    recipients = fetch_active_recipients(engine, staging_schema)
    if not recipients:
        logging.warning(
            "No active Telegram recipients found in %s.dim_telegram_recipient. Skipping.",
            staging_schema,
        )
        return

    if args.date or args.start_date or args.end_date:
        start_date = args.date or args.start_date
        end_date = args.date or args.end_date
        batches = get_batches_for_dates(
            engine,
            dwh_schema,
            start_date=start_date,
            end_date=end_date,
        )
        if not batches:
            logging.info(
                "No prediction batches found in %s.fact_decision for range %s to %s.",
                dwh_schema,
                start_date,
                end_date,
            )
            return

        logging.info("Notification batches to process: %s", len(batches))
        for batch in batches:
            send_consolidated_notifications(
                engine=engine,
                dwh_schema=dwh_schema,
                recipients=recipients,
                bot_token=bot_token,
                notifications=collect_batch_notifications(
                    engine,
                    dwh_schema,
                    staging_schema,
                    batch,
                ),
                force=args.force,
            )
        return

    notifications = []
    signal_batch = get_latest_batch(engine, dwh_schema)
    if not signal_batch:
        logging.info("No prediction batches found in %s.fact_decision.", dwh_schema)
    else:
        signal_notifications = collect_batch_notifications(
            engine,
            dwh_schema,
            staging_schema,
            signal_batch,
        )
        notifications.extend(signal_notifications)

    evaluation_batch = get_latest_evaluated_batch(engine, dwh_schema)
    if not evaluation_batch:
        logging.info("No evaluated prediction batches found in %s.fact_decision.", dwh_schema)
    elif evaluation_batch != signal_batch:
        evaluation_notifications = collect_batch_notifications(
            engine,
            dwh_schema,
            staging_schema,
            evaluation_batch,
        )
        notifications.extend(
            item
            for item in evaluation_notifications
            if item[1] == EVALUATION_NOTIFICATION_TYPE
        )

    send_consolidated_notifications(
        engine=engine,
        dwh_schema=dwh_schema,
        recipients=recipients,
        bot_token=bot_token,
        notifications=notifications,
        force=args.force,
    )


if __name__ == "__main__":
    main()
