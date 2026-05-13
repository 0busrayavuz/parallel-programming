"""Sequential and parallel runners."""

from __future__ import annotations

import logging
import multiprocessing as mp
import time
from collections import deque

import cv2

from .constants import PRODUCT_TITLE
from .display import run_display_loop
from .hud import draw_hud, rolling_fps
from .mp_workers import reader, worker
from .pipeline import process_frame
from .profiles import PROFILES, canonical_profile
from .recorder import VideoRecorder
from .version import __version__

log = logging.getLogger(__name__)


def run_sequential(
    source: str | int,
    max_frames: int | None,
    show_window: bool,
    profile: str,
    recorder: VideoRecorder | None,
) -> int:
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        log.error("Kaynak acilamadi: %s", source)
        return 0

    key = canonical_profile(profile)
    meta = PROFILES.get(key, PROFILES["standard"])
    window = f"{PRODUCT_TITLE} | Sirali"
    if show_window:
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    t0 = time.perf_counter()
    n = 0
    perf_times: deque[float] = deque(maxlen=60)
    rec = recorder or VideoRecorder(None, 30.0)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            n += 1
            out = process_frame(frame, profile)
            now = time.perf_counter()
            perf_times.append(now)
            elapsed = now - t0
            avg_fps = n / elapsed if elapsed > 0 else 0.0
            roll_fps = rolling_fps(perf_times)
            fps_show = roll_fps if roll_fps > 0 else avg_fps

            line1 = f"{PRODUCT_TITLE}  |  {meta.display_name}  |  v{__version__}"
            line2 = (
                f"Sirali (tek surec)  |  W=1  |  profil={meta.key}  |  "
                f"FPS~{fps_show:.1f}  |  kare #{n}"
            )
            draw_hud(out, line1, line2)
            rec.write(out)

            if show_window:
                cv2.imshow(window, out)
                if (cv2.waitKey(1) & 0xFF) == ord("q"):
                    break
            if max_frames is not None and n >= max_frames:
                break
    finally:
        cap.release()
        rec.close()
        if show_window:
            try:
                cv2.destroyWindow(window)
            except cv2.error:
                cv2.destroyAllWindows()

    return n


def run_parallel(
    source: str | int,
    num_workers: int,
    max_pending: int,
    max_frames: int | None,
    show_window: bool,
    profile: str,
    log_level: int,
    recorder: VideoRecorder | None,
) -> int:
    ctx = mp.get_context("spawn")
    job_q: mp.Queue = ctx.Queue(maxsize=max_pending)
    result_q: mp.Queue = ctx.Queue(maxsize=max_pending)
    stop_ev = ctx.Event()
    frames_produced = ctx.Value("i", -1)
    reader_done = ctx.Event()

    procs: list[mp.Process] = [
        ctx.Process(
            target=reader,
            args=(
                source,
                job_q,
                num_workers,
                stop_ev,
                max_frames,
                frames_produced,
                reader_done,
                log_level,
            ),
            daemon=True,
        )
    ]
    procs.extend(
        ctx.Process(
            target=worker,
            args=(job_q, result_q, stop_ev, wid, profile, log_level),
            daemon=True,
        )
        for wid in range(num_workers)
    )

    for p in procs:
        p.start()

    window = f"{PRODUCT_TITLE} | Paralel"
    if show_window:
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    try:
        return run_display_loop(
            result_q,
            stop_ev,
            window,
            max_frames,
            show_window,
            frames_produced,
            reader_done,
            profile,
            parallel_workers=num_workers,
            recorder=recorder,
        )
    finally:
        stop_ev.set()
        for p in procs:
            p.join(timeout=3.0)
            if p.is_alive():
                log.warning("Surec sonlandiriliyor: %s", p.pid)
                p.terminate()
