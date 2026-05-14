"""Sequential and parallel runners."""

from __future__ import annotations

import logging
import multiprocessing as mp
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import cv2
import numpy as np

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


def run_split_screen_compare(
    source: str | int,
    num_workers: int,
    max_frames: int | None,
    show_window: bool,
    profile: str,
    recorder: VideoRecorder | None,
    stats_out: dict[str, Any] | None = None,
) -> int:
    """
    Dikey bolme (sol | sag): ayni kare once seri (ana is parcacigi), sagda
    ThreadPoolExecutor ile process_frame. Tam multiprocessing --mode parallel
    tek UI surecinde senkron tek kare icin uygun olmadigindan sag 'PARALLEL'
    etiketi iplik havuzunu temsil eder; gercek mp throughput ayri kosuda olculur.
    """
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        log.error("Kaynak acilamadi: %s", source)
        return 0

    key = canonical_profile(profile)
    meta = PROFILES.get(key, PROFILES["standard"])
    window = f"{PRODUCT_TITLE} | Split (Seq | Parallel-threads)"
    if show_window:
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    log.info(
        "Split-screen: her karede seri + ThreadPool (%s is) ayni CPU uzerinde; "
        "yan FPSler paylasim yuzunden normalize degildir. Tam kiyas icin "
        "--mode sequential / parallel ve --metrics-out kullanin.",
        max(1, num_workers),
    )

    rec = recorder or VideoRecorder(None, 30.0)
    font = cv2.FONT_HERSHEY_SIMPLEX
    seq_ms_hist: deque[float] = deque(maxlen=30)
    par_ms_hist: deque[float] = deque(maxlen=30)
    contention_frames = 0
    warn_contention = False
    fid = 0
    wall0 = time.perf_counter()
    s_sum = p_sum = w_sum = wait_sum = 0.0
    s_min = p_min = 1e18
    s_max = p_max = 0.0

    try:
        with ThreadPoolExecutor(max_workers=max(1, num_workers)) as pool:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                fid += 1
                t_loop = time.perf_counter()
                bgr = np.ascontiguousarray(frame)
                half_w = max(2, bgr.shape[1] // 2)
                h = bgr.shape[0]

                fut = pool.submit(process_frame, bgr.copy(), profile)
                t_after_submit = time.perf_counter()
                left = process_frame(bgr, profile)
                t_after_seq = time.perf_counter()
                right = fut.result()
                t_after_par = time.perf_counter()

                seq_ms = (t_after_seq - t_after_submit) * 1000.0
                par_wall_ms = (t_after_par - t_after_submit) * 1000.0
                par_wait_ms = (t_after_par - t_after_seq) * 1000.0
                wall_ms = (t_after_par - t_loop) * 1000.0

                seq_ms_hist.append(seq_ms)
                par_ms_hist.append(par_wall_ms)

                s_sum += seq_ms
                p_sum += par_wall_ms
                w_sum += wall_ms
                wait_sum += par_wait_ms
                s_min = min(s_min, seq_ms)
                s_max = max(s_max, seq_ms)
                p_min = min(p_min, par_wall_ms)
                p_max = max(p_max, par_wall_ms)

                if wall_ms > 100.0:
                    contention_frames += 1
                    if contention_frames >= 45 and not warn_contention:
                        warn_contention = True
                        log.warning(
                            "Split-screen: kare basina duvar suresi sik >100ms; CPU doygun. "
                            "Yan FPSleri mutlak performans olarak kullanmayin; tam olcum "
                            "--mode sequential / parallel --metrics-out ile yapin."
                        )

                fps_seq = 1000.0 * len(seq_ms_hist) / max(1e-6, sum(seq_ms_hist))
                fps_par = 1000.0 * len(par_ms_hist) / max(1e-6, sum(par_ms_hist))
                wall_fps = 1000.0 / wall_ms if wall_ms > 1e-3 else 0.0

                if left.shape[:2] != right.shape[:2] or left.shape[2] != right.shape[2]:
                    right = cv2.resize(
                        right,
                        (left.shape[1], left.shape[0]),
                        interpolation=cv2.INTER_AREA,
                    )
                left_s = cv2.resize(left, (half_w, h), interpolation=cv2.INTER_AREA)
                right_s = cv2.resize(right, (half_w, h), interpolation=cv2.INTER_AREA)
                combo = np.hstack((left_s, right_s))
                ch, _cw = combo.shape[:2]
                mid = half_w

                cv2.line(combo, (mid, 0), (mid, ch), (255, 255, 255), 2)

                cv2.putText(
                    combo,
                    "SEQUENTIAL",
                    (12, 36),
                    font,
                    0.85,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    combo,
                    f"FPS~{fps_seq:.1f}  {seq_ms:.1f}ms",
                    (12, 72),
                    font,
                    0.55,
                    (60, 60, 255),
                    2,
                    cv2.LINE_AA,
                )

                cv2.putText(
                    combo,
                    "PARALLEL",
                    (mid + 12, 36),
                    font,
                    0.85,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    combo,
                    f"FPS~{fps_par:.1f}  {par_wall_ms:.1f}ms",
                    (mid + 12, 72),
                    font,
                    0.55,
                    (0, 200, 100),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    combo,
                    f"(threads W={max(1, num_workers)})",
                    (mid + 12, 100),
                    font,
                    0.45,
                    (0, 180, 80),
                    1,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    combo,
                    f"wait-after-seq {par_wait_ms:.1f}ms",
                    (mid + 12, 122),
                    font,
                    0.45,
                    (0, 200, 200),
                    1,
                    cv2.LINE_AA,
                )

                cv2.putText(
                    combo,
                    f"Frame ID: {fid}  |  duvar ~{wall_fps:.1f} FPS",
                    (12, ch - 14),
                    font,
                    0.5,
                    (0, 255, 255),
                    1,
                    cv2.LINE_AA,
                )

                line1 = f"{PRODUCT_TITLE}  |  {meta.display_name}  |  v{__version__}"
                line2 = f"Split-screen  |  profil={meta.key}  |  kare #{fid}"
                draw_hud(combo, line1, line2)
                rec.write(combo)

                if show_window:
                    cv2.imshow(window, combo)
                    if (cv2.waitKey(1) & 0xFF) == ord("q"):
                        break
                if max_frames is not None and fid >= max_frames:
                    break
    finally:
        cap.release()
        rec.close()
        if show_window:
            try:
                cv2.destroyWindow(window)
            except cv2.error:
                cv2.destroyAllWindows()

    elapsed = time.perf_counter() - wall0
    log.info(
        "Split-screen bitti: %s kare, %.3f s, ort. duvar FPS ~%.2f",
        fid,
        elapsed,
        fid / elapsed if elapsed > 0 else 0.0,
    )
    if stats_out is not None and fid > 0:
        stats_out.clear()
        stats_out.update(
            {
                "frames": fid,
                "sequential_ms_mean": round(s_sum / fid, 4),
                "sequential_ms_min": round(s_min, 4),
                "sequential_ms_max": round(s_max, 4),
                "parallel_branch_wall_ms_mean": round(p_sum / fid, 4),
                "parallel_branch_wall_ms_min": round(p_min, 4),
                "parallel_branch_wall_ms_max": round(p_max, 4),
                "wait_after_sequential_ms_mean": round(wait_sum / fid, 4),
                "frame_wall_ms_mean": round(w_sum / fid, 4),
                "approx_fps_from_sequential_ms": round(1000.0 * fid / s_sum, 4) if s_sum > 0 else 0.0,
                "approx_fps_from_parallel_wall_ms": round(1000.0 * fid / p_sum, 4) if p_sum > 0 else 0.0,
                "note": (
                    "Yan yana FPSler ayni CPU paylasimli; tam kiyas icin "
                    "--mode sequential / parallel ve --metrics-out kullanin."
                ),
            }
        )
    return fid
