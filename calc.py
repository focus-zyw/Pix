"""攻速 → 前摇 / 后摇 / 间隔。仅依赖 pix/data/stat_growth.json。"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from pix.paths import resolve_stat_growth_path

AS_CAP = 2.5
WINDUP_DEFAULT_PCT = 0.3

_CN_ALIASES: dict[str, str] = {
    "女枪": "Miss Fortune",
    "赏金猎人": "Miss Fortune",
    "牧魂人": "Yorick",
    "掘墓者": "Yorick",
    "男枪": "Graves",
    "机器人": "Blitzcrank",
    "炸弹人": "Ziggs",
    "琴女": "Sona",
    "风女": "Janna",
    "火男": "Brand",
    "冰女": "Lissandra",
    "岩雀": "Taliyah",
    "小炮": "Tristana",
    "大嘴": "Kog'Maw",
    "深渊巨口": "Kog'Maw",
    "克格莫": "Kog'Maw",
    "老鼠": "Twitch",
    "飞机": "Corki",
    "卡特": "Katarina",
    "剑姬": "Fiora",
    "剑圣": "Master Yi",
    "提莫": "Teemo",
    "蛮王": "Tryndamere",
    "诺手": "Darius",
    "皇子": "Jarvan IV",
    "猪妹": "Sejuani",
    "酒桶": "Gragas",
    "挖掘机": "Rek'Sai",
    "蜘蛛": "Elise",
    "乌鸦": "Swain",
    "发条": "Orianna",
    "妖姬": "LeBlanc",
    "狐狸": "Ahri",
    "阿狸": "Ahri",
    "霞": "Xayah",
    "洛": "Rakan",
    "锤石": "Thresh",
    "牛头": "Alistar",
    "泰坦": "Nautilus",
    "盲僧": "Lee Sin",
    "猴子": "Wukong",
    "悟空": "Wukong",
    "劫": "Zed",
    "亚托克斯": "Aatrox",
    "剑魔": "Aatrox",
    "梦魇": "Nocturne",
    "永恒梦魇": "Nocturne",
    "魔腾": "Nocturne",
    "金克丝": "Jinx",
    "金克斯": "Jinx",
    "璐璐": "Lulu",
}


@lru_cache(maxsize=1)
def load_stat_growth() -> dict[str, Any]:
    p = resolve_stat_growth_path()
    if not p:
        return {}
    return json.loads(p.read_text(encoding="utf-8")).get("champions") or {}


def champion_windup_pct(champion_en: str) -> float:
    stats = load_stat_growth().get(champion_en) or {}
    cast_t = stats.get("attack_cast_time")
    total_t = stats.get("attack_total_time")
    offset = stats.get("attack_delay_offset")
    if cast_t is not None and total_t:
        return float(cast_t) / float(total_t)
    if offset is not None:
        return 0.3 + float(offset)
    return WINDUP_DEFAULT_PCT


def resolve_name(champion: str) -> str:
    if not champion:
        return ""
    raw = str(champion).strip()
    mapped = _CN_ALIASES.get(raw) or _CN_ALIASES.get(re.sub(r"\s+", "", raw))
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
    pct = champion_windup_pct(en)
    interval = 1.0 / as_
    windup = pct / as_
    recovery = interval - windup
    return {
        "champion": en,
        "as": round(as_, 4),
        "windup": round(windup, 4),
        "recovery": round(recovery, 4),
        "interval": round(interval, 4),
    }
