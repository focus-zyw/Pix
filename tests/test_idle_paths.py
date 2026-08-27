"""Idle / out-of-game paths that previously ballooned memory."""

from __future__ import annotations

import ctypes
import inspect
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PARENT = str(_ROOT.parent)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from pix.app import LIVE_MISS_STOP, PixApp
from pix.coach import AttackCoach
from pix.input_win import GlobalKeyWatcher, raw_input_is_key_down, raw_input_vks
from pix import input_win as iw
from pix import live_client
from pix.sprite import visual_state


def _mouse_left_down() -> bytes:
    raw = iw.RAWINPUT()
    raw.header.dwType = iw.RIM_TYPEMOUSE
    raw.header.dwSize = ctypes.sizeof(iw.RAWINPUT)
    raw.data.mouse.u.btn.usButtonFlags = iw.RI_MOUSE_LEFT_BUTTON_DOWN
    return bytes(ctypes.string_at(ctypes.byref(raw), ctypes.sizeof(raw)))


def _mouse_move() -> bytes:
    raw = iw.RAWINPUT()
    raw.header.dwType = iw.RIM_TYPEMOUSE
    raw.header.dwSize = ctypes.sizeof(iw.RAWINPUT)
    raw.data.mouse.lLastX = 3
    return bytes(ctypes.string_at(ctypes.byref(raw), ctypes.sizeof(raw)))


class RawInputMemoryTests(unittest.TestCase):
    def test_on_wm_input_does_not_define_ctypes_structs(self) -> None:
        src = inspect.getsource(GlobalKeyWatcher._on_wm_input)
        self.assertNotIn("class RAWINPUT", src)
        self.assertNotIn("class RAWMOUSE", src)
        self.assertNotIn("class RAWKEYBOARD", src)

    def test_start_raw_does_not_define_ctypes_structs(self) -> None:
        src = inspect.getsource(GlobalKeyWatcher._start_raw)
        self.assertNotIn("class WNDCLASSEXW", src)
        self.assertNotIn("WINFUNCTYPE", src)

    def test_raw_input_parse_does_not_grow_pointer_cache(self) -> None:
        packet = _mouse_left_down()
        self.assertEqual(raw_input_vks(packet), [0x01])
        cache = ctypes._pointer_type_cache
        n0 = len(cache)
        for _ in range(400):
            self.assertEqual(raw_input_vks(packet), [0x01])
        self.assertLessEqual(len(cache) - n0, 1)

    def test_mouse_left_down_is_not_skipped_as_move(self) -> None:
        down = _mouse_left_down()
        move = _mouse_move()
        self.assertTrue(raw_input_is_key_down(down))
        self.assertEqual(raw_input_vks(down), [0x01])
        self.assertFalse(raw_input_is_key_down(move))
        header_sz = ctypes.sizeof(iw.RAWINPUTHEADER)
        old_offset_flags = int.from_bytes(down[header_sz + 2 : header_sz + 4], "little")
        self.assertEqual(old_offset_flags & iw._MOUSE_DOWN_FLAGS, 0)

    def test_raw_start_cycles_do_not_grow_ctypes_cache(self) -> None:
        import gc

        cache = ctypes._pointer_type_cache
        n0 = len(cache)
        s0 = len(ctypes.Structure.__subclasses__())
        for _ in range(200):
            w = GlobalKeyWatcher({"attack": "LMB"}, lambda n, t: None)
            try:
                w._start_raw()
            except Exception:
                pass
            w._teardown_raw()
        gc.collect()
        self.assertLess(len(cache) - n0, 10)
        self.assertLess(len(ctypes.Structure.__subclasses__()) - s0, 10)


class LiveClientReuseTests(unittest.TestCase):
    def tearDown(self) -> None:
        live_client._close_client()

    def test_connect_error_keeps_client(self) -> None:
        import httpx

        class Boom(httpx.BaseTransport):
            def handle_request(self, request: httpx.Request) -> httpx.Response:
                raise httpx.ConnectError("down", request=request)

        live_client._close_client()
        client = httpx.Client(transport=Boom(), trust_env=False)
        live_client._CLIENT = client
        self.assertIsNone(live_client.fetch_all_game_data())
        self.assertIs(live_client._CLIENT, client)


class ParseMeTests(unittest.TestCase):
    def test_riot_id_match_still_live(self) -> None:
        me = live_client.parse_me(
            {
                "activePlayer": {
                    "summonerName": "",
                    "riotId": "Ada#NA1",
                    "championStats": {"attackSpeed": 0.658},
                },
                "allPlayers": [
                    {"summonerName": "Ada", "riotId": "Ada#NA1", "championName": "Ashe"},
                ],
            }
        )
        self.assertIsNotNone(me)
        assert me is not None
        self.assertEqual(me["champion"], "Ashe")
        self.assertEqual(me["as"], 0.658)

    def test_visual_state_turns_ready_when_live(self) -> None:
        self.assertEqual(visual_state({"live": False, "state": "ready"}), "wait")
        self.assertEqual(visual_state({"live": True, "state": "ready"}), "ready")
        self.assertEqual(visual_state({"live": True, "state": "windup"}), "windup")


class CoachIdleTests(unittest.TestCase):
    def test_missed_live_ticks_stop_coach(self) -> None:
        app = PixApp()
        app._coach = AttackCoach("Ashe", 0.658)
        app._live_misses = 0
        app._apply_live(None, None, False)
        self.assertIsNotNone(app._coach)
        for _ in range(LIVE_MISS_STOP):
            app._apply_live(None, None, False)
        self.assertIsNone(app._coach)


if __name__ == "__main__":
    unittest.main()
