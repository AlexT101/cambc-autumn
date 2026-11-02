"""Farming against a live opponent: CAND vs REF gold and captures in an ab.py run's games.

    py tools/ab_farm.py <name>             # replays/ab/<name>/, as ab.py --name wrote it
    py tools/ab_farm.py <name> --json OUT  # also every game's metrics
    py tools/ab_farm.py <name> --suites ladder,gen,fresh/gen-s1  # only these suites (extraction is the slow part)

Extracts the run's batches into replays/ab/<name>/analysis/ (once) and pairs CAND with REF in each game: lifetime
gold earned, capture gold (all, and groups with an Elk or Golem), gold the other team captured on groups this one did
most of the damage on, camp damage and tributed gems. Mean CAND - REF with a bootstrap 95% CI over games.
"""
import argparse
import gzip
import json
import random
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUT = 300
METRICS = {
    "gold150": "gold earned @150", "gold300": "gold earned @300", "gold600": "gold earned @600",
    "gold_end": "gold earned, end", "cap300": "capture gold @300", "big300": "Elk/Golem capture gold @300",
    "lost300": "gold lost @300 (most damage ours, they captured)", "dmg300": "camp damage @300 (k)",
    "gold_per_kdmg300": "capture gold per 1k camp damage @300", "trib600": "tributed gems @600",
    "camp_deaths": "deaths to camps",
}


def at(rounds, values, r):
    return values[min(r, rounds[-1]) - rounds[0]]


def game_metrics(game_dir, maps_dir):
    meta = json.loads((game_dir / "meta.json").read_text(encoding="utf-8"))
    data = json.load(gzip.open(game_dir / "rounds.json.gz"))
    mp = json.loads((maps_dir / f"{meta['map']['hash']}.json").read_text(encoding="utf-8"))
    rounds = data["round"]
    team_of = {c["id"]: c["team"] for c in meta["champions"]}
    camp_group = {c["id"]: c["group"] for c in mp["camps"]}
    big = defaultdict(bool)
    for c in mp["camps"]:
        big[c["group"]] |= c["type"] in ("Elk", "Golem")
    out = []
    for t in (0, 1):
        ours = [c for c in data["champions"] if c["team"] == t]
        m = {f"gold{r}": sum(at(rounds, c["earned"], r) for c in ours) for r in (150, 300, 600)}
        m.update(gold_end=sum(c["earned"][-1] for c in ours), trib600=at(rounds, data["gems"][t], 600),
                 cap300=0.0, big300=0.0, lost300=0.0, dmg300=0.0, camp_deaths=0)
        out.append(m)
    dmg_by = defaultdict(lambda: [0.0, 0.0])
    for line in gzip.open(game_dir / "events.jsonl.gz", "rt"):
        if not line.strip():  # a game with no events at all is one blank line
            continue
        e = json.loads(line)
        k, r = e["k"], e["r"]
        if k in ("attack", "cast") and e.get("cdmg"):
            t = team_of[e["a"]]
            for camp, amount in e["cdmg"]:
                g = camp_group.get(camp)
                if g is None:
                    continue
                dmg_by[g][t] += amount
                if r <= CUT:
                    out[t]["dmg300"] += amount / 1000
        elif k == "capture":
            g, t = e["g"], e["team"]
            if r <= CUT:
                gold = sum(s[2] for s in e["shares"])
                out[t]["cap300"] += gold
                if big[g]:
                    out[t]["big300"] += gold
                if dmg_by[g][1 - t] > dmg_by[g][t]:
                    out[1 - t]["lost300"] += gold
            dmg_by[g] = [0.0, 0.0]
        elif k == "group_respawn":
            dmg_by[e["g"]] = [0.0, 0.0]
        elif k == "death" and "camp" in e:
            out[team_of[e["v"]]]["camp_deaths"] += 1
    for m in out:
        m["gold_per_kdmg300"] = m["cap300"] / max(1.0, m["dmg300"])
    return out


def bootstrap(values, samples=2000, seed=0):
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(samples))
    return means[int(0.025 * samples)], means[int(0.975 * samples)]


def table(pairs):
    lines = ["| Metric | CAND | REF | CAND - REF | 95% CI |", "| --- | --- | --- | --- | --- |"]
    for key, label in METRICS.items():
        cand = [c[key] for c, _ in pairs]
        ref = [r[key] for _, r in pairs]
        diff = [a - b for a, b in zip(cand, ref)]
        lo, hi = bootstrap(diff)
        n = len(pairs)
        lines.append(f"| {label} | {sum(cand) / n:.1f} | {sum(ref) / n:.1f} | {sum(diff) / n:+.1f} | [{lo:+.1f}, {hi:+.1f}] |")
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--json")
    ap.add_argument("--suites", help="Comma-separated suite labels to analyse (as in summary.md), e.g. ladder,gen,fresh/gen-s1")
    args = ap.parse_args()
    run = ROOT / "replays" / "ab" / args.name
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    batches = [(s["suite"], ROOT / s["batch"]) for s in summary["suites"]]
    if args.suites:
        keep = set(args.suites.split(","))
        batches = [b for b in batches if b[0] in keep]
    analysis = run / "analysis"
    if not (analysis / "index.json").exists():
        print("extracting replays", flush=True)
        subprocess.run(["node", str(ROOT / "tools" / "replay" / "extract.mjs"), *(str(b) for _, b in batches),
                        "--out", str(analysis)], cwd=ROOT, stdout=subprocess.DEVNULL, check=False)
    index = {row["source"]: row for row in json.loads((analysis / "index.json").read_text(encoding="utf-8"))["games"]}
    by_suite, games, missing = defaultdict(list), [], 0
    for suite, batch in batches:
        report = json.loads((batch / "results.json").read_text(encoding="utf-8"))
        for m in report["matches"]:
            row = index.get(Path(m["replay"]).relative_to(ROOT).as_posix()) if m.get("replay") else None
            if "error" in m or not row or not row["ok"]:
                missing += 1
                continue
            teams = game_metrics(analysis / row["dir"], analysis / "maps")
            cand = m["order"].index(0)
            pair = (teams[cand], teams[1 - cand])
            by_suite[suite].append(pair)
            games.append({"suite": suite, "map": Path(m["map"]).stem, "cand_team": cand, "cand": pair[0], "ref": pair[1]})
    pairs = [p for ps in by_suite.values() for p in ps]
    print(f"{args.name}: {len(pairs)} games, {missing} missing; CAND {summary['cand']['spec']} vs REF {summary['ref']['spec']}")
    print("\n".join(table(pairs)))
    for suite, ps in by_suite.items():
        print(f"\n{suite} ({len(ps)} games)")
        print("\n".join(table(ps)))
    if args.json:
        Path(args.json).write_text(json.dumps(games), encoding="utf-8")


if __name__ == "__main__":
    main()
