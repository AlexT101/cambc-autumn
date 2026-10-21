"""What spent the fuel of out-of-fuel turns and of big turns, from the OOFCOST, BIGTURN and OOFSELF lines
hyperion prints with `debug_phases` on (BIGTURN also needs `debug_big_turns`; util.h). Per Phase path: the
share of turns it is listed in, mean and p90 inclusive fuel over the turns (0 where it is not listed), mean
self fuel (outside its inner Phases), and its share of the fuel the turns spent; per Phase name (OOFSELF,
any depth): self fuel on out-of-fuel turns.

    py tools/fuel/oof_costs.py replays/batch-A replays/batch-B
    py tools/fuel/oof_costs.py replays/batch-A --by-champion --depth 2 --min-share 1

Arguments are read as by oof_phases.py. A bot's first turn (twice the budget) is left out unless --first.
The bot leaves out entries under 1000 fuel (2000 on BIGTURN lines), so small paths read low. A line the
engine's NUL padding cut short loses its tail; outputs that reached the 1 MiB cap lose their last lines.
"""
import argparse
import collections
import re
import zipfile

from oof_phases import bundles

KINDS = {"OOFCOST": "out-of-fuel turns", "BIGTURN": "turns over 60k that did not run out"}
HEAD = re.compile(r"^(OOFCOST|BIGTURN) (\d+) (\S+) total=(\d+) phases=(\d+)(.*)$", re.M)
SELF = re.compile(r"^OOFSELF (\d+) (\S+) total=(\d+)(.*)$", re.M)
# A line cut short by the engine's padding may run into the next one: an entry's value ends at the first non-digit.
ENTRY = re.compile(r"([^\s=]+)=(\d+)(?:/(\d+))?")
SPLIT = re.compile(r"(?<=[^\n])((?:OOFCOST|BIGTURN|OOFSELF) \d+ \S+ total=)")
TURN_BUDGET = 100000
CAP = 1 << 20


class Turn:
    __slots__ = ("bot", "champion", "round", "total", "phases", "costs")

    def __init__(self, bot, champion, round_, total, phases, costs):
        self.bot, self.champion, self.round, self.total, self.phases, self.costs = bot, champion, round_, total, phases, costs


def entries(rest):
    """{name: (inclusive, self)} from ' a=1 b/c=5/2 ...', stopping at the first token that is not an entry."""
    out = {}
    for token in rest.split():
        m = ENTRY.match(token)
        if not m:
            break
        incl = int(m[2])
        out[m[1]] = (incl, int(m[3]) if m[3] else incl)
        if m.end() != len(token):
            break
    return out


def read(paths, first):
    turns = {kind: [] for kind in KINDS}
    selves = []
    stats = collections.Counter()
    for arg in paths:
        for bundle, team_a, team_b in bundles(arg):
            stats["games"] += 1
            with zipfile.ZipFile(bundle) as z:
                for team, bot in (("a", team_a), ("b", team_b)):
                    raw = z.read(f"team-{team}.stdout")
                    out = raw.replace(b"\0", b"").decode("utf-8", "replace")
                    # A line printed as a turn resumes can lose its newline to the padding.
                    out = SPLIT.sub(r"\n\1", out)
                    found = False
                    for m in HEAD.finditer(out):
                        found = True
                        total = int(m[4])
                        if total > TURN_BUDGET and not first:
                            stats[f"{m[1]} first turns left out"] += 1
                            continue
                        turns[m[1]].append(Turn(bot, m[3], int(m[2]), total, int(m[5]), entries(m[6])))
                    for m in SELF.finditer(out):
                        if int(m[3]) <= TURN_BUDGET or first:
                            selves.append(Turn(bot, m[2], int(m[1]), int(m[3]), 0, entries(m[4])))
                    if found and len(raw) >= CAP - 4096:
                        stats["team outputs at the 1 MiB cap"] += 1
    return turns, selves, stats


def p90(values):
    s = sorted(values)
    return s[min(len(s) - 1, int(0.9 * len(s)))] if s else 0


def summarise(turns, depth):
    """Per path: [ran, mean incl, p90 incl, mean self, share]; plus the turns' total."""
    n = len(turns)
    spent = sum(t.total for t in turns)
    names = {p for t in turns for p in t.costs if p.count("/") < depth}
    rows = {}
    for p in names:
        incl = [t.costs[p][0] if p in t.costs else 0 for t in turns]
        self = [t.costs[p][1] if p in t.costs else 0 for t in turns]
        rows[p] = (sum(1 for t in turns if p in t.costs) / n, sum(incl) / n, p90(incl), sum(self) / n, sum(incl) / spent)
    outside = [t.total - sum(c[0] for p, c in t.costs.items() if "/" not in p) for t in turns]
    # Outside every Phase, and top-level Phases under the floor.
    rows["(rest of turn)"] = (1.0, sum(outside) / n, p90(outside), sum(outside) / n, sum(outside) / spent)
    return rows, spent / n


def tree_order(rows):
    """Depth-first, siblings by share."""
    children = collections.defaultdict(list)
    for p in rows:
        children[p.rsplit("/", 1)[0] if "/" in p else ""].append(p)
    out = []

    def walk(parent):
        for p in sorted(children[parent], key=lambda q: -rows[q][4]):
            out.append(p)
            walk(p)

    walk("")
    return out


def print_table(title, turns, depth, min_share):
    if not turns:
        print(f"\n{title}: none")
        return
    rows, mean_total = summarise(turns, depth)
    shown = [p for p in tree_order(rows) if rows[p][4] * 100 >= min_share]
    print(f"\n{title}: {len(turns)} turns, mean {mean_total:,.0f} fuel spent; paths over {min_share}% of it")
    width = max(len("  " * p.count("/") + p.rsplit("/", 1)[-1]) for p in shown)
    print(f"  {'path':<{width}}   ran   mean incl   p90 incl   mean self   share")
    for p in shown:
        ran, mean, top, self, share = rows[p]
        label = "  " * p.count("/") + p.rsplit("/", 1)[-1]
        print(f"  {label:<{width}}  {ran:4.0%}  {mean:10,.0f} {top:10,} {self:11,.0f}  {share:6.1%}")


def print_by_champion(title, turns, depth, top):
    if not turns:
        return
    by = collections.defaultdict(list)
    for t in turns:
        by[t.champion].append(t)
    champions = sorted(by, key=lambda c: -len(by[c]))
    rows, _ = summarise(turns, depth)
    paths = sorted((p for p in rows), key=lambda p: -rows[p][4])[:top]
    per = {c: summarise(by[c], depth)[0] for c in champions}
    width = max(len(p) for p in paths)
    print(f"\n{title} by champion: share of each champion's spent fuel")
    print(f"  {'path':<{width}}  " + "".join(f"{c[:11]:>12}" for c in champions))
    print(f"  {'(turns)':<{width}}  " + "".join(f"{len(by[c]):>12}" for c in champions))
    for p in paths:
        print(f"  {p:<{width}}  " + "".join(f"{per[c][p][4]:>12.1%}" if p in per[c] else f"{'-':>12}" for c in champions))


def print_selves(selves, top):
    if not selves:
        return
    n = len(selves)
    names = {p for t in selves for p in t.costs}
    rows = []
    for p in names:
        v = [t.costs[p][0] if p in t.costs else 0 for t in selves]
        rows.append((sum(v) / n, p90(v), sum(1 for x in v if x) / n, p))
    rows.sort(reverse=True)
    width = max(len(r[3]) for r in rows[:top])
    print(f"\nSelf fuel by Phase name on out-of-fuel turns (OOFSELF, any depth): {n} turns")
    spent = sum(t.total for t in selves) / n
    print(f"  {'phase':<{width}}   ran   mean self   p90 self   share")
    for mean, top90, ran, p in rows[:top]:
        print(f"  {p:<{width}}  {ran:4.0%}  {mean:10,.0f} {top90:10,}  {mean / spent:6.1%}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--depth", type=int, default=3, help="deepest paths shown (default 3)")
    ap.add_argument("--min-share", type=float, default=0.5, help="hide paths under this percentage of the turns' fuel")
    ap.add_argument("--by-champion", action="store_true", help="also each path's share per champion type")
    ap.add_argument("--top", type=int, default=25, help="rows in the per-champion and per-name tables")
    ap.add_argument("--first", action="store_true", help="keep each bot's first turn (a 200k budget)")
    ap.add_argument("--bot", help="only this bot's lines (default: all)")
    args = ap.parse_args()
    turns, selves, stats = read(args.paths, args.first)
    if args.bot:
        turns = {k: [t for t in v if t.bot == args.bot] for k, v in turns.items()}
        selves = [t for t in selves if t.bot == args.bot]
    print(f"{stats['games']} games; " + ", ".join(f"{v} {k}" for k, v in stats.items() if k != "games"))
    for kind, title in KINDS.items():
        print_table(title.capitalize(), turns[kind], args.depth, args.min_share)
        if args.by_champion:
            print_by_champion(title.capitalize(), turns[kind], args.depth, args.top)
    print_selves(selves, args.top)


if __name__ == "__main__":
    main()
