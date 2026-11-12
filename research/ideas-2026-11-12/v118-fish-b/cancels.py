"""Our own cancels of a winning-bag tribute (score + bag >= 1000): what the next `left` rounds held (replay), and what
the bot did next (exact D branches).

    py research/ideas-2026-11-12/v118-fish-b/cancels.py
For each manual cancel with `left` turn ends to go: the carrier's health then, the champion damage it took over the next
`left` rounds (while doing whatever it did instead), stuns on it, enemy locks placed on that altar in the window, enemies
within 6 at the cancel. "survivable" = damage taken in the window below its health, no stun, no enemy lock at that
altar: the channel would have completed had the enemy acted as it did (it would have hit a standing target harder, so
this is an upper bound). Also the same for cancels by a lock: how far the enemy locker was and whether we had hit it."""
import json, os, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
os.environ["CAMBC_ANALYSIS"] = str(REPO / "replays/v118b/analysis")
sys.path.insert(0, str(REPO / "tools/replay"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis.data import Game, chebyshev  # noqa: E402
import dlib  # noqa: E402


def one(f):
    g = Game(f["dir"]); us = 0 if f["side"] == "a" else 1
    R = g.rounds; ch = R["champions"]; n = len(R["round"])
    b = dlib.branches("d", f["key"])
    out = []
    start = {}
    dmg = {}
    for s, r, a, v, amt, *_ in g.champ_damage:
        dmg.setdefault(v, []).append((r, amt, a))
    stuns = {}
    for e in g.events:
        if e.get("stun"):
            for v in e["stun"]:
                stuns.setdefault(v, []).append(e["r"])
    locks = [(e["r"], tuple(e["to"]), e["a"]) for e in g.events if e["k"] == "lock_place" and e["team"] != us]
    for e in g.events:
        if e["k"] == "tribute_start" and g.team_of[e["a"]] == us:
            start[e["a"]] = e
        elif e["k"] == "tribute_cancel" and e["a"] in start:
            s = start.pop(e["a"]); c = e["a"]; r = e["r"]
            sc = R["gems"][us][max(0, s["r"] - 2)]
            if sc + s["gems"] < 1000:
                continue
            left = e.get("left") or 0
            a = ch[g.idx[c]]; i = max(0, r - 2)
            hp = a["hp"][i]
            taken = sum(amt for rr, amt, _ in dmg.get(c, []) if r <= rr <= r + left)
            stunned = any(r <= rr <= r + left for rr in stuns.get(c, []))
            altar = tuple(s["altar"]) if s.get("altar") else None
            locked = any(r <= rr <= r + left and (altar is None or at == altar) for rr, at, _ in locks)
            p = g.pos(c, i)
            near = sum(1 for x in g.team_ids[1 - us] if g.pos(x, i) and p and chebyshev(g.pos(x, i), p) <= 6)
            died = any(d["v"] == c and r <= d["r"] <= r + left for d in g.deaths)
            row = {"key": f["key"], "res": f["result"], "r": r, "cause": e.get("cause"), "left": left, "gems": s["gems"], "hp": round(hp / a["maxHp"][i], 2),
                   "taken": round(taken), "hp_abs": round(hp), "stunned": stunned, "locked": locked, "near6": near, "died": died,
                   "next": "".join(b.get((rr, c), "?") for rr in range(r, min(n, r + 6) + 1)), "prev_dmg": round(sum(amt for rr, amt, _ in dmg.get(c, []) if r - 2 <= rr < r))}
            if e.get("cause") == "lock":
                lk = [x for x in locks if x[0] == r]
                if lk:
                    who = lk[0][2]; wp = g.pos(who, i)
                    row["locker"] = g.name_of[who]; row["locker_d"] = chebyshev(wp, p) if wp and p else None
                    row["locker_seen_rounds"] = sum(1 for rr in range(max(1, r - 10), r) if who in a["sees"][rr - 1])
                    row["we_hit_locker"] = round(sum(amt for rr, amt, at in dmg.get(who, []) if r - 10 <= rr <= r and g.team_of[at] == us))
            out.append(row)
        elif e["k"] in ("tribute_end",) and e["a"] in start:
            start.pop(e["a"])
    return out


if __name__ == "__main__":
    F = json.load(open(REPO / "replays/v118b/feat.json"))
    with ProcessPoolExecutor(20) as ex:
        S = [d for ds in ex.map(one, F, chunksize=4) for d in ds]
    json.dump(S, open(REPO / "replays/v118b/cancels.json", "w"))
    M = [s for s in S if s["cause"] == "manual"]
    print(len(S), "cancels of a winning-bag channel:", dict(Counter(s["cause"] for s in S)))
    for res in ("win", "loss"):
        T = [s for s in M if s["res"] == res]
        surv = [s for s in T if s["taken"] < s["hp_abs"] and not s["stunned"] and not s["locked"]]
        nodmg = [s for s in T if s["taken"] == 0 and not s["stunned"] and not s["locked"]]
        import statistics as st
        print(f"manual cancels in {res}es: {len(T)} in {len({s['key'] for s in T})} games; turns left median {st.median(s['left'] for s in T)}; no champion damage in the 2 rounds before {sum(s['prev_dmg'] == 0 for s in T)}; "
              f"enemies within 6: 0 in {sum(s['near6'] == 0 for s in T)}, 1 in {sum(s['near6'] == 1 for s in T)}, 2+ in {sum(s['near6'] >= 2 for s in T)}")
        print(f"   survivable over the turns left (damage taken < health, no stun, no enemy lock there): {len(surv)} ({100 * len(surv) // max(1, len(T))}%), in {len({s['key'] for s in surv})} games; took no damage at all: {len(nodmg)}; died in the window {sum(s['died'] for s in T)}")
        print(f"   what it did next (first branch after 't'): {Counter(s['next'][1:2] for s in T).most_common(6)}")
    L = [s for s in S if s["cause"] == "lock"]
    print(f"lock cancels: {len(L)} in {len({s['key'] for s in L})} games; turns left median {st.median(s['left'] for s in L)}; locker {Counter(s.get('locker') for s in L).most_common(5)}; "
          f"locker in the carrier's sight for a median {st.median(s.get('locker_seen_rounds', 0) for s in L)} of the 10 rounds before; we had hit the locker in those rounds in {sum(1 for s in L if s.get('we_hit_locker', 0) > 0)}")
    lostk = sorted({s["key"] for s in M if s["res"] == "loss" and s["taken"] < s["hp_abs"] and not s["stunned"] and not s["locked"]})
    print("losses with a survivable manual cancel:", lostk)
