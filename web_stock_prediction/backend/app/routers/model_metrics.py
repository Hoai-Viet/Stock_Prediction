from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import get_db, DWH

router = APIRouter()


@router.get("/summary")
def get_model_metrics(db: Session = Depends(get_db)):
    """Precision/Recall/F1 per class from evaluated predictions."""
    rows = db.execute(text(f"""
        SELECT
            predicted_label AS label,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE is_correct = true) AS correct,
            COUNT(*) FILTER (WHERE is_correct = false) AS incorrect,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE is_correct = true)
                / NULLIF(COUNT(*) FILTER (WHERE is_correct IS NOT NULL), 0),
                2
            ) AS precision_pct,
            model_version
        FROM {DWH}.fact_decision
        WHERE is_correct IS NOT NULL
        GROUP BY predicted_label, model_version
        ORDER BY model_version DESC, predicted_label
    """)).mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/confusion-matrix")
def get_confusion_matrix(db: Session = Depends(get_db)):
    """Confusion matrix values: predicted vs actual."""
    rows = db.execute(text(f"""
        SELECT
            predicted_label,
            actual_direction,
            COUNT(*) AS count
        FROM {DWH}.fact_decision
        WHERE is_correct IS NOT NULL
          AND actual_direction IS NOT NULL
        GROUP BY predicted_label, actual_direction
        ORDER BY predicted_label, actual_direction
    """)).mappings().fetchall()
    return [dict(r) for r in rows]
