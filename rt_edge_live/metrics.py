"""JSON benchmark payload."""

from __future__ import annotations

from typing import Any

from .constants import PRODUCT_TITLE
from .profiles import PROFILES
from .version import __version__


def metrics_payload(
    *,
    profile: str,
    mode: str,
    workers: int,
    frames: int,
    wall_s: float,
    source: Any,
    record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = PROFILES[profile]
    thr = frames / wall_s if wall_s > 0 else 0.0
    d: dict[str, Any] = {
        "product": PRODUCT_TITLE,
        "version": __version__,
        "profile": meta.key,
        "profile_display": meta.display_name,
        "pipeline": meta.one_line,
        "mode": mode,
        "workers": workers,
        "frames": frames,
        "wall_seconds": round(wall_s, 6),
        "throughput_frames_per_s": round(thr, 4),
        "source": str(source),
    }
    if record is not None:
        d["record"] = record
    return d
