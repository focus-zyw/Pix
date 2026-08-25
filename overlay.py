"""Win32 分层窗：Pix 精灵贴在游戏上，空白点穿。"""

from __future__ import annotations

import ctypes
import sys
import threading
from ctypes import wintypes
from typing import Any, Callable

from pix.sprite import SPRITE, draw_pix, visual_state

WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_NCHITTEST = 0x0084
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_MOUSELEAVE = 0x02A3
WM_APP = 0x8000
WM_PIX_REFRESH = WM_APP + 1

HTCLIENT = 1
HTTRANSPARENT = -1

WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x00080000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

HWND_TOPMOST = -1
SW_SHOWNOACTIVATE = 4
ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01
SWP_NOACTIVATE = 0x0010
TME_LEAVE = 0x00000002
DT_CALCRECT = 0x00000400
DT_NOPREFIX = 0x00000800
DT_LEFT = 0x00000000
TRANSPARENT = 1
ANTIALIASED_QUALITY = 4
DEFAULT_CHARSET = 1
CLIP_DEFAULT_PRECIS = 0
OUT_DEFAULT_PRECIS = 0
FW_NORMAL = 400
BI_RGB = 0
DIB_RGB_COLORS = 0
HIT_ALPHA = 24
DRAG_PX = 6
TIP_GAP = 8
TIP_PAD_X = 10
TIP_PAD_Y = 8
TIP_BG = (12, 16, 22, 230)
TIP_FG = (220, 230, 238)
TIP_DIM = (122, 144, 160)
TIP_ACCENT = (127, 217, 139)
FONT_PX = 13
CAPTURE_PLACEHOLDER = "按下…"
_KEY_LABELS = {
    "LMB": "左键",
    "RMB": "右键",
    "MMB": "中键",
    "X1": "侧键1",
    "X2": "侧键2",
    "SPACE": "空格",
    "ESC": "Esc",
    "ESCAPE": "Esc",
    "CTRL": "Ctrl",
    "CONTROL": "Ctrl",
    "SHIFT": "Shift",
    "ALT": "Alt",
    "TAB": "Tab",
    "ENTER": "Enter",
    "BACK": "Backspace",
}

WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t
)


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_ssize_t),
        ("time", ctypes.c_uint),
        ("pt", POINT),
    ]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", wintypes.BYTE),
        ("BlendFlags", wintypes.BYTE),
        ("SourceConstantAlpha", wintypes.BYTE),
        ("AlphaFormat", wintypes.BYTE),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


class TRACKMOUSEEVENT(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("hwndTrack", ctypes.c_void_p),
        ("dwHoverTime", wintypes.DWORD),
    ]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
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


_API_BOUND = False


def _user32():
    return ctypes.WinDLL("user32", use_last_error=True)


def _gdi32():
    return ctypes.WinDLL("gdi32", use_last_error=True)


def _kernel32():
    return ctypes.WinDLL("kernel32", use_last_error=True)


def _bind_api() -> None:
    global _API_BOUND
    if _API_BOUND:
        return
    user32 = _user32()
    gdi32 = _gdi32()
    user32.CreateWindowExW.restype = ctypes.c_void_p
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
    user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
    user32.RegisterClassExW.restype = wintypes.ATOM
    user32.DefWindowProcW.restype = ctypes.c_ssize_t
    user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
    user32.GetMessageW.restype = ctypes.c_int
    user32.DispatchMessageW.restype = ctypes.c_ssize_t
    user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
    user32.DrawTextW.argtypes = [
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.c_int,
        ctypes.POINTER(RECT),
        wintypes.UINT,
    ]
    user32.DrawTextW.restype = ctypes.c_int
    user32.UpdateLayeredWindow.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(POINT),
        ctypes.POINTER(SIZE),
        ctypes.c_void_p,
        ctypes.POINTER(POINT),
        wintypes.DWORD,
        ctypes.POINTER(BLENDFUNCTION),
        wintypes.DWORD,
    ]
    user32.UpdateLayeredWindow.restype = wintypes.BOOL
    user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT)]
    user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
    user32.TrackMouseEvent.argtypes = [ctypes.POINTER(TRACKMOUSEEVENT)]
    user32.SetWindowPos.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
    user32.SystemParametersInfoW.restype = wintypes.BOOL
    user32.LoadCursorW.restype = ctypes.c_void_p
    user32.SetCapture.restype = ctypes.c_void_p
    gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
    gdi32.CreateDIBSection.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(BITMAPINFO),
        wintypes.UINT,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    gdi32.CreateDIBSection.restype = ctypes.c_void_p
    gdi32.SelectObject.restype = ctypes.c_void_p
    gdi32.CreateFontW.restype = ctypes.c_void_p
    gdi32.SetTextColor.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    gdi32.SetBkMode.argtypes = [ctypes.c_void_p, ctypes.c_int]
    _API_BOUND = True


def _premul_bgra(rgba: bytearray, w: int, h: int) -> bytes:
    out = bytearray(len(rgba))
    for i in range(0, len(rgba), 4):
        r, g, b, a = rgba[i], rgba[i + 1], rgba[i + 2], rgba[i + 3]
        out[i] = (b * a + 127) // 255
        out[i + 1] = (g * a + 127) // 255
        out[i + 2] = (r * a + 127) // 255
        out[i + 3] = a
    return bytes(out)


def _blend(buf: bytearray, w: int, h: int, x: int, y: int, r: int, g: int, b: int, a: float) -> None:
    if a <= 0 or x < 0 or y < 0 or x >= w or y >= h:
        return
    i = (y * w + x) * 4
    src_a = min(1.0, a)
    dst_a = buf[i + 3] / 255.0
    out_a = src_a + dst_a * (1.0 - src_a)
    if out_a <= 0:
        return
    buf[i] = int((r * src_a + buf[i] * dst_a * (1.0 - src_a)) / out_a + 0.5)
    buf[i + 1] = int((g * src_a + buf[i + 1] * dst_a * (1.0 - src_a)) / out_a + 0.5)
    buf[i + 2] = int((b * src_a + buf[i + 2] * dst_a * (1.0 - src_a)) / out_a + 0.5)
    buf[i + 3] = int(out_a * 255 + 0.5)


def _fill_round_rect(
    buf: bytearray, w: int, h: int, x0: int, y0: int, x1: int, y1: int, rad: int, rgb: tuple[int, int, int], a: float
) -> None:
    rr, gg, bb = rgb
    for y in range(y0, y1):
        for x in range(x0, x1):
            dx = 0
            dy = 0
            if x < x0 + rad:
                dx = x0 + rad - x
            elif x >= x1 - rad:
                dx = x - (x1 - rad - 1)
            if y < y0 + rad:
                dy = y0 + rad - y
            elif y >= y1 - rad:
                dy = y - (y1 - rad - 1)
            if dx > 0 and dy > 0 and dx * dx + dy * dy > rad * rad:
                continue
            _blend(buf, w, h, x, y, rr, gg, bb, a)


def _fmt_as(v: Any) -> str:
    try:
        return f"{float(v):.2f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_sec(v: Any) -> str:
    try:
        return f"{float(v):.3f}s"
    except (TypeError, ValueError):
        return "—"


def _tip_lines(snap: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("攻速", _fmt_as(snap.get("as"))),
        ("前摇", _fmt_sec(snap.get("windup"))),
        ("后摇", _fmt_sec(snap.get("recovery"))),
    ]


def display_key(key: str) -> str:
    k = (key or "").strip()
    if not k:
        return "—"
    return _KEY_LABELS.get(k.upper().replace(" ", ""), k)


def settings_rows(attack_key: str, move_key: str, capturing: str | None) -> list[tuple[str, str, str]]:
    attack_val = CAPTURE_PLACEHOLDER if capturing == "attack" else display_key(attack_key)
    move_val = CAPTURE_PLACEHOLDER if capturing == "move" else display_key(move_key)
    return [
        ("attack", "攻击键", attack_val),
        ("move", "移动键", move_val),
    ]


def settings_hint(capturing: str | None) -> str:
    if capturing == "attack":
        return "按下新的攻击键"
    if capturing == "move":
        return "按下新的移动键"
    return "点按键名后按下新键"


def rbutton_closes(snap: dict[str, Any]) -> bool:
    """设置或正在绑定时右键用来设键，不能退出。"""
    return not snap.get("settings") and not snap.get("capturing")


def moved_enough(x0: int, y0: int, x1: int, y1: int, px: int = DRAG_PX) -> bool:
    dx = x1 - x0
    dy = y1 - y0
    return dx * dx + dy * dy >= px * px


def kind_at(regions: list[tuple[str, int, int, int, int]], x: int, y: int) -> str | None:
    for kind, x0, y0, x1, y1 in reversed(regions):
        if x0 <= x < x1 and y0 <= y < y1:
            return kind
    return None


class _GdiFont:
    def __init__(self) -> None:
        _bind_api()
        gdi32 = _gdi32()
        self._font = gdi32.CreateFontW(
            -FONT_PX,
            0,
            0,
            0,
            FW_NORMAL,
            0,
            0,
            0,
            DEFAULT_CHARSET,
            OUT_DEFAULT_PRECIS,
            CLIP_DEFAULT_PRECIS,
            ANTIALIASED_QUALITY,
            0,
            "Microsoft YaHei",
        )
        if not self._font:
            self._font = gdi32.CreateFontW(
                -FONT_PX, 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET, 0, 0, ANTIALIASED_QUALITY, 0, "SimHei"
            )

    def close(self) -> None:
        if self._font:
            _gdi32().DeleteObject(self._font)
            self._font = 0

    def measure(self, text: str) -> tuple[int, int]:
        hdc = _user32().GetDC(None)
        old = _gdi32().SelectObject(hdc, self._font)
        rect = RECT(0, 0, 0, 0)
        _user32().DrawTextW(hdc, text, -1, ctypes.byref(rect), DT_CALCRECT | DT_NOPREFIX)
        _gdi32().SelectObject(hdc, old)
        _user32().ReleaseDC(None, hdc)
        return max(1, rect.right - rect.left), max(1, rect.bottom - rect.top)

    def raster(self, text: str, rgb: tuple[int, int, int]) -> tuple[int, int, bytearray]:
        tw, th = self.measure(text)
        gdi32 = _gdi32()
        user32 = _user32()
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = tw
        bmi.bmiHeader.biHeight = -th
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB
        bits = ctypes.c_void_p()
        hdc = gdi32.CreateCompatibleDC(None)
        hbmp = gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), DIB_RGB_COLORS, ctypes.byref(bits), None, 0)
        old_bmp = gdi32.SelectObject(hdc, hbmp)
        old_font = gdi32.SelectObject(hdc, self._font)
        gdi32.SetBkMode(hdc, TRANSPARENT)
        gdi32.SetTextColor(hdc, rgb[0] | (rgb[1] << 8) | (rgb[2] << 16))
        rc = RECT(0, 0, tw, th)
        user32.DrawTextW(hdc, text, -1, ctypes.byref(rc), DT_LEFT | DT_NOPREFIX)
        nbytes = tw * th * 4
        raw = ctypes.string_at(bits, nbytes)
        out = bytearray(nbytes)
        tr, tg, tb = rgb
        for i in range(0, nbytes, 4):
            b, g, r = raw[i], raw[i + 1], raw[i + 2]
            a = max(b, g, r)
            if a:
                out[i] = tr
                out[i + 1] = tg
                out[i + 2] = tb
                out[i + 3] = a
        gdi32.SelectObject(hdc, old_font)
        gdi32.SelectObject(hdc, old_bmp)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc)
        return tw, th, out


def _paste(dst: bytearray, dw: int, dh: int, src: bytearray, sw: int, sh: int, ox: int, oy: int) -> None:
    for y in range(sh):
        dy = oy + y
        if dy < 0 or dy >= dh:
            continue
        for x in range(sw):
            dx = ox + x
            if dx < 0 or dx >= dw:
                continue
            i = (y * sw + x) * 4
            a = src[i + 3] / 255.0
            if a <= 0:
                continue
            _blend(dst, dw, dh, dx, dy, src[i], src[i + 1], src[i + 2], a)


class PixOverlay:
    def __init__(
        self,
        on_close: Callable[[], None] | None = None,
        on_icon_click: Callable[[], None] | None = None,
        on_bind_slot: Callable[[str], None] | None = None,
    ) -> None:
        if sys.platform != "win32":
            raise RuntimeError("仅支持 Windows")
        self._on_close = on_close
        self._on_icon_click = on_icon_click
        self._on_bind_slot = on_bind_slot
        self._lock = threading.Lock()
        self._snap: dict[str, Any] = {
            "state": "ready",
            "live": False,
            "as": None,
            "windup": None,
            "recovery": None,
        }
        self._hover = False
        self._dragging = False
        self._pressing = False
        self._down_kind: str | None = None
        self._down_sx = 0
        self._down_sy = 0
        self._drag_dx = 0
        self._drag_dy = 0
        self._pix_sx = 80
        self._pix_sy = 80
        self._hwnd = 0
        self._class_name = ""
        self._wndproc_ref: Any = None
        self._class_buf: Any = None
        self._title_buf: Any = None
        self._hit: bytes = b""
        self._hit_w = 0
        self._hit_h = 0
        self._regions: list[tuple[str, int, int, int, int]] = []
        self._tracking = False
        self._font = _GdiFont()
        self._closed = False

    def set_position(self, x: int, y: int) -> None:
        self._pix_sx = int(x)
        self._pix_sy = int(y)

    def position(self) -> tuple[int, int]:
        return self._pix_sx, self._pix_sy

    def set_state(self, snap: dict[str, Any]) -> None:
        with self._lock:
            self._snap = dict(snap)
        hwnd = self._hwnd
        if hwnd:
            _user32().PostMessageW(hwnd, WM_PIX_REFRESH, 0, 0)

    def close(self) -> None:
        hwnd = self._hwnd
        if hwnd:
            _user32().PostMessageW(hwnd, WM_CLOSE, 0, 0)

    def run(self) -> None:
        self._create()
        self._paint()
        user32 = _user32()
        msg = MSG()
        while True:
            r = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if r <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        self._teardown()

    def _create(self) -> None:
        _bind_api()
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:  # noqa: BLE001
            pass
        user32 = _user32()
        kernel32 = _kernel32()
        def_proc = WNDPROC(("DefWindowProcW", user32))

        def _cb(hwnd: int, msg: int, wparam: int, lparam: int) -> int:
            try:
                return self._wndproc(hwnd, msg, wparam, lparam, def_proc)
            except Exception:  # noqa: BLE001
                return int(def_proc(hwnd, msg, wparam, lparam))

        self._wndproc_ref = WNDPROC(_cb)
        self._class_name = f"PixOverlay{id(self):x}"
        self._class_buf = ctypes.create_unicode_buffer(self._class_name)
        self._title_buf = ctypes.create_unicode_buffer("Pix")
        hinst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = self._wndproc_ref
        wc.hInstance = hinst
        wc.hCursor = user32.LoadCursorW(None, ctypes.c_void_p(32512))
        wc.lpszClassName = ctypes.cast(self._class_buf, wintypes.LPCWSTR)
        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if not atom:
            raise OSError("RegisterClassExW 失败")
        ex = WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        hwnd = user32.CreateWindowExW(
            ex,
            self._class_buf,
            self._title_buf,
            WS_POPUP,
            self._pix_sx,
            self._pix_sy,
            SPRITE,
            SPRITE,
            None,
            None,
            hinst,
            None,
        )
        if not hwnd:
            raise OSError("CreateWindowExW 失败")
        self._hwnd = int(hwnd)
        user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)

    def _capturing(self) -> bool:
        with self._lock:
            return bool(self._snap.get("capturing"))

    def _rbutton_closes(self) -> bool:
        with self._lock:
            return rbutton_closes(self._snap)

    def _wndproc(self, hwnd: int, msg: int, wparam: int, lparam: int, def_proc: Any) -> int:
        user32 = _user32()
        if msg == WM_PIX_REFRESH:
            self._paint()
            return 0
        if msg == WM_NCHITTEST:
            x = ctypes.c_short(lparam & 0xFFFF).value
            y = ctypes.c_short((lparam >> 16) & 0xFFFF).value
            return HTCLIENT if self._hit_at_screen(x, y) else HTTRANSPARENT
        if msg == WM_LBUTTONDOWN:
            if self._capturing():
                return 0
            pt = POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            kind = self._kind_at_screen(pt.x, pt.y)
            self._pressing = True
            self._dragging = False
            self._down_kind = kind
            self._down_sx = pt.x
            self._down_sy = pt.y
            if kind == "icon":
                self._drag_dx = pt.x - self._pix_sx
                self._drag_dy = pt.y - self._pix_sy
            user32.SetCapture(hwnd)
            return 0
        if msg == WM_LBUTTONUP:
            capturing = self._capturing()
            was_dragging = self._dragging
            kind = self._down_kind
            self._dragging = False
            self._pressing = False
            self._down_kind = None
            user32.ReleaseCapture()
            if was_dragging:
                self._paint()
                return 0
            if capturing:
                return 0
            if kind == "icon":
                if self._on_icon_click:
                    try:
                        self._on_icon_click()
                    except Exception:  # noqa: BLE001
                        pass
            elif kind in ("attack", "move"):
                if self._on_bind_slot:
                    try:
                        self._on_bind_slot(kind)
                    except Exception:  # noqa: BLE001
                        pass
            self._paint()
            return 0
        if msg == WM_MOUSEMOVE:
            pt = POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            if self._pressing and self._down_kind == "icon" and not self._dragging:
                if moved_enough(self._down_sx, self._down_sy, pt.x, pt.y):
                    self._dragging = True
                    self._hover = False
            if self._dragging:
                self._pix_sx = pt.x - self._drag_dx
                self._pix_sy = pt.y - self._drag_dy
                self._paint()
            elif not self._pressing:
                if not self._hover:
                    self._hover = True
                    self._paint()
                self._track_leave(hwnd)
            return 0
        if msg == WM_MOUSELEAVE:
            self._tracking = False
            if self._hover and not self._dragging:
                self._hover = False
                self._paint()
            return 0
        if msg == WM_RBUTTONUP:
            if not self._rbutton_closes():
                return 0
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            return 0
        if msg == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        if msg == WM_DESTROY:
            self._hwnd = 0
            self._closed = True
            if self._on_close:
                try:
                    self._on_close()
                except Exception:  # noqa: BLE001
                    pass
            user32.PostQuitMessage(0)
            return 0
        return int(def_proc(hwnd, msg, wparam, lparam))

    def _track_leave(self, hwnd: int) -> None:
        if self._tracking:
            return
        tme = TRACKMOUSEEVENT()
        tme.cbSize = ctypes.sizeof(TRACKMOUSEEVENT)
        tme.dwFlags = TME_LEAVE
        tme.hwndTrack = hwnd
        tme.dwHoverTime = 0
        if _user32().TrackMouseEvent(ctypes.byref(tme)):
            self._tracking = True

    def _local_xy(self, sx: int, sy: int) -> tuple[int, int] | None:
        if not self._hwnd:
            return None
        rect = RECT()
        _user32().GetWindowRect(self._hwnd, ctypes.byref(rect))
        return sx - rect.left, sy - rect.top

    def _hit_at_screen(self, sx: int, sy: int) -> bool:
        if not self._hit:
            return False
        xy = self._local_xy(sx, sy)
        if xy is None:
            return False
        x, y = xy
        if x < 0 or y < 0 or x >= self._hit_w or y >= self._hit_h:
            return False
        return self._hit[y * self._hit_w + x] >= HIT_ALPHA

    def _kind_at_screen(self, sx: int, sy: int) -> str | None:
        xy = self._local_xy(sx, sy)
        if xy is None:
            return None
        kind = kind_at(self._regions, xy[0], xy[1])
        if kind == "icon" and not self._hit_at_screen(sx, sy):
            return None
        return kind

    def _paint(self) -> None:
        hwnd = self._hwnd
        if not hwnd:
            return
        with self._lock:
            snap = dict(self._snap)
        hover = self._hover and not self._dragging
        settings_open = bool(snap.get("settings")) and not snap.get("live")
        state = visual_state(snap)
        pix = draw_pix(state)
        panel_w = panel_h = 0
        panel_rgba = bytearray()
        row_rects: list[tuple[str, int, int, int, int]] = []
        if settings_open:
            panel_w, panel_h, panel_rgba, row_rects = self._draw_settings(snap)
        elif hover:
            panel_w, panel_h, panel_rgba = self._draw_tip(snap)
        gap = TIP_GAP if panel_w else 0
        total_w = SPRITE + (gap + panel_w if panel_w else 0)
        total_h = max(SPRITE, panel_h) if panel_h else SPRITE
        canvas = bytearray(total_w * total_h * 4)
        pix_oy = max(0, (total_h - SPRITE) // 2)
        panel_oy = max(0, (total_h - panel_h) // 2) if panel_h else 0
        user32 = _user32()
        work = RECT()
        user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(work), 0)  # SPI_GETWORKAREA
        panel_left = False
        if panel_w and self._pix_sx + SPRITE + gap + panel_w > work.right:
            panel_left = True
        if panel_left:
            _paste(canvas, total_w, total_h, panel_rgba, panel_w, panel_h, 0, panel_oy)
            _paste(canvas, total_w, total_h, pix, SPRITE, SPRITE, panel_w + gap, pix_oy)
            win_x = self._pix_sx - panel_w - gap
            icon_ox = panel_w + gap
            panel_ox = 0
        else:
            _paste(canvas, total_w, total_h, pix, SPRITE, SPRITE, 0, pix_oy)
            if panel_w:
                _paste(canvas, total_w, total_h, panel_rgba, panel_w, panel_h, SPRITE + gap, panel_oy)
            win_x = self._pix_sx
            icon_ox = 0
            panel_ox = SPRITE + gap
        win_y = self._pix_sy - pix_oy
        regions: list[tuple[str, int, int, int, int]] = [
            ("icon", icon_ox, pix_oy, icon_ox + SPRITE, pix_oy + SPRITE)
        ]
        for slot, x0, y0, x1, y1 in row_rects:
            regions.append((slot, panel_ox + x0, panel_oy + y0, panel_ox + x1, panel_oy + y1))
        self._regions = regions
        hit = bytearray(total_w * total_h)
        for i in range(total_w * total_h):
            hit[i] = canvas[i * 4 + 3]
        self._hit = bytes(hit)
        self._hit_w = total_w
        self._hit_h = total_h
        self._blit(hwnd, win_x, win_y, total_w, total_h, canvas)

    def _draw_tip(self, snap: dict[str, Any]) -> tuple[int, int, bytearray]:
        lines = _tip_lines(snap)
        label_w = 0
        value_w = 0
        line_h = 0
        rasters: list[tuple[bytearray, bytearray, int, int, int, int]] = []
        for label, value in lines:
            lw, lh, lb = self._font.raster(label, TIP_DIM)
            vw, vh, vb = self._font.raster(value, TIP_FG)
            label_w = max(label_w, lw)
            value_w = max(value_w, vw)
            line_h = max(line_h, lh, vh)
            rasters.append((lb, vb, lw, lh, vw, vh))
        inner_w = label_w + 10 + value_w
        inner_h = line_h * len(lines) + 4 * (len(lines) - 1)
        tw = inner_w + TIP_PAD_X * 2
        th = inner_h + TIP_PAD_Y * 2
        buf = bytearray(tw * th * 4)
        _fill_round_rect(buf, tw, th, 0, 0, tw, th, 8, TIP_BG[:3], TIP_BG[3] / 255.0)
        y = TIP_PAD_Y
        for lb, vb, lw, lh, vw, vh in rasters:
            _paste(buf, tw, th, lb, lw, lh, TIP_PAD_X, y + (line_h - lh) // 2)
            _paste(buf, tw, th, vb, vw, vh, TIP_PAD_X + label_w + 10, y + (line_h - vh) // 2)
            y += line_h + 4
        return tw, th, buf

    def _draw_settings(self, snap: dict[str, Any]) -> tuple[int, int, bytearray, list[tuple[str, int, int, int, int]]]:
        capturing = snap.get("capturing")
        capturing_s = str(capturing) if capturing else None
        rows = settings_rows(
            str(snap.get("attack_key") or "LMB"),
            str(snap.get("move_key") or "RMB"),
            capturing_s,
        )
        hint = settings_hint(capturing_s)
        label_w = 0
        value_w = 0
        line_h = 0
        rasters: list[tuple[str, bytearray, bytearray, int, int, int, int]] = []
        for slot, label, value in rows:
            color = TIP_ACCENT if capturing_s == slot else TIP_FG
            lw, lh, lb = self._font.raster(label, TIP_DIM)
            vw, vh, vb = self._font.raster(value, color)
            label_w = max(label_w, lw)
            value_w = max(value_w, vw)
            line_h = max(line_h, lh, vh)
            rasters.append((slot, lb, vb, lw, lh, vw, vh))
        hw, hh, hb = self._font.raster(hint, TIP_DIM)
        inner_w = max(label_w + 10 + value_w, hw)
        inner_h = line_h * len(rows) + 4 * len(rows) + hh
        tw = inner_w + TIP_PAD_X * 2
        th = inner_h + TIP_PAD_Y * 2
        buf = bytearray(tw * th * 4)
        _fill_round_rect(buf, tw, th, 0, 0, tw, th, 8, TIP_BG[:3], TIP_BG[3] / 255.0)
        y = TIP_PAD_Y
        row_rects: list[tuple[str, int, int, int, int]] = []
        for slot, lb, vb, lw, lh, vw, vh in rasters:
            row_rects.append((slot, 0, y - 2, tw, y + line_h + 2))
            _paste(buf, tw, th, lb, lw, lh, TIP_PAD_X, y + (line_h - lh) // 2)
            _paste(buf, tw, th, vb, vw, vh, TIP_PAD_X + label_w + 10, y + (line_h - vh) // 2)
            y += line_h + 4
        _paste(buf, tw, th, hb, hw, hh, TIP_PAD_X, y)
        return tw, th, buf, row_rects

    def _blit(self, hwnd: int, x: int, y: int, w: int, h: int, rgba: bytearray) -> None:
        gdi32 = _gdi32()
        user32 = _user32()
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB
        bits = ctypes.c_void_p()
        hdc_screen = user32.GetDC(None)
        hdc = gdi32.CreateCompatibleDC(hdc_screen)
        hbmp = gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), DIB_RGB_COLORS, ctypes.byref(bits), None, 0)
        if not hbmp or not bits.value:
            gdi32.DeleteDC(hdc)
            user32.ReleaseDC(None, hdc_screen)
            return
        premul = _premul_bgra(rgba, w, h)
        ctypes.memmove(bits, premul, len(premul))
        old = gdi32.SelectObject(hdc, hbmp)
        blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
        src = POINT(0, 0)
        dst = POINT(int(x), int(y))
        size = SIZE(int(w), int(h))
        user32.UpdateLayeredWindow(
            hwnd,
            hdc_screen,
            ctypes.byref(dst),
            ctypes.byref(size),
            hdc,
            ctypes.byref(src),
            0,
            ctypes.byref(blend),
            ULW_ALPHA,
        )
        user32.SetWindowPos(hwnd, ctypes.c_void_p(HWND_TOPMOST), 0, 0, 0, 0, 0x0001 | 0x0002 | SWP_NOACTIVATE)
        gdi32.SelectObject(hdc, old)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc)
        user32.ReleaseDC(None, hdc_screen)

    def _teardown(self) -> None:
        self._font.close()
        user32 = _user32()
        if self._class_name:
            try:
                user32.UnregisterClassW(self._class_name, _kernel32().GetModuleHandleW(None))
            except Exception:  # noqa: BLE001
                pass
            self._class_name = ""
        self._wndproc_ref = None
