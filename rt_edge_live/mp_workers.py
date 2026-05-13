"""Okuyucu ve isci surec hedefleri (multiprocessing spawn)."""

from __future__ import annotations

import logging
import multiprocessing as mp
import queue

from .logging_setup import ensure_child_logging
from .pipeline import process_frame

log = logging.getLogger(__name__)


def worker(
    job_q: mp.Queue,
    result_q: mp.Queue,
    stop_ev: mp.Event,
    worker_id: int,
    profile: str,
    log_level: int,
) -> None:
    ensure_child_logging(log_level)
    wlog = logging.getLogger(__name__ + ".worker")
    while not stop_ev.is_set():
        try:
            item = job_q.get(timeout=0.2)
        except queue.Empty:
            continue
        if item is None:
            break
        frame_id, frame = item
        try:
            out = process_frame(frame, profile)
            result_q.put((frame_id, out))
        except Exception as exc:
            wlog.exception("isçi %s kare %s islenemedi", worker_id, frame_id)
            result_q.put((frame_id, None, repr(exc), worker_id))


def reader(
    source: str | int,
    job_q: mp.Queue,
    num_workers: int,
    stop_ev: mp.Event,
    max_frames: int | None,
    frames_produced: mp.Value,
    reader_done: mp.Event,
    log_level: int,
) -> None:
    import cv2

    ensure_child_logging(log_level)
    rlog = logging.getLogger(__name__ + ".reader")
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        rlog.error("Kaynak acilamadi: %s", source)
        stop_ev.set()
        with frames_produced.get_lock():
            frames_produced.value = 0
        reader_done.set()
        for _ in range(num_workers):
            job_q.put(None)
        return

    frame_id = 0
    try:
        while not stop_ev.is_set():
            ret, frame = cap.read()
            if not ret:
                break
            frame_id += 1
            job_q.put((frame_id, frame))
            if max_frames is not None and frame_id >= max_frames:
                break
    finally:
        cap.release()
        with frames_produced.get_lock():
            frames_produced.value = frame_id
        reader_done.set()
        for _ in range(num_workers):
            job_q.put(None)
        rlog.info("Okuma bitti: %s kare", frame_id)
