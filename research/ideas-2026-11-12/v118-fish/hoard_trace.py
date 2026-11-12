"""What our bot decided before each big-bag death: the trace of the victim's last turns.

    py research/ideas-2026-11-12/v118-fish/hoard_trace.py [--bag 100] [--show KEY] [--window 40] [--wins]

For every own death with a bag of --bag gems or more (replays/v118/analysis/deaths.jsonl), reads the victim's turns
from the traced re-run (runs/direct, only rounds the re-run shares with the live game) and reports:
- the bag's state: winning (score + bag >= 1000), banking (branch B / W / T / t on any of the last --window turns), or kept;
- want_home over the window: turns it said yes, the first reason, and how long before the death it first said yes;
- what the turn then did: branch letters of the last 12 turns;
- the recall test on the turns that wanted home: which condition refused it (CR bits);
- our belief of the killer: seen, its Strength and max health, its distance at our turn ends;
- the killer's blows: turns between first hit and death, our health at the first hit.
"""
import argparse, json, statistics as st, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tracelib as T  # noqa: E402

A = T.V / "analysis"


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def study(d, tr, window):
    """One death: per-turn rows over the window and the summary."""
    v, by, r = d["vid"], d["by_id"], d["r"]
    rows = []
    for x in range(max(1, r - window), r + 1):
        t = tr.turn(x, v)
        if not t or "TT" not in t:
            continue
        tt = t["TT"]
        if not tt["alive"]:
            continue
        eb = {e["e"]: e for e in t.get("EB", [])}
        k = eb.get(by)
        wh = [w["code"] for w in t.get("WH", [])]
        rows.append({"r": x, "branch": tt["branch"], "pos": (tt["ex"], tt["ey"]), "start": (tt["sx"], tt["sy"]), "hp": tt["hp"], "maxhp": tt["maxhp"],
                     "gems": tt["gems"], "score": tt["score_us"], "them": tt["score_them"], "winning": tt["winning"], "wh": wh,
                     "cr": t.get("CR"), "cx": "CX" in t,
                     "k": None if not k else {"vis": k["visible"], "d": cheb((tt["ex"], tt["ey"]), (k["x"], k["y"])), "hp": k["hp"], "maxhp": k["maxhp"],
                                              "str": k["str"], "age": x - k["pos_round"]}})
    return rows


def summarise(d, rows):
    if not rows:
        return None
    last = rows[-1]
    home = [x for x in rows if any(c > 0 for c in x["wh"])]
    first_home = home[0]["r"] if home else None
    # the first round of the final unbroken run of want_home turns
    run_start = None
    for x in reversed(rows):
        if any(c > 0 for c in x["wh"]):
            run_start = x["r"]
        else:
            break
    reasons = Counter(next(c for c in x["wh"] if c > 0) for x in home)
    seen = [x for x in rows if x["k"] and x["k"]["vis"]]
    refused = Counter()
    for x in home:
        cr = x["cr"]
        if not cr or not cr["home"]:
            continue
        b = cr["bits"]
        read = b >> 8
        if read & 1 and b & 1:
            refused["walk beats recall"] += 1
        elif read & 2 and b & 2:
            refused["threatened here"] += 1
        elif read & 4 and b & 4:
            refused["can tribute safely"] += 1
        elif read & 8 and not b & 8:
            refused["recall does not outrun"] += 1
        elif read & 8 and b & 8:
            refused["kept"] += 1
    banking = any(x["branch"] in "BWTt" for x in rows[-12:])
    moved = sum(1 for x in rows[-12:] if x["pos"] != x["start"])
    # ping-pong: positions repeating A-B-A in the last 20 turns
    ps = [x["pos"] for x in rows[-20:]]
    flips = sum(1 for i in range(2, len(ps)) if ps[i] == ps[i - 2] and ps[i] != ps[i - 1])
    return {"key": d["key"], "r": d["r"], "victim": d["victim"], "by": d["by"], "bag": d["bag"], "result": d["result"],
            "winning": last["winning"], "short": 1000 - last["score"] - last["gems"], "banking": banking, "last12": "".join(x["branch"] for x in rows[-12:]),
            "home_turns": len(home), "first_home": (d["r"] - first_home) if first_home else None, "run": (d["r"] - run_start) if run_start else 0,
            "reasons": dict(reasons), "seen_turns": len(seen), "first_seen": (d["r"] - seen[0]["r"]) if seen else None,
            "kstr": seen[-1]["k"]["str"] if seen else None, "kmaxhp": seen[-1]["k"]["maxhp"] if seen else None,
            "kd_last": last["k"]["d"] if last["k"] else None, "hp_frac": last["hp"] / max(1, last["maxhp"]), "maxhp": last["maxhp"],
            "refused": dict(refused), "moved12": moved, "flips20": flips, "last_branch": last["branch"], "rows": len(rows),
            "last_home": bool(last["wh"]) and any(c > 0 for c in last["wh"])}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bag", type=int, default=100)
    ap.add_argument("--window", type=int, default=40)
    ap.add_argument("--show")
    ap.add_argument("--wins", action="store_true", help="deaths in our wins too")
    ap.add_argument("--json")
    a = ap.parse_args()
    deaths = [json.loads(l) for l in open(A / "deaths.jsonl")]
    sel = [d for d in deaths if d["us"] and d["bag"] >= a.bag and d["kind"] == "death" and (a.wins or d["result"] == "loss")]
    if a.show:
        sel = [d for d in sel if d["key"] == a.show]
    out, untrusted = [], 0
    cache = {}
    for d in sorted(sel, key=lambda d: (d["key"], d["r"])):
        tr = cache.get(d["key"]) or cache.setdefault(d["key"], T.load(d["key"]))
        if tr.trusted < d["r"] - 1:
            untrusted += 1
            continue
        rows = study(d, tr, a.window)
        s = summarise(d, rows)
        if not s:
            untrusted += 1
            continue
        out.append(s)
        if a.show:
            print(f"{d['key']} r{d['r']} {d['victim']} killed by {d['by']} with {d['bag']} gems; trusted through r{tr.trusted}")
            for x in rows:
                k = x["k"]
                cr = x["cr"]
                print(f"  r{x['r']} {x['branch']} {x['start']}->{x['pos']} hp {x['hp']}/{x['maxhp']} bag {x['gems']} score {x['score']}-{x['them']} win {x['winning']} "
                      f"WH {x['wh']} CR {(cr['home'], bin(cr['bits'])) if cr else None}{' CX' if x['cx'] else ''} "
                      f"killer {('seen' if k['vis'] else 'unseen age ' + str(k['age'])) + ' d ' + str(k['d']) + ' hp ' + str(k['hp']) + '/' + str(k['maxhp']) + ' str ' + str(k['str']) if k else None}")
    n = len(out)
    print(f"\n{len(sel)} deaths with {a.bag}+ gems; traced through the death: {n}; not trusted to the death: {untrusted}")
    if not n:
        return
    P = [s for s in out if s["victim"] == "Prism"]
    for name, S in (("all", out), ("Prism", P)):
        m = len(S)
        if not m:
            continue
        print(f"\n== {name}: {m} deaths; bag median {st.median(s['bag'] for s in S)}")
        print(f"  bag state at the last turn: winning {sum(s['winning'] for s in S)}; banking branch (B/W/T/t) in the last 12 turns {sum(s['banking'] for s in S)}; "
              f"gems short of the win (1000 - score - bag) median {st.median(s['short'] for s in S)}")
        print(f"  want_home said yes on some turn in the window: {sum(s['home_turns'] > 0 for s in S)}; on the last turn: {sum(s['last_home'] for s in S)}; "
              f"final unbroken run of yes turns before the death, median {st.median(s['run'] for s in S)} (quartiles {st.quantiles([s['run'] for s in S], n=4)})")
        rs = Counter()
        for s in S:
            for k, v in s["reasons"].items():
                rs[T.WH_REASON[k]] += v
        print(f"  want_home reasons over those turns: {dict(rs)}")
        print(f"  killer seen at some turn end in the window: {sum(s['seen_turns'] > 0 for s in S)}; rounds from first sight to death, median "
              f"{st.median(s['first_seen'] for s in S if s['first_seen'] is not None)}; believed Strength median {st.median(s['kstr'] for s in S if s['kstr'])}, "
              f"max health median {st.median(s['kmaxhp'] for s in S if s['kmaxhp'])}; our max health median {st.median(s['maxhp'] for s in S)}")
        rf = Counter()
        for s in S:
            for k, v in s["refused"].items():
                rf[k] += v
        print(f"  recall test on turns that wanted home (a recall was running): {dict(rf)}")
        print(f"  last branch: {dict(Counter(s['last_branch'] for s in S).most_common())}")
        print(f"  branch mix over the last 12 turns: {dict(Counter(c for s in S for c in s['last12']).most_common())}")
        print(f"  A-B-A position flips in the last 20 turns: median {st.median(s['flips20'] for s in S)}, 5+ flips in {sum(s['flips20'] >= 5 for s in S)} deaths")
        print(f"  health share at the last turn's end: median {st.median(s['hp_frac'] for s in S):.2f}; at 90%+ {sum(s['hp_frac'] >= 0.9 for s in S)}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=0))
    else:
        for s in sorted(out, key=lambda s: -s["bag"])[:200]:
            print(f"{s['key']} r{s['r']:4d} {s['victim'][:5]:5s}<{(s['by'] or '?')[:5]:5s} bag {s['bag']:4d} short {s['short']:5d} win {s['winning']} bank {int(s['banking'])} last12 {s['last12']:12s} "
                  f"home {s['home_turns']:2d} run {s['run']:2d} seen {s['first_seen']} kstr {s['kstr']} khp {s['kmaxhp']} d {s['kd_last']} hp {s['hp_frac']:.2f}/{s['maxhp']} flips {s['flips20']} {s['refused']}")


if __name__ == "__main__":
    main()
