"""Tribute channels in v118's Fish r8 games: how often a channel of a given length completes, per side.

    py research/ideas-2026-11-12/v118-fish/channels.py

From the live replays' events (replays/v118/extract/ladder): every tribute_start with its gems and length, matched
to the same champion's next tribute_end, tribute_cancel (with its cause) or death. Our bot starts a tribute at every
turn end it can and cancels it next turn when unwanted (bank.cc mite_tribute_habit), so channels cancelled by hand
within one round are listed apart as feints."""
import gzip, json, os, sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
V = REPO / "replays/v118"


def games(local):
    """(key, extract dir, our team index, result) for the live games, or for a local batch's extract (--local EXT:
    an extract.mjs --out dir whose index.json rows name our bot first in `teams` order by side)."""
    if not local:
        man = {f"{g['group'][:8]}-{g['position']}": g for g in json.loads((V / "manifest.json").read_text())["games"]}
        keys = json.loads((V / "extract/ladder/keys.json").read_text())
        for k, g in man.items():
            yield k, V / "extract/ladder" / keys[k]["dir"], 0 if g["our_side"] == "a" else 1, g["result"]
        return
    ext = Path(local)
    for row in json.loads((ext / "index.json").read_text())["games"]:
        us = 0 if not row["teams"][0].startswith("fr8") and "Flp" not in row["teams"][0] else 1
        yield Path(row["source"]).stem, ext / row["dir"], us, "win" if row["winner"] == us else "loss"


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--local", help="a local batch's extract dir (our bot against a body) instead of the live games")
    a = ap.parse_args()
    rows = []
    ngames = 0
    locks = Counter()
    for k, d, us, result in games(a.local):
        ngames += 1
        g = {"result": result}
        meta = json.loads((d / "meta.json").read_text())
        team = {c["id"]: c["team"] for c in meta["champions"]}
        name = {c["id"]: c["name"] for c in meta["champions"]}
        open_ = {}
        with gzip.open(d / "events.jsonl.gz", "rt") as f:
            for line in f:
                e = json.loads(line)
                kk = e["k"]
                if kk == "lock_place":
                    locks["ours" if e["team"] == us else "theirs"] += 1
                if kk == "tribute_start":
                    open_[e["a"]] = e
                elif kk in ("tribute_end", "tribute_cancel") and e["a"] in open_:
                    s = open_.pop(e["a"])
                    rows.append({"key": k, "us": team[e["a"]] == us, "who": name[e["a"]], "r": s["r"], "gems": s["gems"], "dur": s["dur"], "ran": e["r"] - s["r"],
                                 "out": "done" if kk == "tribute_end" else "cancel:" + str(e.get("cause")), "scored": e.get("gems", 0) if kk == "tribute_end" else 0,
                                 "result": g["result"]})
                elif kk == "death" and e["v"] in open_:
                    s = open_.pop(e["v"])
                    rows.append({"key": k, "us": team[e["v"]] == us, "who": name[e["v"]], "r": s["r"], "gems": s["gems"], "dur": s["dur"], "ran": e["r"] - s["r"],
                                 "out": "died", "scored": 0, "result": g["result"]})
        for cid, s in open_.items():
            rows.append({"key": k, "us": team[cid] == us, "who": name[cid], "r": s["r"], "gems": s["gems"], "dur": s["dur"], "ran": meta["result"]["rounds"] - s["r"],
                         "out": "game end", "scored": 0, "result": g["result"]})
    if not a.local:
        (V / "analysis/channels.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    print(f"{ngames} games; locks placed a game: ours {locks['ours'] / ngames:.2f}, theirs {locks['theirs'] / ngames:.2f}")
    buckets = [(1, 2), (3, 5), (6, 10), (11, 20), (21, 40), (41, 70), (71, 999)]
    for side, lab in ((True, "ours"), (False, "Fish's")):
        S = [r for r in rows if r["us"] == side]
        feint = [r for r in S if r["out"] == "cancel:manual" and r["ran"] <= 1]
        real = [r for r in S if not (r["out"] == "cancel:manual" and r["ran"] <= 1)]
        print(f"\n{lab}: {len(S)} tribute starts, {len(feint)} one-round feints left out, {len(real)} channels")
        print("  length (turn ends)   n  completed  cancelled by hand  by stun  by lock  died  game end | gems scored / started")
        for lo, hi in buckets:
            b = [r for r in real if lo <= r["dur"] <= hi]
            if not b:
                continue
            c = Counter(r["out"] for r in b)
            done = c["done"]
            print(f"  {lo:3d}-{hi:<3d}          {len(b):5d}  {done:5d} {100 * done / len(b):3.0f}%  {c['cancel:manual']:6d} {100 * c['cancel:manual'] / len(b):3.0f}%   "
                  f"{c['cancel:stun']:5d}   {c['cancel:lock']:5d}  {c['died']:4d}  {c['game end']:4d}     | {sum(r['scored'] for r in b)} / {sum(r['gems'] for r in b)}")
        if side:
            for res in ("win", "loss"):
                b = [r for r in real if r["dur"] >= 21 and r["result"] == res]
                c = Counter(r["out"] for r in b)
                print(f"  channels of 21+ turns in our {res}s: {len(b)}; {dict(c)}")
            p = [r for r in real if r["who"] == "Prism" and r["dur"] >= 21]
            print(f"  Prism's 21+ turn channels: {len(p)}; {dict(Counter(r['out'] for r in p))}; median rounds run before a cancel "
                  f"{sorted(r['ran'] for r in p if r['out'] != 'done')[len([r for r in p if r['out'] != 'done']) // 2] if any(r['out'] != 'done' for r in p) else '-'}")


if __name__ == "__main__":
    main()
