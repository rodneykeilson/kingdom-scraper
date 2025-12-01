from __future__ import annotations

import argparse
import sys

from .config import ScraperConfig
from .crawler import Crawler


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape kingdomarchives.com assets")
    parser.add_argument("--start-url", default="https://kingdomarchives.com", help="Entry URL to start crawling")
    parser.add_argument("--allowed-domain", default="kingdomarchives.com", help="Domain whitelist to enforce")
    parser.add_argument("--output", default="./data/kingdomarchives", help="Output directory for downloads")
    parser.add_argument("--depth", type=int, default=3, help="Maximum crawl depth for HTML pages")
    parser.add_argument("--concurrency", type=int, default=4, help="Concurrent workers for fetching")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests")
    parser.add_argument("--user-agent", default="KingdomArchivesScraper/0.1", help="Custom user agent")
    parser.add_argument("--execute-downloads", action="store_true", help="Persist assets instead of dry run")
    parser.add_argument("--include", nargs="*", help="URL substrings to include")
    parser.add_argument("--exclude", nargs="*", help="URL substrings to exclude")
    parser.add_argument("--timeout", type=int, default=20, help="Request timeout in seconds")
    parser.add_argument("--retries", type=int, default=3, help="Retry attempts for failed requests")
    return parser.parse_args(args)


def main(argv: list[str] | None = None) -> int:
    config = ScraperConfig.from_args(argv)
    crawler = Crawler(config)
    crawler.run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
