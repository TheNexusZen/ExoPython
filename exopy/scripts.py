import inspect
from . import _state
from .binary import BinaryWriter
from .constants import ActionID, StaticType
from .variables import (
    NovaValue, Variable, Parameter,
    as_nova, as_float_nova, as_object_set, as_typed_nova,
    default_nova_for, resolve_static_type, return_reg,
)


class Activator:
    def __init__(self, activator_type: int, params=()):
        self.activator_type = int(activator_type)
        self.parameters = [as_nova(p) for p in params]

    def _write_to(self, w: BinaryWriter):
        w.write_i32(self.activator_type)
        w.write_vec(self.parameters, lambda p: p._write_to(w))


class Action:
    def __init__(self, action_id: int, writer_fn, *, wait=False, closed=False):
        self.action_id, self.writer_fn, self.wait, self.closed = int(action_id), writer_fn, bool(wait), bool(closed)

    def _write_to(self, w: BinaryWriter):
        w.write_i32(self.action_id)
        w.write_bool(self.closed)
        w.write_bool(self.wait)
        self.writer_fn(w)


class CallParameter:
    def __init__(self, parameter_id: int, value: NovaValue):
        self.parameter_id = int(parameter_id)
        self.value = value

    def _write_to(self, w: BinaryWriter):
        w.write_i32(self.parameter_id)
        self.value._write_to(w)


class FunctionCall:
    def __init__(self, script_id: int, parameters):
        self.script_id = int(script_id)
        self.parameters = list(parameters)

    def _write_to(self, w: BinaryWriter):
        w.write_i32(self.script_id)
        w.write_vec(self.parameters, lambda p: p._write_to(w))


def _unwrap(acts):
    if acts is None:
        return []
    return acts.actions if hasattr(acts, "actions") else list(acts)


class _ActionBuilder:
    def __init__(self):
        self.actions = []

    def _push(self, aid, fn, wait=False):
        self.actions.append(Action(aid, fn, wait=wait))
        return self

    def wait(self, duration):
        d = as_float_nova(duration)
        return self._push(ActionID.Wait, lambda w: d._write_to(w), wait=True)

    def wait_frames(self, frames):
        f = as_nova(frames)
        return self._push(ActionID.WaitFrames, lambda w: f._write_to(w), wait=True)

    def repeat(self, count, body, *, wait=True):
        c, acts = as_nova(count), _unwrap(body)
        return self._push(ActionID.Repeat, lambda w: (w.write_vec(acts, lambda a: a._write_to(w)), c._write_to(w)), wait=wait)

    def repeat_while(self, condition, body, *, wait=True):
        cond, acts = as_nova(condition), _unwrap(body)
        return self._push(ActionID.RepeatWhile, lambda w: (w.write_vec(acts, lambda a: a._write_to(w)), cond._write_to(w)), wait=wait)

    def if_else(self, condition, if_body, else_body=None, *, wait=True):
        cond, ifa, elsa = as_nova(condition), _unwrap(if_body), _unwrap(else_body)
        return self._push(ActionID.ConditionBlock, lambda w: (
            w.write_vec(ifa, lambda a: a._write_to(w)),
            w.write_vec(elsa, lambda a: a._write_to(w)),
            cond._write_to(w),
        ), wait=wait)

    def move(self, target, pos, *, is_global=True, duration=0.0, easing=0, wait=False):
        vals = (as_object_set(target), as_nova(pos), as_nova(bool(is_global)), as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.Move, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def scale(self, target, sc, *, duration=0.0, easing=0, wait=False):
        vals = (as_object_set(target), as_nova(sc), as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.Scale, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def rotate(self, target, rot, *, shortest_path=True, is_global=False, duration=0.0, easing=0, wait=False):
        vals = (as_object_set(target), as_float_nova(rot), as_nova(bool(shortest_path)), as_nova(bool(is_global)), as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.Rotate, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def rotate_around(self, target, pivot, rotation, *, rotate_target=True, duration=0.0, easing=0, wait=False):
        vals = (as_object_set(target), as_nova(pivot), as_float_nova(rotation), as_nova(bool(rotate_target)), as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.RotateAround, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def set_var(self, var, value):
        vid = var.variable_id if isinstance(var, Variable) else int(var)
        val = as_nova(value) if value is not None else None
        return self._push(ActionID.SetVariable, lambda w: (w.write_i32(vid), w.write_option(val, lambda v: v._write_to(w))))

    def reset_var(self, var):
        vid = var.variable_id if isinstance(var, Variable) else int(var)
        return self._push(ActionID.ResetVariable, lambda w: w.write_i32(vid))

    def reset_object(self, target):
        t = as_object_set(target)
        return self._push(ActionID.ResetObject, lambda w: t._write_to(w))

    def set_color(self, target, color, *, channel=0, duration=0.0, easing=0, wait=False):
        col = as_nova(color) if isinstance(color, (NovaValue, Variable, Parameter)) else NovaValue.color(color)
        vals = (as_object_set(target), col, NovaValue.int(channel), as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.SetColor, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def set_transparency(self, target, transparency, *, channel=0, duration=0.0, easing=0, wait=False):
        vals = (as_object_set(target), as_float_nova(transparency), NovaValue.int(channel), as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.SetTransparency, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def set_secondary_color(self, target, color, *, duration=0.0, easing=0, wait=False):
        col = as_nova(color) if isinstance(color, (NovaValue, Variable, Parameter)) else NovaValue.color(color)
        vals = (as_object_set(target), col, as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.SetSecondaryColor, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def set_secondary_transparency(self, target, transparency, *, duration=0.0, easing=0, wait=False):
        vals = (as_object_set(target), as_float_nova(transparency), as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.SetSecondaryTransparency, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def set_border_color(self, target, color, *, duration=0.0, easing=0, wait=False):
        col = as_nova(color) if isinstance(color, (NovaValue, Variable, Parameter)) else NovaValue.color(color)
        vals = (as_object_set(target), col, as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.SetBorderColor, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def set_border_transparency(self, target, transparency, *, duration=0.0, easing=0, wait=False):
        vals = (as_object_set(target), as_float_nova(transparency), as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.SetBorderTransparency, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def set_sprite(self, target, sprite):
        sp = as_nova(sprite) if isinstance(sprite, (NovaValue, Variable, Parameter)) else NovaValue.sprite(sprite)
        t = as_object_set(target)
        return self._push(ActionID.SetSprite, lambda w: (t._write_to(w), sp._write_to(w)))

    def set_text(self, target, text):
        t = as_object_set(target)
        txt = as_nova(text) if isinstance(text, (NovaValue, Variable, Parameter)) else NovaValue.string(text)
        return self._push(ActionID.SetText, lambda w: (t._write_to(w), txt._write_to(w)))

    def set_enabled(self, target, enabled):
        t, en = as_object_set(target), as_nova(enabled)
        return self._push(ActionID.SetEnabled, lambda w: (t._write_to(w), en._write_to(w)))

    def activate(self, target):
        t = as_object_set(target)
        return self._push(ActionID.Activate, lambda w: t._write_to(w))

    def deactivate(self, target):
        t = as_object_set(target)
        return self._push(ActionID.Deactivate, lambda w: t._write_to(w))

    def damage(self, target, amount):
        t, dmg = as_object_set(target), as_float_nova(amount)
        return self._push(ActionID.Damage, lambda w: (t._write_to(w), dmg._write_to(w)))

    def kill(self, target):
        t = as_object_set(target)
        return self._push(ActionID.Kill, lambda w: t._write_to(w))

    def game_finish(self):
        return self._push(ActionID.GameFinish, lambda w: None)

    def camera_pan(self, pos, *, duration=0.0, easing=0, wait=False):
        vals = (as_nova(pos), as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.CameraPan, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def camera_follow_player(self):
        return self._push(ActionID.CameraFollowPlayer, lambda w: None)

    def camera_zoom(self, viewport_size, *, duration=0.0, easing=0, wait=False):
        vals = (as_float_nova(viewport_size), as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.CameraZoom, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def camera_zoom_reset(self, *, duration=0.0, easing=0, wait=False):
        vals = (as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.CameraZoomReset, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def camera_offset(self, offset, *, duration=0.0, easing=0, wait=False):
        vals = (as_nova(offset), as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.CameraOffset, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def camera_offset_reset(self, *, duration=0.0, easing=0, wait=False):
        vals = (as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.CameraOffsetReset, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def camera_shake(self, strength=0.8, roughness=8.0, fade_in=0.02, fade_out=0.15, duration=0.2, wait=False):
        vals = [as_float_nova(x) for x in (strength, roughness, fade_in, fade_out, duration)]
        return self._push(ActionID.CameraShake, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def play_sound(self, sound, *, volume=1.0, pitch=1.0):
        snd = as_nova(sound) if isinstance(sound, (NovaValue, Variable, Parameter)) else NovaValue.sound(sound)
        vals = (snd, as_float_nova(volume), as_float_nova(pitch))
        return self._push(ActionID.PlaySound, lambda w: [v._write_to(w) for v in vals])

    def play_music(self, music, *, volume=1.0, pitch=1.0):
        mus = as_nova(music) if isinstance(music, (NovaValue, Variable, Parameter)) else NovaValue.music(music)
        vals = (mus, as_float_nova(volume), as_float_nova(pitch))
        return self._push(ActionID.PlayMusic, lambda w: [v._write_to(w) for v in vals])

    def set_direction(self, target, direction):
        t, d = as_object_set(target), as_nova(direction)
        return self._push(ActionID.SetDirection, lambda w: (t._write_to(w), d._write_to(w)))

    def set_gravity(self, target, gravity):
        t, g = as_object_set(target), as_nova(gravity)
        return self._push(ActionID.SetGravity, lambda w: (t._write_to(w), g._write_to(w)))

    def set_velocity(self, target, velocity):
        t, v = as_object_set(target), as_nova(velocity)
        return self._push(ActionID.SetVelocity, lambda w: (t._write_to(w), v._write_to(w)))

    def set_cinematic(self, enabled):
        en = as_nova(enabled)
        return self._push(ActionID.SetCinematic, lambda w: en._write_to(w))

    def set_input_enabled(self, enabled):
        en = as_nova(enabled)
        return self._push(ActionID.SetInputEnabled, lambda w: en._write_to(w))

    def set_timer_enabled(self, enabled):
        en = as_nova(enabled)
        return self._push(ActionID.SetTimerEnabled, lambda w: en._write_to(w))

    def game_text(self, text, duration=2.0, wait=False):
        txt = as_nova(text) if isinstance(text, (NovaValue, Variable, Parameter)) else NovaValue.string(text)
        d = as_float_nova(duration)
        return self._push(ActionID.GameTextShow, lambda w: (txt._write_to(w), d._write_to(w)), wait=wait)

    def dialogue_show(self, text, position=(0.0, 0.0), reverse_direction=False, *, wait=False):
        txt = as_nova(text) if isinstance(text, (NovaValue, Variable, Parameter)) else NovaValue.string(text)
        vals = (txt, as_nova(position), as_nova(bool(reverse_direction)))
        return self._push(ActionID.DialogueShow, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def stop_script(self, script):
        sc = as_nova(script) if isinstance(script, (NovaValue, Variable, Parameter)) else NovaValue.script(script)
        return self._push(ActionID.StopScript, lambda w: sc._write_to(w))

    def transition_in(self, transition_type=0, color="#000000", *, duration=0.5, easing=0, wait=False):
        col = as_nova(color) if isinstance(color, (NovaValue, Variable, Parameter)) else NovaValue.color(color)
        vals = (NovaValue.transition(transition_type), col, as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.TransitionIn, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def transition_out(self, transition_type=0, color="#000000", *, duration=0.5, easing=0, wait=False):
        col = as_nova(color) if isinstance(color, (NovaValue, Variable, Parameter)) else NovaValue.color(color)
        vals = (NovaValue.transition(transition_type), col, as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.TransitionOut, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def time_scale(self, scale, *, duration=0.0, easing=0, wait=False):
        vals = (as_float_nova(scale), as_float_nova(duration), NovaValue.easing(easing))
        return self._push(ActionID.TimeScale, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def set_var_over_time(self, var, value, *, duration=1.0, easing=0, wait=False):
        vid = var.variable_id if isinstance(var, Variable) else int(var)
        val = as_nova(value) if value is not None else None
        dur, eas = as_float_nova(duration), NovaValue.easing(easing)
        return self._push(
            ActionID.SetVariableOverTime,
            lambda w: (w.write_i32(vid), w.write_option(val, lambda v: v._write_to(w)), dur._write_to(w), eas._write_to(w)),
            wait=wait,
        )

    def repeat_for_each(self, target, body, *, wait=True):
        t, acts = as_object_set(target), _unwrap(body)
        return self._push(ActionID.RepeatForEachObject, lambda w: (t._write_to(w), w.write_vec(acts, lambda a: a._write_to(w))), wait=wait)

    def stop_sound(self, sound_instance, *, fade_out=0.0):
        vals = (as_nova(sound_instance), as_float_nova(fade_out))
        return self._push(ActionID.StopSound, lambda w: [v._write_to(w) for v in vals])

    def play_particles(self, target):
        t = as_object_set(target)
        return self._push(ActionID.PlayParticleSystem, lambda w: t._write_to(w))

    def stop_particles(self, target, *, clear=False):
        vals = (as_object_set(target), as_nova(bool(clear)))
        return self._push(ActionID.StopParticleSystem, lambda w: [v._write_to(w) for v in vals])

    def raw_action(self, action_id: int, *fields, wait=False):
        vals = [as_nova(f) for f in fields]
        return self._push(action_id, lambda w: [v._write_to(w) for v in vals], wait=wait)

    def ret(self, value, stype=None):
        if stype is None:
            stype = resolve_static_type(None, value)
        else:
            stype = resolve_static_type(stype)
        reg = return_reg(stype)
        return self.set_var(reg, as_typed_nova(value, stype))

    def call(self, fn, *args, wait=True, **kwargs):
        if not isinstance(fn, Script) or not fn.is_function:
            raise TypeError(f"Expected an @exoscript.func / function Script, got {fn!r}")
        if len(args) > len(fn.parameters):
            raise TypeError(f"{fn.script_name}() takes {len(fn.parameters)} args, got {len(args)}")

        call_params = []
        for idx, p in enumerate(fn.parameters):
            if idx < len(args):
                val = as_typed_nova(args[idx], p.static_type)
            elif p.name in kwargs:
                val = as_typed_nova(kwargs[p.name], p.static_type)
            else:
                val = p.default_value
            call_params.append(CallParameter(p.parameter_id, val))

        fc = FunctionCall(fn.script_id, call_params)
        return self._push(ActionID.RunFunction, lambda w: fc._write_to(w), wait=wait)

    def call_id(self, script_id: int, params=(), *, wait=True):
        fc = FunctionCall(script_id, [CallParameter(pid, as_nova(val)) for pid, val in params])
        return self._push(ActionID.RunFunction, lambda w: fc._write_to(w), wait=wait)


class Script(_ActionBuilder):
    def __init__(self, name: str, *, is_function=False, activation_count=0, condition=True):
        super().__init__()
        lvl = _state.get_level()
        self.script_id = lvl._next_script_id()
        self.script_name = str(name)
        self.is_function = bool(is_function)
        self.activation_count = int(activation_count)
        self.condition = as_nova(condition)
        self.activation_list, self.parameters, self.variables = [], [], []
        self._level = lvl
        self._packed = False

    def on(self, activator_type: int, *params):
        self.activation_list.append(Activator(activator_type, params))
        return self

    def param(self, name: str, stype, default=None) -> Parameter:
        st = resolve_static_type(stype, default)
        dv = default_nova_for(st) if default is None else as_typed_nova(default, st)
        p = Parameter(self._level._next_param_id(), name, st, dv)
        self.parameters.append(p)
        return p

    def local(self, name: str, stype, default=None) -> Variable:
        st = resolve_static_type(stype, default)
        iv = default_nova_for(st) if default is None else as_typed_nova(default, st)
        v = Variable(self._level._next_var_id(), name, st, iv)
        self.variables.append(v)
        return v

    def pack(self):
        if not self._packed:
            self._level.nova_scripts.append(self)
            self._packed = True
        return self

    def _write_to(self, w: BinaryWriter):
        w.write_i32(self.script_id)
        w.write_str(self.script_name)
        w.write_bool(self.is_function)
        w.write_i32(self.activation_count)
        self.condition._write_to(w)
        w.write_vec(self.activation_list, lambda a: a._write_to(w))
        w.write_vec(self.parameters, lambda p: p._write_to(w))
        w.write_vec(self.variables, lambda v: v._write_to(w))
        w.write_vec(self.actions, lambda a: a._write_to(w))


def create(name: str, *, is_function=False, activation_count=0, condition=True) -> Script:
    return Script(name, is_function=is_function, activation_count=activation_count, condition=condition)


def function(name: str) -> Script:
    return Script(name, is_function=True, activation_count=0)


def block() -> _ActionBuilder:
    return _ActionBuilder()


def func(py_fn=None, *, name=None):
    def decorator(f):
        sig = inspect.signature(f)
        fn_script = function(name or f.__name__)
        param_objs = []
        for pname, p in sig.parameters.items():
            hint = None if p.annotation is inspect.Parameter.empty else p.annotation
            default = None if p.default is inspect.Parameter.empty else p.default
            param_objs.append(fn_script.param(pname, hint, default))

        body = f(*param_objs)
        if body is not None:
            fn_script.actions.extend(_unwrap(body))
        return fn_script.pack()

    return decorator(py_fn) if py_fn is not None else decorator
