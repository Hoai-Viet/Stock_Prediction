{% macro create_tech_indicators_fn() %}
CREATE OR REPLACE FUNCTION {{ target.schema }}._calc_tech_indicators_v5()
RETURNS TABLE (
    symbol_key integer,
    trade_date date,
    rn integer,
    close_price numeric,
    sma_3 numeric,
    sma_5 numeric,
    sma_9 numeric,
    sma_15 numeric,
    sma_20 numeric,
    sma_50 numeric,
    stddev_20 numeric,
    high_10d numeric,
    atr_14 numeric,
    ema_12 numeric,
    ema_26 numeric,
    avg_gain numeric,
    avg_loss numeric,
    macd_line numeric,
    signal_line numeric,
    volume numeric,
    vol_ma_5 numeric,
    vol_ma_20 numeric,
    obv numeric
)
LANGUAGE plpgsql STABLE
AS $fn$
DECLARE
    rec record;
    v_prev_symbol integer := -1;
    v_ema_12 numeric;
    v_ema_26 numeric;
    v_avg_gain numeric;
    v_avg_loss numeric;
    v_atr_14 numeric;
    v_macd numeric;
    v_signal numeric;
    v_obv numeric;
    k12 CONSTANT numeric := 2.0 / 13.0;  -- EMA 12 multiplier
    k26 CONSTANT numeric := 2.0 / 27.0;  -- EMA 26 multiplier
    k9  CONSTANT numeric := 2.0 / 10.0;  -- EMA 9 multiplier (signal line)
BEGIN
    FOR rec IN
        WITH price_changes AS (
            SELECT
                p.symbol_key AS sk,
                p.trade_date AS td,
                p.close_price::numeric AS cp,
                p.high_price::numeric AS hp,
                p.low_price::numeric AS lp,
                p.volume::numeric AS vol,
                row_number() OVER (PARTITION BY p.symbol_key ORDER BY p.trade_date)::integer AS row_num,
                lag(p.close_price) OVER (
                    PARTITION BY p.symbol_key ORDER BY p.trade_date
                )::numeric AS prev_cp,
                (p.close_price - lag(p.close_price) OVER (
                    PARTITION BY p.symbol_key ORDER BY p.trade_date
                ))::numeric AS diff
            FROM {{ ref('int_price_daily') }} p
        ),
        base AS (
            SELECT
                pc.sk, pc.td, pc.cp, pc.vol, pc.row_num, pc.diff,
                greatest(coalesce(pc.diff, 0), 0)::numeric AS gain,
                greatest(-coalesce(pc.diff, 0), 0)::numeric AS loss,
                avg(pc.cp) OVER (
                    PARTITION BY pc.sk ORDER BY pc.td
                    ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                )::numeric as sma3,
                avg(pc.cp) OVER (
                    PARTITION BY pc.sk ORDER BY pc.td
                    ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                )::numeric AS sma5,
                avg(pc.cp) OVER (
                    PARTITION BY pc.sk ORDER BY pc.td
                    ROWS BETWEEN 8 PRECEDING AND CURRENT ROW
                )::numeric AS sma9,
                avg(pc.cp) OVER (
                    PARTITION BY pc.sk ORDER BY pc.td
                    ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
                )::numeric AS sma15,
                avg(pc.cp) OVER (
                    PARTITION BY pc.sk ORDER BY pc.td
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                )::numeric AS sma20,
                avg(pc.cp) OVER (
                    PARTITION BY pc.sk ORDER BY pc.td
                    ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
                )::numeric AS sma50,
                stddev(pc.cp) OVER (
                    PARTITION BY pc.sk ORDER BY pc.td
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                )::numeric AS std20,
                max(pc.hp) OVER (
                    PARTITION BY pc.sk ORDER BY pc.td
                    ROWS BETWEEN 10 PRECEDING AND 1 PRECEDING
                )::numeric AS high10d,
                greatest(
                    pc.hp - pc.lp,
                    abs(pc.hp - coalesce(pc.prev_cp, pc.cp)),
                    abs(pc.lp - coalesce(pc.prev_cp, pc.cp))
                )::numeric AS true_range,
                avg(pc.vol) OVER (
                    PARTITION BY pc.sk ORDER BY pc.td
                    ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                )::numeric AS vol_ma5,
                avg(pc.vol) OVER (
                    PARTITION BY pc.sk ORDER BY pc.td
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                )::numeric AS vol_ma20
            FROM price_changes pc
        ),
        enriched AS (
            SELECT
                b.*,
                avg(b.true_range) OVER (
                    PARTITION BY b.sk ORDER BY b.td
                    ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                )::numeric AS sma_true_range_14,
                coalesce(avg(b.gain) OVER (
                    PARTITION BY b.sk ORDER BY b.td
                    ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                ), 0)::numeric AS sma_gain_14,
                coalesce(avg(b.loss) OVER (
                    PARTITION BY b.sk ORDER BY b.td
                    ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                ), 0)::numeric AS sma_loss_14
            FROM base b
        )
        SELECT * FROM enriched ORDER BY sk, td
    LOOP
        IF rec.sk != v_prev_symbol THEN
            v_ema_12 := rec.cp;
            v_ema_26 := rec.cp;
            v_avg_gain := rec.sma_gain_14;
            v_avg_loss := rec.sma_loss_14;
            v_atr_14 := null;
            v_macd := 0;
            v_signal := 0;
            v_obv := 0;
            v_prev_symbol := rec.sk;
        ELSE
            v_ema_12 := rec.cp * k12 + v_ema_12 * (1 - k12);
            v_ema_26 := rec.cp * k26 + v_ema_26 * (1 - k26);
            v_avg_gain := (v_avg_gain * 13 + rec.gain) / 14;
            v_avg_loss := (v_avg_loss * 13 + rec.loss) / 14;
            IF rec.row_num = 14 THEN
                v_atr_14 := rec.sma_true_range_14;
            ELSIF rec.row_num > 14 THEN
                v_atr_14 := (v_atr_14 * 13 + rec.true_range) / 14;
            END IF;
            v_macd := v_ema_12 - v_ema_26;
            v_signal := v_macd * k9 + v_signal * (1 - k9);

            IF rec.diff > 0 THEN
                v_obv := v_obv + coalesce(rec.vol, 0);
            ELSIF rec.diff < 0 THEN
                v_obv := v_obv - coalesce(rec.vol, 0);
            END IF;
        END IF;

        symbol_key  := rec.sk;
        trade_date  := rec.td;
        rn          := rec.row_num;
        close_price := rec.cp;
        sma_3       := case when rec.row_num >= 3 then rec.sma3 else null end;
        sma_5       := case when rec.row_num >= 5 then rec.sma5 else null end;
        sma_9       := case when rec.row_num >= 9 then rec.sma9 else null end;
        sma_15      := case when rec.row_num >= 15 then rec.sma15 else null end;
        sma_20      := case when rec.row_num >= 20 then rec.sma20 else null end;
        sma_50      := case when rec.row_num >= 50 then rec.sma50 else null end;
        stddev_20   := case when rec.row_num >= 20 then rec.std20 else null end;
        high_10d    := case when rec.row_num >= 11 then rec.high10d else null end;
        atr_14      := case when rec.row_num >= 14 then v_atr_14 else null end;
        ema_12      := v_ema_12;
        ema_26      := v_ema_26;
        avg_gain    := v_avg_gain;
        avg_loss    := v_avg_loss;
        macd_line   := v_macd;
        signal_line := v_signal;
        volume      := rec.vol;
        vol_ma_5    := rec.vol_ma5;
        vol_ma_20   := rec.vol_ma20;
        obv         := v_obv;

        
        {% if var('backfill_year', none) is not none %}
        IF extract(year from rec.td) = {{ var('backfill_year') }} THEN
            RETURN NEXT;
        END IF;
        {% else %}
        RETURN NEXT;
        {% endif %}

    END LOOP;
END;
$fn$;
{% endmacro %}

