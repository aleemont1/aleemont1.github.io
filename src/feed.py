"""Latest public posts from the blog's RSS feed."""

from __future__ import annotations

import datetime as dt
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import requests

log = logging.getLogger(__name__)

# Cloudflare (Browser Integrity Check) rifiuta con 403 i client che si presentano con lo user agent
# predefinito di una libreria: ne serve uno descrittivo che dica chi siamo.
HEADERS = {
    "User-Agent": "aleemont-portfolio-build/1.0 (+https://aleemont.dev)",
    "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
}


@dataclass(frozen=True)
class Post:
    title: str
    url: str
    date: dt.date | None


def parse(xml: str, blog_url: str, limit: int = 4) -> list[Post]:
    """Parse an RSS 2.0 document.

    Links are rebuilt on ``blog_url``: the feed is generated with whatever
    SITE_URL the blog was built with, and the path is the only part we trust.
    """
    root = ET.fromstring(xml)
    base = blog_url.rstrip("/")
    posts = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        path = urlsplit(link).path or "/"
        date = None
        if item.findtext("pubDate"):
            try:
                date = parsedate_to_datetime(item.findtext("pubDate")).date()
            except (TypeError, ValueError):
                pass
        posts.append(Post(title=title, url=base + path, date=date))
    posts.sort(key=lambda p: p.date or dt.date.min, reverse=True)
    return posts[:limit]


def load(blog_url: str, cached: str | None = None, timeout: float = 15) -> list[Post]:
    try:
        if cached:
            with open(cached, encoding="utf-8") as f:
                return parse(f.read(), blog_url)
        response = requests.get(blog_url.rstrip("/") + "/rss.xml", timeout=timeout, headers=HEADERS)
        response.raise_for_status()
        return parse(response.text, blog_url)
    except Exception as exc:  # the blog being down must not break the portfolio
        log.warning("Blog feed unavailable: %s", exc)
        return []
