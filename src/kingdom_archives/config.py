from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass(slots=True)
class ScraperConfig:
    start_url: str
    allowed_domain: str = "kingdomarchives.com"
    output_dir: Path = Path("./data/kingdomarchives")
    depth: int = 3
    concurrency: int = 4
    delay: float = 0.5
    user_agent: str = "KingdomArchivesScraper/0.1"
    execute_downloads: bool = False
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    request_timeout: int = 20
    max_retries: int = 3

    def matches_include(self, url: str) -> bool:
        if not self.include_patterns:
            return True
        return any(pattern in url for pattern in self.include_patterns)

    def matches_exclude(self, url: str) -> bool:
        return any(pattern in url for pattern in self.exclude_patterns)

    @classmethod
    def from_args(cls, args: Optional[Iterable[str]] = None) -> "ScraperConfig":
        from kingdom_archives.cli import parse_args

        parsed = parse_args(args)
        return cls(
            start_url=parsed.start_url,
            allowed_domain=parsed.allowed_domain,
            output_dir=Path(parsed.output).expanduser().resolve(),
            depth=parsed.depth,
            concurrency=parsed.concurrency,
            delay=parsed.delay,
            user_agent=parsed.user_agent,
            execute_downloads=parsed.execute_downloads,
            include_patterns=list(parsed.include or []),
            exclude_patterns=list(parsed.exclude or []),
            request_timeout=parsed.timeout,
            max_retries=parsed.retries,
        )
