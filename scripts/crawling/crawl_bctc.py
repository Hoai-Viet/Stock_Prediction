import os
import time
import re
import uuid
import unicodedata
import argparse
import pandas as pd
from vnstock import Vnstock

try:
    from vnstock import register_user
except ImportError:
    register_user = None
from sqlalchemy import create_engine, text
from decimal import Decimal, InvalidOperation
from dotenv import load_dotenv
import traceback
import random

# ================= LOAD ENV =================

load_dotenv()

DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST     = os.getenv("DB_HOST")
DB_PORT     = int(os.getenv("DB_PORT"))
DB_NAME     = os.getenv("DB_NAME")
DB_SCHEMA   = os.getenv("DB_SCHEMA", "staging")

FACT_TABLE         = os.getenv("FACT_FINANCIAL_TABLE", "fact_financials")
DIM_SYMBOL         = os.getenv("DIM_SYMBOL", "dim_symbol")
CRAWL_LOG_TABLE    = "crawl_log"
VNSTOCK_API_KEY    = os.getenv("VNSTOCK_API_KEY")

if VNSTOCK_API_KEY and callable(register_user):
    register_user(api_key=VNSTOCK_API_KEY)
else:
    print("VNSTOCK_API_KEY not set or register_user unavailable; running as guest/default auth", flush=True)
# Chá»‰ láº¥y dá»¯ liá»‡u tá»« nÄƒm nÃ y trá»Ÿ Ä‘i (trÃ¡nh crawl quÃ¡ nhiá»u nÄƒm cÅ© khÃ´ng cáº§n thiáº¿t)
MIN_YEAR = int(os.getenv("BCTC_MIN_YEAR", "2015"))

DATA_SOURCES = ["VCI", "KBS"]   # KBS + VCI: recommended sources (TCBS deprecated)

# Report types cáº§n thiáº¿t cho downstream (dbt models)
CRITICAL_REPORT_TYPES = ["BS", "RATIO"]
ALL_REPORT_TYPES      = ["BS", "IS", "CF", "RATIO"]

# ================= DB =================

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    pool_pre_ping=True
)

# ================= DB LOAD =================

def load_bank_symbols():
    try:
        sql = text(f"""
            SELECT symbol_code
            FROM {DB_SCHEMA}.{DIM_SYMBOL}
            WHERE sector_name = 'bank'
            AND is_active = TRUE
        """)
        with engine.connect() as conn:
            rows = conn.execute(sql).fetchall()
        return [r[0] for r in rows]
    except Exception:
        print("âŒ Error load_bank_symbols", flush=True)
        traceback.print_exc()
        return []

# ================= CRAWL LOG =================

def ensure_crawl_log_table():
    ddl = text(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.{CRAWL_LOG_TABLE} (
            log_id        BIGSERIAL PRIMARY KEY,
            run_id        UUID NOT NULL,
            stock_code    VARCHAR(10) NOT NULL,
            report_type   VARCHAR(20),
            source        VARCHAR(20),
            status        VARCHAR(20) NOT NULL,
            rows_inserted INT DEFAULT 0,
            error_message TEXT,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        with engine.begin() as conn:
            conn.execute(ddl)
    except Exception:
        pass


def insert_crawl_log(run_id, stock_code, report_type, source, status,
                     rows_inserted=0, error_message=None):
    sql = text(f"""
        INSERT INTO {DB_SCHEMA}.{CRAWL_LOG_TABLE}
            (run_id, stock_code, report_type, source, status, rows_inserted, error_message)
        VALUES
            (:run_id, :stock_code, :report_type, :source, :status, :rows_inserted, :error_message)
    """)
    try:
        with engine.begin() as conn:
            conn.execute(sql, {
                "run_id":        str(run_id),
                "stock_code":    stock_code,
                "report_type":   report_type,
                "source":        source,
                "status":        status,
                "rows_inserted": rows_inserted,
                "error_message": error_message
            })
    except Exception:
        pass

def prune_financials_before_min_year():
    sql = text(f"""
        DELETE FROM {DB_SCHEMA}.{FACT_TABLE}
        WHERE year < :min_year
    """)
    try:
        with engine.begin() as conn:
            result = conn.execute(sql, {"min_year": MIN_YEAR})
        deleted_rows = result.rowcount if result.rowcount is not None else 0
        print(
            f"Pruned {deleted_rows} rows from {DB_SCHEMA}.{FACT_TABLE} where year < {MIN_YEAR}",
            flush=True
        )
    except Exception:
        print(f"âŒ Error pruning {DB_SCHEMA}.{FACT_TABLE} before year {MIN_YEAR}", flush=True)
        traceback.print_exc()

# ================= UTIL =================

def parse_numeric(val):
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (int, float, Decimal)):
        try:
            return Decimal(str(val))
        except InvalidOperation:
            return None
    val = str(val).strip()
    if val in ("", "-", "N/A", "nan", "None"):
        return None
    val = val.replace(",", "").replace("%", "")
    try:
        return Decimal(val)
    except InvalidOperation:
        return None


def fetch_with_retry(fn, retries=3, sleep=30):
    for i in range(retries):
        try:
            return fn()
        except Exception as e:
            if i == retries - 1:
                raise
            wait = sleep * (i + 1) + random.uniform(0, 10)
            print(f"âš ï¸ Fetch failed ({i+1}/{retries}), sleep {wait:.1f}s: {e}", flush=True)
            time.sleep(wait)

# ================= NORMALIZE =================

def to_metric_code(metric_name: str) -> str:
    """
    Chuyá»ƒn tÃªn metric (cÃ³ thá»ƒ tiáº¿ng Viá»‡t) sang metric_code dáº¡ng UPPER_SNAKE_CASE.
    """
    nfd = unicodedata.normalize("NFD", metric_name)
    ascii_str = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    code = re.sub(r"[^A-Z0-9]", "_", ascii_str.upper())
    code = re.sub(r"_+", "_", code).strip("_")
    return code


def flatten_multiindex_columns(df: pd.DataFrame, sym: str) -> pd.DataFrame:
    """
    Xá»­ lÃ½ MultiIndex columns tá»« finance.ratio().
    Level nÃ o cÃ³ nhiá»u giÃ¡ trá»‹ unique hÆ¡n â†’ Ä‘Ã³ lÃ  level metric.
    """
    if not isinstance(df.columns, pd.MultiIndex):
        return df

    best_level = max(
        range(df.columns.nlevels),
        key=lambda lvl: len(set(df.columns.get_level_values(lvl)))
    )
    df = df.copy()
    df.columns = df.columns.get_level_values(best_level)
    print(f"  [MultiIndex] {sym}: level={best_level}, "
          f"cols={list(df.columns[:5])}", flush=True)
    return df


def normalize_df(df: pd.DataFrame, stock_code: str,
                 report_type: str, statement_type: str) -> list:
    rows = []

    df = flatten_multiindex_columns(df, stock_code)

    # â”€â”€ Lá»c chá»‰ láº¥y dá»¯ liá»‡u tá»« MIN_YEAR trá»Ÿ Ä‘i â”€â”€
    # TÃ¬m cá»™t nÄƒm trÆ°á»›c Ä‘á»ƒ filter
    cols = list(df.columns)
    year_col   = None
    period_col = None
    code_cols  = set()

    for c in cols:
        s = str(c).strip().lower()
        if s in ("nÄƒm", "year", "yearreport"):
            year_col = c
        elif s in ("ká»³", "period", "lengthreport", "quarter"):
            period_col = c
        elif s in ("cp", "ticker", "symbol"):
            code_cols.add(c)

    if year_col is None:
        print(f"  âš ï¸ [{stock_code}][{report_type}/{statement_type}] "
              f"No year column. Cols: {cols[:10]}", flush=True)
        return []

    # Filter nÄƒm
    df = df[df[year_col].notna()]
    df = df[df[year_col].astype(int) >= MIN_YEAR].copy()

    if df.empty:
        print(f"  âš ï¸ [{stock_code}][{report_type}/{statement_type}] "
              f"No data from {MIN_YEAR}+", flush=True)
        return []

    for _, r in df.iterrows():
        year = int(r[year_col])

        if period_col and period_col in r.index and not pd.isna(r[period_col]):
            period = int(r[period_col])
        elif statement_type == "quarter":
            # KhÃ´ng rÃµ ká»³ máº¥y â†’ skip, trÃ¡nh láº«n vÃ o annual data
            print(f"  âš ï¸  [{stock_code}][{report_type}] year={year}: "
                  f"quarter row has no period col, skipping", flush=True)
            continue
        else:
            period = 0  # annual

        for c in cols:
            if c in (year_col, period_col) or c in code_cols:
                continue

            metric_name = str(c).strip()
            if not metric_name or metric_name.lower() in ("nan", "none", ""):
                continue

            metric_code = to_metric_code(metric_name)
            if not metric_code:
                continue

            val = parse_numeric(r[c])
            # dropna=False â†’ nhiá»u giÃ¡ trá»‹ cÃ³ thá»ƒ None, chá»‰ skip None
            if val is None:
                continue

            rows.append({
                "stock_code":     stock_code,
                "year":           year,
                "period":         period,
                "report_type":    report_type,
                "statement_type": statement_type,
                "metric_code":    metric_code,
                "metric_name":    metric_name,
                "metric_value":   val
            })

    return rows


def insert_rows(rows: list):
    if not rows:
        return

    sql = text(f"""
        INSERT INTO {DB_SCHEMA}.{FACT_TABLE} (
            stock_code, year, period, report_type,
            statement_type, metric_code, metric_name, metric_value
        )
        VALUES (
            :stock_code, :year, :period, :report_type,
            :statement_type, :metric_code, :metric_name, :metric_value
        )
        ON CONFLICT (stock_code, year, period, report_type, metric_code)
        DO UPDATE SET
            statement_type = EXCLUDED.statement_type,
            metric_name = EXCLUDED.metric_name,
            metric_value = EXCLUDED.metric_value,
            created_at = CURRENT_TIMESTAMP
    """)

    with engine.begin() as conn:
        conn.execute(sql, rows)

# ================= CRAWL LOGIC =================

def make_jobs(stock):
    """
    Danh sÃ¡ch cÃ¡c jobs cáº§n crawl.

    Thay Ä‘á»•i so vá»›i trÆ°á»›c:
    - dropna=False â†’ KHÃ”NG drop cá»™t náº¿u cÃ³ NaN â†’ giá»¯ láº¡i Ä‘á»§ metric
      (vd: náº¿u 1 nÄƒm BVPS=None, cÅ© sáº½ drop cáº£ cá»™t BVPS, má»›i sáº½ giá»¯ BVPS cho cÃ¡c nÄƒm khÃ¡c)
    - KhÃ´ng crawl CF quarter (Ã­t cáº§n thiáº¿t, tiáº¿t kiá»‡m thá»i gian)
    """
    return [
        # Balance Sheet: year + quarter
        ("BS", "year",
         lambda: stock.finance.balance_sheet(period="year",    lang="vi", dropna=False)),
        ("BS", "quarter",
         lambda: stock.finance.balance_sheet(period="quarter", lang="vi", dropna=False)),

        # Income Statement: year + quarter
        ("IS", "year",
         lambda: stock.finance.income_statement(period="year",    lang="vi", dropna=False)),
        ("IS", "quarter",
         lambda: stock.finance.income_statement(period="quarter", lang="vi", dropna=False)),

        # Cash Flow: chá»‰ year (quarter Ã­t Ä‘Æ°á»£c dÃ¹ng trong downstream)
        ("CF", "year",
         lambda: stock.finance.cash_flow(period="year", dropna=False)),

        # Financial Ratios: lang="en" â†’ metric_code readable, dá»… map vá»›i Cafef/Fireant
        ("RATIO", "year",
         lambda: stock.finance.ratio(period="year",    lang="en", dropna=False)),
        ("RATIO", "quarter",
         lambda: stock.finance.ratio(period="quarter", lang="en", dropna=False)),
    ]


def crawl_symbol(sym, run_id, sources=None, only_report_types=None):
    """
    Crawl 1 symbol tá»« danh sÃ¡ch sources theo thá»© tá»± Æ°u tiÃªn.
    Náº¿u source Ä‘áº§u tráº£ vá» data â†’ khÃ´ng thá»­ source tiáº¿p.
    """
    if sources is None:
        sources = DATA_SOURCES

    result = {
        "success_rpts": set(),
        "failed_rpts":  set(only_report_types or ALL_REPORT_TYPES),
        "source":       None,
        "total_rows":   0
    }

    for source in sources:
        print(f"   Trying source: {source}", flush=True)
        try:
            stock = Vnstock().stock(symbol=sym, source=source)
            all_jobs = make_jobs(stock)

            jobs = [(rpt, stmt, fn) for rpt, stmt, fn in all_jobs
                    if only_report_types is None or rpt in only_report_types]

            source_rows         = 0
            source_success_rpts = set()

            for rpt, stmt, fn in jobs:
                try:
                    df = fetch_with_retry(fn, retries=2, sleep=30)
                except Exception as e:
                    df = None
                    insert_crawl_log(run_id, sym, f"{rpt}/{stmt}", source, "FAILED", 0, str(e))

                time.sleep(random.uniform(1, 3))   # community key: 60 req/min (was 3-7s)

                if df is None or df.empty:
                    if df is not None:
                        insert_crawl_log(run_id, sym, f"{rpt}/{stmt}", source,
                                         "FAILED", 0, "Empty DataFrame")
                    continue

                rows = normalize_df(df, sym, rpt, stmt)

                if not rows:
                    insert_crawl_log(run_id, sym, f"{rpt}/{stmt}", source,
                                     "FAILED", 0, f"0 rows after normalize (min_year={MIN_YEAR})")
                    continue

                insert_rows(rows)
                source_rows += len(rows)
                source_success_rpts.add(rpt)

                insert_crawl_log(run_id, sym, f"{rpt}/{stmt}", source,
                                 "SUCCESS", len(rows))
                print(f"     âœ“ {rpt}/{stmt}: {len(rows)} rows", flush=True)

            if source_rows > 0:
                result["success_rpts"] = source_success_rpts
                result["failed_rpts"]  = set(only_report_types or ALL_REPORT_TYPES) - source_success_rpts
                result["source"]       = source
                result["total_rows"]   = source_rows
                print(f"   âœ“ {source}: {source_rows} rows, reports: {source_success_rpts}", flush=True)
                break
            else:
                print(f"   âš ï¸ No data from {source} for {sym}", flush=True)
                time.sleep(random.uniform(2, 4))

        except Exception as e:
            print(f"   âŒ Error with {source}: {e}", flush=True)
            insert_crawl_log(run_id, sym, None, source, "FAILED", 0, str(e))
            time.sleep(random.uniform(5, 10))

    return result


def validate_db_data(symbols):
    sql = text(f"""
        SELECT stock_code, report_type, COUNT(*) as cnt
        FROM {DB_SCHEMA}.{FACT_TABLE}
        WHERE stock_code = ANY(:symbols)
          AND year >= :min_year
        GROUP BY stock_code, report_type
        ORDER BY stock_code, report_type
    """)
    try:
        with engine.connect() as conn:
            rows = conn.execute(sql, {"symbols": symbols, "min_year": MIN_YEAR}).fetchall()
        db_data = {}
        for stock_code, report_type, cnt in rows:
            db_data.setdefault(stock_code, {})[report_type] = cnt
        return db_data
    except Exception:
        traceback.print_exc()
        return {}


def print_summary(symbols, crawl_results, db_data, run_id):
    total        = len(symbols)
    full_success = []
    partial      = []
    failed       = []

    for sym in symbols:
        r = crawl_results.get(sym)
        if r is None or r["total_rows"] == 0:
            failed.append(sym)
        elif r["failed_rpts"]:
            partial.append((sym, r["failed_rpts"]))
        else:
            full_success.append(sym)

    print("\n" + "=" * 60, flush=True)
    print(f"  CRAWL BCTC  â€”  Run ID: {run_id}  â€”  min_year={MIN_YEAR}", flush=True)
    print("=" * 60, flush=True)
    print(f"  âœ… Full success : {len(full_success)}/{total}", flush=True)
    print(f"  âš ï¸  Partial      : {len(partial)}/{total}", flush=True)
    for sym, missing in partial:
        print(f"       {sym}: missing {missing}", flush=True)
    print(f"  âŒ Failed       : {len(failed)}/{total}", flush=True)
    if failed:
        print(f"       {', '.join(failed)}", flush=True)

    print("\n  DB Validation:", flush=True)
    for rpt in CRITICAL_REPORT_TYPES:
        count = sum(1 for sym in symbols if rpt in db_data.get(sym, {}))
        print(f"    {rpt} coverage: {count}/{total}", flush=True)

    missing_critical = [
        sym for sym in symbols
        if any(rpt not in db_data.get(sym, {}) for rpt in CRITICAL_REPORT_TYPES)
    ]
    if missing_critical:
        print(f"    âš ï¸  Missing critical: {', '.join(missing_critical)}", flush=True)
    else:
        print(f"    âœ… All symbols have BS + RATIO", flush=True)

    print("=" * 60 + "\n", flush=True)

# ================= MAIN =================

def parse_args():
    parser = argparse.ArgumentParser(description="Crawl BCTC data")
    parser.add_argument(
        "--symbol",
        help="Crawl a single stock symbol instead of the default bank symbol list"
    )
    return parser.parse_args()

def run():
    args = parse_args()
    run_id = uuid.uuid4()
    print(f"BCTC crawler started Ã¢â‚¬â€ Run ID: {run_id}", flush=True)
    print(f"Min year: {MIN_YEAR}, Sources: {DATA_SOURCES}", flush=True)

    ensure_crawl_log_table()
    prune_financials_before_min_year()

    if args.symbol:
        symbols = [args.symbol.strip().upper()]
        print(f"Using explicit symbol: {symbols[0]}\n", flush=True)
    else:
        symbols = load_bank_symbols()
        print(f"Found {len(symbols)} bank symbols\n", flush=True)

    crawl_results = {}
    # â”€â”€ PASS 1: Crawl táº¥t cáº£ symbols â”€â”€
    print("â”â”â” PASS 1: Initial crawl â”â”â”", flush=True)
    for sym in symbols:
        print(f"â–¶ {sym}", flush=True)
        result = crawl_symbol(sym, run_id)
        crawl_results[sym] = result

        if result["total_rows"] == 0:
            print(f"  âŒ No data for {sym} from all sources", flush=True)

        time.sleep(random.uniform(5, 12))   # community key: 60 req/min (was 20-40s)

    # â”€â”€ PASS 2: Retry failed & partial â”€â”€
    failed_symbols  = [sym for sym, r in crawl_results.items() if r["total_rows"] == 0]
    partial_symbols = [(sym, r["failed_rpts"]) for sym, r in crawl_results.items()
                       if r["total_rows"] > 0 and r["failed_rpts"]]

    if failed_symbols or partial_symbols:
        print(f"\nâ”â”â” PASS 2: Retry "
              f"({len(failed_symbols)} failed, {len(partial_symbols)} partial) â”â”â”", flush=True)
        time.sleep(random.uniform(5, 12))

        for sym in failed_symbols:
            print(f"ðŸ”„ Retry {sym} (all)", flush=True)
            result = crawl_symbol(sym, run_id)
            if result["total_rows"] > 0:
                crawl_results[sym] = result
                print(f"  âœ… Retry success for {sym}", flush=True)
            else:
                print(f"  âŒ Still failed: {sym}", flush=True)
            time.sleep(random.uniform(5, 12))

        for sym, missing_rpts in partial_symbols:
            print(f"ðŸ”„ Retry {sym} (missing: {missing_rpts})", flush=True)
            result = crawl_symbol(sym, run_id, only_report_types=missing_rpts)
            if result["success_rpts"]:
                crawl_results[sym]["success_rpts"] |= result["success_rpts"]
                crawl_results[sym]["failed_rpts"]  -= result["success_rpts"]
                crawl_results[sym]["total_rows"]   += result["total_rows"]
                print(f"  âœ… Recovered: {result['success_rpts']}", flush=True)
            else:
                print(f"  âš ï¸ Still missing: {missing_rpts}", flush=True)
            time.sleep(random.uniform(5, 12))

    # â”€â”€ Validate & Summary â”€â”€
    db_data = validate_db_data(symbols)
    print_summary(symbols, crawl_results, db_data, run_id)


if __name__ == "__main__":
    run()
