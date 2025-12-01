from __future__ import annotations

from typing import Iterable, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

MEDIA_EXTENSIONS = {
    "audio": {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"},
    "images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"},
    "documents": {".pdf", ".doc", ".docx", ".txt", ".csv", ".xls", ".xlsx"},
}


def _normalize(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return url
    return urljoin("https://kingdomarchives.com", url)


def extract_links(page_url: str, html: str) -> tuple[list[str], list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    assets: list[str] = []

    def add_link(value: str, collection: list[str]) -> None:
        absolute = urljoin(page_url, value)
        if absolute not in collection:
            collection.append(absolute)

    for tag in soup.find_all("a", href=True):
        add_link(tag["href"], links)

    for tag in soup.find_all(["img", "audio", "source", "video"], src=True):
        add_link(tag["src"], assets)

    for tag in soup.find_all("link", href=True):
        add_link(tag["href"], assets)

    return links, assets


def classify_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.lower()
    for label, extensions in MEDIA_EXTENSIONS.items():
        if any(path.endswith(ext) for ext in extensions):
            return label
    if path.endswith(":plain"):
        return "documents"
    if path.endswith(".html") or path.endswith(".htm") or path.endswith("/"):
        return "html"
    return "other"


def filter_domain(urls: Iterable[str], allowed_domain: str) -> list[str]:
    filtered: list[str] = []
    for url in urls:
        parsed = urlparse(url)
        if not parsed.scheme:
            continue
        if allowed_domain in parsed.netloc:
            filtered.append(url)
    return filtered
