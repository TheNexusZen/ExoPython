import json, pprint, sys
from .decompile import decompile, inspect_level

flags = {a for a in sys.argv[1:] if a.startswith("--")}
args = [a for a in sys.argv[1:] if not a.startswith("--")]
as_json = "--json" in flags
show_meta = "--meta" in flags
extract_assets = "--extract-assets" in flags
do_inspect = "--inspect" in flags
dump_json = "--dump-json" in flags

if not args:
    print("Usage: python -m exopy <file.exolvl> [output.py] [--json] [--meta] [--extract-assets] [--inspect] [--dump-json]")
    sys.exit(1)

if do_inspect or dump_json:
    tree = inspect_level(args[0])
    if dump_json:
        print(json.dumps(tree, indent=2, default=str))
    else:
        pprint.pprint(tree, width=100)
    sys.exit(0)

res = decompile(
    args[0],
    args[1] if len(args) > 1 else None,
    generator_mode=as_json,
    include_meta=show_meta,
    extract_assets=extract_assets,
)
if as_json:
    print(json.dumps({k: v for k, v in res.items() if k != "code"}, indent=2))
