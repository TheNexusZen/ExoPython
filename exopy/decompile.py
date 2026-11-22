import base64, hashlib, marshal, zlib
import re
import gzip
import os
import struct
import sys
from dataclasses import asdict
from . import _state
from .binary import BinaryReader, rgba_to_hex
from .constants import TILE_IDS, OBJECT_PROPERTIES
from .errors import (
    WrongMagicError,
    InvalidObjectPropertyError,
    InvalidActionTypeError,
)
from .types_ext import (
    AuthorReplay, Brush, LegacyTileLayers, LocalLevel, Pattern, Prefab, TerrainCopyStyle,
)

_ID_TO_TILE = {v: k for k, v in TILE_IDS.items()}
_ID_TO_PROP = {pid: (name, ptype) for name, (pid, ptype) in OBJECT_PROPERTIES.items()}

KEYS_FILE = os.path.expanduser("~/.exopy_keys.txt")


def _check_owner_key(level_uuid: str, expected_hash_hex: str) -> bool:
    if not expected_hash_hex or not os.path.exists(KEYS_FILE):
        return False
    with open(KEYS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                if k.strip() == level_uuid:
                    h = hashlib.sha256(v.strip().encode("utf-8")).digest()[:8].hex()
                    if h == expected_hash_hex:
                        return True
    return False


def _pack_obfuscated_py(code: str, seed: str) -> str:
    bc = marshal.dumps(compile(code, "<exopy>", "exec"))
    key = hashlib.sha256(seed.encode("utf-8")).digest()[:16]
    raw = zlib.compress(bc, 9)
    xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    blob = base64.b85encode(xored).decode("ascii")
    k_hex = key.hex()
    return (
        "# ExoPy Protected Bytecode\n"
        "import base64 as _b, marshal as _m, zlib as _z\n"
        f"_k=bytes.fromhex('{k_hex}')\n"
        f"_d=_b.b85decode(b'{blob}')\n"
        "exec(_m.loads(_z.decompress(bytes(x^_k[i%len(_k)] for i,x in enumerate(_d)))))\n"
    )


def read_exopy_meta(data: bytes):
    if len(data) >= 12 and data.endswith(b"YPXE"):
        body_len = struct.unpack("<H", data[-6:-4])[0]
        start = len(data) - 6 - body_len
        if start >= 0 and data[start : start + 4] == b"EXPY":
            flags = data[start + 4]
            wm_len = data[start + 5]
            wm = data[start + 6 : start + 6 + wm_len].decode("utf-8", errors="replace")
            kh = ""
            if flags & 0x08:
                kh_start = start + 6 + wm_len
                kh = data[kh_start : kh_start + 8].hex()
            return {
                "source": "footer",
                "compiled_by_exopy": bool(flags & 0x01),
                "decompiled_by_exopy": bool(flags & 0x02),
                "obfuscated": bool(flags & 0x04),
                "watermark": wm,
                "key_hash": kh,
            }, data[:start]
    return None, data


def _safe_ident(name: str, fallback: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip()).strip("_").lower()
    if not s or s[0].isdigit():
        return fallback
    return s


def _try_box(corners):
    if len(corners) != 1 or len(corners[0]) != 4:
        return None
    xs = sorted(set(round(p[0], 3) for p in corners[0]))
    ys = sorted(set(round(p[1], 3) for p in corners[0]))
    if len(xs) == 2 and len(ys) == 2 and abs(xs[0] + xs[1]) < 1e-2 and abs(ys[0] + ys[1]) < 1e-2:
        return (round(xs[1] - xs[0], 3), round(ys[1] - ys[0], 3))
    return None


def _read_prop(r: BinaryReader):
    pid = r.i32()
    if pid not in _ID_TO_PROP:
        raise InvalidObjectPropertyError(pid)
    name, ptype = _ID_TO_PROP[pid]
    if ptype == "color":
        return name, rgba_to_hex(r.color())
    if ptype == "i32":
        return name, r.i32()
    if ptype == "f32":
        return name, r.f32()
    if ptype == "bool":
        return name, r.bool()
    if ptype == "vec2":
        return name, r.vec2()
    if ptype == "str":
        return name, r.string()
    if ptype == "vi32":
        return name, r.vec(r.i32)
    if ptype == "tcorners":
        return name, r.vec(lambda: r.vec(r.vec2))
    raise InvalidObjectPropertyError(ptype)


def _read_nova(r: BinaryReader, ver: int = 18) -> dict:
    dt = r.i32()
    b = r.bool()
    i = r.i32()
    f = r.f32()
    s = r.option(r.string)
    c = r.color()
    v = r.vec2()
    if ver >= 19:
        r.u8()
    il = r.option(lambda: r.vec(r.i32))
    sub = r.option(lambda: r.vec(lambda: _read_nova(r, ver)))
    if ver >= 19:
        r.raw(4)
    return {"dt": dt, "b": b, "i": i, "f": f, "s": s, "c": c, "v": v, "il": il, "sub": sub}


def _fmt_nova(nv: dict) -> str:
    dt = nv["dt"]
    if dt == 0:
        return repr(nv["b"])
    if dt == 38:
        return repr(nv["i"])
    if dt == 56:
        return repr(nv["f"])
    if dt == 94:
        return repr(nv["s"] or "")
    if dt == 99:
        return repr(rgba_to_hex(nv["c"]))
    if dt == 103:
        return repr(nv["v"])
    if dt == 134:
        return f"exovar.object_set({nv['il'] or []!r})"

    kw = []
    if nv["b"]:
        kw.append(f"bool_value={nv['b']!r}")
    if nv["i"]:
        kw.append(f"int_value={nv['i']!r}")
    if nv["f"]:
        kw.append(f"float_value={nv['f']!r}")
    if nv["s"] is not None:
        kw.append(f"string_value={nv['s']!r}")
    if any(abs(x) > 1e-6 for x in nv["c"]):
        kw.append(f"color_value={rgba_to_hex(nv['c'])!r}")
    if nv["v"] != (0.0, 0.0):
        kw.append(f"vector_value={nv['v']!r}")
    if nv["il"] is not None:
        kw.append(f"int_list_value={nv['il']!r}")
    if nv["sub"] is not None:
        subs = ", ".join(_fmt_nova(s) for s in nv["sub"])
        kw.append(f"sub_values=[{subs}]")
    args = f"{dt}, " + ", ".join(kw) if kw else str(dt)
    return f"exovar.value({args})"


def _read_action(r: BinaryReader, ver: int = 18) -> dict:
    aid = r.i32()
    closed = r.bool()
    wait = r.bool()
    rn = lambda: _read_nova(r, ver)
    ra = lambda: r.vec(lambda: _read_action(r, ver))

    if aid == 0:
        d = {"actions": ra(), "count": rn()}
    elif aid == 1:
        d = {"actions": ra(), "condition": rn()}
    elif aid == 2:
        d = {"if_actions": ra(), "else_actions": ra(), "condition": rn()}
    elif aid == 3:
        d = {"fields": [rn()]}
    elif aid == 4:
        d = {"fields": [rn()]}
    elif aid in (5, 12, 13, 32):
        d = {"fields": [rn() for _ in range(5)]}
    elif aid in (6, 14, 15, 16, 17, 44, 45):
        d = {"fields": [rn() for _ in range(4)]}
    elif aid in (7, 8):
        d = {"fields": [rn() for _ in range(6)]}
    elif aid == 9:
        d = {"var_id": r.i32(), "value": r.option(rn)}
    elif aid == 10:
        d = {"var_id": r.i32()}
    elif aid in (11, 21, 22, 24, 38, 39, 40, 43, 51):
        d = {"fields": [rn()]}
    elif aid in (18, 19, 20, 23, 29, 31, 35, 36, 37, 41, 50, 52):
        d = {"fields": [rn(), rn()]}
    elif aid in (25, 27):
        d = {"fields": []}
    elif aid in (26, 28, 30, 33, 34, 42, 46):
        d = {"fields": [rn(), rn(), rn()]}
    elif aid == 47:
        d = {"fn_id": r.i32(), "params": r.vec(lambda: (r.i32(), rn()))}
    elif aid == 48:
        d = {"var_id": r.i32(), "value": r.option(rn), "duration": rn(), "easing": rn()}
    elif aid == 49:
        d = {"target": rn(), "actions": ra()}
    else:
        raise InvalidActionTypeError(aid)

    d.update({"aid": aid, "closed": closed, "wait": wait})
    return d


def _emit_actions(acts, target_var: str, indent: str = "") -> list:
    lines = []
    for a in acts:
        aid, wait = a["aid"], a["wait"]
        if aid == 0:
            lines.append(f"{indent}_rep = exoscript.block()")
            lines.extend(_emit_actions(a["actions"], "_rep", indent))
            lines.append(f"{indent}{target_var}.repeat({_fmt_nova(a['count'])}, _rep, wait={wait!r})")
        elif aid == 1:
            lines.append(f"{indent}_whl = exoscript.block()")
            lines.extend(_emit_actions(a["actions"], "_whl", indent))
            lines.append(f"{indent}{target_var}.repeat_while({_fmt_nova(a['condition'])}, _whl, wait={wait!r})")
        elif aid == 2:
            lines.append(f"{indent}_if = exoscript.block()")
            lines.extend(_emit_actions(a["if_actions"], "_if", indent))
            lines.append(f"{indent}_el = exoscript.block()")
            lines.extend(_emit_actions(a["else_actions"], "_el", indent))
            lines.append(f"{indent}{target_var}.if_else({_fmt_nova(a['condition'])}, _if, _el, wait={wait!r})")
        elif aid == 3:
            lines.append(f"{indent}{target_var}.wait({_fmt_nova(a['fields'][0])})")
        elif aid == 4:
            lines.append(f"{indent}{target_var}.wait_frames({_fmt_nova(a['fields'][0])})")
        elif aid == 5:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.move({f[0]}, {f[1]}, is_global={f[2]}, duration={f[3]}, easing={f[4]}, wait={wait!r})")
        elif aid == 6:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.scale({f[0]}, {f[1]}, duration={f[2]}, easing={f[3]}, wait={wait!r})")
        elif aid == 7:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.rotate({f[0]}, {f[1]}, shortest_path={f[2]}, is_global={f[3]}, duration={f[4]}, easing={f[5]}, wait={wait!r})")
        elif aid == 8:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.rotate_around({f[0]}, {f[1]}, {f[2]}, rotate_target={f[3]}, duration={f[4]}, easing={f[5]}, wait={wait!r})")
        elif aid == 9:
            val_s = _fmt_nova(a["value"]) if a["value"] is not None else "None"
            lines.append(f"{indent}{target_var}.set_var({a['var_id']}, {val_s})")
        elif aid == 10:
            lines.append(f"{indent}{target_var}.reset_var({a['var_id']})")
        elif aid == 11:
            lines.append(f"{indent}{target_var}.reset_object({_fmt_nova(a['fields'][0])})")
        elif aid == 12:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.set_color({f[0]}, {f[1]}, channel={f[2]}, duration={f[3]}, easing={f[4]}, wait={wait!r})")
        elif aid == 13:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.set_transparency({f[0]}, {f[1]}, channel={f[2]}, duration={f[3]}, easing={f[4]}, wait={wait!r})")
        elif aid == 14:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.set_secondary_color({f[0]}, {f[1]}, duration={f[2]}, easing={f[3]}, wait={wait!r})")
        elif aid == 15:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.set_secondary_transparency({f[0]}, {f[1]}, duration={f[2]}, easing={f[3]}, wait={wait!r})")
        elif aid == 16:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.set_border_color({f[0]}, {f[1]}, duration={f[2]}, easing={f[3]}, wait={wait!r})")
        elif aid == 17:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.set_border_transparency({f[0]}, {f[1]}, duration={f[2]}, easing={f[3]}, wait={wait!r})")
        elif aid == 18:
            lines.append(f"{indent}{target_var}.set_sprite({_fmt_nova(a['fields'][0])}, {_fmt_nova(a['fields'][1])})")
        elif aid == 19:
            lines.append(f"{indent}{target_var}.set_text({_fmt_nova(a['fields'][0])}, {_fmt_nova(a['fields'][1])})")
        elif aid == 20:
            lines.append(f"{indent}{target_var}.set_enabled({_fmt_nova(a['fields'][0])}, {_fmt_nova(a['fields'][1])})")
        elif aid == 21:
            lines.append(f"{indent}{target_var}.activate({_fmt_nova(a['fields'][0])})")
        elif aid == 22:
            lines.append(f"{indent}{target_var}.deactivate({_fmt_nova(a['fields'][0])})")
        elif aid == 23:
            lines.append(f"{indent}{target_var}.damage({_fmt_nova(a['fields'][0])}, {_fmt_nova(a['fields'][1])})")
        elif aid == 24:
            lines.append(f"{indent}{target_var}.kill({_fmt_nova(a['fields'][0])})")
        elif aid == 25:
            lines.append(f"{indent}{target_var}.game_finish()")
        elif aid == 26:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.camera_pan({f[0]}, duration={f[1]}, easing={f[2]}, wait={wait!r})")
        elif aid == 27:
            lines.append(f"{indent}{target_var}.camera_follow_player()")
        elif aid == 28:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.camera_zoom({f[0]}, duration={f[1]}, easing={f[2]}, wait={wait!r})")
        elif aid == 29:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.camera_zoom_reset(duration={f[0]}, easing={f[1]}, wait={wait!r})")
        elif aid == 30:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.camera_offset({f[0]}, duration={f[1]}, easing={f[2]}, wait={wait!r})")
        elif aid == 31:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.camera_offset_reset(duration={f[0]}, easing={f[1]}, wait={wait!r})")
        elif aid == 32:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.camera_shake({f[0]}, {f[1]}, {f[2]}, {f[3]}, {f[4]}, wait={wait!r})")
        elif aid == 33:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.play_sound({f[0]}, volume={f[1]}, pitch={f[2]})")
        elif aid == 34:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.play_music({f[0]}, volume={f[1]}, pitch={f[2]})")
        elif aid == 35:
            lines.append(f"{indent}{target_var}.set_direction({_fmt_nova(a['fields'][0])}, {_fmt_nova(a['fields'][1])})")
        elif aid == 36:
            lines.append(f"{indent}{target_var}.set_gravity({_fmt_nova(a['fields'][0])}, {_fmt_nova(a['fields'][1])})")
        elif aid == 37:
            lines.append(f"{indent}{target_var}.set_velocity({_fmt_nova(a['fields'][0])}, {_fmt_nova(a['fields'][1])})")
        elif aid == 38:
            lines.append(f"{indent}{target_var}.set_cinematic({_fmt_nova(a['fields'][0])})")
        elif aid == 39:
            lines.append(f"{indent}{target_var}.set_input_enabled({_fmt_nova(a['fields'][0])})")
        elif aid == 40:
            lines.append(f"{indent}{target_var}.set_timer_enabled({_fmt_nova(a['fields'][0])})")
        elif aid == 41:
            lines.append(f"{indent}{target_var}.game_text({_fmt_nova(a['fields'][0])}, {_fmt_nova(a['fields'][1])}, wait={wait!r})")
        elif aid == 42:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.dialogue_show({f[0]}, {f[1]}, {f[2]}, wait={wait!r})")
        elif aid == 43:
            lines.append(f"{indent}{target_var}.stop_script({_fmt_nova(a['fields'][0])})")
        elif aid == 44:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.transition_in({f[0]}, {f[1]}, duration={f[2]}, easing={f[3]}, wait={wait!r})")
        elif aid == 45:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.transition_out({f[0]}, {f[1]}, duration={f[2]}, easing={f[3]}, wait={wait!r})")
        elif aid == 46:
            f = [_fmt_nova(x) for x in a["fields"]]
            lines.append(f"{indent}{target_var}.time_scale({f[0]}, duration={f[1]}, easing={f[2]}, wait={wait!r})")
        elif aid == 47:
            p_str = ", ".join(f"({pid}, {_fmt_nova(v)})" for pid, v in a["params"])
            lines.append(f"{indent}{target_var}.call_id({a['fn_id']}, [{p_str}], wait={wait!r})")
        elif aid == 48:
            val_s = _fmt_nova(a["value"]) if a["value"] is not None else "None"
            lines.append(f"{indent}{target_var}.set_var_over_time({a['var_id']}, {val_s}, duration={_fmt_nova(a['duration'])}, easing={_fmt_nova(a['easing'])}, wait={wait!r})")
        elif aid == 49:
            lines.append(f"{indent}_fe = exoscript.block()")
            lines.extend(_emit_actions(a["actions"], "_fe", indent))
            lines.append(f"{indent}{target_var}.repeat_for_each({_fmt_nova(a['target'])}, _fe, wait={wait!r})")
        elif aid == 50:
            lines.append(f"{indent}{target_var}.stop_sound({_fmt_nova(a['fields'][0])}, fade_out={_fmt_nova(a['fields'][1])})")
        elif aid == 51:
            lines.append(f"{indent}{target_var}.play_particles({_fmt_nova(a['fields'][0])})")
        elif aid == 52:
            lines.append(f"{indent}{target_var}.stop_particles({_fmt_nova(a['fields'][0])}, clear={_fmt_nova(a['fields'][1])})")
        elif "fields" in a:
            f = ", ".join(_fmt_nova(x) for x in a["fields"])
            lines.append(f"{indent}{target_var}.raw_action({aid}{', ' + f if f else ''}, wait={wait!r})")
    return lines


def _read_var(r: BinaryReader, ver: int = 18) -> dict:
    return {"id": r.i32(), "name": r.string(), "stype": r.i32(), "init": _read_nova(r, ver)}


def _read_script(r: BinaryReader, ver: int = 18) -> dict:
    sid = r.i32()
    name = r.string()
    is_fn = r.bool()
    act_cnt = r.i32()
    cond = _read_nova(r, ver)
    activators = r.vec(lambda: (r.i32(), r.vec(lambda: _read_nova(r, ver))))
    params = r.vec(lambda: _read_var(r, ver))
    local_vars = r.vec(lambda: _read_var(r, ver))
    actions = r.vec(lambda: _read_action(r, ver))
    return {
        "id": sid, "name": name, "is_fn": is_fn, "act_cnt": act_cnt,
        "cond": cond, "activators": activators, "params": params,
        "vars": local_vars, "actions": actions,
    }


def inspect_level(filepath: str) -> dict:
    """Parse an .exolvl file into a complete structured dictionary (mirrors Rust's print_exolvl / serde)."""
    with open(filepath, "rb") as f:
        raw = f.read()

    data = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    exopy_meta, data = read_exopy_meta(data)
    r = BinaryReader(data)
    magic = r.raw(4)
    if magic != b"NYA^":
        raise WrongMagicError(magic)

    local_lvl = LocalLevel.read(r)
    ver = local_lvl.serialization_version
    ld_uuid = r.string()
    ld_ver = r.i32()
    ld_nova = r.bool()
    legacy_tiles = LegacyTileLayers.read(r)

    objects = []
    for _ in range(r.i32()):
        eid, tid = r.i32(), r.i32()
        prefab_eid, prefab_id = r.i32(), r.i32()
        pos, scale, rot, tag = r.vec2(), r.vec2(), r.f32(), r.string()
        props = dict(r.vec(lambda: _read_prop(r)))
        layer = r.i32()
        in_group = r.i32()
        group_members = r.vec(r.i32)
        objects.append({
            "entity_id": eid,
            "tile_id": tid,
            "tile_name": _ID_TO_TILE.get(tid, str(tid)),
            "prefab_entity_id": prefab_eid,
            "prefab_id": prefab_id,
            "position": list(pos),
            "scale": list(scale),
            "rotation": rot,
            "tag": tag,
            "properties": props,
            "in_layer": layer,
            "in_group": in_group,
            "group_members": group_members,
        })

    layers = []
    for _ in range(r.i32()):
        layers.append({
            "layer_id": r.i32(),
            "layer_name": r.string(),
            "selected": r.bool(),
            "invisible": r.bool(),
            "locked": r.bool(),
            "foreground_type": r.i32(),
            "parallax": list(r.vec2()),
            "fixed_size": r.bool(),
            "children": r.vec(r.i32),
        })

    prefabs = [
        {"prefab_id": pf.prefab_id, "image_bytes": len(pf.prefab_image_data), "items": [asdict(i) for i in pf.items]}
        for pf in r.vec(lambda: Prefab.read(r))
    ]
    brushes = [asdict(b) for b in r.vec(lambda: Brush.read(r))]
    patterns = [
        {"pattern_id": pt.pattern_id, "frame_sizes": [len(fr) for fr in pt.pattern_frames]}
        for pt in r.vec(lambda: Pattern.read(r))
    ]
    color_palette = [rgba_to_hex(c) for c in r.vec(r.color)] if ver >= 17 else None

    ld_author_time = r.i64()
    ld_author_laps = r.vec(r.i64)
    ld_silver = r.i64()
    ld_gold = r.i64()
    ld_laps = r.i32()
    center_camera = r.bool()
    legacy_scripts = r.vec(r.i32)
    v19_extra = r.i32() if ver >= 19 else None
    nova_scripts = r.vec(lambda: _read_script(r, ver))
    global_vars = r.vec(lambda: _read_var(r, ver))
    theme = r.string()
    custom_bg_color = rgba_to_hex(r.color())
    terrain_style = asdict(TerrainCopyStyle.read(r))
    terrain_style["unknown1"] = list(terrain_style["unknown1"])
    default_music = r.bool()
    music_ids = r.vec(r.string)
    allow_direction_change = r.bool()
    disable_replays = r.bool()
    disable_revive_pads = r.bool()
    disable_start_anim = r.bool()
    gravity = list(r.vec2())
    replay = AuthorReplay.read(r) if r.i + 4 <= len(r.b) else AuthorReplay()

    return {
        "exopy_meta": exopy_meta,
        "local_level": asdict(local_lvl),
        "level_data": {
            "level_id": ld_uuid,
            "level_version": ld_ver,
            "nova_level": ld_nova,
            "legacy_tiles": asdict(legacy_tiles),
            "objects": objects,
            "layers": layers,
            "prefabs": prefabs,
            "brushes": brushes,
            "patterns": patterns,
            "color_palette": color_palette,
            "author_time": ld_author_time,
            "author_lap_times": ld_author_laps,
            "silver_medal_time": ld_silver,
            "gold_medal_time": ld_gold,
            "laps": ld_laps,
            "center_camera": center_camera,
            "scripts": legacy_scripts,
            "v19_script_extra": v19_extra,
            "nova_scripts": nova_scripts,
            "global_variables": global_vars,
            "theme": theme,
            "custom_background_color": custom_bg_color,
            "terrain_copy_style": terrain_style,
            "default_music": default_music,
            "music_ids": music_ids,
            "allow_direction_change": allow_direction_change,
            "disable_replays": disable_replays,
            "disable_revive_pads": disable_revive_pads,
            "disable_start_animation": disable_start_anim,
            "gravity": gravity,
        },
        "author_replay_bytes": len(replay.data),
    }


def decompile(
    filepath: str,
    out_py: str = None,
    generator_mode: bool = None,
    include_meta: bool = False,
    extract_assets: bool = False,
):
    with open(filepath, "rb") as f:
        raw = f.read()

    data = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    exopy_meta, data = read_exopy_meta(data)
    gen = _state.generator_mode if generator_mode is None else bool(generator_mode)
    is_obf = bool(exopy_meta and exopy_meta.get("obfuscated"))
    r = BinaryReader(data)
    magic = r.raw(4)
    if magic != b"NYA^":
        raise WrongMagicError(magic)

    local_lvl = LocalLevel.read(r)
    ver = local_lvl.serialization_version
    uid = local_lvl.level_id
    lver = local_lvl.level_version
    name = local_lvl.level_name
    thumb = local_lvl.thumbnail
    creation_ticks = local_lvl.creation_date_ticks
    update_ticks = local_lvl.update_date_ticks
    author_ms = local_lvl.author_time
    author_laps = local_lvl.author_lap_times
    silver_ms = local_lvl.silver_medal_time
    gold_ms = local_lvl.gold_medal_time
    laps = max(1, min(10, local_lvl.laps))
    private = local_lvl.private
    nova_lvl = local_lvl.nova_level

    r.string()
    r.i32()
    r.bool()
    legacy_tiles = LegacyTileLayers.read(r)

    objects = []
    for _ in range(r.i32()):
        eid, tid = r.i32(), r.i32()
        prefab_eid, prefab_id = r.i32(), r.i32()
        pos, scale, rot, tag = r.vec2(), r.vec2(), r.f32(), r.string()
        props = dict(r.vec(lambda: _read_prop(r)))
        layer = r.i32()
        in_group = r.i32()
        group_members = r.vec(r.i32)
        if tag == "__EXOPY_META__" and "Text" in props and props["Text"].startswith("EXOPY|"):
            parts = dict(p.split("=", 1) for p in props["Text"].split("|")[1:] if "=" in p)
            exopy_meta = {
                "source": "object",
                "compiled_by_exopy": True,
                "decompiled_by_exopy": parts.get("dec") == "1",
                "obfuscated": parts.get("obf") == "1",
                "watermark": parts.get("wm", ""),
                "key_hash": parts.get("kh", ""),
            }
            if exopy_meta["obfuscated"]:
                is_obf = True
            continue
        objects.append((eid, tid, prefab_eid, prefab_id, pos, scale, rot, tag, props, layer, in_group, group_members))

    layers = []
    for _ in range(r.i32()):
        lid, lname = r.i32(), r.string()
        sel, inv, lock = r.bool(), r.bool(), r.bool()
        fg, plx = r.i32(), r.vec2()
        fixed = r.bool()
        r.vec(r.i32)
        layers.append((lid, lname, sel, inv, lock, fg, plx, fixed))

    prefabs, brushes, patterns, color_palette = [], [], [], []
    legacy_scripts, nova_scripts, global_vars = [], [], []
    terrain_style = TerrainCopyStyle()
    author_replay = AuthorReplay()
    theme, gravity = "Mountains", (0.0, -75.0)
    lvl_settings = {
        "uuid": uid,
        "Private": private,
        "SerializationVersion": ver,
        "LevelVersion": lver,
        "NovaLevel": nova_lvl,
        "CreationTicks": creation_ticks,
        "UpdateTicks": update_ticks,
        "_ExopyDecompiled": True,
    }
    if thumb:
        lvl_settings["Thumbnail"] = thumb
    if author_ms:
        lvl_settings["AuthorTime"] = round(author_ms / 1000.0, 3)
    if author_laps:
        lvl_settings["AuthorLapTimes"] = [round(x / 1000.0, 3) for x in author_laps]
    if silver_ms:
        lvl_settings["Silver"] = round(silver_ms / 1000.0, 3)
    if gold_ms:
        lvl_settings["Gold"] = round(gold_ms / 1000.0, 3)
    tail_note = None

    try:
        prefabs = r.vec(lambda: Prefab.read(r))
        brushes = r.vec(lambda: Brush.read(r))
        patterns = r.vec(lambda: Pattern.read(r))
        if ver >= 17:
            color_palette = r.vec(r.color)
            if color_palette:
                lvl_settings["ColorPalette"] = [rgba_to_hex(c) for c in color_palette]

        r.i64()
        r.vec(r.i64)
        r.i64()
        r.i64()
        r.i32()
        lvl_settings["CenterCamera"] = r.bool()
        legacy_scripts = r.vec(r.i32)
        if ver >= 19:
            lvl_settings["_V19ScriptExtra"] = r.i32()
        nova_scripts = r.vec(lambda: _read_script(r, ver))
        global_vars = r.vec(lambda: _read_var(r, ver))

        raw_theme = r.string().strip().lower()
        theme = raw_theme.capitalize() if raw_theme in ("mountains", "halloween", "christmas", "custom") else "Mountains"
        bg_col = rgba_to_hex(r.color())
        if theme == "Custom":
            lvl_settings["CustomBackgroundColor"] = bg_col
        terrain_style = TerrainCopyStyle.read(r)

        default_music = r.bool()
        music_ids = r.vec(r.string)
        if not default_music and music_ids:
            lvl_settings["music"] = music_ids[0] if len(music_ids) == 1 else music_ids

        lvl_settings["AllowDirectionChange"] = r.bool()
        lvl_settings["DisableReplays"] = r.bool()
        lvl_settings["DisableRevivePads"] = r.bool()
        lvl_settings["DisableStartAnim"] = r.bool()
        gravity = r.vec2()
        if r.i + 4 <= len(r.b):
            author_replay = AuthorReplay.read(r)
    except Exception as e:
        tail_note = f"Partial tail parse ({e})"

    base_name = os.path.splitext(os.path.basename(filepath))[0]
    if out_py is None:
        out_py = f"{base_name}_exopy.py"
    asset_dir = os.path.join(os.path.dirname(os.path.abspath(out_py)), f"{base_name}_assets")

    lines = [
        f"# Decompiled from {os.path.basename(filepath)} (format v{ver})",
        "import exopython as exo",
        "from exopython import scripts as exoscript",
        "from exopython import variables as exovar",
        "from exopython.types_ext import Brush, BrushGrid, BrushObject, Pattern, Prefab, RawObject, TerrainCopyStyle",
        "",
        f"Settings = {lvl_settings!r}",
        f"Level = exo.init({name!r}, {theme!r}, {laps}, {gravity!r}, Settings)",
        "",
    ]
    if tail_note:
        lines.append(f"# Note: {tail_note}")
        lines.append("")

    for lid, lname, sel, inv, lock, fg, plx, fixed in layers:
        if lid == 1:
            if sel or inv or lock or fixed or fg != 0 or plx != (0.0, 0.0):
                lines.append(
                    f"Level.layers[0].selected, Level.layers[0].invisible, Level.layers[0].locked, "
                    f"Level.layers[0].foreground_type, Level.layers[0].parallax, Level.layers[0].fixed_size = "
                    f"{sel!r}, {inv!r}, {lock!r}, {fg!r}, {plx!r}, {fixed!r}"
                )
            continue
        lines.append(f"layer_{lid} = exo.CreateLayer({lname!r}, foreground_type={fg}, parallax={plx})")
        if sel or inv or lock or fixed:
            lines.append(
                f"layer_{lid}.selected, layer_{lid}.invisible, layer_{lid}.locked, layer_{lid}.fixed_size = "
                f"{sel!r}, {inv!r}, {lock!r}, {fixed!r}"
            )
    if len(layers) > 1:
        lines.append("")

    if terrain_style != TerrainCopyStyle():
        lines.append(f"Level.terrain_style = {terrain_style!r}")
        lines.append("")

    # --- Patterns ---
    if patterns:
        lines.append("# --- Patterns ---")
        for pat in patterns:
            if extract_assets:
                os.makedirs(asset_dir, exist_ok=True)
                frame_exprs = []
                for fi, frame_bytes in enumerate(pat.pattern_frames):
                    fname = f"pattern_{pat.pattern_id}_f{fi}.png"
                    fpath = os.path.join(asset_dir, fname)
                    with open(fpath, "wb") as af:
                        af.write(frame_bytes)
                    frame_exprs.append(f"open({fpath!r}, 'rb').read()")
                lines.append(f"Level.patterns.append(Pattern(pattern_id={pat.pattern_id}, pattern_frames=[{', '.join(frame_exprs)}]))")
            elif len(pat.pattern_frames) == 1:
                b64_str = base64.b64encode(pat.pattern_frames[0]).decode("ascii")
                lines.append(f"pat_{pat.pattern_id} = exo.CreateImage({b64_str!r}, mode='pattern')")
                lines.append(f"pat_{pat.pattern_id}.pattern_id = {pat.pattern_id}")
                lines.append(f"Level.patterns[-1].pattern_id = {pat.pattern_id}")
            else:
                lines.append(f"Level.patterns.append({pat!r})")
        lines.append("")

    # --- Prefabs ---
    if prefabs:
        lines.append("# --- Prefabs ---")
        for pf in prefabs:
            if extract_assets and pf.prefab_image_data:
                os.makedirs(asset_dir, exist_ok=True)
                fpath = os.path.join(asset_dir, f"prefab_{pf.prefab_id}.png")
                with open(fpath, "wb") as af:
                    af.write(pf.prefab_image_data)
                lines.append(f"Level.prefabs.append(Prefab(prefab_id={pf.prefab_id}, prefab_image_data=open({fpath!r}, 'rb').read(), items={pf.items!r}))")
            else:
                lines.append(f"Level.prefabs.append({pf!r})")
        lines.append("")

    # --- Brushes ---
    if brushes:
        lines.append("# --- Brushes ---")
        for br in brushes:
            lines.append(f"Level.brushes.append({br!r})")
        lines.append("")

    # --- Legacy Scripts & Author Replay ---
    if legacy_scripts:
        lines.append(f"Level.legacy_scripts = {legacy_scripts!r}")
    if author_replay.data:
        lines.append(f"Level.author_replay.data = {author_replay.data!r}")
    if legacy_scripts or author_replay.data:
        lines.append("")

    # --- Objects ---
    for eid, tid, prefab_eid, prefab_id, pos, scale, rot, tag, props, layer, in_group, group_members in objects:
        tile_arg = repr(_ID_TO_TILE[tid]) if tid in _ID_TO_TILE else str(tid)
        cfg = {}
        if scale != (1.0, 1.0):
            cfg["Scale"] = scale
        if rot != 0.0:
            cfg["Rotation"] = rot
        if tag:
            cfg["Tag"] = tag
        if layer != 1:
            cfg["Layer"] = layer
        if prefab_eid:
            cfg["PrefabEntityId"] = prefab_eid
        if prefab_id:
            cfg["PrefabId"] = prefab_id
        if in_group:
            cfg["InGroup"] = in_group
        if group_members:
            cfg["GroupMembers"] = group_members
        for pk, pv in props.items():
            if pk == "TerrainCorners":
                box = _try_box(pv)
                if box:
                    cfg["Box"] = box
                    continue
            cfg[pk] = pv
        if cfg:
            lines.append(f"exo.CreateObj({tile_arg}, {pos}).settings({cfg!r}).pack()")
        else:
            lines.append(f"exo.CreateObj({tile_arg}, {pos}).pack()")

    if global_vars:
        lines.append("")
        lines.append("# --- Global Variables ---")
        for v in global_vars:
            lines.append(f"var_{v['id']} = exovar.Variable({v['id']}, {v['name']!r}, {v['stype']}, {_fmt_nova(v['init'])})")
            lines.append(f"Level.global_variables.append(var_{v['id']})")

    if nova_scripts:
        lines.append("")
        lines.append("# --- ExoScripts & Functions ---")
        used_names = set()
        for idx, sc in enumerate(nova_scripts):
            base = _safe_ident(sc["name"], f"script_{idx+1}")
            sv = base if base not in used_names else f"{base}_{idx+1}"
            used_names.add(sv)
            c_args = [repr(sc["name"])]
            if sc["is_fn"]:
                c_args.append("is_function=True")
            if sc["act_cnt"] != 0:
                c_args.append(f"activation_count={sc['act_cnt']!r}")
            cond_s = _fmt_nova(sc["cond"])
            if cond_s != "True":
                c_args.append(f"condition={cond_s}")
            lines.append(f"{sv} = exoscript.create({', '.join(c_args)})")
            if sc["is_fn"]:
                lines.append(f"{sv}.script_id = {sc['id']}")
            for act_t, act_p in sc["activators"]:
                p_args = ", ".join(_fmt_nova(p) for p in act_p)
                lines.append(f"{sv}.on({act_t}{', ' + p_args if p_args else ''})")
            for p in sc["params"]:
                lines.append(f"{sv}.parameters.append(exovar.Parameter({p['id']}, {p['name']!r}, {p['stype']}, {_fmt_nova(p['init'])}))")
            for lv in sc["vars"]:
                lines.append(f"{sv}.variables.append(exovar.Variable({lv['id']}, {lv['name']!r}, {lv['stype']}, {_fmt_nova(lv['init'])}))")
            lines.extend(_emit_actions(sc["actions"], sv))
            lines.append(f"{sv}.pack()")
            lines.append("")

    key_hash = exopy_meta.get("key_hash", "") if exopy_meta else ""
    owner_unlocked = is_obf and _check_owner_key(uid, key_hash)
    obf_arg = ", obfuscate=True" if is_obf else ""
    lines.append(f"Level.export('{base_name}_rebuilt.exolvl'{obf_arg})")
    code = "\n".join(lines) + "\n"
    if is_obf and not owner_unlocked:
        code = _pack_obfuscated_py(code, uid)

    with open(out_py, "w", encoding="utf-8") as f:
        f.write(code)

    gen = _state.generator_mode if generator_mode is None else bool(generator_mode)
    result = {
        "ok": tail_note is None,
        "path": out_py,
        "name": name,
        "uuid": uid,
        "counts": {
            "objects": len(objects),
            "scripts": len(nova_scripts),
            "variables": len(global_vars),
            "prefabs": len(prefabs),
            "brushes": len(brushes),
            "patterns": len(patterns),
        },
        "code": code,
    }
    if include_meta:
        result["obfuscated"] = is_obf
        result["unlocked"] = owner_unlocked if is_obf else True
        result["watermark"] = exopy_meta.get("watermark") if exopy_meta else None
    if tail_note:
        result["warning"] = tail_note
    if gen:
        return result
    return code


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    decompile(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
