import copy
import gzip
from typing import Dict, Optional, Tuple
from . import _state
from .binary import BinaryReader
from .constants import DynamicType
from .decompile import _read_script, _read_var, read_exopy_meta
from .errors import WrongMagicError
from .scripts import Action, Activator, CallParameter, FunctionCall, Script
from .types_ext import (
    Brush, BrushGrid, LegacyTileLayers, LocalLevel,
    Pattern, Prefab, RawObject,
)
from .variables import NovaValue, Parameter, Variable


def _remap_nova_dict(nv: dict, maps: dict) -> NovaValue:
    dt = nv["dt"]
    int_val = nv["i"]
    int_list = list(nv["il"]) if nv["il"] is not None else None
    subs = [_remap_nova_dict(s, maps) for s in nv["sub"]] if nv["sub"] is not None else None

    if dt == DynamicType.ObjectConstant and int_val in maps["entity"]:
        int_val = maps["entity"][int_val]
    elif dt == DynamicType.ObjectSetConstant and int_list is not None:
        int_list = [maps["entity"].get(eid, eid) for eid in int_list]
    elif dt == DynamicType.PrefabConstant and int_val in maps["prefab"]:
        int_val = maps["prefab"][int_val]
    elif dt in (
        DynamicType.BoolVariable, DynamicType.IntVariable, DynamicType.FloatVariable,
        DynamicType.StringVariable, DynamicType.ColorVariable, DynamicType.VectorVariable,
        DynamicType.SoundVariable, DynamicType.MusicVariable, DynamicType.ObjectVariable,
        DynamicType.ObjectSetVariable, DynamicType.TransitionVariable, DynamicType.EasingVariable,
        DynamicType.SpriteVariable, DynamicType.ScriptVariable, DynamicType.LayerVariable,
    ) and int_val in maps["var"]:
        int_val = maps["var"][int_val]
    elif dt in (
        DynamicType.BoolParameter, DynamicType.IntParameter, DynamicType.FloatParameter,
        DynamicType.StringParameter, DynamicType.ColorParameter, DynamicType.VectorParameter,
        DynamicType.SoundParameter, DynamicType.MusicParameter, DynamicType.ObjectParameter,
        DynamicType.ObjectSetParameter, DynamicType.TransitionParameter, DynamicType.EasingParameter,
        DynamicType.SpriteParameter, DynamicType.ScriptParameter, DynamicType.LayerParameter,
    ) and int_val in maps["param"]:
        int_val = maps["param"][int_val]
    elif dt == DynamicType.ScriptConstant and int_val in maps["script"]:
        int_val = maps["script"][int_val]
    elif dt == DynamicType.LayerConstant and int_val in maps["layer"]:
        int_val = maps["layer"][int_val]

    return NovaValue(
        dt,
        bool_value=nv["b"],
        int_value=int_val,
        float_value=nv["f"],
        string_value=nv["s"],
        color_value=nv["c"],
        vector_value=nv["v"],
        int_list_value=int_list,
        sub_values=subs,
        unknown5=nv.get("u5", b"\x00"),
        unknown6=nv.get("u6", b"\x00\x00\x00\x00"),
    )


def _rebuild_action(act: dict, maps: dict) -> Action:
    aid = act["aid"]
    closed = act["closed"]
    wait = act["wait"]
    rn = lambda x: _remap_nova_dict(x, maps)

    if aid == 0:
        sub_acts = [_rebuild_action(a, maps) for a in act["actions"]]
        cnt = rn(act["count"])
        return Action(aid, lambda w, ver: (w.write_vec(sub_acts, lambda x: x._write_to(w, ver)), cnt._write_to(w, ver)), wait=wait, closed=closed)
    if aid == 1:
        sub_acts = [_rebuild_action(a, maps) for a in act["actions"]]
        cond = rn(act["condition"])
        return Action(aid, lambda w, ver: (w.write_vec(sub_acts, lambda x: x._write_to(w, ver)), cond._write_to(w, ver)), wait=wait, closed=closed)
    if aid == 2:
        if_acts = [_rebuild_action(a, maps) for a in act["if_actions"]]
        else_acts = [_rebuild_action(a, maps) for a in act["else_actions"]]
        cond = rn(act["condition"])
        return Action(aid, lambda w, ver: (
            w.write_vec(if_acts, lambda x: x._write_to(w, ver)),
            w.write_vec(else_acts, lambda x: x._write_to(w, ver)),
            cond._write_to(w, ver),
        ), wait=wait, closed=closed)
    if aid == 9:
        vid = maps["var"].get(act["var_id"], act["var_id"])
        val = rn(act["value"]) if act["value"] is not None else None
        return Action(aid, lambda w, ver: (w.write_i32(vid), w.write_option(val, lambda v: v._write_to(w, ver))), wait=wait, closed=closed)
    if aid == 10:
        vid = maps["var"].get(act["var_id"], act["var_id"])
        return Action(aid, lambda w, ver: w.write_i32(vid), wait=wait, closed=closed)
    if aid == 47:
        fid = maps["script"].get(act["fn_id"], act["fn_id"])
        cparams = [CallParameter(maps["param"].get(pid, pid), rn(val)) for pid, val in act["params"]]
        fc = FunctionCall(fid, cparams)
        return Action(aid, lambda w, ver: fc._write_to(w, ver), wait=wait, closed=closed)
    if aid == 48:
        vid = maps["var"].get(act["var_id"], act["var_id"])
        val = rn(act["value"]) if act["value"] is not None else None
        dur = rn(act["duration"])
        eas = rn(act["easing"])
        return Action(aid, lambda w, ver: (w.write_i32(vid), w.write_option(val, lambda v: v._write_to(w, ver)), dur._write_to(w, ver), eas._write_to(w, ver)), wait=wait, closed=closed)
    if aid == 49:
        tgt = rn(act["target"])
        sub_acts = [_rebuild_action(a, maps) for a in act["actions"]]
        def _write_fe(w, ver):
            if ver >= 23:
                w.write_vec(sub_acts, lambda x: x._write_to(w, ver))
                tgt._write_to(w, ver)
            else:
                tgt._write_to(w, ver)
                w.write_vec(sub_acts, lambda x: x._write_to(w, ver))
        return Action(aid, _write_fe, wait=wait, closed=closed)

    fields = [rn(f) for f in act.get("fields", [])]
    return Action(aid, lambda w, ver: [f._write_to(w, ver) for f in fields], wait=wait, closed=closed)


def _parse_raw_level(filepath: str) -> dict:
    with open(filepath, "rb") as f:
        raw = f.read()
    data = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    _, data = read_exopy_meta(data)
    r = BinaryReader(data)
    magic = r.raw(4)
    if magic != b"NYA^":
        raise WrongMagicError(magic)

    local_lvl = LocalLevel.read(r)
    ver = local_lvl.serialization_version
    r.string()
    r.i32()
    r.bool()
    LegacyTileLayers.read(r)

    objects = [RawObject.read(r) for _ in range(r.i32())]
    layers = []
    for _ in range(r.i32()):
        layers.append({
            "layer_id": r.i32(),
            "layer_name": r.string(),
            "selected": r.bool(),
            "invisible": r.bool(),
            "locked": r.bool(),
            "foreground_type": r.i32(),
            "parallax": r.vec2(),
            "fixed_size": r.bool(),
            "children": r.vec(r.i32),
        })

    prefabs = r.vec(lambda: Prefab.read(r))
    brushes = r.vec(lambda: Brush.read(r))
    patterns = r.vec(lambda: Pattern.read(r))
    if ver >= 17:
        r.vec(r.color)

    r.i64()
    r.vec(r.i64)
    r.i64()
    r.i64()
    r.i32()
    r.bool()
    r.vec(r.i32)
    if ver >= 19:
        r.raw(4)
    nova_scripts = r.vec(lambda: _read_script(r, ver))
    if ver >= 23:
        r.raw(4)
    global_vars = r.vec(lambda: _read_var(r, ver, is_param=False))

    return {
        "objects": objects,
        "layers": layers,
        "prefabs": prefabs,
        "brushes": brushes,
        "patterns": patterns,
        "nova_scripts": nova_scripts,
        "global_variables": global_vars,
    }


def merge_level(
    filepath: str,
    offset: Tuple[float, float] = (0.0, 0.0),
    *,
    layer_prefix: str = "",
    merge_layers: bool = True,
    merge_scripts: bool = True,
    tag_filter: Optional[str] = None,
) -> dict:
    from . import GameObject, Layer

    lvl = _state.get_level()
    src = _parse_raw_level(filepath)
    ox, oy = float(offset[0]), float(offset[1])

    maps: Dict[str, Dict[int, int]] = {
        "entity": {},
        "layer": {},
        "pattern": {},
        "prefab": {},
        "var": {},
        "param": {},
        "script": {},
    }

    if merge_layers:
        for linfo in src["layers"]:
            old_lid = linfo["layer_id"]
            if old_lid == 1 and not layer_prefix:
                maps["layer"][1] = lvl.layers[0].layer_id
                continue
            new_lid = lvl._next_layer_id()
            maps["layer"][old_lid] = new_lid
            lname = f"{layer_prefix}{linfo['layer_name']}" if layer_prefix else linfo["layer_name"]
            new_layer = Layer(new_lid, lname, linfo["foreground_type"], linfo["parallax"])
            new_layer.selected = linfo["selected"]
            new_layer.invisible = linfo["invisible"]
            new_layer.locked = linfo["locked"]
            new_layer.fixed_size = linfo["fixed_size"]
            lvl.layers.append(new_layer)
    else:
        for linfo in src["layers"]:
            maps["layer"][linfo["layer_id"]] = lvl.layers[0].layer_id

    for pat in src["patterns"]:
        new_pid = lvl._next_pattern_id()
        maps["pattern"][pat.pattern_id] = new_pid
        lvl.patterns.append(Pattern(pattern_id=new_pid, pattern_frames=list(pat.pattern_frames)))

    selected_objs = [
        o for o in src["objects"]
        if o.tag != "__EXOPY_META__" and (tag_filter is None or o.tag == tag_filter)
    ]
    for obj in selected_objs:
        maps["entity"][obj.entity_id] = lvl._next_entity_id()

    for pf in src["prefabs"]:
        new_pf_id = lvl._next_prefab_id()
        maps["prefab"][pf.prefab_id] = new_pf_id
        remapped_items = []
        for item in pf.items:
            it_copy = copy.deepcopy(item)
            it_copy.entity_id = maps["entity"].get(item.entity_id, lvl._next_entity_id())
            it_copy.prefab_id = new_pf_id
            it_copy.in_layer = maps["layer"].get(item.in_layer, lvl.layers[0].layer_id)
            remapped_items.append(it_copy)
        lvl.prefabs.append(Prefab(prefab_id=new_pf_id, prefab_image_data=pf.prefab_image_data, items=remapped_items))

    created_objects = []
    for raw_obj in selected_objs:
        gobj = GameObject(raw_obj.tile_id, (raw_obj.position[0] + ox, raw_obj.position[1] + oy), lvl)
        gobj.entity_id = maps["entity"][raw_obj.entity_id]
        lvl._eid -= 1
        gobj.prefab_entity_id = maps["entity"].get(raw_obj.prefab_entity_id, raw_obj.prefab_entity_id)
        gobj.prefab_id = maps["prefab"].get(raw_obj.prefab_id, raw_obj.prefab_id)
        gobj.scale = raw_obj.scale
        gobj.rotation = raw_obj.rotation
        gobj.tag = raw_obj.tag
        gobj.layer = maps["layer"].get(raw_obj.in_layer, lvl.layers[0].layer_id)
        gobj.in_group = maps["entity"].get(raw_obj.in_group, raw_obj.in_group)
        gobj.group_members = [maps["entity"].get(m, m) for m in raw_obj.group_members]

        for pname, pval in raw_obj.properties:
            if pname == "Pattern" and isinstance(pval, int) and pval in maps["pattern"]:
                gobj.properties[pname] = maps["pattern"][pval]
            elif pname == "LinkedObjects" and isinstance(pval, list):
                gobj.properties[pname] = [maps["entity"].get(eid, eid) for eid in pval]
            else:
                gobj.properties[pname] = copy.deepcopy(pval)

        gobj.pack()
        created_objects.append(gobj)

    for br in src["brushes"]:
        new_bid = lvl._next_brush_id()
        b_objs = []
        for bo in br.objects:
            bo_copy = copy.deepcopy(bo)
            bo_copy.entity_id = maps["entity"].get(bo.entity_id, bo.entity_id)
            b_objs.append(bo_copy)
        lvl.brushes.append(Brush(
            brush_id=new_bid,
            spread=br.spread,
            frequency=br.frequency,
            grid=BrushGrid(br.grid.x, br.grid.y),
            objects=b_objs,
        ))

    created_scripts = []
    if merge_scripts:
        for gv in src["global_variables"]:
            new_vid = lvl._next_var_id()
            maps["var"][gv["id"]] = new_vid
            init_nv = _remap_nova_dict(gv["init"], maps)
            lvl.global_variables.append(Variable(new_vid, gv["name"], gv["stype"], init_nv, unknown4=gv.get("u4", b"\x00\x00\x00\x00")))

        for sc in src["nova_scripts"]:
            maps["script"][sc["id"]] = lvl._next_script_id()
            for p in sc["params"]:
                maps["param"][p["id"]] = lvl._next_param_id()
            for lv in sc["vars"]:
                maps["var"][lv["id"]] = lvl._next_var_id()

        for sc in src["nova_scripts"]:
            new_sc = Script(
                sc["name"],
                is_function=sc["is_fn"],
                activation_count=sc["act_cnt"],
                condition=_remap_nova_dict(sc["cond"], maps),
            )
            new_sc.script_id = maps["script"][sc["id"]]
            lvl._sid -= 1

            for act_t, act_p in sc["activators"]:
                new_sc.activation_list.append(Activator(act_t, [_remap_nova_dict(p, maps) for p in act_p]))
            for p in sc["params"]:
                new_sc.parameters.append(
                    Parameter(maps["param"][p["id"]], p["name"], p["stype"], _remap_nova_dict(p["init"], maps))
                )
            for lv in sc["vars"]:
                new_sc.variables.append(
                    Variable(maps["var"][lv["id"]], lv["name"], lv["stype"], _remap_nova_dict(lv["init"], maps), unknown4=lv.get("u4", b"\x00\x00\x00\x00"))
                )
            new_sc.actions = [_rebuild_action(a, maps) for a in sc["actions"]]
            new_sc.pack()
            created_scripts.append(new_sc)

    return {
        "objects": created_objects,
        "scripts": created_scripts,
        "id_maps": maps,
    }


def extract_prefab(filepath: str, tag: Optional[str] = None, preview_image=None) -> Prefab:
    from . import CreatePrefab

    src = _parse_raw_level(filepath)
    items = [
        o for o in src["objects"]
        if o.tag != "__EXOPY_META__" and (tag is None or o.tag == tag)
    ]
    if not items:
        raise ValueError(f"No matching objects found in {filepath!r} (tag={tag!r})")
    return CreatePrefab(items, preview_image=preview_image)
