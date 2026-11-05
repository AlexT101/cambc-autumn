"""Ladder draft prior from big-arm's per-day archive (replays/ladder-archive/<day>/data, rsynced from
big-arm:~/cambc-autumn/.oarena/archive/<day>/data): the opponents' compositions in pick order per pick count, as the
draft lab's prior.json.

    py tools/draftlab/ladder_prior.py --engine 3.0.0 --top 15 --half-life 24 --out replays/draftlab/LAB/prior.json \
        [--days 2026-11-04,2026-11-05] [--report research/ladder-drafts-DATE.md] [--ladder-out LAB/ladder.jsonl]

Weights: only the `top` best-rated other teams (by their latest rating in the archive; ours is never counted, as the
prior models the opponents we meet) count, each team-game weighted 2^(-age / half_life hours) from the newest game,
since teams are still adapting after a patch. `n` is the weighted count (a float). The archive's `picks` order is the
lab's CHAMPS order; Cassi and Issac are one pick (two units).
"""
import argparse
import collections
import glob
import json
import math
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MY_TEAM = "547efb5b-57e5-4355-8501-3b331f506d62"
CHAMPS = ["ryth", "vesper_vale", "vendetta", "cassi_and_issac", "stellar", "prism", "marcella", "willow", "ren",
          "varg", "tavi", "heart_of_ruin"]
EMBLEMS = ["monster", "power", "durability", "treasure", "jungle", "home", "bruiser", "tribute", "capture",
           "prospector", "hunter", "skirmish", "greed", "collectors"]


def load_day(d):
    m = json.loads((d / "meta.json").read_text())
    a = {f.stem: np.load(f, allow_pickle=True) for f in d.glob("*.npy")}
    return m, a


def games(days, engine, kind):
    """Yield (created, map, [(team_id, team_name, rating, comp, won, emblems)] x2) per finished game."""
    for d in days:
        m, a = load_day(d)
        if engine not in m["engines"]:
            continue
        eng = m["engines"].index(engine)
        kid = m["kinds"].index(kind)
        teams = m["teams"]
        maps = {x["hash"]: x["name"] for x in m["maps"]}
        units = collections.defaultdict(list)
        for i in range(len(a["u_game"])):
            units[(int(a["u_game"][i]), int(a["u_side"][i]))].append(i)
        for g in range(len(a["g_engine"])):
            if a["g_engine"][g] != eng or a["g_kind"][g] != kid:
                continue
            sides = []
            for s in (0, 1):
                us = sorted(units[(g, s)], key=lambda i: int(a["u_slot"][i]))
                comp = []
                for i in us:
                    c = CHAMPS[int(a["u_pick"][i])]
                    if c not in comp:
                        comp.append(c)
                t = teams[int(a["s_team"][2 * g + s])]
                ems = []
                if "u_first_emblem" in a:
                    ems = [int(a["u_first_emblem"][i]) for i in us]
                sides.append((t["id"], t["name"], float(a["g_rating"][g][s]), comp, int(a["g_winner"][g]) == s, ems))
            mh = a["g_map_hash"][g]
            mh = mh.decode() if isinstance(mh, bytes) else str(mh)
            yield float(a["g_created"][g]), maps.get(mh, mh), sides, str(a["matches"][g].decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", default=str(ROOT / "replays" / "ladder-archive"))
    ap.add_argument("--days", default="", help="comma-separated days (default: every day in the archive)")
    ap.add_argument("--engine", default="3.0.0")
    ap.add_argument("--kind", default="ranked")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--half-life", type=float, default=24.0, help="hours")
    ap.add_argument("--min-n", type=float, default=1.0, help="drop compositions below this weighted count")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ladder-out", default="")
    ap.add_argument("--report", default="")
    args = ap.parse_args()
    days = sorted(Path(p).parent for p in glob.glob(f"{args.archive}/*/data/meta.json"))
    if args.days:
        want = set(args.days.split(","))
        days = [d for d in days if d.parent.name in want]
    days = [d / "data" if d.name != "data" else d for d in days]
    rows = list(games(days, args.engine, args.kind))
    if not rows:
        raise SystemExit(f"no {args.kind} games on engine {args.engine} in {days}")
    latest = {}
    for at, _, sides, _ in sorted(rows, key=lambda r: r[0]):
        for tid, name, rating, *_ in sides:
            latest[tid] = (rating, name)
    ranked = sorted(((t, v) for t, v in latest.items() if t != MY_TEAM), key=lambda kv: -kv[1][0])[:args.top]
    tops = {t for t, _ in ranked}
    newest = max(r[0] for r in rows)
    comps = {p: collections.Counter() for p in (3, 4, 5)}
    raw = {p: collections.Counter() for p in (3, 4, 5)}
    champ = {p: collections.Counter() for p in (3, 4, 5)}
    wins = collections.Counter()
    plays = collections.Counter()
    emblems = collections.Counter()
    ladder = []
    for at, mp, sides, mid in rows:
        w = 0.5 ** ((newest - at) / 3600 / args.half_life)
        for tid, name, rating, comp, won, ems in sides:
            p = len(comp)
            if tid in tops and p in comps:
                comps[p][tuple(comp)] += w
                raw[p][tuple(comp)] += 1
                for c in comp:
                    champ[p][c] += w
                    plays[c] += 1
                    wins[c] += won
                for e in ems:
                    if 0 < e <= len(EMBLEMS) * 3:
                        emblems[e] += 1
        (ta, _, ra, ca, wa, _), (tb, _, rb, cb, _, _) = sides
        playing = tops | {MY_TEAM}
        if ta in playing and tb in playing and ta != tb:
            ladder.append({"match": mid, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(at)), "map": mp, "A": ca, "B": cb, "teamA": ta, "teamB": tb,
                           "ratingA": ra, "ratingB": rb, "winner": 0 if wa else 1})
    prior = {p: [{"comp": list(c), "n": round(n, 3)} for c, n in comps[p].most_common() if n >= args.min_n]
             for p in comps}
    prior["teams"] = [{"id": t, "name": n, "rating": r} for t, (r, n) in ranked]
    prior["source"] = {"engine": args.engine, "kind": args.kind, "top": args.top, "half_life_h": args.half_life,
                       "days": [d.parent.name for d in days], "games": len(rows)}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(prior, indent=1), encoding="utf-8")
    if args.ladder_out:
        Path(args.ladder_out).write_text("".join(json.dumps(r) + "\n" for r in ladder), encoding="utf-8")
    tot = {p: sum(raw[p].values()) for p in raw}
    print(f"{len(rows)} games; top {len(tops)} teams; team-games per pick count {tot}; ladder rows {len(ladder)}")
    if args.report:
        out = [f"# Ladder drafts on engine {args.engine} ({', '.join(d.parent.name for d in days)})", "",
               f"From big-arm's archive: {len(rows)} {args.kind} games; the top {len(tops)} other teams by rating "
               f"({', '.join(n for _, (_, n) in ranked)}), team-games weighted by a {args.half_life:g} h half-life. "
               f"Generated by `tools/draftlab/ladder_prior.py`.", ""]
        for p in (3, 4, 5):
            if not tot[p]:
                continue
            W = sum(comps[p].values())
            out += [f"## {p} picks ({tot[p]} team-games)", "", "| composition (pick order) | games | weighted share |",
                    "| --- | --- | --- |"]
            for c, n in comps[p].most_common(10):
                out.append(f"| {', '.join(c)} | {raw[p][c]} | {n / W:.1%} |")
            out += ["", "Champion pick share (weighted, of teams): " +
                    ", ".join(f"{c} {champ[p][c] / W:.0%}" for c, _ in champ[p].most_common()), ""]
        out += ["## Champion win rates (unweighted, top teams' games)", "",
                ", ".join(f"{c} {wins[c] / plays[c]:.0%} of {plays[c]}" for c, _ in plays.most_common()), ""]
        Path(args.report).write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
