"""PNG 解码、编码与缩放（无 Pillow 依赖）。"""

from __future__ import annotations

import struct
import zlib


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def encode_png(rgba: bytes, w: int, h: int) -> bytes:
    raw = b"".join(b"\x00" + rgba[y * w * 4 : (y + 1) * w * 4] for y in range(h))
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def decode_png(data: bytes) -> tuple[int, int, bytes]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("不是 PNG")
    pos = 8
    width = height = bit = color = inter = 0
    idat = bytearray()
    while pos + 12 <= len(data):
        n = struct.unpack(">I", data[pos : pos + 4])[0]
        tag = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + n]
        pos += 12 + n
        if tag == b"IHDR":
            width, height, bit, color, _comp, _filt, inter = struct.unpack(">IIBBBBB", chunk)
        elif tag == b"IDAT":
            idat.extend(chunk)
        elif tag == b"IEND":
            break
    if bit != 8 or inter != 0 or color not in (2, 6):
        raise ValueError(f"不支持的 PNG: bit={bit} color={color} inter={inter}")
    bpp = 4 if color == 6 else 3
    stride = width * bpp
    raw = zlib.decompress(bytes(idat))
    rows: list[bytearray] = []
    i = 0
    prev = bytearray(stride)
    for _ in range(height):
        ftype = raw[i]
        i += 1
        row = bytearray(raw[i : i + stride])
        i += stride
        for x, val in enumerate(row):
            a = row[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if ftype == 1:
                row[x] = (val + a) & 255
            elif ftype == 2:
                row[x] = (val + b) & 255
            elif ftype == 3:
                row[x] = (val + ((a + b) // 2)) & 255
            elif ftype == 4:
                row[x] = (val + _paeth(a, b, c)) & 255
            elif ftype != 0:
                raise ValueError(f"未知 PNG filter: {ftype}")
        rows.append(row)
        prev = row
    if color == 6:
        rgba = b"".join(rows)
    else:
        out = bytearray(width * height * 4)
        k = 0
        for row in rows:
            for x in range(0, stride, 3):
                out[k : k + 4] = bytes((row[x], row[x + 1], row[x + 2], 255))
                k += 4
        rgba = bytes(out)
    return width, height, rgba


def resize_rgba(src: bytes, sw: int, sh: int, dw: int, dh: int) -> bytes:
    out = bytearray(dw * dh * 4)
    for y in range(dh):
        sy = (y + 0.5) * sh / dh - 0.5
        y0 = min(sh - 1, max(0, int(sy)))
        y1 = min(sh - 1, y0 + 1)
        fy = min(1.0, max(0.0, sy - y0))
        for x in range(dw):
            sx = (x + 0.5) * sw / dw - 0.5
            x0 = min(sw - 1, max(0, int(sx)))
            x1 = min(sw - 1, x0 + 1)
            fx = min(1.0, max(0.0, sx - x0))
            i00 = (y0 * sw + x0) * 4
            i10 = (y0 * sw + x1) * 4
            i01 = (y1 * sw + x0) * 4
            i11 = (y1 * sw + x1) * 4
            o = (y * dw + x) * 4
            for c in range(4):
                v = (
                    src[i00 + c] * (1 - fx) * (1 - fy)
                    + src[i10 + c] * fx * (1 - fy)
                    + src[i01 + c] * (1 - fx) * fy
                    + src[i11 + c] * fx * fy
                )
                out[o + c] = int(v + 0.5)
    return bytes(out)
