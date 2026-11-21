# ExoPython (`exopy`)

Write Exoracer levels in Python.

## Install

```bash
pip install exopython
```

---

## Make a Level

```python
import exopy as exo

lvl = exo.init("My First Level", bg_type="Mountains", gravity=(0.0, -74.0))

exo.CreateObj("terrain", (0, -2)).settings({"Box": (40, 2)}).pack()
exo.CreateObj("start", (-15, 0)).pack()
exo.CreateObj("finish", (15, 0)).pack()

lvl.export("my_level.exolvl")
```

Run the script, import the level into Exoracer, and play.

---

## Add a Script

Use `exoscript` for actions and `exovar` for variables:

```python
import exopy as exo
from exopy import scripts as exoscript, variables as exovar

lvl = exo.init("Moving Platform")

platform = exo.CreateObj("terrain", (0, 2)).settings({"Box": (6, 1)}).pack()
count = exovar.Int("count", 0)

(
    exoscript.create("MoveLoop")
    .on(0)
    .repeat(5, exoscript.block()
        .move(platform, (10, 2), duration=1.0, wait=True)
        .move(platform, (0, 2), duration=1.0, wait=True)
        .set_var(count, count + 1)
    )
    .pack()
)

lvl.export("moving_platform.exolvl")
```

---

## Decompile & Protect

Turn an existing `.exolvl` back into Python:

```python
import exopy as exo

exo.decompile("my_level.exolvl", out_py="my_level.py")
```

Lock down your scripts on export so others can't easily read them:

```python
lvl.export("protected.exolvl", obfuscate=True)
```

*(Your private unlock key is saved automatically in `~/.exopy_keys.txt` so only you can decompile it cleanly.)*

---

## License

MIT
