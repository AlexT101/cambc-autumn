"""Puppet counterfactual: a variant of v118 against Fish's recorded inputs in the games where the hoard was killed.

    py research/ideas-2026-11-12/v118-fish/puppet_cf.py ARM [ARM...] [--jobs 12] [--cls hoard-killed]

For each ARM (bots/variants/v118f-ARM, a patched copy of variants/lab-emb6-c520-ps) the patch is applied to the
masked upload (bots/baselines/v118/src), built --release in the harness workspace (replays/v118/ws/bots/m-ARM) and
played against each selected game's puppet. The game equals the live one until the arm first acts differently; from
there Fish's side replays its recorded inputs blindly, so this is the replay counterfactual ("the enemy acting as it
did") played out by our real code, not a prediction of the result: a puppet does not chase, and its later inputs
mostly fail. Reported per arm: the first round it departs from the live game (must be before the death to matter),
and whether the champion that died with the hoard is alive, and with what bag or score, 20 rounds after the live
death. Output: replays/v118/cf/ARM/<key>.json."""
import argparse, concurrent.futures as cf, gzip, json, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
V = REPO / "replays/v118"
WS = V / "ws"
HARNESS = REPO / "tools/replay/harness"
BASE = REPO / "bots/variants/lab-emb6-c520-ps/src"
LIVE = REPO / "bots/baselines/v118/src"


def build(arm):
    bot = WS / "bots" / f"m-{arm}"
    if bot.exists():
        shutil.rmtree(bot)
    shutil.copytree(LIVE, bot / "src")
    src = REPO / "bots/variants" / f"v118f-{arm}" / "src"
    for f in sorted(src.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(src)
        if (BASE / rel).read_bytes() == f.read_bytes():
            continue
        d = subprocess.run(["diff", "-u", str(BASE / rel), str(f)], capture_output=True, text=True).stdout
        r = subprocess.run(["patch", "-s", str(bot / "src" / rel)], input=d, text=True, capture_output=True)
        if r.returncode:
            sys.exit(f"{arm}: patch {rel} failed: {r.stdout}{r.stderr}")
    r = subprocess.run(["cambc", "build", f"bots/m-{arm}", "--release"], cwd=WS, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stdout[-2000:] + r.stderr[-2000:])
    return bot


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arms", nargs="+")
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--cls", default="hoard-killed")
    ap.add_argument("--keys", help="these games instead of a class; their largest own bag death of any kind")
    a = ap.parse_args()
    man = {f"{g['group'][:8]}-{g['position']}": g for g in json.loads((V / "manifest.json").read_text())["games"]}
    rows = [l.split("\t") for l in (V / "analysis/taxonomy.tsv").read_text().split("\n")[1:] if l]
    sel = a.keys.split(",") if a.keys else [r[0] for r in rows if r[3] == "loss" and r[6] == a.cls]
    deaths = {}
    for l in open(V / "analysis/deaths.jsonl"):
        d = json.loads(l)
        if d["us"] and (d["kind"] == "death" or a.keys) and d["bag"] >= 100 and (d["key"] not in deaths or d["bag"] > deaths[d["key"]]["bag"]):
            deaths[d["key"]] = d
    for arm in a.arms:
        build(arm)
        out = V / "cf" / arm
        out.mkdir(parents=True, exist_ok=True)

        def one(k):
            g, d = man[k], deaths[k]
            tmp = out / f"_{k}"
            shutil.rmtree(tmp, ignore_errors=True)
            pair = [f"bots/m-{arm}", f"bots/p-{k}"]
            if g["our_side"] == "b":
                pair.reverse()
            m = subprocess.run(["cambc", "run", *pair, "--map", g["map"].replace("_", "-"), "--release", "-o", str(tmp)], cwd=WS, capture_output=True, text=True)
            reps = list(tmp.glob("*.repl26a"))
            if m.returncode or not reps:
                return {"key": k, "error": (m.stderr + m.stdout)[-300:]}
            rep = out / f"{k}.repl26a"
            shutil.move(str(reps[0]), rep)
            shutil.rmtree(tmp, ignore_errors=True)
            c = subprocess.run(["node", str(HARNESS / "compare.mjs"), str(V / "inputs/ladder" / f"{k}.json.gz"), str(rep)], cwd=REPO, capture_output=True, text=True)
            cmp = json.loads(c.stdout) if c.returncode == 0 else {}
            first = (cmp.get("firstInputDiff") or {}).get("round")
            return {"key": k, "first_diff": first, "death_r": d["r"], "victim": d["vid"], "bag": d["bag"], "rep": str(rep.relative_to(REPO))}

        with cf.ThreadPoolExecutor(a.jobs) as ex:
            res = list(ex.map(one, sel))
        ok = [r for r in res if "error" not in r]
        # decode the counterfactual replays and read the victim's fate
        ext = V / "cf-extract" / arm
        subprocess.run(["node", str(REPO / "tools/replay/extract.mjs"), str(out), "--out", str(ext), "--threads", str(a.jobs)], cwd=REPO, capture_output=True, text=True)
        idx = {Path(r["source"]).stem: r["dir"] for r in json.loads((ext / "index.json").read_text())["games"]}
        for r in ok:
            dd = ext / idx[r["key"]]
            R = json.load(gzip.open(dd / "rounds.json.gz"))
            meta = json.loads((dd / "meta.json").read_text())
            us = 0 if man[r["key"]]["our_side"] == "a" else 1
            ch = next(c for c in R["champions"] if c["id"] == r["victim"])
            at = min(r["death_r"] + 20, len(ch["alive"])) - 1
            died = None
            with gzip.open(dd / "events.jsonl.gz", "rt") as f:
                for line in f:
                    e = json.loads(line)
                    if e["k"] == "death" and e["v"] == r["victim"] and (r["first_diff"] or 0) <= e["r"] <= r["death_r"] + 20:
                        died = (e["r"], e.get("gems", 0))
                        break
            r.update({"alive_after": bool(ch["alive"][at]), "bag_after": ch["gems"][at] or 0, "score_after": R["gems"][us][at], "died_cf": died,
                      "rounds_cf": meta["result"]["rounds"]})
            (out / f"{r['key']}.json").write_text(json.dumps(r))
        before = [r for r in ok if r["first_diff"] and r["first_diff"] < r["death_r"]]
        saved = [r for r in before if not r["died_cf"]]
        print(f"{arm}: {len(sel)} games, {len(ok)} played; departs from the live game before the death in {len(before)}; "
              f"of those the hoard's carrier did not die by the live death round + 20 in {len(saved)} "
              f"(bag then: median {sorted(r['bag_after'] for r in saved)[len(saved) // 2] if saved else 0}); "
              f"died anyway in {len(before) - len(saved)} (bag median {sorted(r['died_cf'][1] for r in before if r['died_cf'])[(len(before) - len(saved)) // 2] if len(before) > len(saved) else 0})")
        lead = sorted(r["death_r"] - r["first_diff"] for r in before)
        if lead:
            print(f"   rounds between the first departure and the live death: median {lead[len(lead) // 2]}, quartiles {lead[len(lead) // 4]}-{lead[3 * len(lead) // 4]}")


if __name__ == "__main__":
    main()
