import gzip
from pathlib import Path
import exopython as exo
from exopython import scripts as exoscript, variables as exovar
from exopython.constants import OldActionType
from exopython.types_ext import LocalLevel, OldAction, OldActionProperty, OldScript, TerrainCopyStyle


def test_build_and_decompile_roundtrip(tmp_path):
    lvl = exo.init("Roundtrip Level", bg_type="Mountains", laps=2, gravity=(0.0, -75.0))
    lvl.terrain_style = TerrainCopyStyle(friction=0.75, round_collider=True)
    fg = exo.CreateLayer("Foreground", foreground_type=1, parallax=(0.5, 0.25))
    fg.locked = True

    plat = exo.CreateObj("terrain", (0, -2)).settings({"Box": (40, 2), "Layer": fg}).pack()
    exo.CreateObj("start", (-15, 0)).pack()
    exo.CreateObj("finish", (15, 0)).pack()

    counter = exovar.Int("counter", 0)
    (
        exoscript.create("LoopMover")
        .on(0)
        .repeat(
            3,
            exoscript.block()
            .move(plat, (5, -2), duration=0.5, wait=True)
            .set_color(plat, "#00F5FF", channel=1, duration=0.25, wait=True)
            .set_border_color(plat, "#FFFFFF", duration=0.2, easing=2, wait=True)
            .set_var(counter, counter + 1),
        )
        .pack()
    )

    out_lvl = tmp_path / "built.exolvl"
    out_py = tmp_path / "decompiled.py"
    lvl.export(str(out_lvl))

    code = exo.decompile(str(out_lvl), out_py=str(out_py))
    assert "channel=1" in code
    assert "easing=2" in code

    ns = {}
    exec(code, ns)
    rebuilt_bytes = ns["Level"].to_bytes()
    orig_bytes = exo.decompile.__globals__["read_exopy_meta"](
        gzip.decompress(out_lvl.read_bytes())
    )[1]
    assert rebuilt_bytes == orig_bytes


def test_v19_roundtrip(tmp_path):
    lvl = exo.init("V19 Test", settings={"SerializationVersion": 19})
    exo.CreateObj("start", (0, 0)).pack()
    exoscript.create("V19Script").on(0).wait(exovar.semitones(2.0)).pack()

    out_lvl = tmp_path / "v19.exolvl"
    out_py = tmp_path / "v19_dec.py"
    lvl.export(str(out_lvl))

    code = exo.decompile(str(out_lvl), out_py=str(out_py))
    ns = {}
    exec(code, ns)
    rebuilt_bytes = ns["Level"].to_bytes()
    orig_bytes = exo.decompile.__globals__["read_exopy_meta"](
        gzip.decompress(out_lvl.read_bytes())
    )[1]
    assert rebuilt_bytes == orig_bytes


def test_old_script_and_local_level_roundtrip():
    sc = OldScript(
        name="LegacyScript",
        actions=[
            OldAction(
                action_type=OldActionType.Move,
                wait=True,
                properties=[OldActionProperty("Target", "1"), OldActionProperty("X", "10")],
            )
        ],
    )
    assert OldScript.from_bytes(sc.to_bytes()) == sc

    ll = LocalLevel(level_name="Editor Level", laps=3)
    assert LocalLevel.from_bytes(ll.to_bytes()) == ll


def test_rust_fixtures_if_present(tmp_path):
    fixtures = Path("tests/test_files")
    if not fixtures.exists():
        return
    for p in sorted(fixtures.glob("*.exolvl")):
        if p.name.startswith("legacy"):
            continue
        raw = gzip.decompress(p.read_bytes())
        out_py = tmp_path / f"{p.stem}.py"
        code = exo.decompile(str(p), out_py=str(out_py))
        ns = {}
        exec(code, ns)
        assert ns["Level"].to_bytes() == raw
