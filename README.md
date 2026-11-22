# ExoPython (`exopython`)

Write, decompile, and script Exoracer (`.exolvl`) levels in Python.

## Install

```bash
pip install exopython
# Optional Pillow support for WebP/JPEG image conversion:
pip install "exopython[image]"
```

---

## Make a Level

```python
import exopython as exo

lvl = exo.init("My First Level", bg_type="Mountains", gravity=(0.0, -74.0))

exo.CreateObj("terrain", (0, -2)).settings({"Box": (40, 2)}).pack()
exo.CreateObj("start", (-15, 0)).pack()
exo.CreateObj("finish", (15, 0)).pack()

lvl.export("my_level.exolvl")
```

---

## Add a Script & Reusable Functions

```python
import exopython as exo
from exopython import scripts as exoscript, variables as exovar

lvl = exo.init("Moving Platform")

platform = exo.CreateObj("terrain", (0, 2)).settings({"Box": (6, 1)}).pack()
count = exovar.Int("count", 0)

@exoscript.func
def flash(target: exovar.ObjectSet, color: exovar.Color = "#00F5FF"):
    return exoscript.block().set_color(target, color, duration=0.15, wait=True)

(
    exoscript.create("MoveLoop")
    .on(0)
    .repeat(5, exoscript.block()
        .move(platform, (10, 2), duration=1.0, wait=True)
        .call(flash, [platform], "#FF4D6D", wait=True)
        .move(platform, (0, 2), duration=1.0, wait=True)
        .set_var(count, count + 1)
    )
    .pack()
)

lvl.export("moving_platform.exolvl")
```

---

## Images & Patterns

Convert PNG/WebP/JPEG images into pixel-art tiles or embedded level patterns:

```python
# Pixel-art rect objects at (0, 10)
exo.CreateImage("logo.png", mode="pixel", pos=(0, 10))

# Or embed as a reusable terrain Pattern
pat = exo.CreateImage("tileset.png", mode="pattern")
exo.CreateObj("terrain", (0, -2)).settings({"Box": (20, 4), "Pattern": pat}).pack()
```

---

## Custom Audio / Music Sequencer

Convert an audio file (`.wav`, or `.mp3`/`.ogg` with `ffmpeg`) into native `PlaySound` + pitch-shifted `FloatSemitones` script actions:

```python
import exopython as exo

# Generate copy-paste Python code:
code = exo.audio_to_python("melody.wav", sound_id="blip", polyphony=2, out_py="melody_script.py")

# Or embed directly into the active level:
exo.audio_to_script("melody.wav", sound_id="blip", polyphony=2)
```

---

## Decompile, Inspect & Protect

Turn an existing `.exolvl` back into Python, inspect its binary tree, or lock down scripts:

```python
import exopython as exo

exo.decompile("my_level.exolvl", out_py="my_level.py")
lvl.export("protected.exolvl", obfuscate=True)
```

*(Private unlock keys are saved automatically in `~/.exopy_keys.txt` with owner-only permissions.)*

CLI shortcuts:

```bash
python -m exopy level.exolvl out.py --extract-assets
python -m exopy level.exolvl --inspect
python -m exopy --audio song.wav song_script.py --sound blip --polyphony 2
```

---

## License

MIT
