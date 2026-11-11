"""Direct traced re-runs: a version's trace bot against each game's puppet, played straight (no recorder).

    py tools/replay/harness/direct_batch.py --version v105 [--keys K1,K2] [--jobs N] [--bot DIR] [--out NAME] [--force]

The recorder/tracer path does not reproduce games on cambc 5.0.1, even with the plain source (README, v105-v111), so
this plays the trace bot (live_trace_bot.py; its release-guard build plays release code) in a debug run against the
puppet. Each game is trusted through the round before its first input or round-hash difference from the ladder replay
(compare.mjs). A game is redone when its result is missing, --force is given, or the trace bot's wasm has changed.

Per game: <dir>/runs/<NAME>/<key>/{direct.repl26a, trace.stdout.gz, direct.json}; NAME defaults to direct, and the
bot defaults to the version's trace_bot. <dir>/runs/<NAME>/direct_validation.json holds every game's direct.json:
ladder_trusted_through, exact, the first differences."""
import argparse, concurrent.futures as cf, gzip, hashlib, json, shutil, subprocess, sys, zipfile
from pathlib import Path

import versions

REPO = versions.REPO
HERE = versions.HERE


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    versions.add_arg(ap)
    ap.add_argument("--keys")
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--bot", help="default: the version's trace_bot")
    ap.add_argument("--out", default="direct")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    cfg = versions.get(a.version)
    ws = cfg.ws
    man = {f"{g['group'][:8]}-{g['position']}": g for g in json.loads(cfg.manifest.read_text())["games"]}
    keys = a.keys.split(",") if a.keys else list(man)
    src = Path(a.bot or cfg.trace_bot).resolve()
    bot = ws / "bots" / f"fc-{a.out}"
    if bot.exists():
        shutil.rmtree(bot / "src", ignore_errors=True)
    shutil.copytree(src / "src", bot / "src", dirs_exist_ok=True)
    (bot / "RELEASE_CODE").unlink(missing_ok=True)
    if (src / "RELEASE_CODE").exists():  # make_trace_bot.py --release-guard
        (bot / "RELEASE_CODE").write_bytes(b"")
    r = subprocess.run(["cambc", "build", str(bot.relative_to(ws))], cwd=ws, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stdout[-3000:] + r.stderr[-3000:])
    wasm = hashlib.sha256((bot / ".cambc/build/bot-injected.wasm").read_bytes()).hexdigest()[:16]
    out = cfg.dir / "runs" / a.out
    out.mkdir(parents=True, exist_ok=True)

    def one(k):
        g = man[k]
        d = out / k
        res_p = d / "direct.json"
        if res_p.exists() and not a.force:
            old = json.loads(res_p.read_text())
            if old.get("wasm") in (wasm, None):  # None: written before stamps
                return old
        d.mkdir(parents=True, exist_ok=True)
        puppet = ws / "bots" / f"p-{k}"
        tmp = d / "_run"
        shutil.rmtree(tmp, ignore_errors=True)
        pair = [str(bot.relative_to(ws)), str(puppet.relative_to(ws))]
        if g["our_side"] == "b":
            pair.reverse()
        m = subprocess.run(["cambc", "run", *pair, "--map", g["map"].replace("_", "-"), "-o", str(tmp), "--log-limit", str(1 << 30)],
                           cwd=ws, capture_output=True, text=True, timeout=3600)
        reps = list(tmp.glob("*.repl26a"))
        if m.returncode or not reps:
            return {"key": k, "status": "run-failed", "error": (m.stderr + m.stdout)[-800:]}
        rep = d / "direct.repl26a"
        shutil.move(str(reps[0]), rep)
        shutil.rmtree(tmp, ignore_errors=True)
        with zipfile.ZipFile(rep) as z:
            text = z.read(f"team-{g['our_side']}.stdout").replace(b"\0", b"")
        with gzip.open(d / "trace.stdout.gz", "wb", compresslevel=6) as f:
            f.write(text)
        c = subprocess.run(["node", str(HERE / "compare.mjs"), str(cfg.inputs / f"{k}.json.gz"), str(rep)],
                           cwd=REPO, capture_output=True, text=True)
        cmp = json.loads(c.stdout) if c.returncode == 0 else {"error": c.stderr[-300:]}
        diffs = [x["round"] for x in (cmp.get("firstInputDiff"), cmp.get("firstRoundDiff")) if x]
        trusted = g["rounds"] if cmp.get("exact") or cmp.get("exactIgnoringRollovers") else (min(diffs) - 1 if diffs else None)
        res = {"key": k, "status": "ok", "rounds": g["rounds"], "ladder_trusted_through": trusted, "exact": bool(cmp.get("exact")),
               "first_input_diff": cmp.get("firstInputDiff"), "first_round_diff": cmp.get("firstRoundDiff"), "bytes": len(text), "wasm": wasm}
        res_p.write_text(json.dumps(res, indent=1))
        return res

    done = []
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for res in ex.map(one, keys):
            done.append(res)
            if res.get("status") == "ok":
                print(f"{res['key']}: trusted {res['ladder_trusted_through']}/{res['rounds']} {'EXACT' if res['exact'] else ''}", flush=True)
            else:
                print(f"{res['key']}: {res['status']} {res.get('error', '')[:200]}", flush=True)
    summ = out / "direct_validation.json"
    old = json.loads(summ.read_text()) if summ.exists() else {}
    old.update({r["key"]: r for r in done})
    summ.write_text(json.dumps(dict(sorted(old.items())), indent=1))
    ok = [r for r in done if r.get("status") == "ok"]
    tr = sum(r["ladder_trusted_through"] or 0 for r in ok)
    print(f"{len(ok)}/{len(done)} ok, {sum(r['exact'] for r in ok)} exact, trusted rounds {tr}/{sum(r['rounds'] for r in ok)}")


if __name__ == "__main__":
    main()
