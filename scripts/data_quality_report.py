"""
Data Quality Report â€” BÃ¡o cÃ¡o cháº¥t lÆ°á»£ng dá»¯ liá»‡u

Cháº¡y hÃ ng ngÃ y (hoáº·c thá»§ cÃ´ng) Ä‘á»ƒ kiá»ƒm tra:
  1. Crawl Log Summary (24h gáº§n nháº¥t)
  2. Intraday Data Gaps
  3. BCTC Data Coverage
  4. News Coverage
  5. ML Pipeline Health

Usage:
    python data_quality_report.py
"""

import os
import sys
from datetime import datetime, timedelta

import psycopg2
from dotenv import load_dotenv

# Load .env tá»« thÆ° má»¥c crawling (cÃ¹ng DB config)
dotenv_path = os.path.join(os.path.dirname(__file__), "crawling", ".env")
load_dotenv(dotenv_path)

DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME"),
}

STAGING = os.getenv("DB_SCHEMA", "staging")
DWH = "dwh"
MIN_BCTC_YEAR = int(os.getenv("BCTC_MIN_YEAR", "2015"))

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  Helpers
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def section(title, icon="ðŸ“‹"):
    """Print a section header."""
    print(f"\n{'â”' * 60}", flush=True)
    print(f"  {icon} {title}", flush=True)
    print(f"{'â”' * 60}", flush=True)


def query(conn, sql, params=None):
    """Execute a query and return all rows."""
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
        return cur.fetchall()


def query_one(conn, sql, params=None):
    """Execute a query and return a single value."""
    rows = query(conn, sql, params)
    return rows[0][0] if rows else None


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  Section 1: Crawl Log Summary
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def report_crawl_log(conn):
    section("CRAWL LOG SUMMARY (24h gáº§n nháº¥t)", "ðŸ“Š")

    since = datetime.now() - timedelta(hours=24)

    # Tá»•ng há»£p theo report_type + status
    rows = query(conn, f"""
        SELECT report_type, status, COUNT(*) as cnt
        FROM {STAGING}.crawl_log
        WHERE created_at >= %s
        GROUP BY report_type, status
        ORDER BY report_type, status
    """, (since,))

    if not rows:
        print("  â„¹ï¸  KhÃ´ng cÃ³ crawl log trong 24h qua", flush=True)
        return

    # NhÃ³m theo report_type
    groups = {}
    for rpt, status, cnt in rows:
        rpt = rpt or "N/A"
        if rpt not in groups:
            groups[rpt] = {}
        groups[rpt][status] = cnt

    print(f"\n  {'Report Type':<12} {'SUCCESS':>8} {'FAILED':>8} {'NO_DATA':>8} {'RETRY_OK':>10}", flush=True)
    print(f"  {'â”€' * 50}", flush=True)
    for rpt in sorted(groups.keys()):
        s = groups[rpt]
        print(f"  {rpt:<12} {s.get('SUCCESS', 0):>8} {s.get('FAILED', 0):>8} "
              f"{s.get('NO_DATA', 0):>8} {s.get('RETRY_SUCCESS', 0):>10}", flush=True)

    # Chi tiáº¿t FAILED
    failed = query(conn, f"""
        SELECT stock_code, report_type, source, error_message
        FROM {STAGING}.crawl_log
        WHERE created_at >= %s AND status IN ('FAILED', 'NO_DATA')
        ORDER BY stock_code, report_type
    """, (since,))

    if failed:
        print(f"\n  âŒ Chi tiáº¿t lá»—i ({len(failed)} records):", flush=True)
        shown = 0
        for code, rpt, source, err in failed:
            if shown >= 20:
                print(f"     ... vÃ  {len(failed) - 20} lá»—i khÃ¡c", flush=True)
                break
            err_short = (err or "N/A")[:80]
            print(f"     {code:<6} {rpt or 'N/A':<10} {source or 'N/A':<10} {err_short}", flush=True)
            shown += 1
    else:
        print("\n  âœ… KhÃ´ng cÃ³ lá»—i nÃ o trong 24h qua", flush=True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  Section 2: Intraday Data Gaps
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def report_intraday_gaps(conn):
    section("INTRADAY DATA GAPS", "ðŸ“ˆ")

    # Láº¥y ngÃ y giao dá»‹ch gáº§n nháº¥t cÃ³ data
    latest_date = query_one(conn, f"""
        SELECT MAX(trade_date) FROM {STAGING}.fact_stock_price_intraday
    """)

    if not latest_date:
        print("  âš ï¸  KhÃ´ng cÃ³ data intraday nÃ o trong DB!", flush=True)
        return

    print(f"  NgÃ y giao dá»‹ch gáº§n nháº¥t cÃ³ data: {latest_date}", flush=True)

    # So sÃ¡nh active symbols vs symbols cÃ³ data ngÃ y Ä‘Ã³
    rows = query(conn, f"""
        SELECT 
            ds.symbol_code,
            COUNT(f.candle_time) as candle_count
        FROM {STAGING}.dim_symbol ds
        LEFT JOIN {STAGING}.fact_stock_price_intraday f
            ON ds.symbol_code = f.symbol_code
            AND f.trade_date = %s
        WHERE ds.is_active = TRUE
        GROUP BY ds.symbol_code
        ORDER BY candle_count ASC
    """, (latest_date,))

    no_data = []
    low_data = []
    ok_count = 0

    for sym, cnt in rows:
        if cnt == 0:
            no_data.append(sym)
        elif cnt < 200:
            low_data.append((sym, cnt))
        else:
            ok_count += 1

    total = len(rows)
    print(f"\n  Tá»•ng symbols active: {total}", flush=True)
    print(f"  âœ… Äá»§ data (â‰¥200 candles): {ok_count}/{total}", flush=True)

    if low_data:
        print(f"  âš ï¸  Ãt candles báº¥t thÆ°á»ng: {len(low_data)}/{total}", flush=True)
        for sym, cnt in low_data[:10]:
            print(f"     {sym}: {cnt} candles", flush=True)
        if len(low_data) > 10:
            print(f"     ... vÃ  {len(low_data) - 10} symbols khÃ¡c", flush=True)

    if no_data:
        print(f"  âŒ KhÃ´ng cÃ³ data ngÃ y {latest_date}: {len(no_data)}/{total}", flush=True)
        print(f"     {', '.join(no_data[:20])}", flush=True)
        if len(no_data) > 20:
            print(f"     ... vÃ  {len(no_data) - 20} symbols khÃ¡c", flush=True)

    # Kiá»ƒm tra gaps 5 ngÃ y gáº§n nháº¥t
    print(f"\n  ðŸ“… PhÃ¢n bá»• data 5 ngÃ y gáº§n nháº¥t:", flush=True)
    date_rows = query(conn, f"""
        SELECT trade_date, COUNT(DISTINCT symbol_code) as sym_count, COUNT(*) as candle_count
        FROM {STAGING}.fact_stock_price_intraday
        WHERE trade_date >= %s
        GROUP BY trade_date
        ORDER BY trade_date DESC
        LIMIT 5
    """, (latest_date - timedelta(days=10),))

    print(f"  {'NgÃ y':<12} {'Symbols':>8} {'Candles':>10}", flush=True)
    print(f"  {'â”€' * 32}", flush=True)
    for d, sym_cnt, candle_cnt in date_rows:
        print(f"  {str(d):<12} {sym_cnt:>8} {candle_cnt:>10}", flush=True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  Section 3: BCTC Data Coverage
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def report_bctc_coverage(conn):
    section("BCTC DATA COVERAGE", "ðŸ¦")

    # Láº¥y táº¥t cáº£ bank symbols
    symbols = query(conn, f"""
        SELECT symbol_code FROM {STAGING}.dim_symbol
        WHERE sector_name = 'bank' AND is_active = TRUE
        ORDER BY symbol_code
    """)
    bank_symbols = [r[0] for r in symbols]

    if not bank_symbols:
        print("  â„¹ï¸  KhÃ´ng cÃ³ bank symbols active", flush=True)
        return

    # Coverage theo report_type
    rows = query(conn, f"""
        SELECT stock_code, report_type, MAX(year) as latest_year,
               COUNT(DISTINCT year) as year_count
        FROM {STAGING}.fact_financials
        WHERE stock_code = ANY(%s)
          AND year >= %s
        GROUP BY stock_code, report_type
        ORDER BY stock_code, report_type
    """, (bank_symbols, MIN_BCTC_YEAR))

    # Build lookup
    coverage = {}
    for code, rpt, latest_yr, yr_cnt in rows:
        if code not in coverage:
            coverage[code] = {}
        coverage[code][rpt] = {"latest_year": latest_yr, "year_count": yr_cnt}

    critical_types = ["BS", "RATIO"]
    all_types = ["BS", "IS", "CF", "RATIO"]

    print(f"\n  {'Symbol':<8}", end="", flush=True)
    for rpt in all_types:
        print(f" {rpt:>8}", end="", flush=True)
    print(f" {'Latest':>8}", flush=True)
    print(f"  {'â”€' * 44}", flush=True)

    missing_critical = []
    for sym in bank_symbols:
        sym_data = coverage.get(sym, {})
        line = f"  {sym:<8}"
        latest = 0
        for rpt in all_types:
            if rpt in sym_data:
                yr_cnt = sym_data[rpt]["year_count"]
                line += f" {yr_cnt:>7}y"
                latest = max(latest, sym_data[rpt]["latest_year"])
            else:
                line += f"    {'âŒ':>5}"
        line += f" {latest:>8}" if latest else f"    {'N/A':>5}"
        print(line, flush=True)

        for rpt in critical_types:
            if rpt not in sym_data:
                missing_critical.append(f"{sym}({rpt})")

    if missing_critical:
        print(f"\n  âš ï¸  Thiáº¿u critical data: {', '.join(missing_critical)}", flush=True)
    else:
        print(f"\n  âœ… Táº¥t cáº£ symbols Ä‘á»u cÃ³ BS + RATIO data", flush=True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  Section 4: News Coverage
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def report_news_coverage(conn):
    section("NEWS COVERAGE", "ðŸ“°")

    # Tá»•ng articles 24h + 7d
    cnt_24h = query_one(conn, f"""
        SELECT COUNT(*) FROM {STAGING}.fact_news_article
        WHERE crawl_time >= NOW() - INTERVAL '24 hours'
    """) or 0

    cnt_7d = query_one(conn, f"""
        SELECT COUNT(*) FROM {STAGING}.fact_news_article
        WHERE crawl_time >= NOW() - INTERVAL '7 days'
    """) or 0

    print(f"\n  Articles crawl Ä‘Æ°á»£c:", flush=True)
    print(f"    24h gáº§n nháº¥t: {cnt_24h}", flush=True)
    print(f"    7 ngÃ y:       {cnt_7d}", flush=True)

    # PhÃ¢n bá»• theo source
    rows = query(conn, f"""
        SELECT source_name,
               COUNT(*) FILTER (WHERE crawl_time >= NOW() - INTERVAL '24 hours') as cnt_24h,
               COUNT(*) FILTER (WHERE crawl_time >= NOW() - INTERVAL '7 days') as cnt_7d,
               MAX(published_at) as last_article
        FROM {STAGING}.fact_news_article
        WHERE crawl_time >= NOW() - INTERVAL '7 days'
        GROUP BY source_name
        ORDER BY source_name
    """)

    if rows:
        print(f"\n  {'Source':<12} {'24h':>6} {'7d':>6} {'BÃ i má»›i nháº¥t':<20}", flush=True)
        print(f"  {'â”€' * 48}", flush=True)
        for src, c24, c7, last in rows:
            last_str = str(last)[:16] if last else "N/A"
            print(f"  {src:<12} {c24:>6} {c7:>6} {last_str:<20}", flush=True)

    # Cáº£nh bÃ¡o feed khÃ´ng cÃ³ article má»›i trong 48h
    known_sources = ["cafef", "vnexpress", "vneconomy"]
    active_sources = {r[0] for r in rows} if rows else set()
    dead_sources = set(known_sources) - active_sources

    if dead_sources:
        print(f"\n  âš ï¸  Feed cÃ³ thá»ƒ bá»‹ cháº¿t (khÃ´ng cÃ³ bÃ i 7d): {', '.join(dead_sources)}", flush=True)
    else:
        print(f"\n  âœ… Táº¥t cáº£ feed sources Ä‘á»u hoáº¡t Ä‘á»™ng", flush=True)

    # Sentiment distribution
    sentiment_rows = query(conn, f"""
        SELECT sentiment_label, COUNT(*) as cnt
        FROM {STAGING}.fact_news_article
        WHERE crawl_time >= NOW() - INTERVAL '7 days'
        GROUP BY sentiment_label
        ORDER BY sentiment_label
    """)

    if sentiment_rows:
        print(f"\n  Sentiment distribution (7d):", flush=True)
        for label, cnt in sentiment_rows:
            pct = cnt / cnt_7d * 100 if cnt_7d > 0 else 0
            bar = "â–ˆ" * int(pct / 3)
            print(f"    {label or 'N/A':<10} {cnt:>5} ({pct:>5.1f}%) {bar}", flush=True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  Section 5: ML Pipeline Health
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def report_ml_health(conn):
    section("ML PIPELINE HEALTH", "ðŸ¤–")

    # Predictions chÆ°a evaluate
    pending = query_one(conn, f"""
        SELECT COUNT(*) FROM {DWH}.fact_decision
        WHERE actual_direction IS NULL
    """) or 0

    total = query_one(conn, f"""
        SELECT COUNT(*) FROM {DWH}.fact_decision
    """) or 0

    evaluated = total - pending

    print(f"\n  Tá»•ng predictions: {total}", flush=True)
    print(f"    âœ… ÄÃ£ evaluate: {evaluated}", flush=True)
    print(f"    â³ ChÆ°a evaluate: {pending}", flush=True)

    # Accuracy 7 ngÃ y gáº§n nháº¥t
    recent_rows = query(conn, f"""
        SELECT 
            predicted_label,
            COUNT(*) as total,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
        FROM {DWH}.fact_decision
        WHERE evaluated_at >= NOW() - INTERVAL '7 days'
          AND actual_direction IS NOT NULL
        GROUP BY predicted_label
        ORDER BY predicted_label
    """)

    if recent_rows:
        print(f"\n  Accuracy (7 ngÃ y gáº§n nháº¥t):", flush=True)
        print(f"  {'Label':<10} {'Correct':>8} {'Total':>8} {'Accuracy':>10}", flush=True)
        print(f"  {'â”€' * 38}", flush=True)
        total_correct = 0
        total_all = 0
        for label, cnt, correct in recent_rows:
            acc = correct / cnt * 100 if cnt > 0 else 0
            total_correct += correct
            total_all += cnt
            print(f"  {label or 'N/A':<10} {correct:>8} {cnt:>8} {acc:>9.1f}%", flush=True)

        if total_all > 0:
            overall = total_correct / total_all * 100
            print(f"  {'OVERALL':<10} {total_correct:>8} {total_all:>8} {overall:>9.1f}%", flush=True)
    else:
        print(f"\n  â„¹ï¸  ChÆ°a cÃ³ evaluation data trong 7 ngÃ y gáº§n nháº¥t", flush=True)

    # Predictions gáº§n nháº¥t
    latest_pred = query(conn, f"""
        SELECT generated_at::date, predicted_label, COUNT(*)
        FROM {DWH}.fact_decision
        WHERE generated_at >= NOW() - INTERVAL '5 days'
        GROUP BY generated_at::date, predicted_label
        ORDER BY generated_at::date DESC, predicted_label
    """)

    if latest_pred:
        print(f"\n  Predictions 5 ngÃ y gáº§n nháº¥t:", flush=True)
        print(f"  {'NgÃ y':<12} {'Label':<10} {'Count':>6}", flush=True)
        print(f"  {'â”€' * 30}", flush=True)
        for d, label, cnt in latest_pred:
            print(f"  {str(d):<12} {label:<10} {cnt:>6}", flush=True)
    else:
        print(f"\n  â„¹ï¸  ChÆ°a cÃ³ predictions gáº§n Ä‘Ã¢y", flush=True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  Main
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def main():
    print("=" * 60, flush=True)
    print(f"  ðŸ“‹ DATA QUALITY REPORT", flush=True)
    print(f"  Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("=" * 60, flush=True)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"\nâŒ KhÃ´ng thá»ƒ káº¿t ná»‘i DB: {e}", flush=True)
        sys.exit(1)

    try:
        report_crawl_log(conn)
        report_intraday_gaps(conn)
        report_bctc_coverage(conn)
        report_news_coverage(conn)
        report_ml_health(conn)

        print(f"\n{'=' * 60}", flush=True)
        print(f"  âœ… Report hoÃ n táº¥t", flush=True)
        print(f"{'=' * 60}\n", flush=True)
    except Exception as e:
        print(f"\nâŒ Lá»—i khi táº¡o report: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()


