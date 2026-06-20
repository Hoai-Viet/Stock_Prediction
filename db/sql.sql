BEGIN;

UPDATE dwh.fact_features_weight
SET weight = CASE
    WHEN rank_no = 16 THEN 0.70
    WHEN rank_no = 17 THEN 0.05
    ELSE 0.0113636363636364
END;

COMMIT;

SELECT
    rank_no,
    buy_case,
    weight
FROM dwh.fact_features_weight
ORDER BY rank_no;

SELECT ROUND(SUM(weight)::numeric, 6) AS total_weight
FROM dwh.fact_features_weight;

select *
from dwh.fact_features_weight 


select count(*)
from (
	select count(trade_date) as daily
	from staging.fact_stock_price_intraday 
	group by trade_date, symbol_code
)

