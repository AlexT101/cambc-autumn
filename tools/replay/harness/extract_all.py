"""Run tools/replay/extract.mjs on a version's games: the ladder replays and the release re-runs.

    py tools/replay/harness/extract_all.py [--version vN] [--kinds ladder,release] [--keys K1,K2] [--threads 2] [--force]

kinds (output under <dir>/extract/, <dir> = replays/<version>):
  ladder   manifest `replay`                    -> extract/ladder
  release  runs/batch/<key>/release.repl26a     -> extract/release

Each output dir is an extract.mjs cache (`<sha16>/{meta.json,events.jsonl.gz,rounds.json.gz}`, `maps/`,
`index.json`, `enums.json`) plus `keys.json`: {key: {dir, source, sha256}}. Resumable: extract.mjs skips
replays it has already decoded (by content hash) unless --force. Games without that replay are skipped.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import versions

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CFG = DIR = None
EXTRACT = REPO / "tools/replay/extract.mjs"
KINDS = {"ladder": "ladder", "release": "release"}
CHUNK = 60  # replay paths per extract.mjs call: Windows caps a command line at 32k characters


def games():
    m = json.loads(CFG.manifest.read_text(encoding="utf-8"))
    return {f"{g['group'][:8]}-{g['position']}": g for g in m["games"]}


def replay_for(kind, key, g):
    if kind == "ladder":
        return REPO / g["replay"]
    return DIR / "runs/batch" / key / f"{kind}.repl26a"


def sha16(p):
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    return h[:16], h


def run_kind(kind, keys, G, threads, force):
    out = DIR / "extract" / KINDS[kind]
    out.mkdir(parents=True, exist_ok=True)
    files = {k: replay_for(kind, k, G[k]) for k in keys}
    files = {k: p for k, p in files.items() if p.exists()}
    t0 = time.time()
    paths = sorted({str(p) for p in files.values()})
    rc = 0
    for i in range(0, len(paths), CHUNK):
        cmd = [shutil.which("node") or "node", str(EXTRACT), *paths[i:i + CHUNK], "--out", str(out), "--threads", str(threads)]
        if force:
            cmd.append("--force")
        r = subprocess.run(cmd, cwd=REPO)
        rc = rc or r.returncode
    keymap_p = out / "keys.json"
    keymap = json.loads(keymap_p.read_text(encoding="utf-8")) if keymap_p.exists() else {}
    for k, p in files.items():
        d, full = sha16(p)
        keymap[k] = {"dir": d, "source": p.relative_to(REPO).as_posix(), "sha256": full,
                     "ok": (out / d / "meta.json").exists() and json.loads((out / d / "meta.json").read_text(encoding="utf-8"))["validation"]["ok"]}
    keymap_p.write_text(json.dumps(dict(sorted(keymap.items())), indent=1))
    dt = time.time() - t0
    bad = [k for k in files if not keymap[k]["ok"]]
    print(f"{kind}: {len(files)} replays ({len(keys) - len(files)} missing) -> {out.relative_to(REPO)} in {dt:.0f} s; "
          f"{len(bad)} not ok{': ' + ','.join(bad[:10]) if bad else ''}", flush=True)
    return rc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    versions.add_arg(ap)
    ap.add_argument("--kinds", default="ladder")
    ap.add_argument("--keys", default="")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    global CFG, DIR
    CFG = versions.get(args.version)
    DIR = CFG.dir
    G = games()
    keys = [k for k in args.keys.split(",") if k] or list(G)
    unknown = [k for k in keys if k not in G]
    if unknown:
        sys.exit(f"unknown keys {unknown[:10]}")
    rc = 0
    for kind in args.kinds.split(","):
        if kind not in KINDS:
            sys.exit(f"unknown kind {kind}; one of {','.join(KINDS)}")
        rc = run_kind(kind, keys, G, args.threads, args.force) or rc
    sys.exit(rc)


if __name__ == "__main__":
    main()
