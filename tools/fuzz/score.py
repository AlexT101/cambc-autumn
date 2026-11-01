"""Per-game pathology metrics of our bot against bots/idle, read from tools/replay/extract.mjs output, and the
composite score (higher is worse). README.md explains each component."""

import gzip
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from solo import game_metrics  # noqa: E402

# A champion staying inside a 3x3 box this many rounds, none of them tributing, teleporting or attacking, is stuck:
# longer than any camp's respawn (a Monolith's 150), so waiting by a camp for it to return doesn't count.
# Recall channels don't excuse a round: a recall started and cancelled every turn is how the bot dithers.
STALL_MIN = 160
# Typical gem rate (tributed per round) by offer rate, as [log offer, log rate] knots: a pilot of 152 astraeus games
# (2026-10-30). The rate saturates near 2 a round whatever the map offers. A screen refits it (state.json).
DEFAULT_BASE = [[math.log(0.5), math.log(0.6)], [math.log(1.2), math.log(1.1)], [math.log(3), math.log(1.35)],
                [math.log(5), math.log(1.5)], [math.log(10), math.log(2.0)]]
# Games expected to reach 1000 by this round must reach it.
NO1000_EXPECT = 1400
WEIGHTS = {"econ": 1.0, "no1000": 1.0, "hoard": 1.0, "asym": 1.0, "untaken": 1.5, "stall": 1.0, "camp_deaths": 1.0, "oof": 1.0,
           "errors": 3.0, "poke": 0.25, "vs_ref": 1.0}
CAPS = {"econ": 3, "hoard": 2, "asym": 2, "untaken": 1, "stall": 3, "camp_deaths": 3, "oof": 3, "errors": 1, "poke": 2, "vs_ref": 3}


def load(analysis, row):
    d = analysis / row["dir"]
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    rounds = json.load(gzip.open(d / "rounds.json.gz"))
    events = [json.loads(line) for line in gzip.open(d / "events.jsonl.gz", "rt", encoding="utf-8")]
    mapjson = json.loads((d / meta["mapFile"]).read_text(encoding="utf-8"))
    return d, meta, rounds, events, mapjson


def offer(mapjson, team):
    """Gems a side owns (shared groups halved, as mapgen's gems_side) and the rate they respawn at, per round."""
    gems = rate = 0.0
    own = []
    for g in mapjson["groups"]:
        # extract.mjs gives a self-mirrored group the side of whichever spawn is nearer by its walk; it is shared.
        shared = g["side"] == -1 or g.get("mirror") == g["id"]
        if not g["gems"] or not (shared or g["side"] == team):
            continue
        share = 0.5 if shared else 1.0
        gems += share * g["gems"]
        rate += share * g["gems"] / max(1, g["respawn"])
        own.append(g)
    return gems, rate, own


def stalls(c, spawn, attack_rounds):
    """Longest run of rounds in a 3x3 box (alive, off spawn) counting only rounds with no channel or attack, and
    the champion-rounds in runs of STALL_MIN or more (chan: 1 recall, 2 tribute, 3 teleport).
    Returns (longest, total, (index of its first round, tile))."""
    xs, ys = c["x"], c["y"]
    n = len(xs)
    best, total, where = 0, 0, None
    i = 0
    while i < n:
        if xs[i] is None or not c["alive"][i] or (spawn["minX"] <= xs[i] <= spawn["maxX"] and spawn["minY"] <= ys[i] <= spawn["maxY"]):
            i += 1
            continue
        lo_x = hi_x = xs[i]
        lo_y = hi_y = ys[i]
        j, quiet = i, 0
        while j < n and xs[j] is not None and c["alive"][j]:
            lo_x, hi_x, lo_y, hi_y = min(lo_x, xs[j]), max(hi_x, xs[j]), min(lo_y, ys[j]), max(hi_y, ys[j])
            if hi_x - lo_x > 2 or hi_y - lo_y > 2:
                break
            if c["chan"][j] not in (2, 3) and j not in attack_rounds:
                quiet += 1
            j += 1
        if quiet > best:
            best, where = quiet, (i, (xs[i], ys[i]))
        if quiet >= STALL_MIN:
            total += quiet
        i = j if j > i + 1 else i + 1
    return best, total, where


def game(analysis, row, team):
    """Raw metrics of team `team` (ours) in one extracted game."""
    d, meta, rounds, events, mapjson = load(analysis, row)
    names = json.loads((analysis / "enums.json").read_text(encoding="utf-8"))["champions"]
    m = game_metrics(d, team)
    m["game"] = row["dir"]
    ours = {c["id"] for c in meta["champions"] if c["team"] == team}
    types = {c["id"]: names[c["type"]] for c in meta["champions"]}
    round_list = rounds["round"]
    first = round_list[0]
    gems, rate, own = offer(mapjson, team)
    m.update(offer_gems=round(gems, 1), offer_rate=round(rate, 3))
    m["gem_rate"] = round(1000 / m["r1000"] if m["r1000"] else m["end_gems"] / max(1, m["rounds"]), 3)

    captured, attacks, pokes, camp_deaths, gems_lost, deaths, recalls = set(), {}, 0, [], 0, 0, [0, 0]
    for e in events:
        k = e["k"]
        if k == "capture" and e["team"] == team:
            captured.add(e["g"])
        elif k in ("attack", "cast") and e.get("a") in ours:
            attacks.setdefault(e["a"], set()).add(e["r"] - first)
            pokes += "tgt" in e
        elif k in ("recall_start", "recall_end") and e.get("a") in ours:
            recalls[k == "recall_end"] += 1
        elif k == "death" and e["v"] in ours:
            deaths += 1
            if "camp" in e:
                camp_deaths.append((e["r"], types[e["v"]], e.get("gems", 0)))
                gems_lost += e.get("gems", 0)
    untaken = [g for g in own if g["id"] not in captured]
    m["groups_own"] = len(own)
    m["groups_untaken"] = len(untaken)
    m["untaken_share"] = round(sum(g["gems"] for g in untaken) / max(1, sum(g["gems"] for g in own)), 3) if own else 0
    m["untaken_types"] = sorted({"+".join(sorted(set(g["types"]))) for g in untaken})
    m["deaths"] = deaths
    m["camp_deaths"] = len(camp_deaths)
    m["camp_death_list"] = camp_deaths[:6]
    m["gems_lost_to_camps"] = gems_lost
    m["poke_actions"] = pokes
    m["carried_end"] = sum(c["gems"][-1] for c in rounds["champions"] if c["team"] == team)
    m["tributes"] = sum(e["k"] == "tribute_end" and e.get("a") in ours for e in events)
    m["recall_starts"], m["recalls"] = recalls

    spawn = mapjson["spawn"][team]
    worst, total, alive_turns, idle_turns = (0, None, None), 0, 0, 0
    for c in rounds["champions"]:
        if c["team"] != team:
            continue
        best, tot, where = stalls(c, spawn, attacks.get(c["id"], set()))
        total += tot
        if best > worst[0]:
            worst = (best, types[c["id"]], [round_list[where[0]], list(where[1])])
        alive_turns += sum(t in (1, 2, 3, 6, 7) for t in c["turn"])
        idle_turns += sum(t == 2 for t in c["turn"])
    m["stall_longest"], m["stall_champion"], m["stall_at"] = worst
    m["stall_rounds"] = total
    m["idle_frac"] = round(idle_turns / max(1, alive_turns), 3)
    m["draft"] = [types[i] for i in sorted(ours)]
    return m


def fit_base(games, bins=8):
    """Knots [log offer, median log gem rate] over offer-rate quantile bins of the games' metrics."""
    pts = sorted((math.log(g["offer_rate"]), math.log(max(g["gem_rate"], 1e-3))) for g in games if g.get("offer_rate", 0) > 0)
    if len(pts) < 4 * bins:
        return DEFAULT_BASE
    size = len(pts) / bins
    chunks = [pts[round(i * size):round((i + 1) * size)] for i in range(bins)]
    return [[round(statistics.median(p[0] for p in c), 4), round(statistics.median(p[1] for p in c), 4)] for c in chunks if c]


def expected_rate(offer_rate, base):
    """The baseline's gem rate at this offer, interpolated in log-log, flat beyond its ends."""
    if offer_rate <= 0:
        return 0.0
    x = math.log(offer_rate)
    if x <= base[0][0]:
        return math.exp(base[0][1])
    for (x0, y0), (x1, y1) in zip(base, base[1:]):
        if x <= x1:
            return math.exp(y0 + (y1 - y0) * (x - x0) / max(x1 - x0, 1e-9))
    return math.exp(base[-1][1])


def components(m, base=DEFAULT_BASE, ref=None):
    """Composite parts, each >= 0 and capped (CAPS), before weighting. `ref`: the reference bot's metrics on the
    same map and side, if a reference was played."""
    c = {}
    expect = expected_rate(m["offer_rate"], base)
    # A drought map can't beat its own offer, so the expectation never exceeds it.
    expect = min(expect, m["offer_rate"]) if m["offer_rate"] else 0.0
    c["econ"] = min(CAPS["econ"], max(0.0, math.log2(expect / max(m["gem_rate"], 1e-3)))) if expect else 0.0
    c["no1000"] = 1.0 if m["r1000"] is None and expect * NO1000_EXPECT >= 1000 else 0.0
    # Gems collected but never tributed by round 2000 (a game reaching 1000 ends with a bag in transit).
    c["hoard"] = min(CAPS["hoard"], m.get("carried_end", 0) / 250) if m["r1000"] is None else 0.0
    # Uncaptured own gem groups matter only in a long game: a fast one had no need of them.
    c["untaken"] = min(CAPS["untaken"], m["untaken_share"] * min(1.0, max(0.0, (m["rounds"] - 500) / 1000)))
    c["stall"] = min(CAPS["stall"], m["stall_rounds"] / 600)
    c["camp_deaths"] = min(CAPS["camp_deaths"], 0.5 * m["camp_deaths"] + m["gems_lost_to_camps"] / 200)
    c["oof"] = min(CAPS["oof"], m["oof_turns"] / 10)
    c["errors"] = 1.0 if m["error_turns"] else 0.0
    c["poke"] = min(CAPS["poke"], m["poke_actions"] / 100)
    if ref is not None:
        c["vs_ref"] = min(CAPS["vs_ref"], max(0.0, math.log2(max(ref["gem_rate"], 1e-3) / max(m["gem_rate"], 1e-3))))
    return {k: round(v, 3) for k, v in c.items()}


def asymmetry(sides):
    """The map is symmetric, so a gem rate differing between sides by more than ~15% is fragile play."""
    rates = [s["gem_rate"] for s in sides if "crash" not in s]
    if len(rates) != 2:
        return 0.0
    gap = abs(math.log2(max(rates[0], 1e-3) / max(rates[1], 1e-3)))
    return round(min(CAPS["asym"], max(0.0, 2 * (gap - 0.2))), 3)


def total(comps):
    return round(sum(WEIGHTS[k] * v for k, v in comps.items()), 3)


def crash_components():
    """A match that failed (crash, timeout) scores as a bot error."""
    return {"errors": 1.0}
