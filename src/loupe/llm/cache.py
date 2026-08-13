"""On-disk cache for model responses.

Keyed on a hash of the agent instructions plus the prompt, so an identical
request returns the stored response without a network call.

Three reasons this exists beyond saving quota:

1. Reproducibility. A demo or an eval run produces identical output every
   time rather than varying with model sampling.
2. Speed. A cached full pipeline run completes in under a second.
3. Debuggability. Cached responses can be inspected on disk when a finding
   looks wrong.

The cache is content-addressed, so changing a prompt automatically produces
a new key. There is no invalidation to get wrong.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from loupe.observability.logging import get_logger

log = get_logger(__name__)

CACHE_DIR = Path("data/cache")


def cache_key(instructions: str, prompt: str, model: str) -> str:
    """Content hash identifying one model request."""
    payload = f"{model}\x00{instructions}\x00{prompt}".encode()
    return hashlib.sha256(payload).hexdigest()[:24]


def read(key: str, cache_dir: Path = CACHE_DIR) -> dict[str, Any] | None:
    """Return a cached response, or None if absent or unreadable."""
    path = cache_dir / f"{key}.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("corrupt cache entry ignored", key=key, error=str(exc))
        return None
    log.debug("cache hit", key=key)
    return payload


def write(key: str, payload: dict[str, Any], cache_dir: Path = CACHE_DIR) -> None:
    """Store a response. Failures are logged, never raised."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        (cache_dir / f"{key}.json").write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )
    except OSError as exc:
        log.warning("cache write failed", key=key, error=str(exc))


def stats(cache_dir: Path = CACHE_DIR) -> dict[str, int]:
    """Entry count and total size on disk."""
    if not cache_dir.exists():
        return {"entries": 0, "bytes": 0}
    files = list(cache_dir.glob("*.json"))
    return {
        "entries": len(files),
        "bytes": sum(f.stat().st_size for f in files),
    }