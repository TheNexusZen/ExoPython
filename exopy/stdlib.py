from . import _state
from . import scripts as exoscript
from . import variables as exovar

def _cached(key: str, builder):
    lvl = _state.get_level()
    if key not in lvl._stdlib_cache:
        lvl._stdlib_cache[key] = builder()
    return lvl._stdlib_cache[key]

def flash():
    def build():
        @exoscript.func(name="std_flash")
        def _fn(target: exovar.ObjectSet, hi_color: exovar.Color = "#FFFFFF", base_color: exovar.Color = "#00F5FF", duration: exovar.Float = 0.15):
            return (
                exoscript.block()
                .set_color(target, hi_color, duration=0.04, wait=True)
                .wait(duration)
                .set_color(target, base_color, duration=0.12, wait=True)
            )
        return _fn
    return _cached("flash", build)

def pulse():
    def build():
        @exoscript.func(name="std_pulse")
        def _fn(target: exovar.ObjectSet, big_scale: exovar.Vector = (1.35, 1.35), duration: exovar.Float = 0.15):
            return (
                exoscript.block()
                .scale(target, big_scale, duration=duration, wait=True)
                .scale(target, (1.0, 1.0), duration=duration, wait=True)
            )
        return _fn
    return _cached("pulse", build)

def glide_between():
    def build():
        @exoscript.func(name="std_glide_between")
        def _fn(target: exovar.ObjectSet, pos_a: exovar.Vector = (0, 0), pos_b: exovar.Vector = (5, 0), duration: exovar.Float = 1.5):
            return (
                exoscript.block()
                .move(target, pos_b, is_global=True, duration=duration, wait=True)
                .move(target, pos_a, is_global=True, duration=duration, wait=True)
            )
        return _fn
    return _cached("glide_between", build)

def banner():
    def build():
        @exoscript.func(name="std_banner")
        def _fn(label: exovar.ObjectSet, message: exovar.String = "HELLO", color: exovar.Color = "#FFE66D"):
            return (
                exoscript.block()
                .set_text(label, message)
                .set_color(label, color, duration=0.1)
                .scale(label, (1.25, 1.25), duration=0.12, wait=True)
                .scale(label, (1.0, 1.0), duration=0.12, wait=True)
            )
        return _fn
    return _cached("banner", build)
