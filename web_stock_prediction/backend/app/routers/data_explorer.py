from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import get_db, DWH

router = APIRouter()

METRIC_COLS = ["close", "ema_12", "ema_26", "rsi", "macd", "sentiment_score"]


@router.get("/")
def get_data_explorer(
    symbol: str = Query(None),
    limit: int = Query(100, le=500),
    mode: str = Query("feature", description="raw or feature"),
    db: Session = Depends(get_db),
):
    """Pivot latest metric rows into wide format for table display."""
    table = "fact_cleaned_metric" if mode == "feature" else "fact_metric"
    symbol_filter = "AND s.symbol_code = UPPER(:symbol)" if symbol else ""
    params = {"limit": limit}
    if symbol:
        params["symbol"] = symbol

    rows = db.execute(text(f"""
        SELECT
            s.symbol_code,
            m.period_date,
            m.metric_code,
            m.metric_value
        FROM {DWH}.{table} m
        LEFT JOIN staging.dim_symbol s ON s.symbol_key = m.symbol_key
        WHERE m.period_type = 'daily'
          AND m.metric_code = ANY(ARRAY{METRIC_COLS!r}::text[])
          {symbol_filter}
        ORDER BY m.period_date DESC, s.symbol_code
        LIMIT :limit
    """), params).mappings().fetchall()
    return [dict(r) for r in rows]
