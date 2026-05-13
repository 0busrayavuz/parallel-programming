"""Islenmis kareleri video dosyasina yazma (Windows uyumlu yedek codec)."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger(__name__)


class VideoRecorder:
    """
    Ilk yazilan karede VideoWriter acilir.
    mp4v basarisizsa ayni klasorde *_rec.avi + MJPG denenir.
    BGR uint8, cift genislik/yukseklik (codec uyumu).
    """

    __slots__ = (
        "_path",
        "_fps",
        "_writer",
        "_opened",
        "_effective_path",
        "_frames_written",
        "_give_up",
    )

    def __init__(self, path: str | None, fps: float) -> None:
        self._path = str(Path(path).resolve()) if path else None
        self._fps = max(1.0, float(fps))
        self._writer: cv2.VideoWriter | None = None
        self._opened = False
        self._effective_path: str | None = None
        self._frames_written = 0
        self._give_up = False

    def _prepare_frame(self, frame_bgr: np.ndarray) -> np.ndarray | None:
        frame = np.ascontiguousarray(frame_bgr)
        if frame.dtype != np.uint8:
            frame = np.clip(frame, 0, 255).astype(np.uint8)
        if frame.ndim != 3 or frame.shape[2] != 3:
            log.error("Kayit: BGR 3 kanal bekleniyor, boyut=%s", getattr(frame, "shape", None))
            return None
        h, w = frame.shape[:2]
        he, we = h - (h % 2), w - (w % 2)
        if he < 2 or we < 2:
            log.error("Kayit: gecersiz boyut %sx%s", w, h)
            return None
        if he != h or we != w:
            frame = frame[:he, :we]
        return frame

    def _try_open(self, w: int, h: int) -> bool:
        if not self._path:
            return False
        base = Path(self._path)
        parent = base.parent
        stem = base.stem
        suffix = base.suffix.lower()
        candidates: list[tuple[str, int]] = []
        if suffix in (".mp4", ".m4v"):
            candidates.append((str(base), cv2.VideoWriter_fourcc(*"mp4v")))
        candidates.append((str(parent / f"{stem}_rec.avi"), cv2.VideoWriter_fourcc(*"MJPG")))
        if suffix == ".avi" and str(base) not in [c[0] for c in candidates]:
            candidates.insert(0, (str(base), cv2.VideoWriter_fourcc(*"MJPG")))

        for out_path, fourcc in candidates:
            wri = cv2.VideoWriter(out_path, fourcc, self._fps, (w, h))
            if wri.isOpened():
                self._writer = wri
                self._opened = True
                self._effective_path = out_path
                log.info("Video kaydi basladi: %s @ %.2f FPS (%sx%s)", out_path, self._fps, w, h)
                return True
            wri.release()
        log.error(
            "VideoWriter hicbir codec ile acilamadi. Denenen yollar: %s",
            [c[0] for c in candidates],
        )
        self._writer = None
        self._opened = False
        return False

    def write(self, frame_bgr: np.ndarray) -> None:
        if not self._path or self._give_up:
            return
        frame = self._prepare_frame(frame_bgr)
        if frame is None:
            return
        h, w = frame.shape[:2]
        if self._writer is None:
            if not self._try_open(w, h):
                self._give_up = True
                return
        assert self._writer is not None
        self._writer.write(frame)
        self._frames_written += 1

    def close(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None
            if self._opened and self._effective_path:
                log.info(
                    "Video kaydi bitti: %s (%s kare)",
                    self._effective_path,
                    self._frames_written,
                )
            self._opened = False

    def get_stats(self) -> dict[str, object]:
        return {
            "requested_path": self._path,
            "output_path": self._effective_path,
            "frames_written": self._frames_written,
            "ok": self._frames_written > 0 and self._effective_path is not None,
        }
