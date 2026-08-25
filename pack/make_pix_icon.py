"""把 assets/pix.png 打成 Windows 多尺寸 .ico。"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parent
ROOT = PACK.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from image_util import decode_png, encode_png, resize_rgba

PREVIEW = PACK / "pix.png"
OUT = PACK / "pix.ico"
PREVIEW_SIZE = 256
SIZES = (16, 24, 32, 48, 64, 128, 256)


def write_ico(path: Path, source: Path) -> Path:
    if not source.exists():
        raise FileNotFoundError(f"缺少图标原稿: {source}")
    sw, sh, rgba = decode_png(source.read_bytes())
    images: list[tuple[int, bytes]] = []
    for size in SIZES:
        scaled = resize_rgba(rgba, sw, sh, size, size) if (sw, sh) != (size, size) else rgba
        images.append((size, encode_png(scaled, size, size)))
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    payload = b""
    for size, png in images:
        w = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(png), offset)
        payload += png
        offset += len(png)
    path.write_bytes(header + entries + payload)
    return path


def write_pix_ico(path: Path = OUT) -> Path:
    src = ROOT / "assets" / "pix.png"
    if not src.is_file():
        raise FileNotFoundError("缺少 assets/pix.png")
    w, h, rgba = decode_png(src.read_bytes())
    preview = resize_rgba(rgba, w, h, PREVIEW_SIZE, PREVIEW_SIZE)
    PREVIEW.write_bytes(encode_png(preview, PREVIEW_SIZE, PREVIEW_SIZE))
    return write_ico(path, src)


if __name__ == "__main__":
    print(write_pix_ico())
