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
                 string_value=None, color_value=(0.0, 0.0, 0.0, 0.0), vector_value=(0.0, 0.0),
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
        return (56 <= self.dynamic_type <= 93) or self.dynamic_type in (
            145, 167, 191, 192, 193, 194, DynamicType.FloatParameter
        )

    def _is_s(self):
        return self.dynamic_type in (
            DynamicType.StringConstant, DynamicType.StringVariable,
            DynamicType.StringFromInt, DynamicType.StringFromFloat,
            DynamicType.StringConcat, DynamicType.StringParameter,
            DynamicType.StringObjectTag, DynamicType.StringSubstring,
        )

    def _is_v(self):
        return (103 <= self.dynamic_type <= 118) or self.dynamic_type in (
            168, 169, 170, 171, 173, 180, 186, 187, DynamicType.VectorParameter
        )

    def __add__(self, o):
        o = as_nova(o)
        if self._is_s() or o._is_s():
            return NovaValue.expr(DynamicType.StringConcat, self, o)
        if self._is_v() or o._is_v():
            return NovaValue.expr(DynamicType.VectorAdd, self, o)
        return NovaValue.expr(DynamicType.FloatAdd if (self._is_f() or o._is_f()) else DynamicType.IntAdd, self, o)

    def __sub__(self, o):
        o = as_nova(o)
        if self._is_v() or o._is_v():
            return NovaValue.expr(DynamicType.VectorSubtract, self, o)
        return NovaValue.expr(DynamicType.FloatSubtract if (self._is_f() or o._is_f()) else DynamicType.IntSubtract, self, o)

    def __mul__(self, o):
        o = as_nova(o)
        if self._is_v():
            return NovaValue.expr(DynamicType.VectorMultiply, self, as_float_nova(o))
        return NovaValue.expr(DynamicType.FloatMultiply if (self._is_f() or o._is_f()) else DynamicType.IntMultiply, self, o)

    def __truediv__(self, o):
        o = as_nova(o)
        if self._is_v():
            return NovaValue.expr(DynamicType.VectorDivide, self, as_float_nova(o))
        return NovaValue.expr(DynamicType.FloatDivide if (self._is_f() or o._is_f()) else DynamicType.IntDivide, self, o)

    def __mod__(self, o):
        o = as_nova(o)
        return NovaValue.expr(DynamicType.FloatModulo if (self._is_f() or o._is_f()) else DynamicType.IntModulo, self, o)

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
    def __mod__(self, o): return self.ref() % o
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
        w.write_i32(self.variable_id)
        w.write_str(self.name)
        w.write_i32(self.static_type)
        self.initial_value._write_to(w)


class Parameter(_ExprMixin):
    def __init__(self, pid, name, stype, default_val):
        self.parameter_id, self.name, self.static_type = int(pid), str(name), int(stype)
        self.default_value = as_typed_nova(default_val, self.static_type)

    def ref(self):
        return NovaValue(_STATIC_TO_PARAM_DYNAMIC[self.static_type], int_value=self.parameter_id)

    def _write_to(self, w: BinaryWriter):
        w.write_i32(self.parameter_id)
        w.write_str(self.name)
        w.write_i32(self.static_type)
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
    if hasattr(val, "layer_id"): return NovaValue.layer(val)
    if hasattr(val, "script_id"): return NovaValue.script(val)
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
    if is_global:
        lvl.global_variables.append(v)
    return v


def Bool(name, value=False, *, is_global=True): return _reg(name, StaticType.Bool, NovaValue.bool(value), is_global)
def Int(name, value=0, *, is_global=True): return _reg(name, StaticType.Int, NovaValue.int(value), is_global)
def Float(name, value=0.0, *, is_global=True): return _reg(name, StaticType.Float, NovaValue.float(value), is_global)
def String(name, value="", *, is_global=True): return _reg(name, StaticType.String, NovaValue.string(value), is_global)
def Color(name, value="#FFFFFF", *, is_global=True): return _reg(name, StaticType.Color, NovaValue.color(value), is_global)
def Vector(name, value=(0.0, 0.0), *, is_global=True): return _reg(name, StaticType.Vector, NovaValue.vector(value), is_global)
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


# --- Player & Input Queries ---
def player(): return NovaValue(DynamicType.ObjectPlayer)
def players(): return NovaValue(DynamicType.ObjectSetPlayers)
def player_on_ground(): return NovaValue(DynamicType.BoolPlayerOnGround)
def player_on_walljump(): return NovaValue(DynamicType.BoolPlayerOnWalljump)
def player_on_booster(): return NovaValue(DynamicType.BoolPlayerOnBooster)
def player_on_swing(): return NovaValue(DynamicType.BoolPlayerOnSwing)
def player_in_floating_zone(): return NovaValue(DynamicType.BoolPlayerInFloatingZone)
def player_using_glider(): return NovaValue(DynamicType.BoolPlayerUsingGlider)
def player_jump_locked(): return NovaValue(DynamicType.BoolPlayerJumpLocked)

def input_pressed(): return NovaValue(DynamicType.BoolInputPressed)
def input_pressed_left(): return NovaValue(DynamicType.BoolInputPressedLeft)
def input_pressed_right(): return NovaValue(DynamicType.BoolInputPressedRight)
def input_held(): return NovaValue(DynamicType.BoolInputHeld)
def input_held_left(): return NovaValue(DynamicType.BoolInputHeldLeft)
def input_held_right(): return NovaValue(DynamicType.BoolInputHeldRight)
def input_released(): return NovaValue(DynamicType.BoolInputReleased)
def input_released_left(): return NovaValue(DynamicType.BoolInputReleasedLeft)
def input_released_right(): return NovaValue(DynamicType.BoolInputReleasedRight)

def pointer_pos(): return NovaValue(DynamicType.VectorPointerPosition)
def pointer_world_pos(): return NovaValue(DynamicType.VectorPointerWorldPosition)
def pointer_down(): return NovaValue(DynamicType.BoolPointerDown)
def pointer_held(): return NovaValue(DynamicType.BoolPointerHeld)
def pointer_released(): return NovaValue(DynamicType.BoolPointerReleased)


# --- Object & ObjectSet Queries ---
def tag(name): return NovaValue.expr(DynamicType.ObjectSetObjectsWithTag, NovaValue.string(name))
def all_objects(): return NovaValue(DynamicType.ObjectSetAllObjects)
def objects_in_layer(layer): return NovaValue.expr(DynamicType.ObjectSetObjectsInLayer, layer)
def objects_in_circle(center, radius): return NovaValue.expr(DynamicType.ObjectSetObjectsInCircle, center, as_float_nova(radius))
def set_concat(a, b): return NovaValue.expr(DynamicType.ObjectSetConcat, as_object_set(a), as_object_set(b))
def set_union(a, b): return NovaValue.expr(DynamicType.ObjectSetUnion, as_object_set(a), as_object_set(b))
def set_intersection(a, b): return NovaValue.expr(DynamicType.ObjectSetIntersection, as_object_set(a), as_object_set(b))
def set_difference(a, b): return NovaValue.expr(DynamicType.ObjectSetDifference, as_object_set(a), as_object_set(b))
def set_remove_at(s, index): return NovaValue.expr(DynamicType.ObjectSetRemoveAtIndex, as_object_set(s), index)
def set_count(s): return NovaValue.expr(DynamicType.IntObjectSetCount, as_object_set(s))
def set_children(obj): return NovaValue.expr(DynamicType.ObjectSetChildren, obj)

def any_object(s): return NovaValue.expr(DynamicType.ObjectAnyObject, as_object_set(s))
def first_from_set(s): return NovaValue.expr(DynamicType.ObjectFirstFromSet, as_object_set(s))
def random_from_set(s): return NovaValue.expr(DynamicType.ObjectRandomFromSet, as_object_set(s))
def element_from_set(s, index): return NovaValue.expr(DynamicType.ObjectElementFromSet, as_object_set(s), index)
def source_object(): return NovaValue(DynamicType.ObjectSourceObject)
def collided_object(): return NovaValue(DynamicType.ObjectCollidedObject)
def target_object(): return NovaValue(DynamicType.ObjectTargetObject)
def repeat_object(): return NovaValue(DynamicType.ObjectRepeatObject)
def parent_object(obj): return NovaValue.expr(DynamicType.ObjectParent, obj)

def obj_pos(obj): return NovaValue.expr(DynamicType.VectorObjectPos, obj)
def obj_global_pos(obj): return NovaValue.expr(DynamicType.VectorObjectGlobalPos, obj)
def obj_scale(obj): return NovaValue.expr(DynamicType.VectorObjectScale, obj)
def obj_global_scale(obj): return NovaValue.expr(DynamicType.VectorObjectGlobalScale, obj)
def obj_velocity(obj): return NovaValue.expr(DynamicType.VectorObjectVelocity, obj)
def obj_rotation(obj): return NovaValue.expr(DynamicType.FloatObjectRotation, obj)
def obj_global_rotation(obj): return NovaValue.expr(DynamicType.FloatObjectGlobalRotation, obj)
def obj_direction(obj): return NovaValue.expr(DynamicType.IntObjectDirection, obj)
def obj_color(obj): return NovaValue.expr(DynamicType.ColorObjectColor, obj)
def obj_tag(obj): return NovaValue.expr(DynamicType.StringObjectTag, obj)
def obj_dead(obj): return NovaValue.expr(DynamicType.BoolObjectDead, obj)
def obj_activated(obj): return NovaValue.expr(DynamicType.BoolObjectActivated, obj)
def objects_colliding(a, b): return NovaValue.expr(DynamicType.BoolObjectsColliding, a, b)
def colliding_with_point(obj, point): return NovaValue.expr(DynamicType.BoolObjectsCollidingWithPoint, obj, point)
def collision_point(a, b): return NovaValue.expr(DynamicType.VectorCollisionPoint, a, b)
def collision_normal(a, b): return NovaValue.expr(DynamicType.VectorCollisionNormal, a, b)
def closest_from_point(s, point): return NovaValue.expr(DynamicType.VectorClosestFromPoint, as_object_set(s), point)


# --- Math, Trigonometry & Vectors ---
def abs_(x):
    nx = as_nova(x)
    return NovaValue.expr(DynamicType.FloatAbs if nx._is_f() else DynamicType.IntAbs, nx)

def sign(x):
    nx = as_nova(x)
    return NovaValue.expr(DynamicType.FloatSign if nx._is_f() else DynamicType.IntSign, nx)

def min_(a, b):
    na, nb = as_nova(a), as_nova(b)
    return NovaValue.expr(DynamicType.FloatMin if (na._is_f() or nb._is_f()) else DynamicType.IntMin, na, nb)

def max_(a, b):
    na, nb = as_nova(a), as_nova(b)
    return NovaValue.expr(DynamicType.FloatMax if (na._is_f() or nb._is_f()) else DynamicType.IntMax, na, nb)

def round_(x, to_int=False):
    return NovaValue.expr(DynamicType.IntRound if to_int else DynamicType.FloatRound, as_float_nova(x))

def ceil(x, to_int=False):
    return NovaValue.expr(DynamicType.IntCeil if to_int else DynamicType.FloatCeil, as_float_nova(x))

def floor(x, to_int=False):
    return NovaValue.expr(DynamicType.IntFloor if to_int else DynamicType.FloatFloor, as_float_nova(x))

def round_decimals(x, decimals): return NovaValue.expr(DynamicType.FloatRoundDecimals, as_float_nova(x), decimals)
def sin(x): return NovaValue.expr(DynamicType.FloatSin, as_float_nova(x))
def cos(x): return NovaValue.expr(DynamicType.FloatCos, as_float_nova(x))
def tan(x): return NovaValue.expr(DynamicType.FloatTan, as_float_nova(x))
def asin(x): return NovaValue.expr(DynamicType.FloatAsin, as_float_nova(x))
def acos(x): return NovaValue.expr(DynamicType.FloatAcos, as_float_nova(x))
def atan(x): return NovaValue.expr(DynamicType.FloatAtan, as_float_nova(x))
def sqrt(x): return NovaValue.expr(DynamicType.FloatSqrt, as_float_nova(x))
def pow_(base, exp): return NovaValue.expr(DynamicType.FloatPow, as_float_nova(base), as_float_nova(exp))
def random_int(lo, hi): return NovaValue.expr(DynamicType.IntRandom, int(lo), int(hi))
def random_float(lo=0.0, hi=1.0): return NovaValue.expr(DynamicType.FloatRandom, as_float_nova(lo), as_float_nova(hi))

def vec_values(x, y): return NovaValue.expr(DynamicType.VectorValues, as_float_nova(x), as_float_nova(y))
def vec_x(v): return NovaValue.expr(DynamicType.FloatVectorX, v)
def vec_y(v): return NovaValue.expr(DynamicType.FloatVectorY, v)
def vec_length(v): return NovaValue.expr(DynamicType.FloatVectorLength, v)
def vec_length_sqr(v): return NovaValue.expr(DynamicType.FloatVectorLengthSqr, v)
def distance(a, b): return NovaValue.expr(DynamicType.FloatVectorDistance, a, b)
def distance_sqr(a, b): return NovaValue.expr(DynamicType.FloatVectorDistanceSqr, a, b)
def vec_dot(a, b): return NovaValue.expr(DynamicType.FloatVectorDot, a, b)
def vec_angle(v): return NovaValue.expr(DynamicType.FloatVectorAngle, v)
def vec_angle_between(a, b): return NovaValue.expr(DynamicType.FloatVectorAngleBetween, a, b)
def vec_normalize(v): return NovaValue.expr(DynamicType.VectorNormalize, v)
def vec_perpendicular(v): return NovaValue.expr(DynamicType.VectorPerpendicular, v)
def vec_reflect(v, normal): return NovaValue.expr(DynamicType.VectorReflect, v, normal)
def vec_rotate(v, angle): return NovaValue.expr(DynamicType.VectorRotate, v, as_float_nova(angle))


# --- Colors, Strings, Time & Camera ---
def color_values(r, g, b, a=1.0):
    return NovaValue.expr(DynamicType.ColorValues, as_float_nova(r), as_float_nova(g), as_float_nova(b), as_float_nova(a))

def color_r(c): return NovaValue.expr(DynamicType.FloatColorR, c)
def color_g(c): return NovaValue.expr(DynamicType.FloatColorG, c)
def color_b(c): return NovaValue.expr(DynamicType.FloatColorB, c)
def color_a(c): return NovaValue.expr(DynamicType.FloatColorA, c)

def to_str(val):
    nv = as_nova(val)
    return NovaValue.expr(DynamicType.StringFromFloat if nv._is_f() else DynamicType.StringFromInt, nv)

def concat(a, b):
    return NovaValue.expr(
        DynamicType.StringConcat,
        NovaValue.string(a) if isinstance(a, str) else a,
        NovaValue.string(b) if isinstance(b, str) else b,
    )

def substring(s, start, length): return NovaValue.expr(DynamicType.StringSubstring, s, start, length)
def str_length(s): return NovaValue.expr(DynamicType.IntStringLength, s)

def level_time(): return NovaValue(DynamicType.FloatLevelTime)
def world_time(): return NovaValue(DynamicType.FloatTime)
def repeat_count(): return NovaValue(DynamicType.IntRepeatCount)
def damage_amount(): return NovaValue(DynamicType.FloatDamageAmount)
def last_sound_instance(): return NovaValue(DynamicType.IntLastSoundInstance)
def camera_pos(): return NovaValue(DynamicType.VectorCameraPos)
def camera_viewport_size(): return NovaValue(DynamicType.FloatCameraViewportSize)


# --- Boolean Logic & Comparisons ---
def not_(cond): return NovaValue.expr(DynamicType.BoolNot, cond)
def and_(a, b): return NovaValue.expr(DynamicType.BoolAnd, a, b)
def or_(a, b): return NovaValue.expr(DynamicType.BoolOr, a, b)
def eq_bool(a, b): return NovaValue.expr(DynamicType.BoolEqualBool, a, b)
def eq_str(a, b): return NovaValue.expr(DynamicType.BoolEqualString, a, b)
def eq_color(a, b): return NovaValue.expr(DynamicType.BoolEqualColor, a, b)
def eq_vec(a, b): return NovaValue.expr(DynamicType.BoolEqualVector, a, b)
def eq_obj(a, b): return NovaValue.expr(DynamicType.BoolEqualObject, a, b)
def ne_bool(a, b): return NovaValue.expr(DynamicType.BoolNotEqualBool, a, b)
def ne_str(a, b): return NovaValue.expr(DynamicType.BoolNotEqualString, a, b)
def ne_color(a, b): return NovaValue.expr(DynamicType.BoolNotEqualColor, a, b)
def ne_vec(a, b): return NovaValue.expr(DynamicType.BoolNotEqualVector, a, b)
def ne_obj(a, b): return NovaValue.expr(DynamicType.BoolNotEqualObject, a, b)


# --- Raw Fallbacks ---
def value(dynamic_type: int, **kwargs): return NovaValue(dynamic_type, **kwargs)
def object_set(objs): return NovaValue.object_set(objs)
