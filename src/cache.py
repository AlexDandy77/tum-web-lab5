"""File-based HTTP cache with TTL."""

import hashlib
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path

CACHE_DIR = Path.home() / ".go2web_cache"
DEFAULT_TTL = 300  # 5 minutes


@dataclass
class CacheEntry:
    url: str
    status_code: int
    headers: dict
    body: str
    cached_at: float
    etag: str
    last_modified: str


class Cache:
    def __init__(self, ttl: int = DEFAULT_TTL):
        CACHE_DIR.mkdir(exist_ok=True)
        self.ttl = ttl

    def _path(self, url: str) -> Path:
        key = hashlib.sha256(url.encode()).hexdigest()
        return CACHE_DIR / f"{key}.json"

    def get(self, url: str):
        """Return CacheEntry if cached (fresh or stale), else None."""
        path = self._path(url)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return CacheEntry(**data)
        except Exception:
            return None

    def is_fresh(self, entry: CacheEntry) -> bool:
        return (time.time() - entry.cached_at) < self.ttl

    def store(self, url: str, status_code: int, headers: dict, body: str,
              etag: str = "", last_modified: str = "") -> None:
        entry = CacheEntry(
            url=url,
            status_code=status_code,
            headers=headers,
            body=body,
            cached_at=time.time(),
            etag=etag,
            last_modified=last_modified,
        )
        self._path(url).write_text(
            json.dumps(asdict(entry), ensure_ascii=False), encoding="utf-8"
        )

    def refresh_ttl(self, url: str) -> None:
        """Update cached_at to now (used after 304 revalidation)."""
        entry = self.get(url)
        if entry:
            entry.cached_at = time.time()
            self._path(url).write_text(
                json.dumps(asdict(entry), ensure_ascii=False), encoding="utf-8"
            )
