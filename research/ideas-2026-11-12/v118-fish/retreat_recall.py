"""The retreat's recall gate against what happened next: how often a refused recall would have landed.

    py research/ideas-2026-11-12/v118-fish/retreat_recall.py [--bag 0]

continue_recall (economy/bank.cc) keeps a running recall for a champion that wants home only if the walk does not
beat it, nothing threatens our tile this turn, no safe tribute is open and recall_outruns() holds (no credible enemy
could walk into reach before it lands). The traced re-runs log which test refused it (CR lines). For every maximal
run of consecutive turns on which a champion wanted home and the recall was refused, this reads the live replay:
- was the champion damaged (by a champion or a camp) or stunned in the rounds the recall still needed (the decision
  round and the four after it)? If not, the recall would have landed, the enemy acting as it did;
- what the walk did instead: on our spawn within 20 rounds, dead within 20 rounds (and the bag lost), or neither.
Only turns in rounds the re-run shares with the live game are used. Split by the refusing test and by bag."""
import argparse, gzip, json, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tracelib as T  # noqa: E402

V = T.V
NEED = 4  # rounds after the decision round the recall still runs
FAR = 5   # an enemy this near the tile could have struck it: ranged attack 3, unit spell 4, ground spell 4 + 1


def refusal(cr):
    b = cr["bits"]
    read = b >> 8
    if read & 1 and b & 1:
        return "walk beats recall"
    if read & 2 and b & 2:
        return "threatened here"
    if read & 4 and b & 4:
        return "can tribute safely"
    if read & 8 and not b & 8:
        return "does not outrun"
    if read & 8 and b & 8:
        return "kept"
    return "?"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bag", type=int, default=0, help="only runs that start with at least this bag")
    a = ap.parse_args()
    man = {f"{g['group'][:8]}-{g['position']}": g for g in json.loads((V / "manifest.json").read_text())["games"]}
    keys = json.loads((V / "extract/ladder/keys.json").read_text())
    runs = []
    for k, g in man.items():
        tr = T.load(k)
        us = 0 if g["our_side"] == "a" else 1
        d = V / "extract/ladder" / keys[k]["dir"]
        meta = json.loads((d / "meta.json").read_text())
        team = {c["id"]: c["team"] for c in meta["champions"]}
        name = {c["id"]: c["name"] for c in meta["champions"]}
        ours = [c for c in team if team[c] == us]
        theirs = [c for c in team if team[c] != us]
        hurt = defaultdict(set)   # champion -> rounds it was damaged or stunned
        died = defaultdict(list)  # champion -> [(round, bag)]
        with gzip.open(d / "events.jsonl.gz", "rt") as f:
            for line in f:
                e = json.loads(line)
                kk = e["k"]
                if kk in ("attack", "cast"):
                    for v, amt in e.get("dmg") or []:
                        if v in team and team[v] == us and amt > 0:
                            hurt[v].add(e["r"])
                    for v in e.get("stun") or []:
                        if v in team and team[v] == us:
                            hurt[v].add(e["r"])
                elif kk == "camp_attack":
                    if e.get("tgt") in team and team[e["tgt"]] == us and e.get("dmg"):
                        hurt[e["tgt"]].add(e["r"])
                    for v, amt in e.get("xdmg", []):
                        if v in team and team[v] == us:
                            hurt[v].add(e["r"])
                elif kk == "death" and team.get(e["v"]) == us:
                    died[e["v"]].append((e["r"], e.get("gems", 0)))
        rounds = json.load(gzip.open(d / "rounds.json.gz"))
        sp = json.loads((V / "extract/ladder/maps" / f"{meta['map']['hash']}.json").read_text())["spawn"][us]
        chs = {c["id"]: c for c in rounds["champions"]}

        def on_spawn(c, r):
            ch = chs[c]
            i = r - 1
            if i >= len(ch["x"]) or ch["x"][i] is None or not ch["alive"][i]:
                return False
            return sp["minX"] <= ch["x"][i] <= sp["maxX"] and sp["minY"] <= ch["y"][i] <= sp["maxY"]

        for c in ours:
            prev, cur = None, None
            for r in range(1, tr.trusted + 1):
                t = tr.turn(r, c)
                cr = (t or {}).get("CR")
                why = refusal(cr) if cr and cr["home"] else None
                refused = why in ("threatened here", "does not outrun", "walk beats recall")
                if refused and "CX" in t:
                    if cur is None or prev != r - 1:
                        cur = {"key": k, "c": c, "who": name[c], "r0": r, "why": why, "len": 0, "bag": t["TT"]["gems"] if "TT" in t else 0, "result": g["result"],
                               "whys": Counter()}
                        runs.append(cur)
                    cur["len"] += 1
                    cur["whys"][why] += 1
                    prev = r
                else:
                    cur = None
            for run in [x for x in runs if x["key"] == k and x["c"] == c]:
                r0 = run["r0"]
                run["clean"] = not any(x in hurt[c] for x in range(r0, r0 + NEED + 1))
                # Stricter: frozen on the tile we stood on, no enemy's actual path came within FAR of it while the recall
                # ran (a pursuer following our walk would pass it), and nothing was hitting us there as it began.
                me = chs[c]
                i0 = r0 - 2  # the end of round r0 - 1: where the turn in r0 starts
                tile = (me["x"][i0], me["y"][i0]) if 0 <= i0 < len(me["x"]) and me["x"][i0] is not None else None
                near = 99
                if tile:
                    for e2 in theirs:
                        ch2 = chs[e2]
                        for x in range(r0 - 1, r0 + NEED + 1):
                            i = x - 1
                            if 0 <= i < len(ch2["x"]) and ch2["alive"][i] and ch2["x"][i] is not None:
                                near = min(near, max(abs(ch2["x"][i] - tile[0]), abs(ch2["y"][i] - tile[1])))
                run["near"] = near
                run["strict"] = tile is not None and near > FAR and not any(x in hurt[c] for x in (r0 - 1, r0))
                run["deaths"] = [(k, c, x) for x, b in died[c] if r0 <= x <= r0 + 20]
                run["first_hurt"] = min((x - r0 for x in hurt[c] if x >= r0), default=None)
                dd = [(x, b) for x, b in died[c] if r0 <= x <= r0 + 20]
                run["died20"] = bool(dd)
                run["lost"] = dd[0][1] if dd else 0
                run["home20"] = any(on_spawn(c, x) for x in range(r0, min(r0 + 21, len(chs[c]["x"]) + 1))) and not dd
    runs = [x for x in runs if x["bag"] >= a.bag and "clean" in x]
    n = len(runs)
    print(f"{n} runs of refused retreat recalls (bag >= {a.bag}), in trusted rounds of {len(man)} games")
    print("first refusing test      runs  no damage in the 5 rounds  no enemy within 5 of the tile either | then: home in 20  died in 20 | distinct deaths in 20, gems; of them after a recall that would have landed (strict)")
    for why in ("does not outrun", "threatened here", "walk beats recall"):
        S = [x for x in runs if x["why"] == why]
        if not S:
            continue
        cl, sc = sum(x["clean"] for x in S), sum(x["strict"] for x in S)
        dd = {}
        for x in S:
            for dk in x["deaths"]:
                dd.setdefault(tuple(dk), [x["lost"], False])
                dd[tuple(dk)][1] |= x["strict"]
        print(f"  {why:22s} {len(S):5d}  {cl:5d} {100 * cl / len(S):3.0f}%   {sc:5d} {100 * sc / len(S):3.0f}% | {sum(x['home20'] for x in S):5d} {100 * sum(x['home20'] for x in S) / len(S):3.0f}%  "
              f"{sum(x['died20'] for x in S):5d} {100 * sum(x['died20'] for x in S) / len(S):3.0f}% | {len(dd)} deaths, {sum(v[0] for v in dd.values())} gems; "
              f"{sum(1 for v in dd.values() if v[1])} deaths, {sum(v[0] for v in dd.values() if v[1])} gems")
    for res in ("win", "loss"):
        S = [x for x in runs if x["why"] == "does not outrun" and x["result"] == res]
        if S:
            print(f"  'does not outrun' runs in our {res}s: {len(S)}; would land {sum(x['clean'] for x in S)}; died in 20 {sum(x['died20'] for x in S)}")
    S = [x for x in runs if x["why"] == "does not outrun"]
    by = defaultdict(list)
    for x in S:
        by[x["who"]].append(x)
    print("  'does not outrun' by champion: " + ", ".join(f"{w} {len(v)} (land {sum(x['clean'] for x in v)}, died {sum(x['died20'] for x in v)})" for w, v in sorted(by.items(), key=lambda kv: -len(kv[1]))))
    hist = Counter(min(x["first_hurt"], 10) if x["first_hurt"] is not None else 99 for x in S)
    print("  rounds from the first refusal to the first damage ('does not outrun'; 10 = 10+, 99 = never):", dict(sorted(hist.items())))
    (V / "analysis/retreat_recall.json").write_text(json.dumps([{**x, "whys": dict(x["whys"])} for x in runs]))


if __name__ == "__main__":
    main()
