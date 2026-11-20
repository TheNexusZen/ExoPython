active_level = None
generator_mode = False

def get_level():
    if active_level is None:
        raise RuntimeError("Call exo.init(...) first.")
    return active_level
