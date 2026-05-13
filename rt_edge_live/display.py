"""Paralel modda sonuc kuyrugunu sirali tuketme + HUD + kayit."""

from __future__ import annotations

import logging
import multiprocessing as mp
import queue
import time
from collections import deque

import cv2
import numpy as np

from .constants import PRODUCT_TITLE
from .hud import draw_hud, rolling_fps
from .profiles import PROFILES, canonical_profile
from .recorder import VideoRecorder
from .version import __version__

log = logging.getLogger(__name__)


def run_display_loop(
    result_q: mp.Queue,
    stop_ev: mp.Event,
    window: str,
    max_frames: int | None,
    show_window: bool,
    frames_produced: mp.Value | None,
    reader_done: mp.Event | None,
    profile: str,
    parallel_workers: int | None,
    recorder: VideoRecorder | None,
) -> int:
    key = canonical_profile(profile)
    meta = PROFILES.get(key, PROFILES["standard"])
    next_id = 1
    buffer: dict[int, np.ndarray] = {}
    t0 = time.perf_counter()
    displayed = 0
    perf_times: deque[float] = deque(maxlen=60)

    def all_stream_displayed() -> bool:
        if reader_done is None or frames_produced is None:
            return False
        if not reader_done.is_set():
            return False
        total = int(frames_produced.value)
        if total <= 0:
            return True
        return next_id > total

    rec = recorder or VideoRecorder(None, 30.0)

    try:
        while not stop_ev.is_set():
            try:
                msg = result_q.get(timeout=0.5)
            except queue.Empty:
                if all_stream_displayed():
                    stop_ev.set()
                    break
                continue

            if len(msg) == 4:
                _fid, _frame, err, wid = msg
                log.error("isçi %s hata paketi: %s", wid, err)
                continue

            fid, frame = msg
            buffer[fid] = frame

            while next_id in buffer:
                img = buffer.pop(next_id)
                displayed += 1
                now = time.perf_counter()
                perf_times.append(now)
                elapsed = now - t0
                avg_fps = displayed / elapsed if elapsed > 0 else 0.0
                roll_fps = rolling_fps(perf_times)
                fps_show = roll_fps if roll_fps > 0 else avg_fps

                if parallel_workers is None:
                    role = "Sirali (tek surec)"
                    wtxt = "W=1"
                else:
                    role = "Paralel (isci havuzu)"
                    wtxt = f"W={parallel_workers}"
                line1 = f"{PRODUCT_TITLE}  |  {meta.display_name}  |  v{__version__}"
                line2 = (
                    f"{role}  |  {wtxt}  |  profil={meta.key}  |  "
                    f"FPS~{fps_show:.1f}  |  kare #{next_id}"
                )
                draw_hud(img, line1, line2)
                rec.write(img)

                if show_window:
                    cv2.imshow(window, img)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        stop_ev.set()
                        break
                next_id += 1
                if max_frames is not None and next_id > max_frames:
                    stop_ev.set()
                    break
            if stop_ev.is_set():
                break
            if max_frames is not None and next_id > max_frames:
                break
            if all_stream_displayed():
                stop_ev.set()
                break
    finally:
        rec.close()

    if show_window:
        try:
            cv2.destroyWindow(window)
        except cv2.error:
            cv2.destroyAllWindows()

    return displayed
