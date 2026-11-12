"""Candidate arms from live positions: v118's Fish r8 games forked mid-game, Fish played on by the r8 body.

    python3 research/ideas-2026-11-12/v118-fish/livefork_arms.py OUT_DIR --cands hf,hb,hb2,rr2 [--forks 300,450,600,750]
        [--seeds 1,2] [--shards 16] [--limit N]
    python3 research/ideas-2026-11-12/v118-fish/livefork_arms.py OUT_DIR --read

forkcomp's livefork (research/ideas-2026-11-12/forkcomp: the live game is the main line, our release build against
the harness puppet, so the engine state at the fork is the live game's, Fish's Vesper with the gold and items it
really had). At each fork, per body noise seed: the reference (variants/lab-emb6-c520-ps, v118 without the live mask,
started cold as every swapped-in bot is) and each candidate (variants/v118f-CAND) take our side against
variants/fr8-g25, plus the puppet arm (what happened) and the live build going on against the body.
--read: candidate minus reference per fork round, paired on (game, fork, seed), SE clustered by game; split by the
live result and by the live game's loss class (taxonomy.tsv)."""
import argparse, importlib.util, json, math, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("lf", ROOT / "research/ideas-2026-11-12/forkcomp/livefork_run.py")
lf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lf)
# Private builds in the harness workspace (replays/v118/ws/bots/c-*): livefork wants a built bot, and a build in
# place in a variant that gates play could race theirs.
REF = "replays/v118/ws/bots/c-ref"
BODY = "variants/fr8-g25"


def body(k):
    return {"bot": BODY, "seed": lf.NOISE0 + k, "salt": k, "unmetered": True}


def read(out):
    games, arms = {}, defaultdict(dict)
    for l in open(f"{out}/out.jsonl"):
        r = json.loads(l)
        if r["type"] == "game":
            games[r["id"]] = r
        else:
            arms[(r["game"], r["fork"])][r["label"]] = r
    cls = {}
    for l in (ROOT / "replays/v118/analysis/taxonomy.tsv").read_text().split("\n")[1:]:
        p = l.split("\t")
        if len(p) > 6:
            cls["v118:" + p[0]] = (p[3], p[6])
    meta = {json.loads(l)["id"]: json.loads(l) for f in sorted(Path(out).glob("games-*.jsonl")) for l in open(f)}

    def outcome(a, ours):
        if not a or "winner" not in a or a.get("error"):
            return None
        if not a.get("finished"):
            return 0.5
        return 0.5 if a["winner"] is None else float(a["winner"] == ours)

    def clustered(pairs):
        by = defaultdict(list)
        for c, v in pairs:
            by[c].append(v)
        n = sum(len(v) for v in by.values())
        if not n:
            return float("nan"), float("nan"), 0
        m = sum(sum(v) for v in by.values()) / n
        var = sum((sum(v) - m * len(v)) ** 2 for v in by.values()) / (n * n)
        g = len(by)
        return m, math.sqrt(var * g / max(1, g - 1)), n

    labels = sorted({l for a in arms.values() for l in a})
    cands = sorted({l.split("+")[0] for l in labels if "+body" in l and not l.startswith("ref")})
    seeds = sorted({l.split("+body")[1] for l in labels if l.startswith("ref+body")})
    forks = sorted({f for _, f in arms})
    print(f"{len(games)} games, {len(arms)} forks; arms {labels}")
    for sel_name, sel in (("all forks", lambda g: True), ("live losses", lambda g: cls[g][0] == "loss"), ("live wins", lambda g: cls[g][0] == "win"),
                          ("live hoard-killed losses", lambda g: cls[g] == ("loss", "hoard-killed")), ("games with our Prism", lambda g: "Prism" in json.dumps(meta[g].get("picks", "Prism")))):
        print(f"\n== {sel_name}")
        base = []
        pl = []
        for (g, f), a in arms.items():
            if not sel(g):
                continue
            ours = meta[g]["ours"]
            for s in seeds:
                o = outcome(a.get(f"ref+body{s}"), ours)
                if o is not None:
                    base.append((g, o))
            o = outcome(a.get("puppet"), ours)
            if o is not None:
                pl.append((g, o))
        m, se, n = clustered(base)
        mp, sep, np_ = clustered(pl)
        print(f"   reference against the body from the fork: {100 * m:.1f}% ± {196 * se:.1f} of {n}; the live continuation (puppet): {100 * mp:.1f}% of {np_}")
        for c in cands:
            line = f"   {c:5s}"
            for fk in forks + ["all"]:
                pairs = []
                for (g, f), a in arms.items():
                    if not sel(g) or (fk != "all" and f != fk):
                        continue
                    ours = meta[g]["ours"]
                    for s in seeds:
                        x, y = outcome(a.get(f"{c}+body{s}"), ours), outcome(a.get(f"ref+body{s}"), ours)
                        if x is not None and y is not None:
                            pairs.append((g, x - y))
                m, se, n = clustered(pairs)
                line += f" | r{fk}: {100 * m:+5.2f} ± {196 * se:4.2f} (n {n})"
            print(line)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--cands", default="hf,hb,hb2,rr2")
    ap.add_argument("--forks", default="300,450,600,750")
    ap.add_argument("--seeds", default="1,2")
    ap.add_argument("--shards", type=int, default=16)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--read", action="store_true")
    a = ap.parse_args()
    if a.read:
        return read(a.out)
    cands = a.cands.split(",")
    seeds = [int(x) for x in a.seeds.split(",")]

    def lines(exp, versions, forks, limit):
        out = []
        val = {x["key"]: x for x in json.load(open(ROOT / "replays/v118/runs/batch/validation.json"))}
        man = {f"{g['group'][:8]}-{g['position']}": g for g in json.load(open(ROOT / "replays/v118/manifest.json"))["games"]}
        ws = "replays/v118/ws"
        seen = set()
        for key, g in sorted(val.items()):
            if not g["release"]["exact"]:
                continue
            cell = (g["map"], g["our_side"])  # five cells were played twice, identically
            if cell in seen:
                continue
            seen.add(cell)
            ours = 0 if g["our_side"] == "a" else 1
            opp = 1 - ours
            fk = [r for r in forks if r <= g["rounds"] - 30]
            if not fk:
                continue
            bots = [None, None]
            bots[ours], bots[opp] = f"{ws}/bots/v118-release", f"{ws}/bots/p-{key}"
            pup = [False, False]
            pup[opp] = True
            arms = [{"label": "puppet"}]
            for s in seeds:
                arms.append({"label": f"live+body{s}", f"t{opp}": body(s)})
                arms.append({"label": f"ref+body{s}", f"t{ours}": {"bot": REF}, f"t{opp}": body(s)})
                for c in cands:
                    arms.append({"label": f"{c}+body{s}", f"t{ours}": {"bot": f"replays/v118/ws/bots/c-{c}"}, f"t{opp}": body(s)})
            out.append({"id": f"v118:{key}", "map": f"{ws}/maps/{g['map'].replace('_', '-')}.map26a", "bots": bots, "puppet": pup, "forks": fk, "arms": arms, "ours": ours,
                        "picks": man[key]["our_draft"], "live": {"result": g.get("score"), "rounds": g["rounds"], "our_side": g["our_side"]}})
        return out[:limit] if limit else out

    lf.lines = lines
    sys.argv = [sys.argv[0], a.out, "--exp", "live", "--versions", "v118", "--forks", a.forks, "--shards", str(a.shards)] + (["--limit", str(a.limit)] if a.limit else [])
    lf.main()


if __name__ == "__main__":
    main()
