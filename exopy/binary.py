import struct
import time

_CS_EPOCH_TICKS = 621355968000000000
_CS_KIND_UTC = 1 << 62


def now_cs_ticks() -> int:
    """Return current UTC timestamp formatted as C# DateTime.ToBinary() ticks."""
    ticks = int(time.time() * 10_000_000) + _CS_EPOCH_TICKS
    return ticks | _CS_KIND_UTC


def parse_color(rgba):
    if isinstance(rgba, str):
        h = rgba.lstrip("#")
        if len(h) == 6:
            return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, 1.0)
        if len(h) == 8:
            return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, int(h[6:8], 16) / 255.0)
        raise ValueError(f"Invalid hex color: {rgba}")
    if len(rgba) == 3:
        return (float(rgba[0]), float(rgba[1]), float(rgba[2]), 1.0)
    return tuple(float(x) for x in rgba[:4])


def rgba_to_hex(rgba) -> str:
    r, g, b, a = [max(0, min(255, int(round(c * 255)))) for c in rgba]
    return f"#{r:02X}{g:02X}{b:02X}" if a == 255 else f"#{r:02X}{g:02X}{b:02X}{a:02X}"


class BinaryWriter:
    def __init__(self):
        self.buf = bytearray()

    def write_raw(self, b: bytes):
        self.buf.extend(b)

    def write_u8(self, v: int):
        self.buf.extend(struct.pack("<B", int(v) & 0xFF))

    def write_bool(self, v: bool):
        self.write_u8(1 if v else 0)

    def write_i32(self, v: int):
        self.buf.extend(struct.pack("<i", int(v)))

    def write_i64(self, v: int):
        self.buf.extend(struct.pack("<q", int(v)))

    def write_f32(self, v: float):
        self.buf.extend(struct.pack("<f", float(v)))

    def write_varint(self, v: int):
        v = int(v)
        while v >= 0x80:
            self.write_u8((v & 0x7F) | 0x80)
            v >>= 7
        self.write_u8(v)

    def write_str(self, s: str):
        raw = str(s).encode("utf-8")
        self.write_varint(len(raw))
        self.buf.extend(raw)

    def write_bytes(self, b: bytes):
        self.write_i32(len(b))
        self.buf.extend(b)

    def write_vec2(self, vec):
        self.write_f32(vec[0])
        self.write_f32(vec[1])

    def write_color(self, rgba):
        for c in parse_color(rgba):
            self.write_f32(c)

    def write_datetime_now(self):
        self.write_i64(now_cs_ticks())

    def write_vec(self, items, fn):
        self.write_i32(len(items))
        for item in items:
            fn(item)

    def write_option(self, val, fn):
        if val is None:
            self.write_bool(False)
        else:
            self.write_bool(True)
            fn(val)

    def to_bytes(self) -> bytes:
        return bytes(self.buf)


class BinaryReader:
    def __init__(self, b: bytes):
        self.b, self.i = b, 0

    def raw(self, n: int) -> bytes:
        if self.i + n > len(self.b):
            raise EOFError("Unexpected end of file")
        s = self.b[self.i : self.i + n]
        self.i += n
        return s

    def u8(self) -> int:
        return self.raw(1)[0]

    def bool(self) -> bool:
        return self.u8() != 0

    def i32(self) -> int:
        return struct.unpack("<i", self.raw(4))[0]

    def i64(self) -> int:
        return struct.unpack("<q", self.raw(8))[0]

    def f32(self) -> float:
        return round(struct.unpack("<f", self.raw(4))[0], 4)

    def vec2(self):
        return (self.f32(), self.f32())

    def color(self):
        return tuple(struct.unpack("<f", self.raw(4))[0] for _ in range(4))

    def varint(self) -> int:
        v = shift = 0
        while True:
            b = self.u8()
            v |= (b & 0x7F) << shift
            if not (b & 0x80):
                return v
            shift += 7

    def string(self) -> str:
        return self.raw(self.varint()).decode("utf-8", errors="replace")

    def bytes_vec(self) -> bytes:
        return self.raw(self.i32())

    def vec(self, fn):
        return [fn() for _ in range(self.i32())]

    def option(self, fn):
        return fn() if self.bool() else None
