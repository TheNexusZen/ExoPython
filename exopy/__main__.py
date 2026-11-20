import json, sys
from .decompile import decompile

flags = {a for a in sys.argv[1:] if a.startswith("--")}
args = [a for a in sys.argv[1:] if not a.startswith("--")]
as_json = "--json" in flags
show_meta = "--meta" in flags

if not args:
    print("Usage: python -m exopy <file.exolvl> [output.py] [--json] [--meta]")
    sys.exit(1)

res = decompile(
    args[0],
    args[1] if len(args) > 1 else None,
    generator_mode=as_json,
    include_meta=show_meta,
)
if as_json:
    print(json.dumps({k: v for k, v in res.items() if k != "code"}, indent=2))
