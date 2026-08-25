"""攻速 → 前摇 / 后摇 / 间隔。依赖 pix/data/stat_growth.json 与 champion_aliases.json。

前摇时间用 wiki 通式：baseWindup + modifier × (间隔 × pct − baseWindup)。
modifier 缺省 1，即 pct ÷ 攻速。
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from pix.paths import resolve_pix_file, resolve_stat_growth_path

# 海克斯大乱斗上限 5.0；峡谷 Live 已截在 ~3.003，min(as, 5) 对普通模式是空操作。
AS_CAP = 5.0
WINDUP_DEFAULT_PCT = 0.3


@lru_cache(maxsize=1)
def load_stat_growth() -> dict[str, Any]:
    p = resolve_stat_growth_path()
    if not p:
        return {}
    return json.loads(p.read_text(encoding="utf-8")).get("champions") or {}


@lru_cache(maxsize=1)
def load_aliases() -> dict[str, str]:
    p = resolve_pix_file("data", "champion_aliases.json")
    if not p:
        return {}
    blob = json.loads(p.read_text(encoding="utf-8"))
    aliases = blob.get("aliases")
    return aliases if isinstance(aliases, dict) else {}


def _windup_pct_from_stats(stats: dict[str, Any]) -> float:
    cast_t = stats.get("attack_cast_time")
    total_t = stats.get("attack_total_time")
    offset = stats.get("attack_delay_offset")
    if cast_t is not None and total_t:
        return float(cast_t) / float(total_t)
    if offset is not None:
        return 0.3 + float(offset)
    return WINDUP_DEFAULT_PCT


def champion_windup_pct(champion_en: str) -> float:
    return _windup_pct_from_stats(load_stat_growth().get(champion_en) or {})


def _windup_seconds(stats: dict[str, Any], pct: float, as_: float) -> float:
    """当前前摇秒数。modifier 缺省 1 时等于 pct / as_。"""
    current = pct / as_
    modifier = stats.get("windup_modifier")
    as_base = stats.get("as_base")
    if modifier is None or as_base is None:
        return current
    as_base_f = float(as_base)
    if as_base_f <= 0:
        return current
    base_windup = pct / as_base_f
    return base_windup + float(modifier) * (current - base_windup)


def resolve_name(champion: str) -> str:
    if not champion:
        return ""
    raw = str(champion).strip()
    aliases = load_aliases()
    compact = re.sub(r"[\s·・]+", "", raw)
    mapped = aliases.get(raw) or aliases.get(compact)
    if mapped:
        return mapped
    growth = load_stat_growth()
    if raw in growth:
        return raw
    lower = raw.lower()
    for en in growth:
        if en.lower() == lower:
            return en
    return raw


def attack_timing(champion: str | None, attack_speed: float | None) -> dict[str, Any] | None:
    if not champion or attack_speed is None:
        return None
    en = resolve_name(champion)
    try:
        as_ = float(attack_speed)
    except (TypeError, ValueError):
        return None
    base = {
        "champion": en,
        "as": round(as_, 4),
        "windup": None,
        "recovery": None,
        "interval": None,
    }
    if as_ <= 0:
        return base
    as_ = min(as_, AS_CAP)
    stats = load_stat_growth().get(en) or {}
    pct = _windup_pct_from_stats(stats)
    interval = 1.0 / as_
    windup = _windup_seconds(stats, pct, as_)
    recovery = interval - windup
    return {
        "champion": en,
        "as": round(as_, 4),
        "windup": round(windup, 4),
        "recovery": round(recovery, 4),
        "interval": round(interval, 4),
    }
