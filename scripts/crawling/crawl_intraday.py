import os
import uuid
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta
import pandas as pd
import sys
import io
from dotenv import load_dotenv


# Fix encoding issue on Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load .env
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

DB_CONFIG = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'dbname': os.getenv('DB_NAME')
}
DB_SCHEMA = os.getenv('DB_SCHEMA', 'staging')

try:
    from vnstock import Vnstock
except ImportError:
    print("Error: Could not import vnstock. Please install it.")
    sys.exit(1)

try:
    from vnstock import register_user
except ImportError:
    register_user = None
VNSTOCK_API_KEY = os.getenv('VNSTOCK_API_KEY')
if VNSTOCK_API_KEY and callable(register_user):
    register_user(api_key=VNSTOCK_API_KEY)
else:
    print("VNSTOCK_API_KEY not set or register_user unavailable; running as guest/default auth")
CRAWL_LOG_TABLE = "crawl_log"

def insert_crawl_log(conn, run_id, stock_code, report_type, source, status, rows_inserted=0, error_message=None):
    """Ghi 1 dòng log vào crawl_log."""
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO {DB_SCHEMA}.{CRAWL_LOG_TABLE}
                    (run_id, stock_code, report_type, source, status, rows_inserted, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (str(run_id), stock_code, report_type, source, status, rows_inserted, error_message))
            conn.commit()
    except Exception as e:
        print(f"  ⚠️ Failed to insert crawl_log for {stock_code}: {e}")
        conn.rollback()

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def get_active_symbols(conn):
    try:
        with conn.cursor() as cur:
            query = f"SELECT symbol_code FROM {DB_SCHEMA}.dim_symbol WHERE is_active = TRUE"
            cur.execute(query)
            rows = cur.fetchall()
            return [row[0] for row in rows]
    except Exception as e:
        print(f"Error fetching symbols: {e}")
        return []

def crawl_and_save_data(conn, symbols, run_id):
    # Reuse single Vnstock() instance — change symbol/source via .stock()
    # Sources theo thứ tự ưu tiên: VCI → KBS (fallback)
    SOURCES = ['VCI', 'KBS']
    stock_api = Vnstock()

    # Time range: Last 30 days
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    print(f"Crawling data from {start_date} to {end_date}...")

    results = {}  # {symbol: {"status": ..., "rows": ..., "error": ...}}

    for symbol in symbols:
        print(f"Processing {symbol}...")
        df = None
        used_source = None

        for source in SOURCES:
            try:
                stock = stock_api.stock(symbol=symbol, source=source)
                df = stock.quote.history(start=start_date, end=end_date, interval='1m')
                if df is not None and not df.empty:
                    used_source = source
                    break
                else:
                    print(f"  No data from {source} for {symbol}, trying next...")
            except Exception as e:
                print(f"  {source} failed for {symbol}: {e}, trying next...")

        try:
            if df is not None and not df.empty:

                if 'time' not in df.columns:
                    print(f"  Warning: 'time' column missing for {symbol}. Skipping.")
                    insert_crawl_log(conn, run_id, symbol, 'INTRADAY', used_source or 'UNKNOWN', 'FAILED', 0, "'time' column missing")
                    results[symbol] = {"status": "FAILED", "rows": 0, "error": "'time' column missing"}
                    continue
                
                records = []
                for _, row in df.iterrows():
                    candle_time = pd.to_datetime(row['time'])
                    trade_date = candle_time.date()
                    
                    # Multiply by 1000 to convert from 'thousands' to VND for BIGINT storage
                    rec = (
                        symbol,
                        1440, 
                        candle_time,
                        trade_date,
                        int(float(row.get('open', 0) or 0) * 1000),
                        int(float(row.get('high', 0) or 0) * 1000),
                        int(float(row.get('low', 0) or 0) * 1000),
                        int(float(row.get('close', 0) or 0) * 1000),
                        int(row.get('volume', 0) or 0)
                    )
                    records.append(rec)
                
                if records:
                    with conn.cursor() as cur:
                        table_name = f"{DB_SCHEMA}.fact_stock_price_intraday"
                        query = f"""
                            INSERT INTO {table_name} 
                            (symbol_code, interval_key, candle_time, trade_date, open, high, low, close, volume)
                            VALUES %s
                            ON CONFLICT (symbol_code, interval_key, candle_time) 
                            DO UPDATE SET
                                open = EXCLUDED.open,
                                high = EXCLUDED.high,
                                low = EXCLUDED.low,
                                close = EXCLUDED.close,
                                volume = EXCLUDED.volume;
                        """
                        execute_values(cur, query, records)
                        conn.commit()
                        print(f"  Inserted {len(records)} rows for {symbol}.")
                        insert_crawl_log(conn, run_id, symbol, 'INTRADAY', used_source, 'SUCCESS', len(records))
                        results[symbol] = {"status": "SUCCESS", "rows": len(records), "error": None}
                else:
                    print(f"  No valid records to insert for {symbol}.")
                    insert_crawl_log(conn, run_id, symbol, 'INTRADAY', used_source or 'UNKNOWN', 'NO_DATA', 0, "No valid records after parsing")
                    results[symbol] = {"status": "NO_DATA", "rows": 0, "error": "No valid records"}

            else:
                print(f"  No data found for {symbol}.")
                insert_crawl_log(conn, run_id, symbol, 'INTRADAY', 'ALL_FAILED', 'NO_DATA', 0, "All sources returned empty/None")
                results[symbol] = {"status": "NO_DATA", "rows": 0, "error": "API returned empty"}
                
        except Exception as e:
            print(f"  Error processing {symbol}: {e}")
            conn.rollback()
            insert_crawl_log(conn, run_id, symbol, 'INTRADAY', used_source or 'UNKNOWN', 'FAILED', 0, str(e)[:500])
            results[symbol] = {"status": "FAILED", "rows": 0, "error": str(e)[:200]}

    return results

def print_summary(results, run_id):
    """In summary report cuối cùng."""
    total = len(results)
    success = [s for s, r in results.items() if r["status"] == "SUCCESS"]
    no_data = [s for s, r in results.items() if r["status"] == "NO_DATA"]
    failed = [s for s, r in results.items() if r["status"] == "FAILED"]
    total_rows = sum(r["rows"] for r in results.values())

    print("\n" + "=" * 60, flush=True)
    print(f"  CRAWL INTRADAY SUMMARY  —  Run ID: {run_id}", flush=True)
    print("=" * 60, flush=True)
    print(f"  ✅ Success  : {len(success)}/{total} symbols ({total_rows} total rows)", flush=True)
    print(f"  ℹ️  No data  : {len(no_data)}/{total} symbols", flush=True)
    if no_data:
        print(f"       {', '.join(no_data)}", flush=True)
    print(f"  ❌ Failed   : {len(failed)}/{total} symbols", flush=True)
    if failed:
        for sym in failed:
            err = results[sym].get("error", "N/A")
            print(f"       {sym}: {err}", flush=True)
    print("=" * 60 + "\n", flush=True)


def main():
    run_id = uuid.uuid4()
    conn = get_db_connection()
    if not conn:
        return

    try:
        print(f"Intraday crawler started — Run ID: {run_id}", flush=True)
        symbols = get_active_symbols(conn)
        print(f"Found {len(symbols)} active symbols in schema '{DB_SCHEMA}'")
        
        if symbols:
            results = crawl_and_save_data(conn, symbols, run_id)
            print_summary(results, run_id)
        else:
            print("No active symbols found in DB.")
            
    finally:
        conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    main()
