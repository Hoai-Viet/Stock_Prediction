from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import get_db, DWH

router = APIRouter()


@router.get("/kpis")
def get_kpis(db: Session = Depends(get_db)):
    """Top-level KPI cards for the dashboard."""
    result = db.execute(text(f"""
        SELECT
            COUNT(*) FILTER (WHERE trade_date = CURRENT_DATE) AS total_predictions_today,
            COUNT(*) FILTER (WHERE trade_date = CURRENT_DATE AND predicted_label = 'BUY') AS buy_signals,
            COUNT(*) FILTER (WHERE trade_date = CURRENT_DATE AND predicted_label = 'SELL') AS sell_signals,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE is_correct = true)
                / NULLIF(COUNT(*) FILTER (WHERE is_correct IS NOT NULL), 0),
                2
            ) AS accuracy_pct,
            model_version
        FROM {DWH}.fact_decision
        GROUP BY model_version
        ORDER BY MAX(generated_at) DESC
        LIMIT 1
    """)).mappings().fetchone()
    if not result:
        return {"total_predictions_today": 0, "buy_signals": 0, "sell_signals": 0, "accuracy_pct": None, "model_version": "N/A"}
    return dict(result)


@router.get("/accuracy-over-time")
def get_accuracy_over_time(db: Session = Depends(get_db)):
    """Model accuracy per trade date for the performance chart."""
    rows = db.execute(text(f"""
        SELECT
            trade_date,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE is_correct = true)
                / NULLIF(COUNT(*) FILTER (WHERE is_correct IS NOT NULL), 0),
                2
            ) AS accuracy_pct
        FROM {DWH}.fact_decision
        WHERE is_correct IS NOT NULL
        GROUP BY trade_date
        ORDER BY trade_date DESC
        LIMIT 60
    """)).mappings().fetchall()
    return [dict(r) for r in rows]
