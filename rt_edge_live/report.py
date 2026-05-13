"""Markdown rapor uretimi (tek kosu veya iki JSON kiyas)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def _decode_file_bytes(raw: bytes) -> str:
    if raw.startswith(b"\xff\xfe\x00\x00"):
        return raw.decode("utf-32-le")
    if raw.startswith(b"\x00\x00\xfe\xff"):
        return raw.decode("utf-32-be")
    if raw.startswith(b"\xff\xfe"):
        return raw.decode("utf-16-le")
    if raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16-be")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-16-le")


def _load_json_file(path: str | Path) -> dict[str, Any]:
    """PowerShell `> f.json` (UTF-16), Out-File utf8, veya cok satirli JSON."""
    p = Path(path)
    raw = p.read_bytes()
    if not raw.strip():
        raise ValueError(f"Bos dosya: {p}")
    text = _decode_file_bytes(raw).strip()

    for chunk in (text, text.splitlines()[0] if text else ""):
        if not chunk:
            continue
        try:
            obj = json.loads(chunk)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue

    i0, i1 = text.find("{"), text.rfind("}")
    if i0 != -1 and i1 > i0:
        obj = json.loads(text[i0 : i1 + 1])
        if isinstance(obj, dict):
            return obj

    raise ValueError(f"JSON parse edilemedi: {p}")


def write_run_markdown(out_path: str | Path, payload: dict[str, Any]) -> None:
    """Tek calistirmanin olcum raporu (Markdown)."""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    rec = payload.get("record") or {}
    rec_rows = ""
    if rec:
        rec_rows = (
            f"| Istek yolu | `{rec.get('requested_path', '-')}` |\n"
            f"| Yazilan dosya | `{rec.get('output_path', '-')}` |\n"
            f"| Kare sayisi | {rec.get('frames_written', 0)} |\n"
            f"| Basarili | {rec.get('ok', False)} |\n"
        )

    body = f"""# {payload.get("product", "Rapor")} - Olcum ciktisi

- **Rapor zamanı (UTC)**: {_utc_now()}
- **Yazılım sürümü**: `{payload.get("version", "?")}`

## 1. Deney koşulları

| Alan | Değer |
|------|-------|
| Kaynak | `{payload.get("source", "")}` |
| Profil | `{payload.get("profile", "")}` ({payload.get("profile_display", "")}) |
| İş hattı | {payload.get("pipeline", "")} |
| Mod | `{payload.get("mode", "")}` |
| İşçi (workers) | {payload.get("workers", "")} |

## 2. Sonuç özeti

| Metrik | Değer |
|--------|-------|
| İşlenen kare | {payload.get("frames", 0)} |
| Duvar saati (s) | {payload.get("wall_seconds", 0)} |
| Throughput (kare/s) | **{payload.get("throughput_frames_per_s", 0)}** |

## 3. Video kaydı

{rec_rows if rec_rows else "_Kayit istenmedi veya dosya acilamadi / kare yazilmadi._"}

## 4. Ham JSON (kopyala / arşiv)

```json
{json.dumps(payload, ensure_ascii=False, indent=2)}
```

---
*Bu dosya `python -m rt_edge_live --report ...` ile otomatik üretilmiştir.*
"""
    p.write_text(body, encoding="utf-8")


def write_compare_markdown(
    out_path: str | Path,
    path_a: str | Path,
    path_b: str | Path,
    label_a: str = "Koşu A",
    label_b: str = "Koşu B",
) -> None:
    """Iki JSON olcum dosyasini tabloda kiyaslar."""
    a = _load_json_file(path_a)
    b = _load_json_file(path_b)
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    thr_a = float(a.get("throughput_frames_per_s") or 0)
    thr_b = float(b.get("throughput_frames_per_s") or 0)
    if thr_a > 0 and thr_b > 0:
        hiz_oran = thr_b / thr_a
        kiyas = f"**B / A throughput oranı:** {hiz_oran:.3f}x (1.0 ustu B daha hizli)"
    else:
        kiyas = "Throughput kiyaslanamadi (sifir kare veya sure)."

    body = f"""# Karsilastirmali olcum raporu

- **Rapor zamanı (UTC)**: {_utc_now()}
- **{label_a}**: `{path_a}`
- **{label_b}**: `{path_b}`

## Yan yana ozet

| Metrik | {label_a} | {label_b} |
|--------|-----------|-----------|
| Mod | {a.get("mode")} | {b.get("mode")} |
| Workers | {a.get("workers")} | {b.get("workers")} |
| Profil | {a.get("profile")} | {b.get("profile")} |
| Kare | {a.get("frames")} | {b.get("frames")} |
| Sure (s) | {a.get("wall_seconds")} | {b.get("wall_seconds")} |
| Throughput (kare/s) | **{a.get("throughput_frames_per_s")}** | **{b.get("throughput_frames_per_s")}** |

## Yorum

{kiyas}

## Ham JSON — {label_a}

```json
{json.dumps(a, ensure_ascii=False, indent=2)}
```

## Ham JSON — {label_b}

```json
{json.dumps(b, ensure_ascii=False, indent=2)}
```
"""
    p.write_text(body, encoding="utf-8")
