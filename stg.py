"""攻击/移动状态机（前摇、后摇、可攻击）。"""

from __future__ import annotations

from typing import Any

from pix.calc import attack_timing

READY = "ready"
WINDUP = "windup"
RECOVERY = "recovery"


class StgGame:
    def __init__(self, champion: str, attack_speed: float) -> None:
        timing = attack_timing(champion, attack_speed)
        if timing is None or timing["windup"] is None or timing["interval"] is None:
            raise ValueError("攻速无效")
        self.interval = float(timing["interval"])
        self.windup = float(timing["windup"])
        self.state = READY
        self.windup_end: float | None = None
        self.interval_end: float | None = None
        self.pending_damage = False

    def attack(self, t: float) -> dict[str, Any]:
        t = float(t)
        if self.state != READY:
            return {"event": "blocked", "state": self.state, "can_attack": False}
        self.state = WINDUP
        self.windup_end = t + self.windup
        self.interval_end = t + self.interval
        self.pending_damage = True
        return {"event": "windup_start", "state": self.state, "can_attack": False}

    def move(self, t: float) -> dict[str, Any]:
        if self.state == WINDUP:
            self.state = READY
            self.windup_end = None
            self.interval_end = None
            self.pending_damage = False
            return {"event": "cancel", "state": self.state, "can_attack": True}
        return {"event": "move", "state": self.state, "can_attack": self.can_attack}

    def advance(self, t: float) -> list[str]:
        t = float(t)
        events: list[str] = []
        if self.state == WINDUP and self.pending_damage and self.windup_end is not None and t >= self.windup_end:
            self.pending_damage = False
            self.state = RECOVERY
            events.append("damage")
        if self.state == RECOVERY and self.interval_end is not None and t >= self.interval_end:
            self.state = READY
            events.append("ready")
        return events

    @property
    def can_attack(self) -> bool:
        return self.state == READY
