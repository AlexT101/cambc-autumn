#!/usr/bin/env python3
"""Tabulate WLK lines (winst.py) from batch dirs: python3 wan.py BATCHDIR... [--pkl OUT]"""
import sys, zipfile, pickle, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np

PARTS = {0: "route", 1: "route_around", 2: "occupied_into", 3: "search(host)", 4: "kept_steps", 5: "travel", 6: "ahead",
         7: "walk_round route", 8: "plan", 9: "landing_veto", 10: "guard fn", 11: "guard cover", 12: "move_to", 13: "dash_to",
         14: "pull", 15: "fight_near", 16: "travel_dash", 17: "enclosed", 18: "descend_with", 19: "step_field",
         20: "search_approach", 21: "make_way/labelled", 22: "know_failure", 23: "blocked", 24: "closer_neighbours",
         25: "walk_parted", 26: "round_fails", 27: "near_crossings", 28: "take", 29: "plan boards", 30: "plan ends loop",
         31: "#plan ends", 32: "#plan w field", 33: "ra walls", 34: "ra first steps", 35: "ra found bookkeeping",
         36: "#ahead tiles", 37: "make_pull", 38: "plan guard", 39: "plan blocked", 40: "plan shut bits",
         41: "plan camps+passes", 42: "plan dash_from", 44: "turns_at", 45: "ra scan", 46: "#first steps"}


def one(p):
    recs = []
    try:
        z = zipfile.ZipFile(p)
    except Exception:
        return recs
    with z:
        for t in "ab":
            try:
                s = z.read(f"team-{t}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
            except KeyError:
                continue
            for line in s.splitlines():
                if not line.startswith("WLK ") or line.count("|") != 2:
                    continue
                h, acc, ev = line.split("|")
                h = h.split()
                if len(h) != 8:
                    continue
                r = dict(map=Path(p).stem, round=int(h[1]), handle=int(h[2]), entry=h[3], cut=int(h[4]), bank=int(h[5]),
                         total=int(h[6]), chunks=int(h[7]), acc={}, ev=ev.split())
                for a in acc.split():
                    k, v = a.split(":")
                    f, c = v.split("/")
                    r["acc"][int(k)] = (int(f), int(c))
                recs.append(r)
    return recs


def q(xs, ps=(50, 90, 99)):
    xs = np.array(xs, dtype=float)
    if len(xs) == 0:
        return "n=0"
    return f"n={len(xs):7d} mean {xs.mean()/1000:6.2f}k " + " ".join(f"p{p}={np.percentile(xs, p)/1000:6.2f}k" for p in ps)


def main():
    args = sys.argv[1:]
    pkl = None
    if "--pkl" in args:
        i = args.index("--pkl")
        pkl = args[i + 1]
        del args[i:i + 2]
    recs = []
    if args and args[0].endswith(".pkl"):
        recs = pickle.load(open(args[0], "rb"))
        report(recs)
        return
    paths = [str(p) for d in args for p in Path(d).rglob("*.repl26a")] + [str(p) for d in args for p in Path(d).rglob("*.zip")]
    with ProcessPoolExecutor(32) as ex:
        for rs in ex.map(one, paths, chunksize=4):
            recs.extend(rs)
    if pkl:
        pickle.dump(recs, open(pkl, "wb"))
    print(f"{len(paths)} replays, {len(recs)} walks")
    report(recs)


def report(recs):
    for name, sel in [("all", lambda r: True), ("cut nb", lambda r: r["cut"] and not r["bank"]), ("cut bank", lambda r: r["cut"] and r["bank"]),
                      ("uncut", lambda r: not r["cut"])]:
        rs = [r for r in recs if sel(r)]
        if not rs:
            continue
        print(f"\n== {name}: walks {q([r['total'] for r in rs])}")
        # Per turn (sum of walks).
        turns = collections.Counter()
        for r in rs:
            turns[(r["map"], r["round"], r["handle"])] += r["total"]
        print(f"   per turn {q(list(turns.values()))}")
        ent = collections.Counter(r["entry"] for r in rs)
        print("   entries:", dict(ent))
        tot = sum(r["total"] for r in rs)
        print(f"   {'part':20s} {'fuel/walk':>9s} {'share':>6s} {'calls/walk':>10s} {'per call':>8s} {'p99/walk':>8s}")
        for k, nm in PARTS.items():
            f = [r["acc"].get(k, (0, 0))[0] for r in rs]
            c = sum(r["acc"].get(k, (0, 0))[1] for r in rs)
            if not c:
                continue
            print(f"   {nm:20s} {np.mean(f):9.0f} {sum(f)/tot:6.1%} {c/len(rs):10.2f} {sum(f)/c:8.0f} {np.percentile(f, 99):8.0f}")
        # Searches.
        ss = collections.defaultdict(list)
        ratio = []
        for r in rs:
            for e in r["ev"]:
                if e[0] == "S" and e.count("/") == 3:
                    kind = e[1]
                    lay, cap, fuel, at = e[2:].split("/")
                    ss[kind].append((int(lay), int(cap), int(fuel), int(at)))
                    ratio.append(int(fuel) / (r["chunks"] * (16 + int(lay)) + 30))
        for kind, v in ss.items():
            lay = [x[0] for x in v]
            fu = [x[2] for x in v]
            found = sum(1 for x in v if x[3] != 65535)
            print(f"   search {kind}: {len(v)} ({len(v)/len(rs):.2f}/walk), found {found/len(v):.0%}, layers p50 {np.percentile(lay,50):.0f} p90 {np.percentile(lay,90):.0f}, fuel {q(fu)}")
        if ratio:
            print(f"   search fuel / (chunks*(16+layers)+30): p50 {np.percentile(ratio,50):.3f} p10 {np.percentile(ratio,10):.3f} p90 {np.percentile(ratio,90):.3f}")
        # Kept tests and what followed.
        why = collections.Counter()
        follow_fuel = collections.Counter()
        wide_ok = collections.Counter()
        changed = []
        for r in rs:
            ev = r["ev"]
            for i, e in enumerate(ev):
                if e[0] != "K" or e.count("/") != 4:
                    continue
                w, kind = e[1], e[2]
                parts = e[3:].split("/")
                ch, gd, wide = int(parts[0]), int(parts[1]), int(parts[2])
                why[(w, kind)] += 1
                nxt = ev[i + 1] if i + 1 < len(ev) else ""
                sf = 0
                if nxt.startswith("S") and nxt.count("/") == 3:
                    sf = int(nxt[2:].split("/")[2])
                follow_fuel[(w, kind)] += sf
                if w in "MT":
                    changed.append(ch)
                    if wide == 1:
                        wide_ok[(w, kind)] += 1
                        follow_fuel[("wide-ok", w, kind)] += sf
        print("   kept tests (why, kind): count, search fuel after, all-tile test passes")
        for key, n in sorted(why.items(), key=lambda kv: -kv[1]):
            print(f"     {key}: {n} ({n/len(rs):.2f}/walk), search fuel after {follow_fuel[key]/len(rs):.0f}/walk, wide ok {wide_ok.get(key,0)} ({follow_fuel.get(('wide-ok',)+key,0)/len(rs):.0f}/walk)")
        if changed:
            print(f"   changed tiles on M/T misses: p50 {np.percentile(changed,50):.0f} p90 {np.percentile(changed,90):.0f}")


if __name__ == "__main__":
    main()
