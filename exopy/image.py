import base64
import binascii
import io
import os
import struct
import zlib
from typing import Tuple, Union

try:
    from PIL import Image as PILImage
    _HAS_PIL = True
except ImportError:
    PILImage = None
    _HAS_PIL = False

from . import _state
from .binary import BinaryReader, BinaryWriter
from .types_ext import Pattern


def _decode_png_fallback(png_bytes: bytes) -> Tuple[int, int, bytes]:
    if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("Pillow is required for WebP/JPEG/GIF images (`pip install pillow`)")
    pos = 8
    width = height = bit_depth = color_type = 0
    idat = bytearray()
    while pos < len(png_bytes):
        length = struct.unpack(">I", png_bytes[pos : pos + 4])[0]
        tag = png_bytes[pos + 4 : pos + 8]
        chunk_data = png_bytes[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", chunk_data)
        elif tag == b"IDAT":
            idat.extend(chunk_data)
        elif tag == b"IEND":
            break

    if bit_depth != 8 or color_type not in (2, 6):
        raise RuntimeError("Install Pillow (`pip install pillow`) to load indexed/16-bit PNGs")

    bpp = 4 if color_type == 6 else 3
    raw = zlib.decompress(bytes(idat))
    stride = width * bpp
    out = bytearray(width * height * 4)
    prev = bytearray(stride)
    src = 0

    for y in range(height):
        ftype = raw[src]
        src += 1
        row = bytearray(raw[src : src + stride])
        src += stride
        if ftype == 1:
            for i in range(bpp, stride):
                row[i] = (row[i] + row[i - bpp]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                a = row[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                a = row[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                row[i] = (row[i] + (a if (pa <= pb and pa <= pc) else (b if pb <= pc else c))) & 0xFF
        prev = row
        dst = y * width * 4
        if bpp == 4:
            out[dst : dst + width * 4] = row
        else:
            for x in range(width):
                out[dst + x * 4 : dst + x * 4 + 3] = row[x * 3 : x * 3 + 3]
                out[dst + x * 4 + 3] = 255
    return width, height, bytes(out)


def _resolve_raw_bytes(source: Union[str, bytes, bytearray]) -> bytes:
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    if not isinstance(source, str):
        raise TypeError(f"Expected file path, base64 string, or bytes; got {type(source).__name__}")

    s = source.strip()
    if s.startswith("data:") and ";base64," in s:
        b64_part = s.split(";base64,", 1)[1]
        return base64.b64decode(b64_part)

    if len(s) < 260 and os.path.exists(s):
        with open(s, "rb") as f:
            return f.read()

    try:
        decoded = base64.b64decode(s, validate=True)
        if decoded:
            return decoded
    except (binascii.Error, ValueError):
        pass

    raise FileNotFoundError(f"Image file not found and input is not valid base64: {s[:64]!r}")


def _load_rgba_and_png(source: Union[str, bytes, bytearray]) -> Tuple[int, int, bytes, bytes]:
    raw = _resolve_raw_bytes(source)
    if _HAS_PIL:
        with PILImage.open(io.BytesIO(raw)) as img:
            rgba_img = img.convert("RGBA")
            w, h = rgba_img.size
            rgba = rgba_img.tobytes()
            buf = io.BytesIO()
            rgba_img.save(buf, format="PNG")
            return w, h, rgba, buf.getvalue()
    w, h, rgba = _decode_png_fallback(raw)
    return w, h, rgba, raw


class ExoImage:
    def __init__(self, source: Union[str, bytes, bytearray], mode: str = "pixel", pos: Tuple[float, float] = (0.0, 0.0)):
        m = str(mode).strip().lower()
        if m not in ("pixel", "pattern"):
            raise ValueError("mode must be 'pixel' or 'pattern'")

        self.mode = m
        self.pos = (float(pos[0]), float(pos[1]))
        self.width, self.height, self.rgba, self.png_bytes = _load_rgba_and_png(source)
        self.pattern_id = None
        self.objects = []

        lvl = _state.get_level()
        if self.mode == "pattern":
            self.pattern_id = lvl._next_pattern_id()
            lvl.patterns.append(Pattern(pattern_id=self.pattern_id, pattern_frames=[self.png_bytes]))
        else:
            self._build_pixels(lvl)

    def to_base64(self, data_url: bool = False) -> str:
        b64 = base64.b64encode(self.png_bytes).decode("ascii")
        return f"data:image/png;base64,{b64}" if data_url else b64

    def _pixel(self, x: int, y: int) -> Tuple[int, int, int, int]:
        i = (y * self.width + x) * 4
        return self.rgba[i], self.rgba[i + 1], self.rgba[i + 2], self.rgba[i + 3]

    def _build_pixels(self, lvl):
        from . import GameObject

        ox, oy = self.pos
        step = 0.5
        for y in range(self.height):
            x = 0
            while x < self.width:
                r, g, b, a = self._pixel(x, y)
                if a == 0:
                    x += 1
                    continue
                run = 1
                while x + run < self.width and self._pixel(x + run, y) == (r, g, b, a):
                    run += 1

                col = f"#{r:02X}{g:02X}{b:02X}" if a == 255 else f"#{r:02X}{g:02X}{b:02X}{a:02X}"
                cx = ox + (x + run / 2.0) * step
                cy = oy - (y + 0.5) * step
                obj = GameObject("rect", (cx, cy), lvl).settings({
                    "Width": run * step,
                    "Height": step,
                    "Color": col,
                }).pack()
                self.objects.append(obj)
                x += run

    @classmethod
    def read(cls, r: BinaryReader) -> bytes:
        return r.bytes_vec()

    def write(self, w: BinaryWriter):
        w.write_bytes(self.png_bytes)
