"""Run a version's whole harness chain; every step skips finished work, so rerun it after new downloads.

    py tools/replay/harness/pipeline.py --version v47 [--jobs 12] [--slots 8] [--skip manifest,trace,extract]

Steps: manifest (build_manifest.py, for versions whose manifest is generated), setup (setup_ws.py),
decode (decode_all.mjs), batch (batch.py), trace (trace_batch.py --all), extract (extract_all.py),
summary (v38lib.py summary).
"""
import argparse
import shutil
import subprocess
import sys
import time

import versions

HERE = versions.HERE
STEPS = ["manifest", "setup", "decode", "batch", "trace", "extract", "summary"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    versions.add_arg(ap)
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--slots", type=int, default=8)
    ap.add_argument("--skip", default="")
    args = ap.parse_args()
    cfg = versions.get(args.version)
    skip = set(filter(None, args.skip.split(",")))
    py, v = sys.executable, ["--version", cfg.name]
    cmds = {
        "manifest": [py, HERE / "build_manifest.py", *v],
        "setup": [py, HERE / "setup_ws.py", *v],
        "decode": [shutil.which("node") or "node", HERE / "decode_all.mjs", "--list", cfg.dir / "ladder-list.json",
                   "--out", cfg.inputs, "--threads", str(args.jobs)],
        "batch": [py, HERE / "batch.py", *v, "--jobs", str(args.jobs)],
        "trace": [py, HERE / "trace_batch.py", *v, "--all", "--slots", str(args.slots)],
        "extract": [py, HERE / "extract_all.py", *v, "--threads", str(args.jobs)],
        "summary": [py, HERE / "v38lib.py", *v, "summary"],
    }
    if not str(cfg.manifest).startswith(str(cfg.dir)):
        skip.add("manifest")  # committed manifest (v38)
    for step in STEPS:
        if step in skip:
            continue
        t0 = time.time()
        print(f"== {step}", flush=True)
        r = subprocess.run([str(c) for c in cmds[step]], cwd=versions.REPO)
        print(f"== {step}: exit {r.returncode} in {time.time() - t0:.0f} s", flush=True)
        if r.returncode and step in ("manifest", "setup", "decode"):
            sys.exit(r.returncode)


if __name__ == "__main__":
    main()
