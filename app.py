"""Pix 叠加层：游戏内精灵 + 实战提示。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ is None:
    _root = Path(__file__).resolve().parent.parent
    _root_str = str(_root)
    if _root_str not in sys.path:
        sys.path.insert(0, _root_str)
import threading
import time
from typing import Any

from pix.calc import attack_timing
from pix.coach import AttackCoach
from pix.input_win import GlobalKeyWatcher, is_input_available, key_to_vk
from pix.live_client import fetch_all_game_data, parse_me
from pix.overlay import PixOverlay
from pix.paths import prefs_path

POLL_SEC = 1.0
COACH_HZ = 60.0

DEFAULT_PREFS = {
    "attack_key": "LMB",
    "move_key": "RMB",
    "x": 80,
    "y": 80,
}


class PixApp:
    def __init__(self) -> None:
        self.window: PixOverlay | None = None
        self._stop = threading.Event()
        self._coach_loop_stop = threading.Event()
        self._coach: AttackCoach | None = None
        self._coach_t0 = 0.0
        self._coach_watcher: GlobalKeyWatcher | None = None
        self._coach_lock = threading.Lock()
        self._coach_push_key: tuple[Any, ...] | None = None
        self._live_push_key: tuple[Any, ...] | None = None
        self._current_champion: str | None = None
        self._current_as: float | None = None
        self._live = False
        self._closed = False
        self._settings_open = False
        self._capturing: str | None = None
        self._capture_watcher: GlobalKeyWatcher | None = None
        self._prefs = self._load_prefs()

    def _load_prefs(self) -> dict[str, Any]:
        prefs = dict(DEFAULT_PREFS)
        p = prefs_path()
        if p.exists():
            try:
                loaded = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    prefs.update(loaded)
            except Exception:  # noqa: BLE001
                pass
        return prefs

    def _save_prefs(self) -> None:
        try:
            p = prefs_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                json.dumps(self._prefs, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:  # noqa: BLE001
            pass

    def _start_coach(self) -> str | None:
        if not is_input_available():
            return "仅支持 Windows"
        if not self._current_champion or self._current_as is None:
            return None
        timing = attack_timing(self._current_champion, self._current_as)
        if timing is None or timing["windup"] is None:
            return "攻速无效"
        self._stop_coach_watcher()
        with self._coach_lock:
            self._coach = AttackCoach(self._current_champion, self._current_as)
            self._coach_t0 = time.monotonic()
            self._coach_push_key = None
        bindings = {
            "attack": str(self._prefs.get("attack_key") or "LMB"),
            "move": str(self._prefs.get("move_key") or "RMB"),
        }
        try:
            self._coach_watcher = GlobalKeyWatcher(bindings, self._on_coach_key, poll_hz=COACH_HZ)
            self._coach_watcher.start()
        except ValueError as exc:
            self._coach_watcher = None
            with self._coach_lock:
                self._coach = None
            return str(exc)
        return None

    def _stop_coach_watcher(self) -> None:
        watcher = self._coach_watcher
        self._coach_watcher = None
        if watcher is not None:
            watcher.stop()

    def _on_coach_key(self, name: str, t: float) -> None:
        del t
        with self._coach_lock:
            if self._coach is None:
                return
            now = time.monotonic() - self._coach_t0
            if name == "attack":
                self._coach.press_attack(now)
            elif name == "move":
                self._coach.press_move(now)

    def _coach_loop(self) -> None:
        interval = 1.0 / COACH_HZ
        while not self._coach_loop_stop.is_set():
            with self._coach_lock:
                coach = self._coach
                if coach is not None:
                    t = time.monotonic() - self._coach_t0
                    coach.tick(t)
                    if self._current_champion and self._current_as is not None:
                        coach.update_timing(self._current_champion, self._current_as)
                    snap = self._coach_snapshot_locked(t)
                else:
                    snap = self._idle_snapshot()
            key = (
                snap.get("state"),
                snap.get("live"),
                snap.get("settings"),
                snap.get("capturing"),
                snap.get("attack_key"),
                snap.get("move_key"),
                round(float(snap.get("as") or 0), 2),
                round(float(snap.get("windup") or 0), 3),
            )
            if key != self._coach_push_key:
                self._coach_push_key = key
                self._push(snap)
            self._coach_loop_stop.wait(interval)

    def _coach_snapshot_locked(self, t: float) -> dict[str, Any]:
        assert self._coach is not None
        snap = self._coach.snapshot(t)
        return self._enrich(snap)

    def _idle_snapshot(self) -> dict[str, Any]:
        timing = attack_timing(self._current_champion, self._current_as)
        if timing is None:
            return self._enrich(
                {
                    "state": "ready",
                    "label": "等待对局",
                    "as": None,
                    "windup": None,
                    "recovery": None,
                }
            )
        return self._enrich(
            {
                "state": "ready",
                "label": "等待攻击键",
                "as": timing["as"],
                "windup": timing["windup"],
                "recovery": timing["recovery"],
            }
        )

    def _enrich(self, snap: dict[str, Any]) -> dict[str, Any]:
        snap = dict(snap)
        snap["live"] = self._live
        snap["champion"] = self._current_champion or ""
        snap["settings"] = self._settings_open and not self._live
        snap["capturing"] = self._capturing if snap["settings"] else None
        snap["attack_key"] = str(self._prefs.get("attack_key") or "LMB")
        snap["move_key"] = str(self._prefs.get("move_key") or "RMB")
        if snap.get("as") is None and self._current_as is not None:
            snap["as"] = round(float(self._current_as), 4)
        if snap.get("windup") is None and self._current_champion and self._current_as is not None:
            timing = attack_timing(self._current_champion, self._current_as)
            if timing:
                snap["windup"] = timing.get("windup")
                snap["recovery"] = timing.get("recovery")
        return snap

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            champion: str | None = None
            as_: float | None = None
            live = False
            data = fetch_all_game_data()
            if data:
                me = parse_me(data) or {}
                champion = (me.get("champion") or "").strip() or None
                as_ = me.get("as") if me.get("as") is not None else None
                live = bool(champion) and as_ is not None
            self._current_champion = champion
            self._current_as = as_
            self._live = live
            if live:
                self._close_settings()

            if live and self._coach is None:
                self._start_coach()
            self._stop.wait(POLL_SEC)

    def _push(self, snapshot: dict[str, Any]) -> None:
        if self._closed or self.window is None:
            return
        try:
            self.window.set_state(snapshot)
        except Exception:  # noqa: BLE001
            pass

    def _refresh_overlay(self) -> None:
        with self._coach_lock:
            if self._coach is not None:
                t = time.monotonic() - self._coach_t0
                snap = self._coach_snapshot_locked(t)
            else:
                snap = self._idle_snapshot()
        self._push(snap)

    def _close_settings(self) -> None:
        changed = self._settings_open or self._capturing is not None or self._capture_watcher is not None
        self._settings_open = False
        self._capturing = None
        self._stop_capture_watcher()
        if changed:
            self._refresh_overlay()

    def _on_icon_click(self) -> None:
        if self._live:
            return
        if self._settings_open:
            self._close_settings()
            return
        self._settings_open = True
        self._refresh_overlay()

    def _on_bind_slot(self, slot: str) -> None:
        if self._live or not self._settings_open:
            return
        if slot not in ("attack", "move"):
            return
        if self._capturing == slot:
            self._capturing = None
            self._stop_capture_watcher()
            self._refresh_overlay()
            return
        self._capturing = slot
        if self._capture_watcher is None:
            self._start_capture_watcher()
        self._refresh_overlay()

    def _start_capture_watcher(self) -> None:
        if not is_input_available():
            return
        try:
            self._capture_watcher = GlobalKeyWatcher({}, self._on_capture_key, catch_all=True)
            self._capture_watcher.start()
        except ValueError:
            self._capture_watcher = None

    def _stop_capture_watcher(self) -> None:
        watcher = self._capture_watcher
        self._capture_watcher = None
        if watcher is not None:
            watcher.stop()

    def _on_capture_key(self, name: str, t: float) -> None:
        del t
        slot = self._capturing
        if not slot:
            return
        try:
            key_to_vk(name)
        except ValueError:
            return
        self._capturing = None
        self._prefs[f"{slot}_key"] = name
        self._save_prefs()
        self._stop_capture_watcher()
        self._refresh_overlay()

    def _on_window_close(self) -> None:
        self._closed = True
        if self.window is not None:
            x, y = self.window.position()
            self._prefs["x"] = x
            self._prefs["y"] = y
            self._save_prefs()
        self._stop.set()
        self._coach_loop_stop.set()
        self._stop_capture_watcher()
        self._stop_coach_watcher()
        with self._coach_lock:
            self._coach = None

    def start(self) -> None:
        if sys.platform != "win32":
            raise SystemExit("Pix 实战提示仅支持 Windows")

        overlay = PixOverlay(
            on_close=self._on_window_close,
            on_icon_click=self._on_icon_click,
            on_bind_slot=self._on_bind_slot,
        )
        overlay.set_position(int(self._prefs.get("x") or 80), int(self._prefs.get("y") or 80))
        self.window = overlay

        threading.Thread(target=self._poll_loop, daemon=True).start()
        threading.Thread(target=self._coach_loop, daemon=True).start()
        overlay.run()


def main() -> None:
    PixApp().start()


if __name__ == "__main__":
    main()
