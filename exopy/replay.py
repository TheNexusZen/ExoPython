from dataclasses import dataclass, field
from typing import List, Tuple
from .binary import BinaryReader, BinaryWriter


@dataclass
class ReplayFrame:
    time: float
    position: Tuple[float, float] = (0.0, 0.0)
    velocity: Tuple[float, float] = (0.0, 0.0)
    input_flags: int = 0

    def write(self, w: BinaryWriter):
        w.write_f32(self.time)
        w.write_vec2(self.position)
        w.write_vec2(self.velocity)
        w.write_u8(self.input_flags)

    @classmethod
    def read(cls, r: BinaryReader) -> "ReplayFrame":
        return cls(
            time=r.f32(),
            position=r.vec2(),
            velocity=r.vec2(),
            input_flags=r.u8(),
        )


@dataclass
class ParsedReplay:
    version: int = 1
    total_time_ms: int = 0
    frames: List[ReplayFrame] = field(default_factory=list)
    raw_tail: bytes = b""

    def to_bytes(self) -> bytes:
        if not self.frames and self.raw_tail and self.version == 0:
            return self.raw_tail
        w = BinaryWriter()
        w.write_i32(self.version)
        w.write_i64(self.total_time_ms)
        w.write_vec(self.frames, lambda f: f.write(w))
        if self.raw_tail:
            w.write_raw(self.raw_tail)
        return w.to_bytes()

    @classmethod
    def from_bytes(cls, data: bytes) -> "ParsedReplay":
        if not data:
            return cls()
        if len(data) >= 16:
            r = BinaryReader(data)
            ver = r.i32()
            total_ms = r.i64()
            count = r.i32()
            if 0 <= count <= 1_000_000 and 16 + count * 21 <= len(data):
                frames = [ReplayFrame.read(r) for _ in range(count)]
                tail = data[r.i :]
                return cls(version=ver, total_time_ms=total_ms, frames=frames, raw_tail=tail)
        return cls(version=0, total_time_ms=0, frames=[], raw_tail=data)

    def add_frame(
        self,
        time: float,
        position: Tuple[float, float] = (0.0, 0.0),
        velocity: Tuple[float, float] = (0.0, 0.0),
        *,
        jump_pressed: bool = False,
        left_pressed: bool = False,
        right_pressed: bool = False,
    ) -> "ParsedReplay":
        flags = (int(bool(jump_pressed)) << 0) | (int(bool(left_pressed)) << 1) | (int(bool(right_pressed)) << 2)
        self.frames.append(ReplayFrame(float(time), position, velocity, flags))
        self.total_time_ms = max(self.total_time_ms, int(round(float(time) * 1000)))
        return self
