"""Run a live version's whole harness chain; every step skips finished work, so rerun it after new downloads.

    py tools/replay/harness/pipeline.py --version vN [--jobs 12] [--opps fish,mite] [--skip direct,...]

Steps:
  manifest  scrim_manifest.py (--opps, default fish,mite)
  setup     setup_ws.py
  decode    decode_all.mjs
  batch     batch.py: puppets, release re-runs (they prove the source), validation
  tracebot  live_trace_bot.py: the version's source plus the combat lab's lines -> <dir>/trace-bot
  direct    direct_batch.py: the trace bot against each puppet, trusted rounds per game
  extract   extract_all.py --kinds ladder: the ladder replays' tables, which give outcomes
"""
import argparse
import shutil
import subprocess
import sys
import time

import versions

HERE = versions.HERE
STEPS = ["manifest", "setup", "decode", "batch", "tracebot", "direct", "extract"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    versions.add_arg(ap)
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--skip", default="")
    ap.add_argument("--opps", default="fish,mite", help="the scrim opponents to re-run (scrim_manifest.py)")
    args = ap.parse_args()
    cfg = versions.get(args.version)
    skip = set(filter(None, args.skip.split(",")))
    py, v = sys.executable, ["--version", cfg.name]
    cmds = {
        "manifest": [py, HERE / "scrim_manifest.py", *v, "--opps", args.opps],
        "setup": [py, HERE / "setup_ws.py", *v],
        "decode": [shutil.which("node") or "node", HERE / "decode_all.mjs", "--list", cfg.dir / "ladder-list.json",
                   "--out", cfg.inputs, "--threads", str(args.jobs)],
        "batch": [py, HERE / "batch.py", *v, "--jobs", str(args.jobs)],
        "tracebot": [py, HERE / "live_trace_bot.py", *v],
        "direct": [py, HERE / "direct_batch.py", *v, "--jobs", str(args.jobs)],
        "extract": [py, HERE / "extract_all.py", *v, "--kinds", "ladder", "--threads", str(args.jobs)],
    }
    for step in STEPS:
        if step in skip:
            continue
        t0 = time.time()
        print(f"== {step}", flush=True)
        r = subprocess.run([str(c) for c in cmds[step]], cwd=versions.REPO)
        print(f"== {step}: exit {r.returncode} in {time.time() - t0:.0f} s", flush=True)
        if r.returncode and step in ("manifest", "setup", "decode", "tracebot"):
            sys.exit(r.returncode)


if __name__ == "__main__":
    main()
