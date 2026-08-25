"""Live Client：读本机英雄名与攻速。"""

from __future__ import annotations

import threading
from typing import Any

import httpx

LIVE_BASE = "https://127.0.0.1:2999/liveclientdata"
_TIMEOUT = httpx.Timeout(connect=1.0, read=2.0, write=1.0, pool=1.0)
_CLIENT: httpx.Client | None = None
_CLIENT_LOCK = threading.Lock()


def _client() -> httpx.Client:
    global _CLIENT
    with _CLIENT_LOCK:
        if _CLIENT is None:
            _CLIENT = httpx.Client(verify=False, timeout=_TIMEOUT, trust_env=False)
        return _CLIENT


def _close_client() -> None:
    global _CLIENT
    with _CLIENT_LOCK:
        old, _CLIENT = _CLIENT, None
    if old is None:
        return
    try:
        old.close()
    except Exception:  # noqa: BLE001
        pass


def fetch_all_game_data() -> dict[str, Any] | None:
    try:
        r = _client().get(f"{LIVE_BASE}/allgamedata")
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:  # noqa: BLE001
        _close_client()
        return None


def parse_me(data: dict[str, Any]) -> dict[str, Any] | None:
    active = data.get("activePlayer") or {}
    my_name = (active.get("summonerName") or "").strip()
    stats = active.get("championStats") or {}
    me: dict[str, Any] | None = None
    for p in data.get("allPlayers") or []:
        if (p.get("summonerName") or "").strip() == my_name:
            me = {
                "champion": (p.get("championName") or "").strip() or "?",
                "is_me": True,
            }
            break
    if me is None:
        if not my_name and not stats:
            return None
        me = {
            "champion": (active.get("championName") or "").strip() or "?",
            "is_me": True,
        }
    if stats.get("attackSpeed") is not None:
        me["as"] = float(stats["attackSpeed"])
    return me
