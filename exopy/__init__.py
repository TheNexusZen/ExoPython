import gzip, hashlib, os, secrets, struct, uuid
from . import _state, scripts, variables, stdlib
from .decompile import decompile
from .binary import BinaryWriter, parse_color
from .constants import THEMES, DEFAULT_SETTINGS, TILE_IDS, OBJECT_PROPERTIES


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
    with open(KEYS_FILE, "a", encoding="utf-8") as f:
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

    def _write_to(self, w: BinaryWriter):
        w.write_i32(self.layer_id); w.write_str(self.layer_name)
        w.write_bool(self.selected); w.write_bool(self.invisible); w.write_bool(self.locked)
        w.write_i32(self.foreground_type); w.write_vec2(self.parallax); w.write_bool(self.fixed_size)
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
        self.pos = (float(pos[0]), float(pos[1]))
        self.scale = (1.0, 1.0)
        self.rotation = 0.0
        self.tag = ""
        self.layer = level.layers[0].layer_id
        self.properties = {}
        self._level = level

    def settings(self, cfg: dict):
        for k, v in cfg.items():
            if k == "Rotation": self.rotation = float(v)
            elif k == "Scale": self.scale = (float(v[0]), float(v[1]))
            elif k == "Tag": self.tag = str(v)
            elif k == "Layer": self.layer = v.layer_id if isinstance(v, Layer) else int(v)
            elif k == "Box":
                hw, hh = float(v[0]) / 2.0, float(v[1]) / 2.0
                self.properties["TerrainCorners"] = [[(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]]
            elif k in OBJECT_PROPERTIES:
                self.properties[k] = v
            else:
                raise ValueError(f"Unknown object property: '{k}'")
        return self

    def pack(self):
        if self.tile_id == TILE_IDS["terrain"] and "TerrainCorners" not in self.properties:
            self.properties["TerrainCorners"] = [[(-3.0, -1.0), (3.0, -1.0), (3.0, 1.0), (-3.0, 1.0)]]
        self._level.objects.append(self)
        layer = self._level._get_layer(self.layer)
        if layer and self.entity_id not in layer.children:
            layer.children.append(self.entity_id)
        return self

    def _write_to(self, w: BinaryWriter):
        w.write_i32(self.entity_id); w.write_i32(self.tile_id)
        w.write_i32(0); w.write_i32(0)
        w.write_vec2(self.pos); w.write_vec2(self.scale); w.write_f32(self.rotation); w.write_str(self.tag)
        w.write_i32(len(self.properties))
        for name, val in self.properties.items():
            pid, pt = OBJECT_PROPERTIES[name]
            w.write_i32(pid)
            if pt == "color": w.write_color(val)
            elif pt == "i32": w.write_i32(val)
            elif pt == "f32": w.write_f32(val)
            elif pt == "bool": w.write_bool(val)
            elif pt == "vec2": w.write_vec2(val)
            elif pt == "str": w.write_str(val)
            elif pt == "vi32": w.write_vec(val, w.write_i32)
            elif pt == "tcorners": w.write_vec(val, lambda poly: w.write_vec(poly, w.write_vec2))
        w.write_i32(self.layer); w.write_i32(0); w.write_vec([], w.write_i32)


class ExoLevel:
    def __init__(self, name, bg_type="Mountains", laps=1, gravity=(0.0, -75.0), settings=None):
        tk = str(bg_type).strip().lower()
        if tk not in THEMES:
            raise ValueError("bg_type must be Mountains, Halloween, Christmas, or Custom")
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

        self.objects, self.layers, self.nova_scripts, self.global_variables = [], [Layer(1, "Layer 1")], [], []
        self._eid = self._vid = self._sid = self._pid = 1
        self._lid = 2
        self._return_regs = {}
        self._stdlib_cache = {}

    def _next_entity_id(self): v = self._eid; self._eid += 1; return v
    def _next_layer_id(self): v = self._lid; self._lid += 1; return v
    def _next_var_id(self): v = self._vid; self._vid += 1; return v
    def _next_script_id(self): v = self._sid; self._sid += 1; return v
    def _next_param_id(self): v = self._pid; self._pid += 1; return v
    def _get_layer(self, lid): return next((l for l in self.layers if l.layer_id == lid), None)

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

    def to_bytes(self) -> bytes:
        w = BinaryWriter()
        w.write_raw(b"NYA^")
        w.write_i32(18); w.write_str(self.uuid); w.write_i32(1); w.write_str(self.name); w.write_str("")
        w.write_datetime_now(); w.write_datetime_now()
        w.write_i64(int(round(float(self.settings.get("AuthorTime", 0.0)) * 1000))); w.write_vec([], w.write_i64); w.write_i64(int(round(float(self.settings.get("Silver", 0.0)) * 1000))); w.write_i64(int(round(float(self.settings.get("Gold", 0.0)) * 1000)))
        w.write_i32(self.laps); w.write_bool(self.settings["Private"]); w.write_bool(True)
        w.write_str(self.uuid); w.write_i32(1); w.write_bool(True)
        for _ in range(6): w.write_vec([], w.write_i32)
        w.write_vec(self.objects, lambda o: o._write_to(w))
        w.write_vec(self.layers, lambda l: l._write_to(w))
        for _ in range(4): w.write_i32(0)
        w.write_i64(int(round(float(self.settings.get("AuthorTime", 0.0)) * 1000))); w.write_vec([], w.write_i64); w.write_i64(int(round(float(self.settings.get("Silver", 0.0)) * 1000))); w.write_i64(int(round(float(self.settings.get("Gold", 0.0)) * 1000)))
        w.write_i32(self.laps); w.write_bool(self.settings["CenterCamera"])
        w.write_vec([], w.write_i32)
        w.write_vec(self.nova_scripts, lambda s: s._write_to(w))
        w.write_vec(self.global_variables, lambda v: v._write_to(w))
        w.write_str(self.theme); w.write_color(self.custom_bg_color); w.write_raw(b"\x00\x00\x00\x00")
        w.write_i32(0); w.write_vec2((0.0, 0.0)); w.write_vec2((0.0, 0.0))
        w.write_color((0.0, 0.0, 0.0, 0.0)); w.write_color((0.0, 0.0, 0.0, 0.0)); w.write_i32(0)
        w.write_color((0.0, 0.0, 0.0, 0.0)); w.write_f32(0.0); w.write_f32(0.0)
        w.write_bool(False); w.write_bool(False); w.write_f32(0.0)
        music = self.settings["music"]
        if not music:
            w.write_bool(True); w.write_vec([], w.write_str)
        else:
            w.write_bool(False); w.write_vec([music] if isinstance(music, str) else list(music), w.write_str)
        w.write_bool(self.settings["AllowDirectionChange"])
        w.write_bool(self.settings["DisableReplays"])
        w.write_bool(self.settings["DisableRevivePads"])
        w.write_bool(self.settings["DisableStartAnim"])
        w.write_vec2(self.gravity)
        w.write_i32(0)
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

        fns = sum(1 for s in self.nova_scripts if s.is_function)
        gen = _state.generator_mode if generator_mode is None else bool(generator_mode)
        fname = os.path.basename(filepath)
        result = {
            "ok": True,
            "path": filepath,
            "uuid": self.uuid,
            "counts": {
                "objects": len(self.objects),
                "scripts": len(self.nova_scripts),
                "variables": len(self.global_variables),
            },
        }
        if include_meta:
            result["obfuscated"] = obf
            result["watermark"] = wm
        if gen:
            return result
        pass
        return filepath


def init(name, bg_type="Mountains", laps=1, gravity=(0.0, -75.0), settings=None):
    _state.active_level = ExoLevel(name, bg_type, laps, gravity, settings)
    return _state.active_level


def CreateObj(name, pos: tuple):
    return GameObject(name, pos, _state.get_level())


def CreateLayer(name: str, foreground_type: int = 0, parallax=(0.0, 0.0)):
    lvl = _state.get_level()
    layer = Layer(lvl._next_layer_id(), name, foreground_type, parallax)
    lvl.layers.append(layer)
    return layer


def set_generator_mode(enabled: bool = True):
    _state.generator_mode = bool(enabled)
