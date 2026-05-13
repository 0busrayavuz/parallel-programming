"""Profil tanimlari ve canonical anahtar."""

from __future__ import annotations

from dataclasses import dataclass

PROFILE_KEYS: tuple[str, ...] = ("fast", "standard", "quality")

_LEGACY_PROFILE_ALIASES: dict[str, str] = {
    "light": "fast",
    "balanced": "standard",
    "heavy": "quality",
}

PROFILE_CLI_CHOICES: tuple[str, ...] = PROFILE_KEYS + tuple(_LEGACY_PROFILE_ALIASES.keys())


def canonical_profile(name: str) -> str:
    key = name.strip().lower()
    return _LEGACY_PROFILE_ALIASES.get(key, key)


@dataclass(frozen=True, slots=True)
class PipelineProfile:
    key: str
    display_name: str
    one_line: str


PROFILES: dict[str, PipelineProfile] = {
    "fast": PipelineProfile(
        key="fast",
        display_name="Hizli onizleme",
        one_line="Gaussian yumusatma + Canny (dusuk gecikme)",
    ),
    "standard": PipelineProfile(
        key="standard",
        display_name="Uretim standardi",
        one_line="CLAHE + Gaussian + Canny + morfoloji + kenar overlay",
    ),
    "quality": PipelineProfile(
        key="quality",
        display_name="Yuksek dogruluk",
        one_line="CLAHE + bilateral + Canny + morfoloji + overlay",
    ),
}
