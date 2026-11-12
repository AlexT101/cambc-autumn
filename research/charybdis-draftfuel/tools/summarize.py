"""Rebuild the compact evidence from the retained draft probes and bench JSONs."""
import collections
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research/charybdis-draftfuel/results"


def read(path):
    return json.loads((ROOT / path).read_text())


def draft(name):
    return read(f"replays/draftlab/chy-draftfuel-{name}/rows.json")


def stats(xs):
    xs = sorted(xs)
    return dict(n=len(xs), mean=statistics.mean(xs), p50=statistics.median(xs),
                p99=xs[int(.99 * (len(xs) - 1))], p999=xs[int(.999 * (len(xs) - 1))], max=max(xs), min=min(xs))


def source(name):
    p = ROOT / "bots/variants" / f"chy-draftfuel-{name}/src"
    files = {str(f.relative_to(p)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(p.rglob("*")) if f.is_file()}
    return dict(files=files, sha256=hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest())


base, final, real = draft("base-plain"), draft("final-plain"), draft("final-real")
assert len(base) == len(final) == len(real) == 10576
for b, a, r in zip(base, final, real):
    assert (b["map"], b["side"]) == (a["map"], a["side"]) == (r["map"], r["side"])
    assert len(b["fuel"]) == len(a["fuel"]) == len(r["fuel"]) in (3, 4, 5)
    assert not b["lines"] and not a["lines"] and not r["lines"]
    assert a["fuel"][0] < b["fuel"][0] and r["fuel"][0] < 10000000
bp, ap, rp = draft("base-all"), draft("final-all"), draft("real-plans")
plan_turns = 0
for b, a, r in zip(bp, ap, rp):
    assert (b["map"], b["side"]) == (a["map"], a["side"]) == (r["map"], r["side"])
    assert b["lines"] == a["lines"] == r["lines"]
    plan_turns += sum(l.startswith("PLAN ") for l in a["lines"])
assert len(bp) == len(ap) == len(rp) == len(base)
summary = dict(
    engine="cambc 5.0.1", maps=len(base) // 2, team_drafts=len(base),
    first_turn={name: stats([r["fuel"][0] for r in rows]) for name, rows in [("base", base), ("final", final), ("real", real)]},
    savings=stats([b["fuel"][0] - a["fuel"][0] for b, a in zip(base, final)]),
    later_turn_max={name: max(max(r["fuel"][1:]) for r in rows) for name, rows in [("base", base), ("final", final), ("real", real)]},
    identical_plans=plan_turns, identical_feature_and_work_rows=len(bp),
    source={name: source(name) for name in ["base", "final"]})
summary["headroom"] = {name: 10000000 - summary["first_turn"][name]["max"] for name in ["base", "final"]}
summary["headroom_gain_pct"] = 100 * (summary["headroom"]["final"] / summary["headroom"]["base"] - 1)
benches, champions = {}, collections.Counter()
for name in ["wide", "td", "heavy", "stress"]:
    b = read(f"replays/fuel/chy-draftfuel-base-{name}.json")
    a = read(f"replays/fuel/chy-draftfuel-final-{name}.json")
    assert a["fuel"] == b["fuel"] == 100000000 and a["test_draft"] == b["test_draft"]
    assert len(a["games"]) == len(b["games"])
    for x, y in zip(a["games"], b["games"]):
        assert (x["map"], x["side"]) == (y["map"], y["side"])
        assert x["replay"] == y["replay"] and x["draft"] == y["draft"]
        champions.update(x["draft"])
    benches[name] = dict(identical=len(a["games"]), base_draft_max=max(g["draft_fuel"][0] for g in b["games"]),
                         final_draft_max=max(g["draft_fuel"][0] for g in a["games"]))
summary["bench"] = benches
summary["bench_champion_picks"] = dict(champions)
coverage = draft("coverage")
summary["coverage"] = dict(maps=len(coverage) // 2,
    sight=[sum(int(l.split()[k]) for r in coverage for l in r["lines"] if l.startswith("GAP ")) for k in [1, 2, 3]],
    empty_ward_sites=sum(l.startswith("WARDZERO ") for r in coverage for l in r["lines"]))
main_real = draft("main-real")
assert main_real == real
main_bench = read("replays/fuel/chy-draftfuel-main-heavy.json")
heavy_base = read("replays/fuel/chy-draftfuel-base-heavy.json")
assert len(main_bench["games"]) == len(heavy_base["games"]) == 54
for a, b in zip(main_bench["games"], heavy_base["games"]):
    assert (a["map"], a["side"], a["replay"]) == (b["map"], b["side"], b["replay"])
summary["main_recheck"] = dict(identical_real_budget_draft_fuel=len(main_real), identical_heavy_bench_replays=54)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "source"}, indent=2))
