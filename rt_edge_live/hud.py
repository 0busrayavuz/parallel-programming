"""Ust bant (HUD) ve FPS tahmini."""

from __future__ import annotations

from collections import deque

import cv2
import numpy as np


def rolling_fps(perf_times: deque[float]) -> float:
    if len(perf_times) < 2:
        return 0.0
    dt = perf_times[-1] - perf_times[0]
    if dt <= 0:
        return 0.0
    return (len(perf_times) - 1) / dt


def draw_hud(img: np.ndarray, line1: str, line2: str) -> None:
    h, w = img.shape[:2]
    band_h = min(68, max(48, h // 5))
    roi = img[0:band_h, 0:w]
    panel = np.full_like(roi, (24, 26, 30))
    img[0:band_h, 0:w] = cv2.addWeighted(roi, 0.38, panel, 0.62, 0.0)

    x0, y1, y2 = 12, 26, 54
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, line1, (x0, y1), font, 0.72, (248, 248, 248), 2, cv2.LINE_AA)
    cv2.putText(img, line2, (x0, y2), font, 0.58, (205, 215, 225), 1, cv2.LINE_AA)
