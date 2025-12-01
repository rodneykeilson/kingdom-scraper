from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse

import requests
from requests import Response, Session
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from .config import ScraperConfig


@dataclass(slots=True)
class HttpResult:
    url: str
    status_code: int
    content: bytes
    headers: dict[str, str]

    @property
    def content_type(self) -> str:
        return self.headers.get("Content-Type", "").split(";")[0].strip()

    @property
    def content_length(self) -> int:
        try:
            return int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            return 0


def create_session(config: ScraperConfig) -> Session:
    session = requests.Session()
    session.headers.update({"User-Agent": config.user_agent})
    return session


def _validate_domain(url: str, allowed_domain: str) -> None:
    parsed = urlparse(url)
    if parsed.netloc and allowed_domain not in parsed.netloc:
        raise ValueError(f"Blocked cross-domain request to {parsed.netloc}")


class HttpClient:
    def __init__(self, config: ScraperConfig) -> None:
        self.config = config
        self.session = create_session(config)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception_type((requests.RequestException, ValueError)),
    )
    def get(self, url: str) -> HttpResult:
        _validate_domain(url, self.config.allowed_domain)
        response = self.session.get(url, timeout=self.config.request_timeout)
        response.raise_for_status()
        time.sleep(self.config.delay)
        return HttpResult(
            url=response.url,
            status_code=response.status_code,
            content=response.content,
            headers=dict(response.headers),
        )

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def fetch_many(client: HttpClient, urls: Iterable[str]) -> list[HttpResult]:
    results: list[HttpResult] = []
    for url in urls:
        results.append(client.get(url))
    return results
