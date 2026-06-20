import hashlib
import os
import re
import ssl
import uuid
import unicodedata
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import psycopg2
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import urllib3
from requests.adapters import HTTPAdapter


load_dotenv()

DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME"),
}

DB_SCHEMA = os.getenv("DB_SCHEMA", "staging")
REQUEST_TIMEOUT = int(os.getenv("NEWS_REQUEST_TIMEOUT", "20"))
NEWS_VERIFY_SSL = os.getenv("NEWS_VERIFY_SSL", "true").lower() in {"1", "true", "yes"}

NEWS_SOURCES = {
    "cafef": [
        "https://cafef.vn/thi-truong-chung-khoan.rss",
        "https://cafef.vn/tai-chinh-ngan-hang.rss",
    ],
    "vnexpress": [
        "https://vnexpress.net/rss/kinh-doanh.rss",
    ],
    "vneconomy": [
        "https://vneconomy.vn/chung-khoan.rss",
        "https://vneconomy.vn/tai-chinh.rss",
    ],
}

NEGATION_TERMS = {"khong", "chua", "chang"}

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
        print(f"  ⚠️ Failed to insert crawl_log: {e}")
        conn.rollback()


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def load_sentiment_keywords(conn):
    """Load positive/negative sentiment keywords from dim_news_keyword."""
    positive_terms = {}
    negative_terms = {}
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT term, sentiment, weight
            FROM {DB_SCHEMA}.dim_news_keyword
            WHERE is_active = TRUE
            """
        )
        for term, sentiment, weight in cur.fetchall():
            w = float(weight)
            if sentiment == "positive":
                positive_terms[term] = w
            else:
                negative_terms[term] = w
    print(f"Loaded {len(positive_terms)} positive + {len(negative_terms)} negative keywords.")
    return positive_terms, negative_terms


def load_symbol_aliases(conn):
    """Load symbol alias mapping from dim_symbol_alias."""
    aliases = {}
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT symbol_code, alias
            FROM {DB_SCHEMA}.dim_symbol_alias
            WHERE is_active = TRUE
            ORDER BY symbol_code
            """
        )
        for symbol_code, alias in cur.fetchall():
            aliases.setdefault(symbol_code, []).append(alias)
    print(f"Loaded aliases for {len(aliases)} symbols.")
    return aliases


def normalize_text(value, strip_accents=False):
    if not value:
        return ""
    text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    text = text.lower()
    if strip_accents:
        text = text.replace("đ", "d").replace("Đ", "D")
        text = "".join(
            ch for ch in unicodedata.normalize("NFKD", text)
            if not unicodedata.combining(ch)
        )
    text = re.sub(r"\s+", " ", text).strip()
    return text


def score_sentiment(title, snippet, positive_terms, negative_terms):
    title_norm = normalize_text(title, strip_accents=True)
    body_norm = normalize_text(snippet, strip_accents=True)

    raw_score = 0.0
    for term, weight in positive_terms.items():
        raw_score += title_norm.count(term) * weight * 1.8
        raw_score += body_norm.count(term) * weight
    for term, weight in negative_terms.items():
        raw_score += title_norm.count(term) * weight * 1.8
        raw_score += body_norm.count(term) * weight

    token_text = f"{title_norm} {body_norm}"
    neg_count = sum(token_text.count(t) for t in NEGATION_TERMS)
    if neg_count and raw_score != 0:
        raw_score *= 0.7

    score = max(-1.0, min(1.0, raw_score))
    confidence = min(1.0, abs(score) * 1.5)
    if score >= 0.15:
        label = "good"
    elif score <= -0.15:
        label = "bad"
    else:
        label = "neutral"
    return score, label, confidence


def parse_datetime(value):
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def parse_rss(xml_text):
    def local_name(tag):
        if not tag:
            return ""
        if "}" in tag:
            return tag.split("}", 1)[1].lower()
        return str(tag).lower()

    def child_text_by_names(node, names):
        names = {n.lower() for n in names}
        for child in list(node):
            if local_name(child.tag) in names:
                return (child.text or "").strip()
        return ""

    def child_attr_by_names(node, names, attr):
        names = {n.lower() for n in names}
        for child in list(node):
            if local_name(child.tag) in names:
                return (child.attrib.get(attr) or "").strip()
        return ""

    items = []
    try:
        root = ET.fromstring(xml_text)
        for node in root.iter():
            node_name = local_name(node.tag)
            if node_name not in {"item", "entry"}:
                continue

            title = child_text_by_names(node, {"title"})
            link = child_text_by_names(node, {"link"})
            if not link:
                link = child_attr_by_names(node, {"link"}, "href")
            pub_date = child_text_by_names(node, {"pubdate", "published", "updated"})
            snippet = child_text_by_names(node, {"description", "summary", "content", "content:encoded"})

            items.append(
                {
                    "title": title,
                    "link": link,
                    "published_at": parse_datetime(pub_date),
                    "snippet": snippet,
                }
            )

        if items:
            return items
    except ET.ParseError:
        # Fallback #1: sanitize common malformed XML entities then parse again.
        cleaned = re.sub(r"&(?!#?\w+;)", "&amp;", xml_text)
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)
        try:
            root = ET.fromstring(cleaned)
            for node in root.iter():
                node_name = local_name(node.tag)
                if node_name not in {"item", "entry"}:
                    continue

                title = child_text_by_names(node, {"title"})
                link = child_text_by_names(node, {"link"})
                if not link:
                    link = child_attr_by_names(node, {"link"}, "href")
                pub_date = child_text_by_names(node, {"pubdate", "published", "updated"})
                snippet = child_text_by_names(node, {"description", "summary", "content", "content:encoded"})
                items.append(
                    {
                        "title": title,
                        "link": link,
                        "published_at": parse_datetime(pub_date),
                        "snippet": snippet,
                    }
                )
            if items:
                return items
        except ET.ParseError:
            pass

    # Fallback #2: html parser (does not require lxml/xml parser dependency).
    soup = BeautifulSoup(xml_text, "html.parser")
    for item in soup.find_all("item"):
        items.append(
            {
                "title": item.title.get_text(strip=True) if item.title else "",
                "link": item.link.get_text(strip=True) if item.link else "",
                "published_at": parse_datetime(item.pubDate.get_text(strip=True) if item.pubDate else None),
                "snippet": item.description.decode_contents() if item.description else "",
            }
        )
    for entry in soup.find_all("entry"):
        link = ""
        if entry.link:
            link = entry.link.get("href") or entry.link.get_text(strip=True)
        items.append(
            {
                "title": entry.title.get_text(strip=True) if entry.title else "",
                "link": (link or "").strip(),
                "published_at": parse_datetime(entry.updated.get_text(strip=True) if entry.updated else None),
                "snippet": entry.summary.decode_contents() if entry.summary else "",
            }
        )
    return items


class WeakTLSAdapter(HTTPAdapter):
    """Fallback adapter for legacy TLS endpoints (e.g. small DH key feeds)."""

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        context = ssl._create_unverified_context()
        context.check_hostname = False
        context.set_ciphers("DEFAULT:@SECLEVEL=1")
        pool_kwargs["ssl_context"] = context
        return super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)


def load_active_symbols(conn):
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT symbol_code
            FROM {DB_SCHEMA}.dim_symbol
            WHERE is_active = TRUE
            """
        )
        return [row[0].upper() for row in cur.fetchall()]


def detect_symbols(text, symbols, symbol_aliases):
    found = {}
    upper_text = f" {text.upper()} "
    norm_text = f" {normalize_text(text, strip_accents=True)} "

    for symbol in symbols:
        if re.search(rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])", upper_text):
            found[symbol] = ("ticker_regex", 0.95)

    for symbol, aliases in symbol_aliases.items():
        if symbol not in symbols or symbol in found:
            continue
        for alias in aliases:
            alias_norm = normalize_text(alias, strip_accents=True)
            if alias_norm and f" {alias_norm} " in norm_text:
                found[symbol] = ("alias_dict", 0.70)
                break

    return [(sym, meta[0], meta[1]) for sym, meta in sorted(found.items())]


def upsert_article(conn, source_name, article, positive_terms, negative_terms):
    url = article["link"]
    if not url:
        return None

    score, label, confidence = score_sentiment(
        article["title"], article["snippet"], positive_terms, negative_terms
    )
    article_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    quality_flag = "ok" if article["title"] else "low_content"
    published_at = article["published_at"] or datetime.now(timezone.utc)

    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO {DB_SCHEMA}.fact_news_article (
                source_name,
                article_url,
                article_url_hash,
                title,
                content_snippet,
                published_at,
                language,
                sentiment_score,
                sentiment_label,
                confidence,
                quality_flag
            ) VALUES (%s, %s, %s, %s, %s, %s, 'vi', %s, %s, %s, %s)
            ON CONFLICT (source_name, article_url_hash)
            DO UPDATE SET
                title = EXCLUDED.title,
                content_snippet = EXCLUDED.content_snippet,
                published_at = EXCLUDED.published_at,
                sentiment_score = EXCLUDED.sentiment_score,
                sentiment_label = EXCLUDED.sentiment_label,
                confidence = EXCLUDED.confidence,
                quality_flag = EXCLUDED.quality_flag,
                crawl_time = now()
            RETURNING article_id
            """,
            (
                source_name,
                url,
                article_hash,
                article["title"],
                article["snippet"],
                published_at,
                score,
                label,
                confidence,
                quality_flag,
            ),
        )
        return cur.fetchone()[0]


def upsert_symbol_links(conn, article_id, symbols):
    if not symbols:
        return
    rows = [(article_id, s, method, confidence) for s, method, confidence in symbols]
    with conn.cursor() as cur:
        cur.executemany(
            f"""
            INSERT INTO {DB_SCHEMA}.bridge_news_symbol (
                article_id,
                symbol_code,
                match_method,
                match_confidence
            ) VALUES (%s, %s, %s, %s)
            ON CONFLICT (article_id, symbol_code) DO NOTHING
            """,
            rows,
        )


def crawl_source(source_name, feed_url):
    request_kwargs = {
        "timeout": REQUEST_TIMEOUT,
        "headers": {"User-Agent": "stock-project-news-crawler/1.0"},
        "verify": NEWS_VERIFY_SSL,
    }
    try:
        resp = requests.get(feed_url, **request_kwargs)
        resp.raise_for_status()
        return parse_rss(resp.text)
    except requests.exceptions.SSLError:
        # Fallback for hosts with incomplete SSL chain / weak DH params.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        session = requests.Session()
        session.mount("https://", WeakTLSAdapter())
        resp = session.get(
            feed_url,
            timeout=REQUEST_TIMEOUT,
            headers=request_kwargs["headers"],
            verify=False,
        )
        resp.raise_for_status()
        return parse_rss(resp.text)


def main():
    run_id = uuid.uuid4()
    conn = get_db_connection()
    conn.autocommit = False
    total_articles = 0
    total_symbol_links = 0

    feed_results = {}  # {"source:url": {"status", "articles", "error"}}

    try:
        print(f"News crawler started — Run ID: {run_id}", flush=True)
        symbols = load_active_symbols(conn)
        print(f"Loaded {len(symbols)} active symbols.")

        positive_terms, negative_terms = load_sentiment_keywords(conn)
        symbol_aliases = load_symbol_aliases(conn)

        for source_name, urls in NEWS_SOURCES.items():
            for feed_url in urls:
                feed_key = f"{source_name}:{feed_url.split('/')[-1]}"
                feed_articles = 0
                try:
                    items = crawl_source(source_name, feed_url)
                    print(f"{source_name}: {feed_url} -> {len(items)} items")
                except Exception as exc:
                    print(f"Failed feed {feed_url}: {exc}")
                    insert_crawl_log(conn, run_id, source_name, 'NEWS', feed_url[:20], 'FAILED', 0, str(exc)[:500])
                    feed_results[feed_key] = {"status": "FAILED", "articles": 0, "error": str(exc)[:200]}
                    continue

                for item in items:
                    try:
                        article_id = upsert_article(
                            conn, source_name, item, positive_terms, negative_terms
                        )
                        if not article_id:
                            continue
                        text = f"{item['title']} {item['snippet']} {item.get('link', '')}"
                        detected = detect_symbols(text, symbols, symbol_aliases)
                        upsert_symbol_links(conn, article_id, detected)
                        total_articles += 1
                        feed_articles += 1
                        total_symbol_links += len(detected)
                    except Exception as exc:
                        print(f"Failed item {item.get('link', '')}: {exc}")
                        conn.rollback()
                        continue

                conn.commit()
                insert_crawl_log(conn, run_id, source_name, 'NEWS', feed_url[:20], 'SUCCESS', feed_articles)
                feed_results[feed_key] = {"status": "SUCCESS", "articles": feed_articles, "error": None}

        # Summary report
        print("\n" + "=" * 60, flush=True)
        print(f"  CRAWL NEWS SUMMARY  —  Run ID: {run_id}", flush=True)
        print("=" * 60, flush=True)
        success_feeds = [k for k, v in feed_results.items() if v["status"] == "SUCCESS"]
        failed_feeds = [k for k, v in feed_results.items() if v["status"] == "FAILED"]
        print(f"  ✅ Success  : {len(success_feeds)}/{len(feed_results)} feeds", flush=True)
        print(f"  ❌ Failed   : {len(failed_feeds)}/{len(feed_results)} feeds", flush=True)
        if failed_feeds:
            for f in failed_feeds:
                err = feed_results[f].get("error", "N/A")
                print(f"       {f}: {err}", flush=True)
        print(f"  📰 Total    : {total_articles} articles, {total_symbol_links} symbol links", flush=True)
        print("=" * 60 + "\n", flush=True)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
