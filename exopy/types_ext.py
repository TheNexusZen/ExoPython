import uuid
from dataclasses import dataclass, field
from typing import List, Tuple
from .binary import BinaryReader, BinaryWriter, now_cs_ticks, rgba_to_hex
from .constants import OBJECT_PROPERTIES, OldActionType
from .errors import InvalidObjectPropertyError, InvalidOldActionTypeError

_ID_TO_PROP = {pid: (name, ptype) for name, (pid, ptype) in OBJECT_PROPERTIES.items()}
_VALID_OLD_ACTION_TYPES = {
    v for k, v in vars(OldActionType).items() if not k.startswith("_") and isinstance(v, int)
}


def read_prop_list(r: BinaryReader) -> List[Tuple[str, object]]:
    count = r.i32()
    props = []
    for _ in range(count):
        pid = r.i32()
        if pid not in _ID_TO_PROP:
            raise InvalidObjectPropertyError(pid)
        name, ptype = _ID_TO_PROP[pid]
        if ptype == "color":
            val = rgba_to_hex(r.color())
        elif ptype == "i32":
            val = r.i32()
        elif ptype == "f32":
            val = r.f32()
        elif ptype == "bool":
            val = r.bool()
        elif ptype == "vec2":
            val = r.vec2()
        elif ptype == "str":
            val = r.string()
        elif ptype == "vi32":
            val = r.vec(r.i32)
        elif ptype == "tcorners":
            val = r.vec(lambda: r.vec(r.vec2))
        else:
            raise InvalidObjectPropertyError(ptype)
        props.append((name, val))
    return props


def write_prop_list(w: BinaryWriter, props: List[Tuple[str, object]]):
    w.write_i32(len(props))
    for name, val in props:
        if name not in OBJECT_PROPERTIES:
            raise InvalidObjectPropertyError(name)
        pid, pt = OBJECT_PROPERTIES[name]
        w.write_i32(pid)
        if pt == "color":
            w.write_color(val)
        elif pt == "i32":
            w.write_i32(val)
        elif pt == "f32":
            w.write_f32(val)
        elif pt == "bool":
            w.write_bool(val)
        elif pt == "vec2":
            w.write_vec2(val)
        elif pt == "str":
            w.write_str(val)
        elif pt == "vi32":
            w.write_vec(val, w.write_i32)
        elif pt == "tcorners":
            w.write_vec(val, lambda poly: w.write_vec(poly, w.write_vec2))


@dataclass
class BrushGrid:
    x: int = 0
    y: int = 0

    @classmethod
    def read(cls, r: BinaryReader) -> "BrushGrid":
        return cls(x=r.i32(), y=r.i32())

    def write(self, w: BinaryWriter):
        w.write_i32(self.x)
        w.write_i32(self.y)


@dataclass
class BrushObject:
    entity_id: int
    properties: List[Tuple[str, object]] = field(default_factory=list)
    weight: float = 1.0
    scale: float = 1.0
    rotation: float = 0.0
    flip_x: bool = False
    flip_y: bool = False

    @classmethod
    def read(cls, r: BinaryReader) -> "BrushObject":
        return cls(
            entity_id=r.i32(),
            properties=read_prop_list(r),
            weight=r.f32(),
            scale=r.f32(),
            rotation=r.f32(),
            flip_x=r.bool(),
            flip_y=r.bool(),
        )

    def write(self, w: BinaryWriter):
        w.write_i32(self.entity_id)
        write_prop_list(w, self.properties)
        w.write_f32(self.weight)
        w.write_f32(self.scale)
        w.write_f32(self.rotation)
        w.write_bool(self.flip_x)
        w.write_bool(self.flip_y)


@dataclass
class Brush:
    brush_id: int
    spread: Tuple[float, float] = (0.0, 0.0)
    frequency: float = 1.0
    grid: BrushGrid = field(default_factory=BrushGrid)
    objects: List[BrushObject] = field(default_factory=list)

    @classmethod
    def read(cls, r: BinaryReader) -> "Brush":
        return cls(
            brush_id=r.i32(),
            spread=r.vec2(),
            frequency=r.f32(),
            grid=BrushGrid.read(r),
            objects=r.vec(lambda: BrushObject.read(r)),
        )

    def write(self, w: BinaryWriter):
        w.write_i32(self.brush_id)
        w.write_vec2(self.spread)
        w.write_f32(self.frequency)
        self.grid.write(w)
        w.write_vec(self.objects, lambda o: o.write(w))


@dataclass
class Pattern:
    pattern_id: int
    pattern_frames: List[bytes] = field(default_factory=list)

    @classmethod
    def read(cls, r: BinaryReader) -> "Pattern":
        return cls(
            pattern_id=r.i32(),
            pattern_frames=r.vec(r.bytes_vec),
        )

    def write(self, w: BinaryWriter):
        w.write_i32(self.pattern_id)
        w.write_vec(self.pattern_frames, w.write_bytes)


@dataclass
class RawObject:
    entity_id: int
    tile_id: int
    prefab_entity_id: int = 0
    prefab_id: int = 0
    position: Tuple[float, float] = (0.0, 0.0)
    scale: Tuple[float, float] = (1.0, 1.0)
    rotation: float = 0.0
    tag: str = ""
    properties: List[Tuple[str, object]] = field(default_factory=list)
    in_layer: int = 1
    in_group: int = 0
    group_members: List[int] = field(default_factory=list)

    @classmethod
    def read(cls, r: BinaryReader) -> "RawObject":
        return cls(
            entity_id=r.i32(),
            tile_id=r.i32(),
            prefab_entity_id=r.i32(),
            prefab_id=r.i32(),
            position=r.vec2(),
            scale=r.vec2(),
            rotation=r.f32(),
            tag=r.string(),
            properties=read_prop_list(r),
            in_layer=r.i32(),
            in_group=r.i32(),
            group_members=r.vec(r.i32),
        )

    def write(self, w: BinaryWriter):
        w.write_i32(self.entity_id)
        w.write_i32(self.tile_id)
        w.write_i32(self.prefab_entity_id)
        w.write_i32(self.prefab_id)
        w.write_vec2(self.position)
        w.write_vec2(self.scale)
        w.write_f32(self.rotation)
        w.write_str(self.tag)
        write_prop_list(w, self.properties)
        w.write_i32(self.in_layer)
        w.write_i32(self.in_group)
        w.write_vec(self.group_members, w.write_i32)


@dataclass
class Prefab:
    prefab_id: int
    prefab_image_data: bytes = b""
    items: List[RawObject] = field(default_factory=list)

    @classmethod
    def read(cls, r: BinaryReader) -> "Prefab":
        return cls(
            prefab_id=r.i32(),
            prefab_image_data=r.bytes_vec(),
            items=r.vec(lambda: RawObject.read(r)),
        )

    def write(self, w: BinaryWriter):
        w.write_i32(self.prefab_id)
        w.write_bytes(self.prefab_image_data)
        w.write_vec(self.items, lambda item: item.write(w))


@dataclass
class OldActionProperty:
    name: str
    value: str

    @classmethod
    def read(cls, r: BinaryReader) -> "OldActionProperty":
        return cls(name=r.string(), value=r.string())

    def write(self, w: BinaryWriter):
        w.write_str(self.name)
        w.write_str(self.value)


@dataclass
class OldAction:
    action_type: int
    wait: bool = False
    properties: List[OldActionProperty] = field(default_factory=list)

    @classmethod
    def read(cls, r: BinaryReader) -> "OldAction":
        atype = r.i32()
        if atype not in _VALID_OLD_ACTION_TYPES:
            raise InvalidOldActionTypeError(atype)
        return cls(
            action_type=atype,
            wait=r.bool(),
            properties=r.vec(lambda: OldActionProperty.read(r)),
        )

    def write(self, w: BinaryWriter):
        atype = int(self.action_type)
        if atype not in _VALID_OLD_ACTION_TYPES:
            raise InvalidOldActionTypeError(atype)
        w.write_i32(atype)
        w.write_bool(self.wait)
        w.write_vec(self.properties, lambda p: p.write(w))


@dataclass
class OldScript:
    script_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "New Script"
    creation_date_ticks: int = field(default_factory=now_cs_ticks)
    actions: List[OldAction] = field(default_factory=list)

    @classmethod
    def read(cls, r: BinaryReader) -> "OldScript":
        return cls(
            script_id=r.string(),
            name=r.string(),
            creation_date_ticks=r.i64(),
            actions=r.vec(lambda: OldAction.read(r)),
        )

    def write(self, w: BinaryWriter):
        w.write_str(str(self.script_id))
        w.write_str(self.name)
        w.write_i64(int(self.creation_date_ticks))
        w.write_vec(self.actions, lambda a: a.write(w))

    def to_bytes(self) -> bytes:
        w = BinaryWriter()
        self.write(w)
        return w.to_bytes()

    @classmethod
    def from_bytes(cls, data: bytes) -> "OldScript":
        return cls.read(BinaryReader(data))


@dataclass
class LocalLevel:
    serialization_version: int = 18
    level_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    level_version: int = 1
    level_name: str = "New level"
    thumbnail: str = ""
    creation_date_ticks: int = field(default_factory=now_cs_ticks)
    update_date_ticks: int = field(default_factory=now_cs_ticks)
    author_time: int = 0
    author_lap_times: List[int] = field(default_factory=list)
    silver_medal_time: int = 0
    gold_medal_time: int = 0
    laps: int = 1
    private: bool = False
    nova_level: bool = True

    @classmethod
    def read(cls, r: BinaryReader) -> "LocalLevel":
        return cls(
            serialization_version=r.i32(),
            level_id=r.string(),
            level_version=r.i32(),
            level_name=r.string(),
            thumbnail=r.string(),
            creation_date_ticks=r.i64(),
            update_date_ticks=r.i64(),
            author_time=r.i64(),
            author_lap_times=r.vec(r.i64),
            silver_medal_time=r.i64(),
            gold_medal_time=r.i64(),
            laps=r.i32(),
            private=r.bool(),
            nova_level=r.bool(),
        )

    def write(self, w: BinaryWriter):
        w.write_i32(self.serialization_version)
        w.write_str(str(self.level_id))
        w.write_i32(self.level_version)
        w.write_str(self.level_name)
        w.write_str(self.thumbnail)
        w.write_i64(int(self.creation_date_ticks))
        w.write_i64(int(self.update_date_ticks))
        w.write_i64(int(self.author_time))
        w.write_vec(self.author_lap_times, w.write_i64)
        w.write_i64(int(self.silver_medal_time))
        w.write_i64(int(self.gold_medal_time))
        w.write_i32(self.laps)
        w.write_bool(self.private)
        w.write_bool(self.nova_level)

    def to_bytes(self) -> bytes:
        w = BinaryWriter()
        self.write(w)
        return w.to_bytes()

    @classmethod
    def from_bytes(cls, data: bytes) -> "LocalLevel":
        return cls.read(BinaryReader(data))


@dataclass
class LegacyTileLayers:
    under_decoration_tiles: List[int] = field(default_factory=list)
    background_decoration_tiles: List[int] = field(default_factory=list)
    terrain_tiles: List[int] = field(default_factory=list)
    floating_zone_tiles: List[int] = field(default_factory=list)
    object_tiles: List[int] = field(default_factory=list)
    foreground_decoration_tiles: List[int] = field(default_factory=list)

    @classmethod
    def read(cls, r: BinaryReader) -> "LegacyTileLayers":
        return cls(
            under_decoration_tiles=r.vec(r.i32),
            background_decoration_tiles=r.vec(r.i32),
            terrain_tiles=r.vec(r.i32),
            floating_zone_tiles=r.vec(r.i32),
            object_tiles=r.vec(r.i32),
            foreground_decoration_tiles=r.vec(r.i32),
        )

    def write(self, w: BinaryWriter):
        for lst in (
            self.under_decoration_tiles,
            self.background_decoration_tiles,
            self.terrain_tiles,
            self.floating_zone_tiles,
            self.object_tiles,
            self.foreground_decoration_tiles,
        ):
            w.write_vec(lst, w.write_i32)


@dataclass
class TerrainCopyStyle:
    unknown1: bytes = b"\x00\x00\x00\x00"
    pattern_id: int = 0
    pattern_tiling: Tuple[float, float] = (0.0, 0.0)
    pattern_offset: Tuple[float, float] = (0.0, 0.0)
    color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    secondary_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    blend_mode: int = 0
    border_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    border_thickness: float = 0.0
    border_corner_radius: float = 0.0
    round_reflex_angles: bool = False
    round_collider: bool = False
    friction: float = 0.0

    @classmethod
    def read(cls, r: BinaryReader) -> "TerrainCopyStyle":
        return cls(
            unknown1=r.raw(4),
            pattern_id=r.i32(),
            pattern_tiling=r.vec2(),
            pattern_offset=r.vec2(),
            color=r.color(),
            secondary_color=r.color(),
            blend_mode=r.i32(),
            border_color=r.color(),
            border_thickness=r.f32(),
            border_corner_radius=r.f32(),
            round_reflex_angles=r.bool(),
            round_collider=r.bool(),
            friction=r.f32(),
        )

    def write(self, w: BinaryWriter):
        w.write_raw(self.unknown1[:4].ljust(4, b"\x00"))
        w.write_i32(self.pattern_id)
        w.write_vec2(self.pattern_tiling)
        w.write_vec2(self.pattern_offset)
        w.write_color(self.color)
        w.write_color(self.secondary_color)
        w.write_i32(self.blend_mode)
        w.write_color(self.border_color)
        w.write_f32(self.border_thickness)
        w.write_f32(self.border_corner_radius)
        w.write_bool(self.round_reflex_angles)
        w.write_bool(self.round_collider)
        w.write_f32(self.friction)


@dataclass
class AuthorReplay:
    data: bytes = b""

    @classmethod
    def read(cls, r: BinaryReader) -> "AuthorReplay":
        return cls(data=r.bytes_vec())

    def write(self, w: BinaryWriter):
        w.write_bytes(self.data)
