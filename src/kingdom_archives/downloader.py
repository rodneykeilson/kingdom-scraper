from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from slugify import slugify

from .client import HttpResult

MEDIA_DIR_MAP = {
    "audio": "media/audio",
    "images": "media/images",
    "documents": "media/documents",
    "html": "html",
    "other": "media/other",
}


@dataclass(slots=True)
class DownloadRecord:
    url: str
    saved_path: str
    content_type: str
    content_length: int
    sha256: str
    fetched_at: str
    status_code: int


class DownloadWriter:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.manifest_dir = root / "manifests"
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.download_log = self.manifest_dir / "downloads.log"

    def target_path(self, url: str, classification: str, content_type: str) -> Path:
        parsed = urlparse(url)
        stem = parsed.path.rstrip("/") or "index"
        slug = slugify(stem.replace("/", "-")) or "asset"
        extension = self._extension_from_type(content_type, parsed.path)
        relative_dir = MEDIA_DIR_MAP.get(classification, "media/other")
        directory = self.root / relative_dir
        directory.mkdir(parents=True, exist_ok=True)
        filename = f"{slug}{extension}"
        return directory / filename

    def save(self, result: HttpResult, classification: str) -> DownloadRecord:
        path = self.target_path(result.url, classification, result.content_type)
        path.write_bytes(result.content)

        digest = hashlib.sha256(result.content).hexdigest()
        record = DownloadRecord(
            url=result.url,
            saved_path=str(path.relative_to(self.root)),
            content_type=result.content_type,
            content_length=result.content_length or len(result.content),
            sha256=digest,
            fetched_at=datetime.now(tz=timezone.utc).isoformat(),
            status_code=result.status_code,
        )
        self._write_metadata(path, record)
        self._append_log(record)
        return record

    def _write_metadata(self, path: Path, record: DownloadRecord) -> None:
        metadata_path = path.with_suffix(path.suffix + ".json")
        metadata_path.write_text(json.dumps(asdict(record), indent=2))

    def _append_log(self, record: DownloadRecord) -> None:
        with self.download_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record)) + "\n")

    @staticmethod
    def _extension_from_type(content_type: str, original_path: str) -> str:
        if "/" in content_type:
            subtype = content_type.split("/")[1]
            if ";" in subtype:
                subtype = subtype.split(";")[0]
            if subtype:
                return f".{subtype}"
        parsed = urlparse(original_path)
        suffix = Path(parsed.path).suffix
        return suffix or ""
