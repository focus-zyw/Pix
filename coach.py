"""实战提示：攻击键触发后按 Live 攻速展示前摇 / 后摇 / 可攻击。"""

from __future__ import annotations

from typing import Any

from pix.calc import attack_timing
from pix.stg import READY, RECOVERY, WINDUP, StgGame

_PHASE_LABEL = {
    READY: "可攻击",
    WINDUP: "前摇中",
    RECOVERY: "后摇中",
}


class AttackCoach:
    def __init__(self, champion: str, attack_speed: float) -> None:
        self._game = StgGame(champion, attack_speed)
        self._armed = False

    @property
    def game(self) -> StgGame:
        return self._game

    def update_timing(self, champion: str, attack_speed: float) -> None:
        timing = attack_timing(champion, attack_speed)
        if timing is None or timing["windup"] is None or timing["interval"] is None:
            return
        self._game.windup = float(timing["windup"])
        self._game.interval = float(timing["interval"])

    def press_attack(self, t: float) -> None:
        self._armed = True
        self._game.attack(t)

    def press_move(self, t: float) -> None:
        self._game.move(t)

    def tick(self, t: float) -> list[str]:
        return self._game.advance(t)

    def snapshot(self, t: float) -> dict[str, Any]:
        g = self._game
        state = g.state
        recovery = max(0.0, g.interval - g.windup)
        return {
            "armed": self._armed,
            "state": state,
            "can_attack": g.can_attack,
            "label": _PHASE_LABEL[state],
            "as": round(1.0 / g.interval, 4) if g.interval > 0 else 0.0,
            "windup": g.windup,
            "recovery": recovery,
            "interval": g.interval,
        }
