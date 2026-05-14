"""CLI ve uygulama girisi."""

from __future__ import annotations

import argparse
import json
import logging
import multiprocessing as mp
import time
from pathlib import Path
from typing import Any

from .constants import PRODUCT_TITLE
from .logging_setup import configure_logging
from .metrics import metrics_payload
from .profiles import PROFILE_CLI_CHOICES, PROFILE_KEYS, PROFILES, canonical_profile
from .recorder import VideoRecorder
from .report import (
    write_compare_markdown,
    write_compare_markdown_payloads,
    write_run_markdown,
)
from .runners import run_parallel, run_sequential, run_split_screen_compare
from .version import __version__
from .video_source import parse_source

log = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    legacy = "light|balanced|heavy -> fast|standard|quality"
    epilog = """
Ornekler:
  Kamera, paralel:
    python -m rt_edge_live --source 0 --mode parallel --profile standard
  UTF-8 metrik dosyasi (kiyaslama icin onerilen):
    python -m rt_edge_live --source demo.mp4 --mode sequential --max-frames 500 --no-window --metrics-out seq.json
    python -m rt_edge_live --source demo.mp4 --mode parallel --workers 4 --max-frames 500 --no-window --metrics-out par.json
  Kiyaslama raporu (iki JSON):
    python -m rt_edge_live --compare-json seq.json par.json --report RAPOR.md
  Tek kosu + rapor + kayit:
    python -m rt_edge_live --source demo.mp4 --max-frames 200 --record cikti.mp4 --report rapor.md
  Split-screen (sol seri, sag iplik havuzu; ayni Frame ID):
    python -m rt_edge_live --source 0 --mode split-screen --workers 4 --profile standard --record split.mp4
  split.mp4: seri + paralel tek JSON (seq_split / par_split):
    python -m rt_edge_live --source split.mp4 --metrics-split-out split.json --max-frames 500 --no-window --profile stress --workers 4 --log-level WARNING
  Agir profil (paralellik demasi, --profile stress):
    python -m rt_edge_live --source demo.mp4 --mode sequential --profile stress --max-frames 200 --no-window --metrics-out seq_s.json
    python -m rt_edge_live --source demo.mp4 --mode parallel --profile stress --workers 4 --max-frames 200 --no-window --metrics-out par_s.json
"""
    parser = argparse.ArgumentParser(
        description=(
            f"{PRODUCT_TITLE} v{__version__} - "
            "OpenCV + multiprocessing RT is hatti"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument("--source", default="0", help="Kamera indeksi veya video yolu")
    parser.add_argument(
        "--mode",
        choices=("parallel", "sequential", "split-screen"),
        default="parallel",
        help=(
            "parallel: multiprocessing isci havuzu; sequential: tek surec; "
            "split-screen: dikey bolme sol seri / sag ThreadPool (UI icin; tam mp ayri kosu)"
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, (mp.cpu_count() or 4) - 1),
        help="Paralel modda isci sayisi",
    )
    parser.add_argument("--queue-size", type=int, default=32, help="Kuyruk max boyutu")
    parser.add_argument("--max-frames", type=int, default=None, help="N kare sonra dur")
    parser.add_argument("--no-window", action="store_true", help="Goruntu penceresi yok")
    parser.add_argument("--benchmark", action="store_true", help="Insan okunur olcum ozeti")
    parser.add_argument(
        "--metrics-json",
        action="store_true",
        help="Tek satir JSON olcum (stdout)",
    )
    parser.add_argument(
        "--metrics-out",
        type=str,
        default=None,
        metavar="PATH",
        help="Metrik JSON dosyasina yaz (UTF-8; PowerShell > yerine onerilir)",
    )
    parser.add_argument(
        "--record",
        type=str,
        default=None,
        metavar="PATH",
        help="Islenmis videoyu MP4 olarak kaydet",
    )
    parser.add_argument(
        "--record-fps",
        type=float,
        default=30.0,
        help="Kayit FPS",
    )
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        metavar="PATH",
        help="Markdown olcum raporu dosyasi (kosu sonrasi)",
    )
    parser.add_argument(
        "--compare-json",
        nargs=2,
        metavar=("A.json", "B.json"),
        default=None,
        help="Iki JSON olcumunu Markdown raporda kiyasla (--report zorunlu)",
    )
    parser.add_argument(
        "--metrics-split-out",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Once sequential sonra parallel kosar; seq_split ve par_split tek UTF-8 JSON'a yazilir "
            "(--mode split-screen ile birlikte kullanilamaz; --metrics-out ile birlikte degil)"
        ),
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help="Log seviyesi",
    )
    parser.add_argument(
        "--profile",
        choices=PROFILE_CLI_CHOICES,
        default="standard",
        help=f"Profil ({legacy}; stress=agir CPU, paralel kiyas)",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    level = getattr(logging, args.log_level)
    configure_logging(level)

    if args.compare_json:
        if not args.report:
            parser.error("--compare-json ile birlikte --report RAPOR.md gerekli")
        write_compare_markdown(
            args.report,
            args.compare_json[0],
            args.compare_json[1],
            label_a="Koşu A",
            label_b="Koşu B",
        )
        log.info("Karsilastirma raporu yazildi: %s", args.report)
        return

    profile = canonical_profile(args.profile)
    if profile not in PROFILE_KEYS:
        log.warning("Bilinmeyen profil, standard: %s", args.profile)
        profile = "standard"

    source = parse_source(args.source)
    num_workers = max(1, args.workers)
    max_pending = max(num_workers * 2, args.queue_size)
    show_window = not args.no_window
    max_frames = args.max_frames
    meta = PROFILES[profile]

    if args.metrics_split_out:
        if args.mode == "split-screen":
            parser.error("--metrics-split-out ile --mode split-screen birlikte kullanilamaz")
        if args.metrics_out:
            parser.error("--metrics-split-out ile --metrics-out birlikte kullanilamaz")
        log.info(
            "metrics-split-out: once sequential sonra parallel (profile=%s workers=%s source=%s)",
            profile,
            num_workers,
            source,
        )
        try:
            t0 = time.perf_counter()
            count_seq = run_sequential(
                source, max_frames, False, profile, recorder=None
            )
            wall_seq = time.perf_counter() - t0
        except KeyboardInterrupt:
            log.warning("Ctrl+C ile durduruldu (sequential asamasinda)")
            raise SystemExit(130) from None

        payload_seq = metrics_payload(
            profile=profile,
            mode="sequential",
            workers=1,
            frames=count_seq,
            wall_s=wall_seq,
            source=source,
            record=None,
        )

        try:
            t0 = time.perf_counter()
            count_par = run_parallel(
                source,
                num_workers,
                max_pending,
                max_frames,
                False,
                profile,
                level,
                recorder=None,
            )
            wall_par = time.perf_counter() - t0
        except KeyboardInterrupt:
            log.warning("Ctrl+C ile durduruldu (parallel asamasinda)")
            raise SystemExit(130) from None

        payload_par = metrics_payload(
            profile=profile,
            mode="parallel",
            workers=num_workers,
            frames=count_par,
            wall_s=wall_par,
            source=source,
            record=None,
        )

        combined: dict[str, Any] = {
            "profile": profile,
            "source": str(source),
            "workers_parallel": num_workers,
            "seq_split": payload_seq,
            "par_split": payload_par,
        }
        if max_frames is not None:
            combined["max_frames"] = max_frames

        outp = Path(args.metrics_split_out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(
            json.dumps(combined, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log.info("Birlesik metrik JSON yazildi: %s", outp.resolve())

        if args.metrics_json:
            print(json.dumps(combined, ensure_ascii=False))

        if args.report:
            write_compare_markdown_payloads(
                args.report,
                payload_seq,
                payload_par,
                label_a="Koşu A (seq_split)",
                label_b="Koşu B (par_split)",
                ref_a=f"{outp.name} → seq_split",
                ref_b=f"{outp.name} → par_split",
            )
            log.info("Karsilastirma raporu yazildi: %s", args.report)

        if not args.metrics_json and (
            args.benchmark or args.max_frames is not None
        ):
            thr_s = count_seq / wall_seq if wall_seq > 0 else 0.0
            thr_p = count_par / wall_par if wall_par > 0 else 0.0
            print("--- RT Kenar Analitigi / split cift olcum ---")
            print(f"  urun      : {PRODUCT_TITLE} v{__version__}")
            print(f"  profil    : {meta.key} ({meta.display_name})")
            print(f"  cikti     : {outp.resolve()}")
            print(f"  sequential: {count_seq} kare, {wall_seq:.3f} s, {thr_s:.2f} kare/s")
            print(
                f"  parallel  : {count_par} kare, {wall_par:.3f} s, {thr_p:.2f} kare/s "
                f"(workers={num_workers})"
            )
            print("------------------------------------")

        log.info("Bitti: seq %s kare, par %s kare", count_seq, count_par)
        return

    record_path = args.record
    if record_path:
        Path(record_path).parent.mkdir(parents=True, exist_ok=True)
    recorder = VideoRecorder(record_path, args.record_fps) if record_path else None

    split_stats: dict[str, Any] = {}

    log.info(
        "Basladi: mode=%s profile=%s workers=%s source=%s",
        args.mode,
        profile,
        num_workers if args.mode in ("parallel", "split-screen") else 1,
        source,
    )

    t_wall0 = time.perf_counter()
    try:
        if args.mode == "sequential":
            count = run_sequential(
                source, max_frames, show_window, profile, recorder=recorder
            )
        elif args.mode == "split-screen":
            count = run_split_screen_compare(
                source,
                num_workers,
                max_frames,
                show_window,
                profile,
                recorder=recorder,
                stats_out=split_stats,
            )
        else:
            count = run_parallel(
                source,
                num_workers,
                max_pending,
                max_frames,
                show_window,
                profile,
                level,
                recorder=recorder,
            )
    except KeyboardInterrupt:
        log.warning("Ctrl+C ile durduruldu")
        raise SystemExit(130) from None

    wall = time.perf_counter() - t_wall0
    wn = num_workers if args.mode in ("parallel", "split-screen") else 1

    rec_stats = recorder.get_stats() if recorder else None
    payload = metrics_payload(
        profile=profile,
        mode=args.mode,
        workers=wn,
        frames=count,
        wall_s=wall,
        source=source,
        record=rec_stats,
    )
    if split_stats:
        payload["split_screen"] = split_stats

    if args.metrics_json:
        print(json.dumps(payload, ensure_ascii=False))
    if args.metrics_out:
        outp = Path(args.metrics_out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log.info("Metrik JSON yazildi: %s", outp.resolve())
    if not args.metrics_json and (args.benchmark or args.max_frames is not None or split_stats):
        thr = count / wall if wall > 0 else 0.0
        print("--- RT Kenar Analitigi / olcum ---")
        print(f"  urun      : {PRODUCT_TITLE} v{__version__}")
        print(f"  profil    : {meta.key} ({meta.display_name})")
        print(f"  hat       : {meta.one_line}")
        print(f"  mod       : {args.mode}  workers={wn}")
        print(f"  kare      : {count}")
        print(f"  sure (s)  : {wall:.3f}")
        print(f"  throughput: {thr:.2f} kare/s")
        if rec_stats:
            print(
                f"  kayit     : ok={rec_stats.get('ok')} "
                f"cikti={rec_stats.get('output_path')} "
                f"kare={rec_stats.get('frames_written')}"
            )
        if split_stats:
            print(f"  split seq ms (ort) : {split_stats.get('sequential_ms_mean')}")
            print(f"  split par ms (ort): {split_stats.get('parallel_branch_wall_ms_mean')}")
            print(f"  split wait ms (ort): {split_stats.get('wait_after_sequential_ms_mean')}")
        print("------------------------------------")

    if args.report:
        write_run_markdown(args.report, payload)
        log.info("Rapor yazildi: %s", args.report)

    log.info("Bitti: %s kare, %.3f s", count, wall)
