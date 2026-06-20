from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import get_db, DWH

router = APIRouter()


@router.get("/")
def get_signals(
    label: str = Query(None, description="BUY or SELL"),
    db: Session = Depends(get_db),
):
    """Latest actionable signals — BUY/SELL only, today's predictions."""
    label_filter = "AND d.predicted_label = :label" if label else "AND d.predicted_label != 'SILENT'"
    params = {"label": label.upper()} if label else {}

    rows = db.execute(text(f"""
        SELECT
            s.symbol_code,
            d.predicted_label,
            d.model_version,
            d.trade_date,
            d.generated_at,
            d.is_correct,
            d.actual_direction,
            -- Latest close price as entry proxy
            (
                SELECT m.metric_value
                FROM {DWH}.fact_metric m
                WHERE m.symbol_key = d.symbol_key
                  AND m.metric_code = 'close'
                  AND m.period_type = 'daily'
                ORDER BY m.period_date DESC
                LIMIT 1
            ) AS entry_price
        FROM {DWH}.fact_decision d
        LEFT JOIN staging.dim_symbol s ON s.symbol_key = d.symbol_key
        WHERE d.trade_date = (SELECT MAX(trade_date) FROM {DWH}.fact_decision)
          {label_filter}
        ORDER BY d.generated_at DESC
        LIMIT 200
    """), params).mappings().fetchall()
    return [dict(r) for r in rows]
