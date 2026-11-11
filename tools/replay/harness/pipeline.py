"""Run a version's whole harness chain; every step skips finished work, so rerun it after new downloads.

    py tools/replay/harness/pipeline.py --version v47 [--jobs 12] [--slots 8] [--skip manifest,trace,extract]

Steps: manifest (build_manifest.py, for versions whose manifest is generated), setup (setup_ws.py),
decode (decode_all.mjs), batch (batch.py), trace (trace_batch.py --all), extract (extract_all.py),
summary (v38lib.py summary).

Live versions (v87 on, cambc 5.0.1; versions.py reads them from the scheduler) run their own chain, since the
recorder and tracer do not reproduce their games:
  manifest  scrim_manifest.py (--opps, default fish,mite)
  setup, decode
  batch     batch.py without its recorder stage: puppets, release re-runs (they prove the source), validation
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
STEPS = ["manifest", "setup", "decode", "batch", "trace", "extract", "summary"]
LIVE_STEPS = ["manifest", "setup", "decode", "batch", "tracebot", "direct", "extract"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    versions.add_arg(ap)
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--slots", type=int, default=8)
    ap.add_argument("--skip", default="")
    ap.add_argument("--opps", default="fish,mite", help="live versions: the scrim opponents to re-run (scrim_manifest.py)")
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
    steps = STEPS
    if cfg.live:
        steps = LIVE_STEPS
        cmds.update({
            "manifest": [py, HERE / "scrim_manifest.py", *v, "--opps", args.opps],
            "batch": [py, HERE / "batch.py", *v, "--jobs", str(args.jobs), "--stages", "gen,build,release,validate,summary"],
            "tracebot": [py, HERE / "live_trace_bot.py", *v],
            "direct": [py, HERE / "direct_batch.py", *v, "--jobs", str(args.jobs)],
            "extract": [py, HERE / "extract_all.py", *v, "--kinds", "ladder", "--threads", str(args.jobs)],
        })
    if not str(cfg.manifest).startswith(str(cfg.dir)):
        skip.add("manifest")  # committed manifest (v38)
    for step in steps:
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
