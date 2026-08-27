"""Windows 全局按键监听（只读、零注入）。

游戏在前台时 GetAsyncKeyState 往往读不到；改用 Raw Input + RIDEV_INPUTSINK
在本进程隐藏窗口收 WM_INPUT，不注入、不改游戏。注册失败则回退轮询。
"""

from __future__ import annotations

import ctypes
import sys
import threading
import time
from collections.abc import Callable
from ctypes import wintypes
from typing import Any

_VK: dict[str, int] = {
    "LMB": 0x01,
    "RMB": 0x02,
    "MMB": 0x04,
    "X1": 0x05,
    "X2": 0x06,
    "BACK": 0x08,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "SHIFT": 0x10,
    "CTRL": 0x11,
    "CONTROL": 0x11,
    "ALT": 0x12,
    "PAUSE": 0x13,
    "CAPSLOCK": 0x14,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "SPACE": 0x20,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "END": 0x23,
    "HOME": 0x24,
    "ARROWLEFT": 0x25,
    "ARROWUP": 0x26,
    "ARROWRIGHT": 0x27,
    "ARROWDOWN": 0x28,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
}

_GET_ASYNC: Any = None

WM_INPUT = 0x00FF
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
RIDEV_INPUTSINK = 0x00000100
RIDEV_REMOVE = 0x00000001
RID_INPUT = 0x10000003
RIM_TYPEMOUSE = 0
RIM_TYPEKEYBOARD = 1
RI_KEY_BREAK = 1
RI_MOUSE_LEFT_BUTTON_DOWN = 0x0001
RI_MOUSE_RIGHT_BUTTON_DOWN = 0x0004
RI_MOUSE_MIDDLE_BUTTON_DOWN = 0x0010
RI_MOUSE_BUTTON_4_DOWN = 0x0040
RI_MOUSE_BUTTON_5_DOWN = 0x0100
WS_POPUP = 0x80000000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
_RAW_BUF_MIN = 256
_MOUSE_DOWN_FLAGS = (
    RI_MOUSE_LEFT_BUTTON_DOWN
    | RI_MOUSE_RIGHT_BUTTON_DOWN
    | RI_MOUSE_MIDDLE_BUTTON_DOWN
    | RI_MOUSE_BUTTON_4_DOWN
    | RI_MOUSE_BUTTON_5_DOWN
)

_WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t
)


class _MSG_POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_ssize_t),
        ("time", ctypes.c_uint),
        ("pt", _MSG_POINT),
    ]


class _WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", _WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.c_void_p),
        ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", ctypes.c_void_p),
    ]


_USER32: Any = None
_KERNEL32: Any = None
_RAW_WINAPI_BOUND = False


def _user32() -> Any:
    global _USER32
    if _USER32 is None:
        _USER32 = ctypes.WinDLL("user32", use_last_error=True)
    return _USER32


def _kernel32() -> Any:
    global _KERNEL32
    if _KERNEL32 is None:
        _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    return _KERNEL32


def _bind_raw_winapi() -> None:
    global _RAW_WINAPI_BOUND
    if _RAW_WINAPI_BOUND:
        return
    user32 = _user32()
    kernel32 = _kernel32()
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = ctypes.c_void_p
    user32.RegisterClassExW.argtypes = [ctypes.POINTER(_WNDCLASSEXW)]
    user32.RegisterClassExW.restype = wintypes.ATOM
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    user32.CreateWindowExW.restype = ctypes.c_void_p
    user32.RegisterRawInputDevices.argtypes = [
        ctypes.POINTER(RAWINPUTDEVICE),
        wintypes.UINT,
        wintypes.UINT,
    ]
    user32.RegisterRawInputDevices.restype = wintypes.BOOL
    user32.GetMessageW.argtypes = [ctypes.POINTER(_MSG), ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
    user32.GetMessageW.restype = ctypes.c_int
    user32.TranslateMessage.argtypes = [ctypes.POINTER(_MSG)]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(_MSG)]
    user32.DispatchMessageW.restype = ctypes.c_ssize_t
    user32.PostMessageW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_size_t,
        ctypes.c_ssize_t,
    ]
    _RAW_WINAPI_BOUND = True


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", ctypes.c_void_p),
        ("wParam", ctypes.c_size_t),
    ]


class _BTN(ctypes.Structure):
    _fields_ = [("usButtonFlags", wintypes.USHORT), ("usButtonData", wintypes.USHORT)]


class _BU(ctypes.Union):
    _fields_ = [("ulButtons", wintypes.ULONG), ("btn", _BTN)]


class RAWMOUSE(ctypes.Structure):
    _fields_ = [
        ("usFlags", wintypes.USHORT),
        ("_pad", wintypes.USHORT),
        ("u", _BU),
        ("ulRawButtons", wintypes.ULONG),
        ("lLastX", wintypes.LONG),
        ("lLastY", wintypes.LONG),
        ("ulExtraInformation", wintypes.ULONG),
    ]


class RAWKEYBOARD(ctypes.Structure):
    _fields_ = [
        ("MakeCode", wintypes.USHORT),
        ("Flags", wintypes.USHORT),
        ("Reserved", wintypes.USHORT),
        ("VKey", wintypes.USHORT),
        ("Message", wintypes.UINT),
        ("ExtraInformation", wintypes.ULONG),
    ]


class _DATA(ctypes.Union):
    _fields_ = [("mouse", RAWMOUSE), ("keyboard", RAWKEYBOARD)]


class RAWINPUT(ctypes.Structure):
    _fields_ = [("header", RAWINPUTHEADER), ("data", _DATA)]


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", ctypes.c_void_p),
    ]


_GET_RAW_INPUT_DATA: Any = None


def _get_raw_input_data() -> Any:
    global _GET_RAW_INPUT_DATA
    if _GET_RAW_INPUT_DATA is None:
        fn = ctypes.WinDLL("user32", use_last_error=True).GetRawInputData
        fn.argtypes = [
            ctypes.c_void_p,
            wintypes.UINT,
            ctypes.c_void_p,
            ctypes.POINTER(wintypes.UINT),
            wintypes.UINT,
        ]
        fn.restype = wintypes.UINT
        _GET_RAW_INPUT_DATA = fn
    return _GET_RAW_INPUT_DATA


def _as_raw_input(buf: bytes) -> RAWINPUT | None:
    n = ctypes.sizeof(RAWINPUT)
    if len(buf) < ctypes.sizeof(RAWINPUTHEADER):
        return None
    if len(buf) < n:
        buf = buf + bytes(n - len(buf))
    return RAWINPUT.from_buffer_copy(buf[:n])


def raw_input_is_key_down(buf: bytes) -> bool:
    """True if this packet is a mouse-button or key down (ignore pointer moves)."""
    raw = _as_raw_input(buf)
    if raw is None:
        return False
    if raw.header.dwType == RIM_TYPEMOUSE:
        return bool(int(raw.data.mouse.u.btn.usButtonFlags) & _MOUSE_DOWN_FLAGS)
    if raw.header.dwType == RIM_TYPEKEYBOARD:
        if int(raw.data.keyboard.Flags) & RI_KEY_BREAK:
            return False
        vk = int(raw.data.keyboard.VKey)
        return bool(vk and vk != 0xFF)
    return False


def raw_input_vks(buf: bytes) -> list[int]:
    """Parse one RAWINPUT packet into virtual-key codes that just went down."""
    raw = _as_raw_input(buf)
    if raw is None:
        return []
    vks: list[int] = []
    if raw.header.dwType == RIM_TYPEMOUSE:
        flags = int(raw.data.mouse.u.btn.usButtonFlags)
        if flags & RI_MOUSE_LEFT_BUTTON_DOWN:
            vks.append(0x01)
        if flags & RI_MOUSE_RIGHT_BUTTON_DOWN:
            vks.append(0x02)
        if flags & RI_MOUSE_MIDDLE_BUTTON_DOWN:
            vks.append(0x04)
        if flags & RI_MOUSE_BUTTON_4_DOWN:
            vks.append(0x05)
        if flags & RI_MOUSE_BUTTON_5_DOWN:
            vks.append(0x06)
    elif raw.header.dwType == RIM_TYPEKEYBOARD:
        if int(raw.data.keyboard.Flags) & RI_KEY_BREAK:
            return []
        vk = int(raw.data.keyboard.VKey)
        if vk and vk != 0xFF:
            vks.append(vk)
    return vks


def is_input_available() -> bool:
    return sys.platform == "win32"


_VK_BY_CODE: dict[int, str] = {}
for _name, _code in _VK.items():
    _VK_BY_CODE.setdefault(_code, _name)


def key_to_vk(key: str) -> int:
    """配置键名 → 虚拟键码。"""
    k = (key or "").strip().upper().replace(" ", "")
    if not k:
        raise ValueError("空按键")
    if k in _VK:
        return _VK[k]
    if k.startswith("VK") and len(k) >= 3:
        try:
            return int(k[2:], 16)
        except ValueError:
            pass
    if len(k) == 1:
        return ord(k)
    if k.startswith("F") and k[1:].isdigit():
        n = int(k[1:])
        if 1 <= n <= 24:
            return 0x70 + n - 1
    raise ValueError(f"未知按键: {key}")


def vk_to_key(vk: int) -> str:
    """虚拟键码 → 配置键名（与 key_to_vk 可互转）。"""
    vk = int(vk)
    if vk in _VK_BY_CODE:
        return _VK_BY_CODE[vk]
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk)
    if 0x70 <= vk <= 0x87:
        return f"F{vk - 0x70 + 1}"
    if vk <= 0:
        raise ValueError("空按键")
    return f"VK{vk:02X}"


def is_key_down(vk: int) -> bool:
    if sys.platform != "win32":
        return False
    global _GET_ASYNC
    if _GET_ASYNC is None:
        import ctypes

        fn = ctypes.WinDLL("user32", use_last_error=True).GetAsyncKeyState
        fn.argtypes = [ctypes.c_int]
        fn.restype = ctypes.c_short
        _GET_ASYNC = fn
    return bool(_GET_ASYNC(int(vk)) & 0x8000)


class GlobalKeyWatcher:
    """Raw Input 收按下边沿；失败则轮询。回调 on_press(name, t)，t 仅作参考。

    catch_all 时 name 是配置键名（任意按下），否则是 bindings 里的逻辑名。
    """

    def __init__(
        self,
        bindings: dict[str, str],
        on_press: Callable[[str, float], None],
        *,
        poll_hz: float = 125.0,
        catch_all: bool = False,
    ) -> None:
        self._vk_to_names: dict[int, list[str]] = {}
        for name, key in bindings.items():
            vk = key_to_vk(key)
            self._vk_to_names.setdefault(vk, []).append(name)
        self._on_press = on_press
        self._poll_hz = poll_hz
        self._catch_all = catch_all
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None
        self._t0 = 0.0
        self._hwnd = 0
        self._class_name = ""
        self._wndproc_ref: Any = None
        self._def_proc: Any = None
        self._class_buf: Any = None
        self._title_buf: Any = None
        self._last_fire: dict[int, float] = {}
        self._raw_buf = ctypes.create_string_buffer(_RAW_BUF_MIN)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._ready.clear()
        self._t0 = time.monotonic()
        self._last_fire = {}
        self._hwnd = 0
        self._thread = threading.Thread(target=self._loop, daemon=True, name="atk-keys")
        self._thread.start()
        self._ready.wait(timeout=2.0)

    def stop(self) -> None:
        self._ready.wait(timeout=2.0)
        self._stop.set()
        hwnd = self._hwnd
        if hwnd:
            try:
                _bind_raw_winapi()
                _user32().PostMessageW(hwnd, WM_CLOSE, 0, 0)
            except Exception:  # noqa: BLE001
                pass
        th = self._thread
        self._thread = None
        if th is not None and th is not threading.current_thread():
            th.join(timeout=2.0)
        self._hwnd = 0

    def _fire(self, vk: int) -> None:
        now_abs = time.monotonic()
        vk = int(vk)
        if now_abs - self._last_fire.get(vk, 0.0) < 0.03:
            return
        self._last_fire[vk] = now_abs
        names = self._vk_to_names.get(vk) or []
        t = now_abs - self._t0
        if self._catch_all:
            try:
                self._on_press(vk_to_key(vk), t)
            except Exception:  # noqa: BLE001
                pass
            return
        for name in names:
            try:
                self._on_press(name, t)
            except Exception:  # noqa: BLE001
                pass

    def _loop(self) -> None:
        if sys.platform != "win32":
            self._ready.set()
            return
        try:
            ok = self._start_raw()
        except Exception:  # noqa: BLE001
            ok = False
        self._ready.set()
        try:
            if ok:
                self._raw_message_loop()
            else:
                self._poll_loop()
        finally:
            self._teardown_raw()

    def _start_raw(self) -> bool:
        _bind_raw_winapi()
        user32 = _user32()
        kernel32 = _kernel32()
        def_proc = _WNDPROC(("DefWindowProcW", user32))
        self._def_proc = def_proc

        def _cb(hwnd: int, msg: int, wparam: int, lparam: int) -> int:
            if msg == WM_INPUT:
                self._on_wm_input(lparam)
                return 0
            if msg == WM_DESTROY:
                self._hwnd = 0
                user32.PostQuitMessage(0)
                return 0
            return int(def_proc(hwnd, msg, wparam, lparam))

        self._wndproc_ref = _WNDPROC(_cb)
        self._class_name = f"AtkRawIn{id(self):x}"
        self._class_buf = ctypes.create_unicode_buffer(self._class_name)
        self._title_buf = ctypes.create_unicode_buffer("atk-rawin")
        hinst = kernel32.GetModuleHandleW(None)
        wc = _WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(_WNDCLASSEXW)
        wc.lpfnWndProc = self._wndproc_ref
        wc.hInstance = hinst
        wc.lpszClassName = ctypes.cast(self._class_buf, wintypes.LPCWSTR)
        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if not atom:
            self._class_name = ""
            return False

        hwnd = user32.CreateWindowExW(
            WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
            self._class_buf,
            self._title_buf,
            WS_POPUP,
            0,
            0,
            1,
            1,
            None,
            None,
            hinst,
            None,
        )
        if not hwnd:
            self._teardown_raw()
            return False
        self._hwnd = int(hwnd)

        devices = (RAWINPUTDEVICE * 2)()
        devices[0].usUsagePage = 0x01
        devices[0].usUsage = 0x02
        devices[0].dwFlags = RIDEV_INPUTSINK
        devices[0].hwndTarget = hwnd
        devices[1].usUsagePage = 0x01
        devices[1].usUsage = 0x06
        devices[1].dwFlags = RIDEV_INPUTSINK
        devices[1].hwndTarget = hwnd
        ok = bool(user32.RegisterRawInputDevices(devices, 2, ctypes.sizeof(RAWINPUTDEVICE)))
        if not ok:
            self._teardown_raw()
            return False
        return True

    def _on_wm_input(self, lparam: int) -> None:
        get_data = _get_raw_input_data()
        hraw = ctypes.c_void_p(lparam & 0xFFFFFFFFFFFFFFFF)
        size = wintypes.UINT(0)
        header_sz = ctypes.sizeof(RAWINPUTHEADER)
        get_data(hraw, RID_INPUT, None, ctypes.byref(size), header_sz)
        if not size.value:
            return
        if size.value > len(self._raw_buf):
            self._raw_buf = ctypes.create_string_buffer(size.value)
        size.value = len(self._raw_buf)
        got = get_data(hraw, RID_INPUT, self._raw_buf, ctypes.byref(size), header_sz)
        if got == 0xFFFFFFFF or got == 0:
            return
        packet = self._raw_buf.raw[:got]
        if not raw_input_is_key_down(packet):
            return
        for vk in raw_input_vks(packet):
            self._fire(vk)

    def _raw_message_loop(self) -> None:
        _bind_raw_winapi()
        user32 = _user32()
        msg = _MSG()
        while not self._stop.is_set():
            r = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if r <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _teardown_raw(self) -> None:
        if sys.platform != "win32":
            return
        _bind_raw_winapi()
        user32 = _user32()
        kernel32 = _kernel32()
        hwnd = self._hwnd
        self._hwnd = 0
        if hwnd:
            devices = (RAWINPUTDEVICE * 2)()
            devices[0].usUsagePage = 0x01
            devices[0].usUsage = 0x02
            devices[0].dwFlags = RIDEV_REMOVE
            devices[1].usUsagePage = 0x01
            devices[1].usUsage = 0x06
            devices[1].dwFlags = RIDEV_REMOVE
            try:
                user32.RegisterRawInputDevices(devices, 2, ctypes.sizeof(RAWINPUTDEVICE))
            except Exception:  # noqa: BLE001
                pass
            try:
                user32.DestroyWindow(hwnd)
            except Exception:  # noqa: BLE001
                pass
        if self._class_name:
            try:
                user32.UnregisterClassW(self._class_name, kernel32.GetModuleHandleW(None))
            except Exception:  # noqa: BLE001
                pass
            self._class_name = ""
        self._wndproc_ref = None

    def _poll_loop(self) -> None:
        vks = list(range(1, 255)) if self._catch_all else list(self._vk_to_names)
        down = {vk: is_key_down(vk) for vk in vks}
        interval = 1.0 / max(1.0, self._poll_hz)
        while not self._stop.is_set():
            for vk in vks:
                now = is_key_down(vk)
                if now and not down[vk]:
                    self._fire(vk)
                down[vk] = now
            self._stop.wait(interval)

    @property
    def available(self) -> bool:
        return is_input_available()
