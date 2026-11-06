"""Fuel round 6 bench summary: OOF turns, mean fuel, farm cut short, and (at 100M) the decision change rate.

    python3 research/ideas-2026-11-05/fuel6-tools/an.py TAG [BASE]      # modes found under replays/fuel/fuelbud/bench

Per mode (def/wide/pool at 100M, wide/pool at the real budget), from the JSON and the kept games:
- oof: the bot's out-of-fuel play turns (bench JSON); fuel: mean fuel a play turn (rounds 2+);
- farm-cut: farm-partial-evaluation SHORTCUT lines of our bot per farm-branch turn (D lines with 'F');
- at 100M against BASE (default base): identical replays, and the decision change rate: each game is compared with
  the base's game on the same map and side until the first round where our D lines or the opponent's stdout differ
  (the opponent is the same bot in both, so its output changes only once our play reaches it). Rate = diverged games
  / our turns played before divergence (an exposure estimate, so 1 change per N turns).
"""
import json
import re
import statistics
import sys
import zipfile
from pathlib import Path

D = Path("/home/ubuntu/cambc-autumn/replays/fuel/fuelbud/bench")


def bundle(gdir, key):
    p = list((gdir / key).glob("*.repl26a"))
    return p[0] if p else None


def lines(b, team):
    with zipfile.ZipFile(b) as z:
        return z.read(f"team-{team}.stdout").decode("utf-8", "replace").splitlines()


def dlines(ls):
    return [l for l in ls if l.startswith("D ")]


def stats(tag, mode):
    j = D / f"{tag}-{mode}.json"
    if not j.exists():
        return None
    data = json.load(open(j))
    g = D / f"g-{tag}-{mode}"
    oof = sum(x.get("out_of_fuel", 0) for x in data["games"] if "error" not in x)
    farm_t = cut = turns = 0
    for x in data["games"]:
        key = f"{Path(x['path']).stem if x['path'].endswith('.map26a') else x['map']}-{x['side']}"
        b = bundle(g, key) if g.exists() else None
        if not b:
            continue
        ls = lines(b, x["side"])
        ds = dlines(ls)
        turns += len(ds)
        farm_t += sum(1 for l in ds if l.split()[3] == "F")
        cut += sum(1 for l in ls if l.startswith("SHORTCUT") and l.endswith("farm-partial-evaluation"))
    return data, oof, data["all"]["mean"], cut, farm_t, turns


def first_div(bc, bb, side):
    other = "b" if side == "a" else "a"
    dc, db = dlines(lines(bc, side)), dlines(lines(bb, side))
    rd = None
    for i, (x, y) in enumerate(zip(dc, db)):
        if x != y:
            rd = int(x.split()[1]) if x.split()[1] == y.split()[1] else min(int(x.split()[1]), int(y.split()[1]))
            break
    else:
        if len(dc) != len(db):
            k = min(len(dc), len(db))
            rd = int((dc if len(dc) > k else db)[k].split()[1])
    oc, ob = lines(bc, other), lines(bb, other)
    last = 0
    for x, y in zip(oc, ob):
        if x.startswith("D "):
            last = int(x.split()[1])
        if x != y:
            ro = last + 1
            rd = ro if rd is None else min(rd, ro)
            break
    # our turns before rd
    n = sum(1 for l in db if rd is None or int(l.split()[1]) < rd)
    return rd, n


def main():
    tag = sys.argv[1]
    base = sys.argv[2] if len(sys.argv) > 2 else "base"
    for mode in ("def-100M", "wide-100M", "pool-100M", "wide-real", "pool-real"):
        s = stats(tag, mode)
        if not s:
            continue
        data, oof, mean, cut, farm_t, turns = s
        out = f"{mode:10s} oof {oof:5d} fuel {mean:6.0f} farm-cut {cut:6d}/{farm_t:6d} = {cut / max(1, farm_t):.3f} turns {turns}"
        if mode.endswith("100M") and tag != base:
            bj = D / f"{base}-{mode}.json"
            if bj.exists():
                bd = json.load(open(bj))
                key = lambda x: (x["map"], x["side"])
                bm = {key(x): x for x in bd["games"] if "error" not in x}
                same = div = expo = 0
                rounds = []
                fb = fc = hb = hc = ob = oc = nt = 0
                for x in data["games"]:
                    if "error" in x or key(x) not in bm:
                        continue
                    if x["replay"] == bm[key(x)]["replay"]:
                        same += 1
                    k = f"{Path(x['path']).stem if x['path'].endswith('.map26a') else x['map']}-{x['side']}"
                    bc, bb = bundle(D / f"g-{tag}-{mode}", k), bundle(D / f"g-{base}-{mode}", k)
                    if not (bc and bb):
                        continue
                    rd, n = first_div(bc, bb, x["side"])
                    expo += n
                    # fuel on the same states: our play turns (rounds 2+) before the first divergence
                    pb, pc = bm[key(x)]["play"], x["play"]
                    per = x.get("bodies") or 1
                    k = len(pb) if rd is None else max(0, min(len(pb), len(pc), (rd - 2) * per))
                    for u, v in zip(pb[:k], pc[:k]):
                        fb += u; fc += v; nt += 1
                        if u >= 70000: hb += u; hc += v
                        ob += u > 100000; oc += v > 100000
                    if rd is not None:
                        div += 1
                        rounds.append(rd)
                out += f" | identical {same}/{len(data['games'])} diverged {div} first-div median r{statistics.median(rounds) if rounds else '-'}"
                out += f" rate 1/{expo / div:.0f} turns" if div else f" rate 0/{expo}"
                if nt:
                    out += f"\n{'':10s} same-state turns {nt}: fuel {(fc - fb) / fb:+.2%}, heavy(>=70k) {(hc - hb) / max(1, hb):+.2%}, >100k {ob} -> {oc}"
        print(out)


main()
