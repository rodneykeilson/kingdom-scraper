from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Deque, Iterable
from collections import deque


@dataclass(slots=True)
class CrawlQueueItem:
    url: str
    depth: int


@dataclass(slots=True)
class CrawlState:
    queue: Deque[CrawlQueueItem] = field(default_factory=deque)
    visited: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "queue": [asdict(item) for item in self.queue],
            "visited": list(self.visited),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CrawlState":
        queue_items = deque(CrawlQueueItem(**item) for item in data.get("queue", []))
        visited = set(data.get("visited", []))
        return cls(queue=queue_items, visited=visited)

    def enqueue(self, url: str, depth: int) -> None:
        self.queue.append(CrawlQueueItem(url=url, depth=depth))

    def dequeue(self) -> CrawlQueueItem:
        return self.queue.popleft()

    def persist(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "CrawlState":
        if not path.exists():
            return cls()
        return cls.from_dict(json.loads(path.read_text()))
