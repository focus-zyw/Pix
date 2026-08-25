"""Pix 精灵：从 assets 加载 PNG，缩放至叠加层尺寸。"""

from __future__ import annotations

from functools import lru_cache

from pix.image_util import decode_png, resize_rgba
from pix.paths import resolve_pix_file

SPRITE = 80

_STATE_FILES: dict[str, str] = {
    "wait": "pix.png",
    "ready": "ready_green.png",
    "windup": "ready_yellow.png",
    "recovery": "ready_red.png",
}

_FALLBACK_FILES = ("ready.png", "pix.png")


def _scale_to_sprite(rgba: bytes, w: int, h: int) -> bytearray:
    if w == SPRITE and h == SPRITE:
        return bytearray(rgba)
    return bytearray(resize_rgba(rgba, w, h, SPRITE, SPRITE))


@lru_cache(maxsize=8)
def _load_asset(name: str) -> bytearray | None:
    path = resolve_pix_file("assets", name)
    if not path:
        return None
    w, h, rgba = decode_png(path.read_bytes())
    return _scale_to_sprite(rgba, w, h)


def draw_pix(state: str) -> bytearray:
    name = _STATE_FILES.get(state)
    if name:
        buf = _load_asset(name)
        if buf is not None:
            return buf
    for alt in _FALLBACK_FILES:
        buf = _load_asset(alt)
        if buf is not None:
            return buf
    return bytearray(SPRITE * SPRITE * 4)


def visual_state(snap: dict) -> str:
    if not snap.get("live"):
        return "wait"
    return str(snap.get("state") or "ready")
