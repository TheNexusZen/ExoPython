import gzip, hashlib, json, os, secrets, struct, uuid
from dataclasses import asdict
from . import _state, scripts, variables, stdlib, types_ext, errors
from .decompile import decompile, inspect_level
from .binary import BinaryWriter, now_cs_ticks, parse_color, rgba_to_hex
from .constants import THEMES, DEFAULT_SETTINGS, TILE_IDS, OBJECT_PROPERTIES
from .errors import (
    ExopyError, WrongMagicError, InvalidDynamicTypeError, InvalidStaticTypeError,
    InvalidObjectPropertyError, InvalidOldActionTypeError, InvalidActionTypeError,
    InvalidThemeError,
)
from .image import ExoImage, _resolve_raw_bytes
from .types_ext import (
    AuthorReplay, Brush, BrushGrid, BrushObject,
    LegacyTileLayers, LocalLevel, OldAction, OldActionProperty, OldScript,
    Pattern, Prefab, RawObject, TerrainCopyStyle,
)

KEYS_FILE = os.path.expanduser("~/.exopy_keys.txt")


def _get_or_create_key(level_uuid: str) -> str:
    keys = {}
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    keys[k.strip()] = v.strip()
    if level_uuid in keys:
        return keys[level_uuid]
    new_key = secrets.token_hex(16)
    fd = os.open(KEYS_FILE, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write(f"{level_uuid}={new_key}\n")
    return new_key


def _build_exopy_footer(obfuscated=False, watermark="made with exopy", decompiled=False, key_hash: bytes = b"") -> bytes:
    flags = 0x01
    if decompiled:
        flags |= 0x02
    if obfuscated:
        flags |= 0x04
    if key_hash:
        flags |= 0x08
    wm_bytes = str(watermark or "")[:200].encode("utf-8")
    body = b"EXPY" + bytes([flags, len(wm_bytes)]) + wm_bytes + key_hash
    return body + struct.pack("<H", len(body)) + b"YPXE"


class Layer:
    def __init__(self, layer_id: int, name: str, foreground_type: int = 0, parallax=(0.0, 0.0)):
        self.layer_id, self.layer_name = int(layer_id), str(name)
        self.selected = self.invisible = self.locked = self.fixed_size = False
        self.foreground_type = int(foreground_type)
        self.parallax = (float(parallax[0]), float(parallax[1]))
        self.children = []

    def to_dict(self) -> dict:
        return {
            "layer_id": self.layer_id,
            "layer_name": self.layer_name,
            "selected": self.selected,
            "invisible": self.invisible,
            "locked": self.locked,
            "foreground_type": self.foreground_type,
            "parallax": list(self.parallax),
            "fixed_size": self.fixed_size,
            "children": list(self.children),
        }

    def _write_to(self, w: BinaryWriter):
        w.write_i32(self.layer_id)
        w.write_str(self.layer_name)
        w.write_bool(self.selected)
        w.write_bool(self.invisible)
        w.write_bool(self.locked)
        w.write_i32(self.foreground_type)
        w.write_vec2(self.parallax)
        w.write_bool(self.fixed_size)
        w.write_vec(self.children, w.write_i32)


class GameObject:
    def __init__(self, obj_type, pos: tuple, level):
        if isinstance(obj_type, int):
            self.tile_id = obj_type
        elif isinstance(obj_type, str) and obj_type.lower() in TILE_IDS:
            self.tile_id = TILE_IDS[obj_type.lower()]
        else:
            raise ValueError(f"Unknown object '{obj_type}'. Valid: {list(TILE_IDS.keys())} or int tile_id")
        self.entity_id = level._next_entity_id()
        self.prefab_entity_id = 0
        self.prefab_id = 0
        self.pos = (float(pos[0]), float(pos[1]))
        self.scale = (1.0, 1.0)
        self.rotation = 0.0
        self.tag = ""
        self.layer = level.layers[0].layer_id
        self.in_group = 0
        self.group_members = []
        self.properties = {}
        self._level = level

    def settings(self, cfg: dict):
        for k, v in cfg.items():
            if k == "Rotation":
                self.rotation = float(v)
            elif k == "Scale":
                self.scale = (float(v[0]), float(v[1]))
            elif k == "Tag":
                self.tag = str(v)
            elif k == "Layer":
                self.layer = v.layer_id if isinstance(v, Layer) else int(v)
            elif k == "PrefabEntityId":
                self.prefab_entity_id = int(v)
            elif k == "PrefabId":
                self.prefab_id = int(v)
            elif k == "InGroup":
                self.in_group = int(v)
            elif k == "GroupMembers":
                self.group_members = [int(x) for x in v]
            elif k == "Pattern":
                pat_id = v.pattern_id if hasattr(v, "pattern_id") else int(v)
                if pat_id is None:
                    raise ValueError("Cannot use a 'pixel' ExoImage as a Pattern; use mode='pattern'")
                self.properties["Pattern"] = pat_id
                if "FillMode" not in cfg and "FillMode" not in self.properties:
                    self.properties["FillMode"] = 1
            elif k == "Box":
                hw, hh = float(v[0]) / 2.0, float(v[1]) / 2.0
                self.properties["TerrainCorners"] = [[(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]]
            elif k in OBJECT_PROPERTIES:
                self.properties[k] = v
            else:
                raise InvalidObjectPropertyError(k)
        return self

    def pack(self):
        if self.tile_id == TILE_IDS["terrain"] and "TerrainCorners" not in self.properties:
            self.properties["TerrainCorners"] = [[(-3.0, -1.0), (3.0, -1.0), (3.0, 1.0), (-3.0, 1.0)]]
        self._level.objects.append(self)
        layer = self._level._get_layer(self.layer)
        if layer and self.entity_id not in layer.children:
            layer.children.append(self.entity_id)
        return self

    def _to_raw_object(self) -> RawObject:
        return RawObject(
            entity_id=self.entity_id,
            tile_id=self.tile_id,
            prefab_entity_id=self.prefab_entity_id,
            prefab_id=self.prefab_id,
            position=self.pos,
            scale=self.scale,
            rotation=self.rotation,
            tag=self.tag,
            properties=list(self.properties.items()),
            in_layer=self.layer,
            in_group=self.in_group,
            group_members=list(self.group_members),
        )

    def to_dict(self) -> dict:
        return asdict(self._to_raw_object())

    def _write_to(self, w: BinaryWriter):
        w.write_i32(self.entity_id)
        w.write_i32(self.tile_id)
        w.write_i32(self.prefab_entity_id)
        w.write_i32(self.prefab_id)
        w.write_vec2(self.pos)
        w.write_vec2(self.scale)
        w.write_f32(self.rotation)
        w.write_str(self.tag)
        w.write_i32(len(self.properties))
        for name, val in self.properties.items():
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
        w.write_i32(self.layer)
        w.write_i32(self.in_group)
        w.write_vec(self.group_members, w.write_i32)


class ExoLevel:
    def __init__(self, name, bg_type="Mountains", laps=1, gravity=(0.0, -74.0), settings=None):
        tk = str(bg_type).strip().lower()
        if tk not in THEMES:
            raise InvalidThemeError(bg_type)
        if not (1 <= int(laps) <= 10):
            raise ValueError("laps must be 1..10")

        self.settings = DEFAULT_SETTINGS.copy()
        if settings:
            self.settings.update(settings)

        custom_uid = self.settings.get("uuid") or self.settings.get("UUID")
        self.uuid = str(custom_uid) if custom_uid else str(uuid.uuid4())
        self.name, self.theme, self.laps = str(name), THEMES[tk], int(laps)
        self.gravity = (float(gravity[0]), float(gravity[1]))
        self.custom_bg_color = parse_color(self.settings.get("CustomBackgroundColor", (0.0, 0.0, 0.0, 1.0)))
        self.thumbnail = str(self.settings.get("Thumbnail", ""))
        self.serialization_version = int(self.settings.get("SerializationVersion", 18))
        self.level_version = int(self.settings.get("LevelVersion", 1))
        self.nova_level = bool(self.settings.get("NovaLevel", True))
        self.creation_ticks = self.settings.get("CreationTicks")
        self.update_ticks = self.settings.get("UpdateTicks")
        self.v19_script_extra = int(self.settings.get("_V19ScriptExtra", 0))

        self.legacy_tiles = LegacyTileLayers()
        self.objects, self.layers = [], [Layer(1, "Layer 1")]
        self.prefabs: list[Prefab] = []
        self.brushes: list[Brush] = []
        self.patterns: list[Pattern] = []
        self.color_palette = list(self.settings.get("ColorPalette", []))
        self.legacy_scripts: list[int] = []
        self.nova_scripts, self.global_variables = [], []
        self.terrain_style = TerrainCopyStyle()
        self.author_replay = AuthorReplay()

        self._eid = self._vid = self._sid = self._pid = self._pat_id = 1
        self._prefab_id = self._brush_id = 1
        self._lid = 2
        self._return_regs = {}
        self._stdlib_cache = {}

    def _next_entity_id(self):
        v = self._eid
        self._eid += 1
        return v

    def _next_layer_id(self):
        v = self._lid
        self._lid += 1
        return v

    def _next_var_id(self):
        v = self._vid
        self._vid += 1
        return v

    def _next_script_id(self):
        v = self._sid
        self._sid += 1
        return v

    def _next_param_id(self):
        v = self._pid
        self._pid += 1
        return v

    def _next_pattern_id(self):
        v = self._pat_id
        self._pat_id += 1
        return v

    def _next_prefab_id(self):
        v = self._prefab_id
        self._prefab_id += 1
        return v

    def _next_brush_id(self):
        v = self._brush_id
        self._brush_id += 1
        return v

    def _get_layer(self, lid):
        return next((l for l in self.layers if l.layer_id == lid), None)

    def _obfuscate_names(self):
        def _mangle(seed):
            return "_0x" + hashlib.md5(f"{self.uuid}:{seed}".encode()).hexdigest()[:6]

        for idx, v in enumerate(self.global_variables):
            v.name = _mangle(f"gv_{idx}_{v.variable_id}")
        for idx, s in enumerate(self.nova_scripts):
            s.script_name = _mangle(f"sc_{idx}_{s.script_id}")
            for pi, p in enumerate(s.parameters):
                p.name = _mangle(f"p_{idx}_{pi}_{p.parameter_id}")
            for vi, lv in enumerate(s.variables):
                lv.name = _mangle(f"lv_{idx}_{vi}_{lv.variable_id}")

    def to_dict(self) -> dict:
        return {
            "serialization_version": self.serialization_version,
            "uuid": self.uuid,
            "level_version": self.level_version,
            "name": self.name,
            "theme": self.theme,
            "laps": self.laps,
            "gravity": list(self.gravity),
            "nova_level": self.nova_level,
            "custom_background_color": rgba_to_hex(self.custom_bg_color),
            "settings": dict(self.settings),
            "objects": [o.to_dict() for o in self.objects],
            "layers": [l.to_dict() for l in self.layers],
            "global_variables": [v.to_dict() for v in self.global_variables],
            "scripts_count": len(self.nova_scripts),
            "prefabs_count": len(self.prefabs),
            "brushes_count": len(self.brushes),
            "patterns_count": len(self.patterns),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_bytes(self) -> bytes:
        ver = self.serialization_version
        w = BinaryWriter()
        w.write_raw(b"NYA^")
        w.write_i32(ver)
        w.write_str(self.uuid)
        w.write_i32(self.level_version)
        w.write_str(self.name)
        w.write_str(self.thumbnail)
        w.write_i64(int(self.creation_ticks) if self.creation_ticks is not None else now_cs_ticks())
        w.write_i64(int(self.update_ticks) if self.update_ticks is not None else now_cs_ticks())
        author_ms = int(round(float(self.settings.get("AuthorTime", 0.0)) * 1000))
        author_laps = [int(round(float(x) * 1000)) for x in self.settings.get("AuthorLapTimes", [])]
        silver_ms = int(round(float(self.settings.get("Silver", 0.0)) * 1000))
        gold_ms = int(round(float(self.settings.get("Gold", 0.0)) * 1000))

        w.write_i64(author_ms)
        w.write_vec(author_laps, w.write_i64)
        w.write_i64(silver_ms)
        w.write_i64(gold_ms)
        w.write_i32(self.laps)
        w.write_bool(self.settings["Private"])
        w.write_bool(self.nova_level)

        w.write_str(self.uuid)
        w.write_i32(self.level_version)
        w.write_bool(self.nova_level)
        self.legacy_tiles.write(w)
        w.write_vec(self.objects, lambda o: o._write_to(w))
        w.write_vec(self.layers, lambda l: l._write_to(w))
        w.write_vec(self.prefabs, lambda p: p.write(w))
        w.write_vec(self.brushes, lambda b: b.write(w))
        w.write_vec(self.patterns, lambda pt: pt.write(w))
        if ver >= 17:
            w.write_vec(self.color_palette, w.write_color)

        w.write_i64(author_ms)
        w.write_vec(author_laps, w.write_i64)
        w.write_i64(silver_ms)
        w.write_i64(gold_ms)
        w.write_i32(self.laps)
        w.write_bool(self.settings["CenterCamera"])
        w.write_vec(self.legacy_scripts, w.write_i32)
        if ver >= 19:
            w.write_i32(self.v19_script_extra)
        w.write_vec(self.nova_scripts, lambda s: s._write_to(w, ver))
        w.write_vec(self.global_variables, lambda v: v._write_to(w, ver))
        w.write_str(self.theme)
        w.write_color(self.custom_bg_color)
        self.terrain_style.write(w)

        music = self.settings["music"]
        if not music:
            w.write_bool(True)
            w.write_vec([], w.write_str)
        else:
            w.write_bool(False)
            w.write_vec([music] if isinstance(music, str) else list(music), w.write_str)
        w.write_bool(self.settings["AllowDirectionChange"])
        w.write_bool(self.settings["DisableReplays"])
        w.write_bool(self.settings["DisableRevivePads"])
        w.write_bool(self.settings["DisableStartAnim"])
        w.write_vec2(self.gravity)
        self.author_replay.write(w)
        return w.to_bytes()

    def export(
        self,
        filepath: str,
        compress: bool = True,
        generator_mode: bool = None,
        obfuscate: bool = None,
        metadata_mode: str = "footer",
        include_meta: bool = False,
    ):
        obf = bool(self.settings.get("Obfuscate", False)) if obfuscate is None else bool(obfuscate)
        from_dec = bool(self.settings.get("_ExopyDecompiled", False))
        wm = "recompiled with exopy" if from_dec else "made with exopy"

        key_hash = b""
        if obf:
            self._obfuscate_names()
            secret_key = _get_or_create_key(self.uuid)
            key_hash = hashlib.sha256(secret_key.encode("utf-8")).digest()[:8]

        meta_obj = None
        if metadata_mode == "object":
            kh_part = f"|kh={key_hash.hex()}" if key_hash else ""
            tag_val = f"EXOPY|obf={int(obf)}|dec={int(from_dec)}|wm={wm}{kh_part}"
            meta_obj = GameObject("text", (90000019828.0, 90000019828.0), self).settings({
                "Text": tag_val, "FontSize": 0.1, "Tag": "__EXOPY_META__",
            }).pack()

        raw_bytes = self.to_bytes()
        if metadata_mode == "footer":
            raw_bytes += _build_exopy_footer(obfuscated=obf, watermark=wm, decompiled=from_dec, key_hash=key_hash)

        data = gzip.compress(raw_bytes) if compress else raw_bytes
        with open(filepath, "wb") as f:
            f.write(data)

        if meta_obj is not None:
            self.objects.remove(meta_obj)

        gen = _state.generator_mode if generator_mode is None else bool(generator_mode)
        result = {
            "ok": True,
            "path": filepath,
            "uuid": self.uuid,
            "counts": {
                "objects": len(self.objects),
                "scripts": len(self.nova_scripts),
                "variables": len(self.global_variables),
                "prefabs": len(self.prefabs),
                "brushes": len(self.brushes),
                "patterns": len(self.patterns),
            },
        }
        if include_meta:
            result["obfuscated"] = obf
            result["watermark"] = wm
        if gen:
            return result
        return filepath


def init(name, bg_type="Mountains", laps=1, gravity=(0.0, -74.0), settings=None):
    _state.active_level = ExoLevel(name, bg_type, laps, gravity, settings)
    return _state.active_level


def CreateObj(name, pos: tuple):
    return GameObject(name, pos, _state.get_level())


def CreateLayer(name: str, foreground_type: int = 0, parallax=(0.0, 0.0)):
    lvl = _state.get_level()
    layer = Layer(lvl._next_layer_id(), name, foreground_type, parallax)
    lvl.layers.append(layer)
    return layer


def CreateImage(source, mode: str = "pixel", pos: tuple = (0.0, 0.0)) -> ExoImage:
    """Create a pixel-art object group or level Pattern from a file path, bytes, or base64 string."""
    return ExoImage(source, mode=mode, pos=pos)


def CreatePrefab(objects, preview_image=None) -> Prefab:
    """Register a reusable Prefab from a list of GameObjects or RawObjects."""
    lvl = _state.get_level()
    pid = lvl._next_prefab_id()
    img_bytes = b""
    if preview_image is not None:
        img_bytes = preview_image.png_bytes if hasattr(preview_image, "png_bytes") else _resolve_raw_bytes(preview_image)
    items = [o._to_raw_object() if hasattr(o, "_to_raw_object") else o for o in objects]
    pf = Prefab(prefab_id=pid, prefab_image_data=img_bytes, items=items)
    lvl.prefabs.append(pf)
    return pf


def CreateBrush(objects, spread=(0.0, 0.0), frequency: float = 1.0, grid=(0, 0)) -> Brush:
    """Register a scatter Brush from a list of GameObjects or BrushObjects."""
    lvl = _state.get_level()
    bid = lvl._next_brush_id()
    b_objs = []
    for o in objects:
        if isinstance(o, BrushObject):
            b_objs.append(o)
        elif hasattr(o, "entity_id"):
            b_objs.append(BrushObject(
                entity_id=o.entity_id,
                properties=list(o.properties.items()),
                scale=o.scale[0],
                rotation=o.rotation,
            ))
        else:
            raise TypeError(f"Unsupported brush object: {o!r}")
    br = Brush(
        brush_id=bid,
        spread=(float(spread[0]), float(spread[1])),
        frequency=float(frequency),
        grid=BrushGrid(int(grid[0]), int(grid[1])),
        objects=b_objs,
    )
    lvl.brushes.append(br)
    return br


def set_generator_mode(enabled: bool = True):
    _state.generator_mode = bool(enabled)
