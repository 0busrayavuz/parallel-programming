"""Kenar analitigi is hatti (stateless, isci surece uygun)."""

from __future__ import annotations

import cv2
import numpy as np

from .profiles import PROFILE_KEYS, canonical_profile


class EdgeInspectionPipeline:
    """
    Kenar analitigi hatti. Tum asamalar stateless; isci sureclerde guvenle
    calistirilir (`apply` + profil anahtari).
    """

    __slots__ = ()

    @staticmethod
    def _to_gray(bgr: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def _edges_fast(gray: np.ndarray) -> np.ndarray:
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        return cv2.Canny(blurred, 65, 125)

    @staticmethod
    def _edges_standard(bgr: np.ndarray, gray: np.ndarray) -> np.ndarray:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        eq = clahe.apply(gray)
        blurred = cv2.GaussianBlur(eq, (7, 7), 0)
        edges = cv2.Canny(blurred, 48, 138)
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        return cv2.addWeighted(bgr, 0.28, edges_bgr, 0.72, 0.0)

    @staticmethod
    def _edges_quality(bgr: np.ndarray, gray: np.ndarray) -> np.ndarray:
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        eq = clahe.apply(gray)
        smooth = cv2.bilateralFilter(eq, 9, 80, 80)
        edges = cv2.Canny(smooth, 38, 125)
        kernel = np.ones((5, 5), np.uint8)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        edges = cv2.dilate(edges, np.ones((2, 2), np.uint8), iterations=1)
        edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        return cv2.addWeighted(bgr, 0.22, edges_bgr, 0.78, 0.0)

    @staticmethod
    def _edges_stress(bgr: np.ndarray, gray: np.ndarray) -> np.ndarray:
        """
        Paralel vs seri kiyasinda IPC maliyetini gormezden gelecek kadar agir is.
        Hedef: tipik 640x480 civarinda kare basina ~30-80 ms (makineye gore degisir).
        """
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        eq = clahe.apply(gray)
        x = cv2.medianBlur(eq, 15)
        k = 21
        for _ in range(11):
            x = cv2.GaussianBlur(x, (k, k), 0)
            x = cv2.Canny(x, 38, 115)
        x = cv2.medianBlur(x, 11)
        kernel = np.ones((7, 7), np.uint8)
        x = cv2.morphologyEx(x, cv2.MORPH_CLOSE, kernel)
        edges_bgr = cv2.cvtColor(x, cv2.COLOR_GRAY2BGR)
        out = cv2.addWeighted(bgr, 0.25, edges_bgr, 0.75, 0.0)
        # Kucuk bolgede ek CPU (vektorize; numpy) - grain size artisi
        patch = out[::8, ::8].astype(np.float64)
        for _ in range(18):
            patch = np.sqrt(np.abs(patch) + 1.0)
        out[::8, ::8] = np.clip(patch, 0, 255).astype(np.uint8)
        return out

    @classmethod
    def apply(cls, bgr: np.ndarray, profile: str) -> np.ndarray:
        key = canonical_profile(profile)
        if key not in PROFILE_KEYS:
            key = "standard"
        gray = cls._to_gray(bgr)
        if key == "fast":
            e = cls._edges_fast(gray)
            return cv2.cvtColor(e, cv2.COLOR_GRAY2BGR)
        if key == "standard":
            return cls._edges_standard(bgr, gray)
        if key == "stress":
            return cls._edges_stress(bgr, gray)
        return cls._edges_quality(bgr, gray)


def process_frame(frame: np.ndarray, profile: str) -> np.ndarray:
    """Multiprocessing is hedefi (pickle dostu ince sarici)."""
    return EdgeInspectionPipeline.apply(frame, profile)
