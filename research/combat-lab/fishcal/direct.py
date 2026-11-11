"""Direct debug re-runs: a version's fishcal trace bot (debug build) against each game's puppet, no recorder.

    python3 direct.py VERSION [--keys K1,K2] [--jobs N] [--bot DIR] [--out NAME] [--force]

The harness's tracer (fuel replayed from a recorder run) does not reproduce v105 on cambc 5.0.1, even with the plain
source, so this plays the debug build straight. Its fuel is the debug build's own: the workspace SDK refunds a debug
block's overhead (CAMBC_DEBUG_REFUND 10), so the game follows the ladder's until a fuel-gated choice tips, and each game
is trusted through the round before its first input or round-hash difference from the ladder replay (compare.mjs).

Per game: replays/<VERSION>/runs/<NAME>/<key>/{direct.repl26a, trace.stdout.gz, direct.json}; NAME defaults to direct.
direct.json carries ladder_trusted_through, so collect.py reads it as it reads trace_validation.json."""
import argparse, concurrent.futures as cf, gzip, json, shutil, subprocess, sys, zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/replay/harness"))
import versions  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("version")
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
    out = cfg.dir / "runs" / a.out
    out.mkdir(parents=True, exist_ok=True)

    def one(k):
        g = man[k]
        d = out / k
        res_p = d / "direct.json"
        if res_p.exists() and not a.force:
            return json.loads(res_p.read_text())
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
        c = subprocess.run(["node", str(REPO / "tools/replay/harness/compare.mjs"), str(cfg.inputs / f"{k}.json.gz"), str(rep)],
                           cwd=REPO, capture_output=True, text=True)
        cmp = json.loads(c.stdout) if c.returncode == 0 else {"error": c.stderr[-300:]}
        diffs = [x["round"] for x in (cmp.get("firstInputDiff"), cmp.get("firstRoundDiff")) if x]
        trusted = g["rounds"] if cmp.get("exact") or cmp.get("exactIgnoringRollovers") else (min(diffs) - 1 if diffs else None)
        res = {"key": k, "status": "ok", "rounds": g["rounds"], "ladder_trusted_through": trusted, "exact": bool(cmp.get("exact")),
               "first_input_diff": cmp.get("firstInputDiff"), "first_round_diff": cmp.get("firstRoundDiff"), "bytes": len(text)}
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
