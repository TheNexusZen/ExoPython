import argparse, json, pprint, sys
from .decompile import decompile, inspect_level
from .sounds import audio_to_python


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m exopy",
        description="ExoPython CLI: decompile, inspect, or convert audio to Exoracer scripts.",
    )
    parser.add_argument("input", help="Path to .exolvl file (or audio file when --audio is used)")
    parser.add_argument("output", nargs="?", default=None, help="Optional output .py path")
    parser.add_argument("--json", action="store_true", help="Output summary metadata as JSON")
    parser.add_argument("--meta", action="store_true", help="Include ExoPy watermark/obfuscation metadata")
    parser.add_argument("--extract-assets", action="store_true", help="Extract embedded pattern/prefab PNGs")
    parser.add_argument("--inspect", action="store_true", help="Pretty-print full parsed .exolvl structure")
    parser.add_argument("--dump-json", action="store_true", help="Dump full parsed .exolvl structure as JSON")
    parser.add_argument("--audio", action="store_true", help="Convert an audio file into an Exoracer sound script")
    parser.add_argument("--sound", default="blip", help="In-game sound ID for --audio (default: blip)")
    parser.add_argument("--polyphony", type=int, default=1, help="Max simultaneous voices for --audio (default: 1)")
    parser.add_argument("--step", type=float, default=0.06, help="Analysis step in seconds for --audio (default: 0.06)")
    parser.add_argument("--loop", type=int, default=0, help="Repeat count for --audio (default: 0)")

    ns = parser.parse_args(argv)

    if ns.audio:
        code = audio_to_python(
            ns.input,
            sound_id=ns.sound,
            polyphony=ns.polyphony,
            step_sec=ns.step,
            loop=ns.loop,
            out_py=ns.output,
        )
        if not ns.output:
            print(code)
        elif ns.json:
            print(json.dumps({"ok": True, "path": ns.output, "sound_id": ns.sound, "polyphony": ns.polyphony}, indent=2))
        return

    if ns.inspect or ns.dump_json:
        tree = inspect_level(ns.input)
        if ns.dump_json:
            print(json.dumps(tree, indent=2, default=str))
        else:
            pprint.pprint(tree, width=100)
        return

    res = decompile(
        ns.input,
        ns.output,
        generator_mode=ns.json,
        include_meta=ns.meta,
        extract_assets=ns.extract_assets,
    )
    if ns.json:
        print(json.dumps({k: v for k, v in res.items() if k != "code"}, indent=2))


if __name__ == "__main__":
    main()
