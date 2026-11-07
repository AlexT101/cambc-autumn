#!/usr/bin/env python3
"""Alternatives report: how ocean's choice at a fighter's first strike-search decision compares with the
search's next-best candidates, by rollout outcome.

    python3 tools/combatlab/alt_report.py OUT.jsonl [--gem 0.01] [--death 1.0] [--margin 0.25] [--json SUMMARY]

OUT.jsonl is `fastrunner scenario ... --lab --decisions --alt K` output. Rollout 0 is ocean's own play; a rollout
with `alt.fighter` = f and `alt.k` = k plays the search's k-th choice at f's first decision. A rollout's reward from
team t's side is V(t) - V(other), V summing over the team's fighters: hp / max hp if alive, -death per death, plus
gem per carried gem.
"""
import argparse
import collections
import json
import statistics


def team_value(fighters, team, death, gem):
    v = 0.0
    for f in fighters:
        if f["team"] != team:
            continue
        v += (f["hp"] / f["max_hp"] if f["alive"] and f["max_hp"] > 0 else 0.0) - death * f["deaths"] + gem * f["gems"]
    return v


def reward(row, team, death, gem):
    return team_value(row["fighters"], team, death, gem) - team_value(row["fighters"], 1 - team, death, gem)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--death", type=float, default=1.0)
    ap.add_argument("--gem", type=float, default=0.01)
    ap.add_argument("--margin", type=float, default=0.25, help="a 'clear' gain or loss, in reward units")
    ap.add_argument("--json")
    a = ap.parse_args()

    base, alts = {}, collections.defaultdict(list)
    for line in open(a.out):
        r = json.loads(line)
        if "fighters" not in r:
            continue
        alt = r.get("alt") or {}
        if alt.get("k", 0) == 0:
            base[r["id"]] = r
        else:
            alts[(r["id"], alt["fighter"])].append(r)

    team_of = lambda row, fid: next(f["team"] for f in row["fighters"] if f["id"] == fid)
    groups = []  # one per decision with at least one alternative
    for (sid, fid), rs in alts.items():
        b = base.get(sid)
        if b is None:
            continue
        t = team_of(b, fid)
        r0 = reward(b, t, a.death, a.gem)
        first = (b.get("alt") or {}).get("first", {}).get(str(fid)) or {}
        plan0 = None
        for f in b["fighters"]:
            if f["id"] == fid:
                for d in f.get("decisions", []):
                    for p in d.get("plans", []):
                        if p.get("r") == first.get("round") and p.get("call") == first.get("call"):
                            plan0 = p
        deltas = [reward(r, t, a.death, a.gem) - r0 for r in sorted(rs, key=lambda r: r["alt"]["k"])]
        strike = plan0 is not None and (plan0["c"].get("raw", 0) != 0 or "a" in plan0["c"].get("ops", "") or "c" in plan0["c"].get("ops", ""))
        groups.append({"id": sid, "fighter": fid, "n": len(deltas) + 1, "deltas": deltas, "strike": strike,
                       "total0": plan0["c"]["total"] if plan0 else None})

    def summarise(gs, name):
        if not gs:
            return {"name": name, "decisions": 0}
        alld = [d for g in gs for d in g["deltas"]]
        best = [max(g["deltas"]) for g in gs]
        s = {
            "name": name,
            "decisions": len(gs),
            "alternatives": len(alld),
            "mean_alt_minus_ocean": statistics.fmean(alld),
            "share_alt_identical": sum(d == 0 for d in alld) / len(alld),
            "share_alt_better": sum(d > 0 for d in alld) / len(alld),
            "share_alt_worse": sum(d < 0 for d in alld) / len(alld),
            "share_decisions_some_alt_clearly_better": sum(b > a.margin for b in best) / len(gs),
            "share_decisions_ocean_clearly_best": sum(all(d < -a.margin for d in g["deltas"]) for g in gs) / len(gs),
            "mean_best_gain": statistics.fmean(best),
            "by_rank": {},
        }
        by_k = collections.defaultdict(list)
        for g in gs:
            for k, d in enumerate(g["deltas"], 1):
                by_k[k].append(d)
        for k in sorted(by_k):
            v = by_k[k]
            s["by_rank"][k] = {"n": len(v), "mean": statistics.fmean(v), "better": sum(d > 0 for d in v) / len(v)}
        return s

    out = [summarise(groups, "all"), summarise([g for g in groups if g["strike"]], "ocean's choice hits or casts"),
           summarise([g for g in groups if not g["strike"]], "ocean's choice only walks")]
    for s in out:
        print(f"\n## {s['name']}: {s['decisions']} decisions")
        if not s["decisions"]:
            continue
        print(f"alternatives {s['alternatives']}; alternative minus ocean: mean {s['mean_alt_minus_ocean']:+.3f}; "
              f"identical {s['share_alt_identical']:.0%}, better {s['share_alt_better']:.0%}, worse {s['share_alt_worse']:.0%}")
        print(f"decisions where some alternative is better by > {a.margin}: {s['share_decisions_some_alt_clearly_better']:.0%}; "
              f"where ocean beats every alternative by > {a.margin}: {s['share_decisions_ocean_clearly_best']:.0%}; mean best gain {s['mean_best_gain']:+.3f}")
        print("by rank: " + ", ".join(f"{k}: {v['mean']:+.3f} ({v['better']:.0%} better, n {v['n']})" for k, v in s["by_rank"].items()))
    if a.json:
        json.dump({"args": vars(a), "summaries": out}, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
