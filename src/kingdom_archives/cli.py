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
    
    # Voicelines-only mode
    parser.add_argument(
        "--voicelines-only",
        action="store_true",
        help="Only download agent voicelines with organized filenames (e.g., Yoru_Match_Start_1.mp3)",
    )
    parser.add_argument(
        "--agents",
        nargs="*",
        help="Specific agents to scrape voicelines for (e.g., --agents yoru jett). If not specified, all agents are scraped.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip downloading files that already exist. Useful for resuming interrupted downloads.",
    )
    
    return parser.parse_args(args)


def main(argv: list[str] | None = None) -> int:
    parsed = parse_args(argv)
    config = ScraperConfig.from_args(argv)
    
    if parsed.voicelines_only:
        # Use voicelines-only scraper
        from .voicelines import VoicelinesScraper
        
        scraper = VoicelinesScraper(config)
        try:
            scraper.run(agents=parsed.agents, skip_existing=parsed.skip_existing)
        finally:
            scraper.close()
    else:
        # Use general crawler
        crawler = Crawler(config)
        crawler.run()
    
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
