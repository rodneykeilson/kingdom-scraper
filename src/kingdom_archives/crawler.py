from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from .client import HttpClient, HttpResult
from .config import ScraperConfig
from .downloader import DownloadWriter
from .parser import classify_url, extract_links, filter_domain
from .state import CrawlState


class Crawler:
    def __init__(self, config: ScraperConfig) -> None:
        self.config = config
        self.state_path = self.config.output_dir / "manifests" / "crawl-state.json"
        self.state = CrawlState.load(self.state_path)
        if not self.state.queue:
            self.state.enqueue(self.config.start_url, depth=0)
        self.writer = DownloadWriter(self.config.output_dir)
        self.http = HttpClient(self.config)

    def run(self) -> None:
        with ThreadPoolExecutor(max_workers=self.config.concurrency) as executor:
            while self.state.queue:
                item = self.state.dequeue()
                if item.depth > self.config.depth:
                    continue
                if item.url in self.state.visited:
                    continue
                self.state.visited.add(item.url)
                classification = classify_url(item.url)
                future = executor.submit(self._process_url, item.url, classification, item.depth)
                for completed in as_completed([future]):
                    completed.result()
                self.state.persist(self.state_path)
        self.http.close()

    def _process_url(self, url: str, classification: str, depth: int) -> None:
        try:
            result = self.http.get(url)
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to fetch {url}: {exc}")
            return

        # Use Content-Type from response to determine if this is an HTML page
        # This handles modern clean URLs like /agents, /about that return HTML
        content_type = result.content_type.lower()
        if content_type.startswith("text/html"):
            self._handle_html(url, result, depth)
        elif classification == "html":
            # Fallback: URL looks like HTML but Content-Type says otherwise
            self._handle_html(url, result, depth)
        else:
            self._handle_asset(result, classification)

    def _handle_html(self, url: str, result: HttpResult, depth: int) -> None:
        html_path = self.writer.target_path(url, "html", result.content_type)
        html_path.write_bytes(result.content)
        links, assets = extract_links(url, result.content.decode(errors="ignore"))
        scoped_links = filter_domain(links, self.config.allowed_domain)
        scoped_assets = filter_domain(assets, self.config.allowed_domain)
        self._enqueue_new(scoped_links, depth + 1)
        self._enqueue_assets(scoped_assets)

    def _enqueue_assets(self, assets: Iterable[str]) -> None:
        for asset in assets:
            if not self._should_visit(asset):
                continue
            self.state.enqueue(asset, depth=0)

    def _handle_asset(self, result: HttpResult, classification: str) -> None:
        if not self.config.execute_downloads:
            print(f"Discovered {classification}: {result.url}")
            return
        record = self.writer.save(result, classification)
        print(f"Downloaded {classification}: {record.saved_path}")

    def _enqueue_new(self, links: Iterable[str], depth: int) -> None:
        for link in links:
            if not self._should_visit(link):
                continue
            self.state.enqueue(link, depth=depth)

    def _should_visit(self, url: str) -> bool:
        if self.config.matches_exclude(url):
            return False
        if not self.config.matches_include(url):
            return False
        parsed = urlparse(url)
        if parsed.fragment:
            return False
        if url in self.state.visited:
            return False
        return True
