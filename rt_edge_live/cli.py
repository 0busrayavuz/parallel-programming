"""CLI ve uygulama girisi."""

from __future__ import annotations

import argparse
import json
import logging
import multiprocessing as mp
import time
from pathlib import Path

from .constants import PRODUCT_TITLE
from .logging_setup import configure_logging
from .metrics import metrics_payload
from .profiles import PROFILE_CLI_CHOICES, PROFILE_KEYS, PROFILES, canonical_profile
from .recorder import VideoRecorder
from .report import write_compare_markdown, write_run_markdown
from .runners import run_parallel, run_sequential
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
        choices=("parallel", "sequential"),
        default="parallel",
        help="parallel: isci havuzu; sequential: tek surec",
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
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help="Log seviyesi",
    )
    parser.add_argument(
        "--profile",
        choices=PROFILE_CLI_CHOICES,
        default="standard",
        help=f"Profil ({legacy})",
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

    record_path = args.record
    if record_path:
        Path(record_path).parent.mkdir(parents=True, exist_ok=True)
    recorder = VideoRecorder(record_path, args.record_fps) if record_path else None

    log.info(
        "Basladi: mode=%s profile=%s workers=%s source=%s",
        args.mode,
        profile,
        num_workers if args.mode == "parallel" else 1,
        source,
    )

    t_wall0 = time.perf_counter()
    try:
        if args.mode == "sequential":
            count = run_sequential(
                source, max_frames, show_window, profile, recorder=recorder
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
    wn = num_workers if args.mode == "parallel" else 1

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
    if not args.metrics_json and (args.benchmark or args.max_frames is not None):
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
        print("------------------------------------")

    if args.report:
        write_run_markdown(args.report, payload)
        log.info("Rapor yazildi: %s", args.report)

    log.info("Bitti: %s kare, %.3f s", count, wall)
