# ML Trading Model Documentation

## Overview
This pipeline predicts **BUY / SELL / SILENT** signals for stocks using XGBoost classification trained on technical indicators from `fact_metric`.

---

## Label Definition

| Label | Condition | Meaning |
|-------|-----------|---------|
| **BUY** | `future_return >= +2%` | Strong upward movement expected |
| **SELL** | `future_return <= -2%` | Strong downward movement expected |
| **SILENT** | Otherwise | Sideways/unclear market |

- **Forward horizon**: 5 trading days
- **Thresholds**: ±2% (configurable in `.env`)

---

## Feature Selection

### Momentum Indicators
| Feature | Description | Why It Matters |
|---------|-------------|----------------|
| `rsi_14` | Relative Strength Index (14 periods) | Overbought (>70) / Oversold (<30) detection |
| `macd_hist` | MACD Histogram | Shows momentum acceleration/deceleration |
| `return_1d` | 1-day return | Short-term momentum |
| `return_5d` | 5-day return | Medium-term momentum |

### Trend Indicators
| Feature | Description | Why It Matters |
|---------|-------------|----------------|
| `ma_5_ratio` | Price / SMA(5) | Price vs short-term trend |
| `ma_20_ratio` | Price / SMA(20) | Price vs medium-term trend |
| `ema_12_ratio` | Price / EMA(12) | Price vs exponential trend |

### Volatility Indicators
| Feature | Description | Why It Matters |
|---------|-------------|----------------|
| `bb_percent_b_20` | Bollinger %B | Position within Bollinger Bands (0-1) |
| `bb_width_20` | Bollinger Bandwidth | Volatility measure |
| `price_bb_position` | (Price - Lower) / (Upper - Lower) | Normalized BB position |

---

## Model Behavior in Different Markets

### Trending Up Market
- High `ma_5_ratio`, `ma_20_ratio` → More **BUY** signals
- Rising `macd_hist` → Confirms uptrend

### Trending Down Market
- Low `rsi_14` (<30) signals oversold → Potential reversal
- Negative `macd_hist` → Confirms downtrend

### Sideways/Range-Bound Market
- **Most signals = SILENT** because:
  - `future_return` stays within ±2%
  - RSI oscillates 40-60
  - `bb_percent_b` stays near 0.5
- This is intentional: avoid trading when no clear direction

---

## Class Imbalance Handling

The model uses `sample_weight` to handle imbalanced classes:
```python
class_weights = {i: total / (n_classes * count[i])}
```

Typically SILENT dominates (60-70%), while BUY and SELL are rarer events.

---

## Threshold Tuning Guide

To adjust sensitivity:

| Change | Effect |
|--------|--------|
| Lower `BUY_THRESHOLD` (e.g., 1%) | More BUY signals, lower precision |
| Higher `BUY_THRESHOLD` (e.g., 3%) | Fewer BUY signals, higher precision |
| Same for `SELL_THRESHOLD` | Affects SELL signal sensitivity |

Edit thresholds in `scripts/ml/.env` and retrain the model.

---

## Query Examples

### Today's Top Recommendations
```sql
SELECT symbol_key, predicted_label, prob_buy, prob_sell
FROM dwh.fact_trade_decision
WHERE trade_date = CURRENT_DATE
ORDER BY prob_buy DESC
LIMIT 10;
```

### Historical Accuracy Check
```sql
-- Compare predictions vs actual returns (requires joining with prices)
SELECT 
    td.predicted_label,
    COUNT(*) as n,
    AVG(CASE WHEN actual_return > 0.02 THEN 1 ELSE 0 END) as buy_hit_rate
FROM dwh.fact_trade_decision td
JOIN ... -- actual returns
GROUP BY td.predicted_label;
```
