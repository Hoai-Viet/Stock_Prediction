from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urljoin
from urllib.request import Request, urlopen
import re
import time
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Query

router = APIRouter()

NEWS_CACHE_SECONDS = 600
_external_cache = {"expires_at": 0.0, "items": []}

NEWS_FEEDS = [
    {
        "source": "CafeF",
        "category": "Chứng khoán",
        "feed_url": "https://cafef.vn/thi-truong-chung-khoan.rss",
        "fallback_url": "https://cafef.vn/thi-truong-chung-khoan.chn",
    },
    {
        "source": "Vietstock",
        "category": "Chứng khoán",
        "feed_url": "https://vietstock.vn/rss/chung-khoan.rss",
        "fallback_url": "https://vietstock.vn/chung-khoan.htm",
    },
    {
        "source": "VnExpress",
        "category": "Chứng khoán",
        "feed_url": "https://vnexpress.net/rss/kinh-doanh.rss",
        "fallback_url": "https://vnexpress.net/kinh-doanh/chung-khoan",
    },
]


def _fetch_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml, application/xml, text/html;q=0.9, */*;q=0.8",
        },
    )
    with urlopen(request, timeout=8) as response:
        payload = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="ignore")


def _strip_html(value: str) -> str:
    clean = re.sub(r"<br\s*/?>", " ", value or "", flags=re.I)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _extract_image(value: str) -> str | None:
    match = re.search(r"<img[^>]+src=[\"']([^\"']+)[\"']", value or "", flags=re.I)
    if match:
        return match.group(1)
    media_match = re.search(r"url=[\"']([^\"']+\.(?:jpg|jpeg|png|webp)(?:\?[^\"']*)?)[\"']", value or "", flags=re.I)
    return media_match.group(1) if media_match else None


def _article_metadata(url: str) -> tuple[str | None, str | None]:
    try:
        html = _fetch_text(url)
    except Exception:
        return None, None

    image_match = re.search(
        r"<meta[^>]+(?:property|name)=[\"']og:image[\"'][^>]+content=[\"']([^\"']+)[\"']",
        html,
        flags=re.I,
    )
    if not image_match:
        image_match = re.search(
            r"<meta[^>]+content=[\"']([^\"']+)[\"'][^>]+(?:property|name)=[\"']og:image[\"']",
            html,
            flags=re.I,
        )

    description_match = re.search(
        r"<meta[^>]+(?:property|name)=[\"'](?:og:description|description)[\"'][^>]+content=[\"']([^\"']+)[\"']",
        html,
        flags=re.I,
    )
    if not description_match:
        description_match = re.search(
            r"<meta[^>]+content=[\"']([^\"']+)[\"'][^>]+(?:property|name)=[\"'](?:og:description|description)[\"']",
            html,
            flags=re.I,
        )

    image_url = unescape(image_match.group(1)) if image_match else None
    description = _strip_html(description_match.group(1)) if description_match else None
    return image_url, description


def _normalize_date(value: str | None) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    try:
        return parsedate_to_datetime(value).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def _rss_items(feed: dict, limit: int) -> list[dict]:
    xml_text = _fetch_text(feed["feed_url"]).strip()
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        return []

    items = []
    for index, item in enumerate(channel.findall("item")[:limit]):
        title = _strip_html(item.findtext("title") or "")
        link = _strip_html(item.findtext("link") or "")
        description_html = item.findtext("description") or ""
        summary = _strip_html(description_html)
        image_url = _extract_image(description_html)

        if not image_url:
            for child in item:
                tag = child.tag.split("}")[-1].lower()
                if tag in {"content", "thumbnail"} and child.attrib.get("url"):
                    image_url = child.attrib["url"]
                    break

        if not title or not link:
            continue

        if not image_url or not summary:
            article_image, article_summary = _article_metadata(link)
            image_url = image_url or article_image
            summary = summary or article_summary or ""

        items.append(
            {
                "id": f"{feed['source'].lower()}-{index}-{abs(hash(link))}",
                "title": title,
                "category": feed["category"],
                "source": feed["source"],
                "timestamp": _normalize_date(item.findtext("pubDate")),
                "summary": summary,
                "url": link,
                "image_url": image_url,
                "sentiment": "Neutral",
            }
        )
    return items


def _html_items(feed: dict, limit: int) -> list[dict]:
    html = _fetch_text(feed["fallback_url"])
    anchors = re.findall(r"<a\b([^>]*)>(.*?)</a>", html, flags=re.I | re.S)
    items = []
    seen = set()

    for attrs, body in anchors:
        href_match = re.search(r"href=[\"']([^\"']+)[\"']", attrs, flags=re.I)
        if not href_match:
            continue

        href = urljoin(feed["fallback_url"], href_match.group(1))
        title = _strip_html(body)
        if len(title) < 28 or href in seen or href == feed["fallback_url"]:
            continue

        seen.add(href)
        image_url, summary = _article_metadata(href)
        items.append(
            {
                "id": f"{feed['source'].lower()}-html-{len(items)}-{abs(hash(href))}",
                "title": title,
                "category": feed["category"],
                "source": feed["source"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": summary or "",
                "url": href,
                "image_url": _extract_image(body) or image_url,
                "sentiment": "Neutral",
            }
        )
        if len(items) >= limit:
            break

    return items


def _load_external_news(per_source_limit: int) -> list[dict]:
    source_groups = []
    for feed in NEWS_FEEDS:
        try:
            source_items = _rss_items(feed, per_source_limit)
        except Exception:
            try:
                source_items = _html_items(feed, per_source_limit)
            except Exception:
                source_items = []
        source_groups.append(source_items)

    items = []
    for index in range(per_source_limit):
        for source_items in source_groups:
            if index < len(source_items):
                items.append(source_items[index])
    return items


@router.get("/external")
def get_external_news(limit: int = Query(9, ge=1, le=30), refresh: bool = False):
    """Latest market news pulled from external Vietnamese financial news sources."""
    now = time.time()
    if refresh or now >= _external_cache["expires_at"]:
        per_source_limit = max(
            2,
            min(6, ((limit + len(NEWS_FEEDS) - 1) // len(NEWS_FEEDS)) + 1),
        )
        _external_cache["items"] = _load_external_news(per_source_limit=per_source_limit)
        _external_cache["expires_at"] = now + NEWS_CACHE_SECONDS

    return {"news": _external_cache["items"][:limit]}


@router.get("/latest")
def get_latest_news(limit: int = Query(9, ge=1, le=30)):
    """Backward-compatible latest news endpoint."""
    return get_external_news(limit=limit)
