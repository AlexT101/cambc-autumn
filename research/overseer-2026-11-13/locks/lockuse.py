"""What a lock-using bot's locks did, from extracted replays (tools/replay/extract.mjs --out DIR).

    python3 lockuse.py DIR LOCKBOT [OTHERBOT]

Per game length bucket: lock buys and placements by LOCKBOT; placements that cancelled tributes (whose, how many
gems) and pre-emptive ones; enemy tributes blocked by its locks; its locks destroyed; and deaths beside an enemy
tribute (a LOCKBOT body dying within 3 of an altar an enemy is tributing at, carrying a lock or not) against the
same count for OTHERBOT's bodies. Win rate of LOCKBOT by bucket.
"""
import gzip, json, sys
from collections import Counter, defaultdict
from pathlib import Path


def bucket(r):
    return "<600" if r < 600 else "600-899" if r < 900 else "900-1499" if r < 1500 else "1500+"


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def main():
    root, lockbot = Path(sys.argv[1]), sys.argv[2]
    tot = defaultdict(Counter)
    for d in sorted(p for p in root.iterdir() if (p / "meta.json").exists()):
        m = json.load(open(d / "meta.json"))
        names = [t["name"] for t in m["teams"]]
        if lockbot not in names: continue
        L = names.index(lockbot)
        rounds = m["result"]["rounds"]
        b = bucket(rounds)
        c = tot[b]
        c["games"] += 1
        c["wins"] += m["result"]["winner"] == L
        team = {ch["id"]: ch["team"] for ch in m["champions"]}
        mp = json.load(open(d / m["mapFile"])) if (d / m["mapFile"]).exists() else None
        ev = [json.loads(l) for l in gzip.open(d / "events.jsonl.gz", "rt")]
        by_step = defaultdict(list)
        for e in ev: by_step[e["s"]].append(e)
        tributing = {}  # champion -> (altar tile, gems) while channelling
        recent_cancel = []  # (round, altar tile) of L's locks that cancelled an enemy tribute
        for e in ev:
            k = e["k"]
            if k == "tribute_start": tributing[e["a"]] = (tuple(e["altar"]) if isinstance(e.get("altar"), list) else e.get("at"), e["gems"])
            elif k in ("tribute_end", "tribute_cancel"): tributing.pop(e["a"], None)
            if k == "shop" and team.get(e["a"]) == L and e.get("cons", {}).get("Altar lock", 0) > 0:
                c["buys"] += e["cons"]["Altar lock"]
            elif k == "consumable" and team.get(e["a"]) == L and "altar_lock" in e.get("cons", {}):
                pass
            elif k == "lock_place" and e["team"] == L:
                c["places"] += 1
                cancels = [x for x in by_step[e["s"]] if x["k"] == "tribute_cancel" and x.get("cause") == "lock"]
                if not cancels: c["preempt"] += 1
                if any(team.get(x["a"]) != L for x in cancels): recent_cancel.append((e["r"], tuple(e["to"])))
                for x in cancels:
                    own = team.get(x["a"]) == L
                    if not own:
                        # What became of the cancelled bag: banked by that champion, or lost with it.
                        fate = "fate_open"
                        for y in ev:
                            if y["s"] <= x["s"]: continue
                            if y["k"] == "tribute_end" and y["a"] == x["a"]: fate = "fate_banked"; break
                            if y["k"] == "death" and y["v"] == x["a"]: fate = "fate_killed"; break
                        c[fate] += 1
                    c["cancel_own" if own else "cancel_enemy"] += 1
                    c["cancel_own_gems" if own else "cancel_enemy_gems"] += x["gems"]
                    if not own and x["gems"] >= 20: c["cancel_enemy_20+"] += 1
            elif k == "tribute_cancel" and e.get("cause") == "manual":
                side = "L" if team.get(e["a"]) == L else "O"
                c[f"own_cancel_manual_{side}"] += 1
                c[f"own_cancel_manual_gems_{side}"] += e["gems"]
            elif k == "tribute_blocked" and team.get(e["a"]) != L:
                c["enemy_blocked"] += 1
                c["enemy_blocked_gems"] += e["gems"]
            elif k == "tribute_blocked" and team.get(e["a"]) == L:
                c["own_blocked"] += 1
            elif k == "lock_destroyed":
                c["destroyed_ours" if e["team"] == L else "destroyed_theirs"] += 1
            elif k == "death":
                v = e["v"]
                side = "L" if team.get(v) == L else "O"
                c[f"deaths_{side}"] += 1
                c[f"death_gems_{side}"] += e.get("gems", 0)
                at = e.get("at")
                if at and any(e["r"] - r0 <= 15 and cheb(at, t0) <= 4 for r0, t0 in recent_cancel):
                    c[f"deaths_after_cancel_{side}"] += 1
                    c[f"deaths_after_cancel_gems_{side}"] += e.get("gems", 0)
                if at:
                    near = any(team.get(t) != team.get(v) and tile and cheb(at, tile) <= 3 for t, (tile, _) in tributing.items())
                    if near:
                        c[f"deaths_by_tribute_{side}"] += 1
                        c[f"deaths_by_tribute_gems_{side}"] += e.get("gems", 0)
    keys = ["games", "wins", "buys", "places", "preempt", "cancel_enemy", "cancel_enemy_gems", "cancel_enemy_20+", "fate_banked", "fate_killed", "fate_open", "cancel_own",
            "cancel_own_gems", "enemy_blocked", "enemy_blocked_gems", "own_blocked", "destroyed_ours", "destroyed_theirs", "deaths_L",
            "deaths_O", "deaths_by_tribute_L", "deaths_by_tribute_O", "deaths_by_tribute_gems_L", "deaths_by_tribute_gems_O",
            "deaths_after_cancel_L", "deaths_after_cancel_O", "deaths_after_cancel_gems_L", "deaths_after_cancel_gems_O", "own_cancel_manual_L", "own_cancel_manual_O", "own_cancel_manual_gems_L", "own_cancel_manual_gems_O", "death_gems_L", "death_gems_O"]
    order = ["<600", "600-899", "900-1499", "1500+"]
    allc = sum((tot[b] for b in order), Counter())
    print("per game (sums / games):")
    print(f"{'':28s}" + "".join(f"{b:>11s}" for b in order + ["all"]))
    for k in keys:
        row = [tot[b][k] for b in order] + [allc[k]]
        g = [tot[b]["games"] for b in order] + [allc["games"]]
        if k == "games": print(f"{k:28s}" + "".join(f"{x:>11d}" for x in row))
        else: print(f"{k:28s}" + "".join(f"{x / max(1, n):>11.3f}" for x, n in zip(row, g)))


main()
