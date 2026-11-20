from . import _state
from .binary import BinaryWriter, parse_color
from .constants import DynamicType, StaticType

_STATIC_TO_VAR_DYNAMIC = {
    StaticType.Bool: DynamicType.BoolVariable,
    StaticType.Int: DynamicType.IntVariable,
    StaticType.Float: DynamicType.FloatVariable,
    StaticType.String: DynamicType.StringVariable,
    StaticType.Color: DynamicType.ColorVariable,
    StaticType.Vector: DynamicType.VectorVariable,
    StaticType.Sound: DynamicType.SoundVariable,
    StaticType.Music: DynamicType.MusicVariable,
    StaticType.Object: DynamicType.ObjectVariable,
    StaticType.ObjectSet: DynamicType.ObjectSetVariable,
    StaticType.Transition: DynamicType.TransitionVariable,
    StaticType.Easing: DynamicType.EasingVariable,
    StaticType.Sprite: DynamicType.SpriteVariable,
    StaticType.Script: DynamicType.ScriptVariable,
    StaticType.Layer: DynamicType.LayerVariable,
}

_STATIC_TO_PARAM_DYNAMIC = {
    StaticType.Bool: DynamicType.BoolParameter,
    StaticType.Int: DynamicType.IntParameter,
    StaticType.Float: DynamicType.FloatParameter,
    StaticType.String: DynamicType.StringParameter,
    StaticType.Color: DynamicType.ColorParameter,
    StaticType.Vector: DynamicType.VectorParameter,
    StaticType.Sound: DynamicType.SoundParameter,
    StaticType.Music: DynamicType.MusicParameter,
    StaticType.Object: DynamicType.ObjectParameter,
    StaticType.ObjectSet: DynamicType.ObjectSetParameter,
    StaticType.Transition: DynamicType.TransitionParameter,
    StaticType.Easing: DynamicType.EasingParameter,
    StaticType.Sprite: DynamicType.SpriteParameter,
    StaticType.Script: DynamicType.ScriptParameter,
    StaticType.Layer: DynamicType.LayerParameter,
}

class NovaValue:
    def __init__(self, dynamic_type: int, *, bool_value=False, int_value=0, float_value=0.0,
                 string_value=None, color_value=(0.0,0.0,0.0,0.0), vector_value=(0.0,0.0),
                 int_list_value=None, sub_values=None):
        self.dynamic_type = int(dynamic_type)
        self.bool_value = bool(bool_value)
        self.int_value = int(int_value)
        self.float_value = float(float_value)
        self.string_value = string_value
        self.color_value = parse_color(color_value)
        self.vector_value = (float(vector_value[0]), float(vector_value[1]))
        self.int_list_value = list(int_list_value) if int_list_value is not None else None
        self.sub_values = list(sub_values) if sub_values is not None else None

    @classmethod
    def bool(cls, v): return cls(DynamicType.BoolConstant, bool_value=bool(v))
    @classmethod
    def int(cls, v): return cls(DynamicType.IntConstant, int_value=int(v))
    @classmethod
    def float(cls, v): return cls(DynamicType.FloatConstant, float_value=float(v))
    @classmethod
    def string(cls, v): return cls(DynamicType.StringConstant, string_value=str(v))
    @classmethod
    def color(cls, v): return cls(DynamicType.ColorConstant, color_value=v)
    @classmethod
    def vector(cls, v): return cls(DynamicType.VectorConstant, vector_value=v)
    @classmethod
    def easing(cls, v=0): return cls(DynamicType.EasingConstant, int_value=int(v))
    @classmethod
    def transition(cls, v=0): return cls(DynamicType.TransitionConstant, int_value=int(v))
    @classmethod
    def sound(cls, v=""): return cls(DynamicType.SoundConstant, string_value=str(v))
    @classmethod
    def music(cls, v=""): return cls(DynamicType.MusicConstant, string_value=str(v))
    @classmethod
    def sprite(cls, v=""): return cls(DynamicType.SpriteConstant, string_value=str(v))
    @classmethod
    def script(cls, s): return cls(DynamicType.ScriptConstant, int_value=s.script_id if hasattr(s, "script_id") else int(s))
    @classmethod
    def layer(cls, l): return cls(DynamicType.LayerConstant, int_value=l.layer_id if hasattr(l, "layer_id") else int(l))
    @classmethod
    def object(cls, o): return cls(DynamicType.ObjectConstant, int_value=o.entity_id if hasattr(o, "entity_id") else int(o))
    @classmethod
    def object_set(cls, objs): return cls(DynamicType.ObjectSetConstant, int_list_value=[o.entity_id if hasattr(o, "entity_id") else int(o) for o in objs])
    @classmethod
    def expr(cls, dt, *args): return cls(dt, sub_values=[as_nova(a) for a in args])

    def _is_f(self):
        return 56 <= self.dynamic_type <= 93 or self.dynamic_type in (145, DynamicType.FloatParameter)

    def _is_s(self):
        return self.dynamic_type in (
            DynamicType.StringConstant, DynamicType.StringVariable,
            DynamicType.StringFromInt, DynamicType.StringFromFloat,
            DynamicType.StringConcat, DynamicType.StringParameter,
        )

    def __add__(self, o):
        o = as_nova(o)
        if self._is_s() or o._is_s():
            return NovaValue.expr(DynamicType.StringConcat, self, o)
        return NovaValue.expr(DynamicType.FloatAdd if (self._is_f() or o._is_f()) else DynamicType.IntAdd, self, o)
    def __sub__(self, o):
        o = as_nova(o)
        return NovaValue.expr(DynamicType.FloatSubtract if (self._is_f() or o._is_f()) else DynamicType.IntSubtract, self, o)
    def __mul__(self, o):
        o = as_nova(o)
        return NovaValue.expr(DynamicType.FloatMultiply if (self._is_f() or o._is_f()) else DynamicType.IntMultiply, self, o)
    def __truediv__(self, o):
        o = as_nova(o)
        return NovaValue.expr(DynamicType.FloatDivide if (self._is_f() or o._is_f()) else DynamicType.IntDivide, self, o)
    def __lt__(self, o): return NovaValue.expr(DynamicType.BoolLess, self, as_nova(o))
    def __le__(self, o): return NovaValue.expr(DynamicType.BoolLessOrEqual, self, as_nova(o))
    def __gt__(self, o): return NovaValue.expr(DynamicType.BoolGreater, self, as_nova(o))
    def __ge__(self, o): return NovaValue.expr(DynamicType.BoolGreaterOrEqual, self, as_nova(o))
    def eq(self, o): return NovaValue.expr(DynamicType.BoolEqualNumber, self, as_nova(o))
    def ne(self, o): return NovaValue.expr(DynamicType.BoolNotEqualNumber, self, as_nova(o))

    def _write_to(self, w: BinaryWriter):
        w.write_i32(self.dynamic_type)
        w.write_bool(self.bool_value)
        w.write_i32(self.int_value)
        w.write_f32(self.float_value)
        w.write_option(self.string_value, w.write_str)
        w.write_color(self.color_value)
        w.write_vec2(self.vector_value)
        w.write_option(self.int_list_value, lambda lst: w.write_vec(lst, w.write_i32))
        w.write_option(self.sub_values, lambda lst: w.write_vec(lst, lambda v: v._write_to(w)))


class _ExprMixin:
    def __add__(self, o): return self.ref() + o
    def __sub__(self, o): return self.ref() - o
    def __mul__(self, o): return self.ref() * o
    def __truediv__(self, o): return self.ref() / o
    def __lt__(self, o): return self.ref() < o
    def __le__(self, o): return self.ref() <= o
    def __gt__(self, o): return self.ref() > o
    def __ge__(self, o): return self.ref() >= o
    def eq(self, o): return self.ref().eq(o)
    def ne(self, o): return self.ref().ne(o)


class Variable(_ExprMixin):
    def __init__(self, vid, name, stype, init_val):
        self.variable_id, self.name, self.static_type = int(vid), str(name), int(stype)
        self.initial_value = as_typed_nova(init_val, self.static_type)
    def ref(self):
        return NovaValue(_STATIC_TO_VAR_DYNAMIC[self.static_type], int_value=self.variable_id)
    def _write_to(self, w: BinaryWriter):
        w.write_i32(self.variable_id); w.write_str(self.name); w.write_i32(self.static_type)
        self.initial_value._write_to(w)


class Parameter(_ExprMixin):
    def __init__(self, pid, name, stype, default_val):
        self.parameter_id, self.name, self.static_type = int(pid), str(name), int(stype)
        self.default_value = as_typed_nova(default_val, self.static_type)
    def ref(self):
        return NovaValue(_STATIC_TO_PARAM_DYNAMIC[self.static_type], int_value=self.parameter_id)
    def _write_to(self, w: BinaryWriter):
        w.write_i32(self.parameter_id); w.write_str(self.name); w.write_i32(self.static_type)
        self.default_value._write_to(w)


def as_nova(val):
    if isinstance(val, NovaValue): return val
    if isinstance(val, (Variable, Parameter)): return val.ref()
    if isinstance(val, bool): return NovaValue.bool(val)
    if isinstance(val, int): return NovaValue.int(val)
    if isinstance(val, float): return NovaValue.float(val)
    if isinstance(val, str):
        return NovaValue.color(val) if (val.startswith("#") and len(val) in (7, 9)) else NovaValue.string(val)
    if hasattr(val, "entity_id"): return NovaValue.object(val)
    if isinstance(val, (tuple, list)):
        if len(val) == 2 and all(isinstance(x, (int, float)) for x in val): return NovaValue.vector(val)
        if len(val) == 4 and all(isinstance(x, (int, float)) for x in val): return NovaValue.color(val)
        return NovaValue.object_set(val)
    raise TypeError(f"Cannot convert {type(val).__name__} to NovaValue")


def as_float_nova(val):
    if isinstance(val, (NovaValue, Variable, Parameter)):
        return as_nova(val)
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return NovaValue.float(val)
    return as_nova(val)


def as_object_set(target):
    if isinstance(target, (NovaValue, Variable, Parameter)): return as_nova(target)
    if isinstance(target, str): return NovaValue.expr(DynamicType.ObjectSetObjectsWithTag, NovaValue.string(target))
    if hasattr(target, "entity_id"): return NovaValue.object_set([target])
    if isinstance(target, (list, tuple)): return NovaValue.object_set(target)
    raise TypeError(f"Invalid target: {target!r}")


def default_nova_for(stype: int) -> NovaValue:
    return {
        StaticType.Bool: NovaValue.bool(False),
        StaticType.Int: NovaValue.int(0),
        StaticType.Float: NovaValue.float(0.0),
        StaticType.String: NovaValue.string(""),
        StaticType.Color: NovaValue.color("#FFFFFF"),
        StaticType.Vector: NovaValue.vector((0.0, 0.0)),
        StaticType.Sound: NovaValue.sound(""),
        StaticType.Music: NovaValue.music(""),
        StaticType.Object: NovaValue.object(0),
        StaticType.ObjectSet: NovaValue.object_set([]),
        StaticType.Transition: NovaValue.transition(0),
        StaticType.Easing: NovaValue.easing(0),
        StaticType.Sprite: NovaValue.sprite(""),
        StaticType.Script: NovaValue.script(0),
        StaticType.Layer: NovaValue.layer(1),
    }[int(stype)]


def as_typed_nova(val, stype: int) -> NovaValue:
    if isinstance(val, (NovaValue, Variable, Parameter)):
        return as_nova(val)
    st = int(stype)
    if st == StaticType.Bool: return NovaValue.bool(val)
    if st == StaticType.Int: return NovaValue.int(val)
    if st == StaticType.Float: return NovaValue.float(val)
    if st == StaticType.String: return NovaValue.string(val)
    if st == StaticType.Color: return NovaValue.color(val)
    if st == StaticType.Vector: return NovaValue.vector(val)
    if st == StaticType.Sound: return NovaValue.sound(val)
    if st == StaticType.Music: return NovaValue.music(val)
    if st == StaticType.Object: return NovaValue.object(val)
    if st == StaticType.ObjectSet: return as_object_set(val)
    if st == StaticType.Transition: return NovaValue.transition(val)
    if st == StaticType.Easing: return NovaValue.easing(val)
    if st == StaticType.Sprite: return NovaValue.sprite(val)
    if st == StaticType.Script: return NovaValue.script(val)
    if st == StaticType.Layer: return NovaValue.layer(val)
    return as_nova(val)


def _reg(name, st, iv, is_global=True):
    lvl = _state.get_level()
    v = Variable(lvl._next_var_id(), name, st, iv)
    if is_global: lvl.global_variables.append(v)
    return v

def Bool(name, value=False, *, is_global=True): return _reg(name, StaticType.Bool, NovaValue.bool(value), is_global)
def Int(name, value=0, *, is_global=True): return _reg(name, StaticType.Int, NovaValue.int(value), is_global)
def Float(name, value=0.0, *, is_global=True): return _reg(name, StaticType.Float, NovaValue.float(value), is_global)
def String(name, value="", *, is_global=True): return _reg(name, StaticType.String, NovaValue.string(value), is_global)
def Color(name, value="#FFFFFF", *, is_global=True): return _reg(name, StaticType.Color, NovaValue.color(value), is_global)
def Vector(name, value=(0.0,0.0), *, is_global=True): return _reg(name, StaticType.Vector, NovaValue.vector(value), is_global)
def Object(name, obj=0, *, is_global=True): return _reg(name, StaticType.Object, NovaValue.object(obj), is_global)
def ObjectSet(name, objs=(), *, is_global=True): return _reg(name, StaticType.ObjectSet, NovaValue.object_set(objs), is_global)

HINT_TO_STATIC = {
    bool: StaticType.Bool, Bool: StaticType.Bool,
    int: StaticType.Int, Int: StaticType.Int,
    float: StaticType.Float, Float: StaticType.Float,
    str: StaticType.String, String: StaticType.String,
    Color: StaticType.Color,
    Vector: StaticType.Vector,
    Object: StaticType.Object,
    ObjectSet: StaticType.ObjectSet,
}

def resolve_static_type(hint, default=None) -> int:
    if isinstance(hint, int) and 0 <= hint <= 14:
        return hint
    if hint in HINT_TO_STATIC:
        return HINT_TO_STATIC[hint]
    if default is not None:
        if isinstance(default, bool): return StaticType.Bool
        if isinstance(default, int): return StaticType.Int
        if isinstance(default, float): return StaticType.Float
        if isinstance(default, str):
            return StaticType.Color if (default.startswith("#") and len(default) in (7, 9)) else StaticType.String
        if isinstance(default, (tuple, list)) and len(default) == 2: return StaticType.Vector
    raise ValueError(f"Cannot infer StaticType from annotation {hint!r} / default {default!r}")

def return_reg(stype: int) -> Variable:
    lvl = _state.get_level()
    st = int(stype)
    if st not in lvl._return_regs:
        names = {
            StaticType.Bool: "_rv_bool", StaticType.Int: "_rv_int",
            StaticType.Float: "_rv_float", StaticType.String: "_rv_str",
            StaticType.Color: "_rv_color", StaticType.Vector: "_rv_vec",
            StaticType.Object: "_rv_obj", StaticType.ObjectSet: "_rv_set",
        }
        lvl._return_regs[st] = _reg(names.get(st, f"_rv_{st}"), st, default_nova_for(st), is_global=True)
    return lvl._return_regs[st]

def player(): return NovaValue(DynamicType.ObjectPlayer)
def players(): return NovaValue(DynamicType.ObjectSetPlayers)
def tag(name): return NovaValue.expr(DynamicType.ObjectSetObjectsWithTag, NovaValue.string(name))
def obj_pos(obj): return NovaValue.expr(DynamicType.VectorObjectPos, obj)
def obj_global_pos(obj): return NovaValue.expr(DynamicType.VectorObjectGlobalPos, obj)
def pointer_world_pos(): return NovaValue(DynamicType.VectorPointerWorldPosition)
def pointer_down(): return NovaValue(DynamicType.BoolPointerDown)
def pointer_held(): return NovaValue(DynamicType.BoolPointerHeld)
def distance(a, b): return NovaValue.expr(DynamicType.FloatVectorDistance, a, b)
def random_int(lo, hi): return NovaValue.expr(DynamicType.IntRandom, int(lo), int(hi))
def to_str(val): return NovaValue.expr(DynamicType.StringFromInt, val)
def concat(a, b): return NovaValue.expr(DynamicType.StringConcat, NovaValue.string(a) if isinstance(a, str) else a, NovaValue.string(b) if isinstance(b, str) else b)
def not_(cond): return NovaValue.expr(DynamicType.BoolNot, cond)
def and_(a, b): return NovaValue.expr(DynamicType.BoolAnd, a, b)
def or_(a, b): return NovaValue.expr(DynamicType.BoolOr, a, b)


def value(dynamic_type: int, **kwargs):
    return NovaValue(dynamic_type, **kwargs)

def object_set(objs):
    return NovaValue.object_set(objs)
