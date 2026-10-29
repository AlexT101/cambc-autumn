"""Tables from the fuel census's CEN lines (tools/fuel/census/census.h, instrumented by instrument.py).

    py tools/fuel/census/census.py GAMES_DIR [GAMES_DIR ...]

GAMES_DIR: bench.py's --games directory (one <map>-<side>/ folder a game; the census bot plays `side`) or any
folder of replays whose stdout has CEN lines (both teams are read then).
Groups: OOF-first (ran out, began on time), OOF-late (ran out after the turn before ran out), heavy-fine (finished,
>= 65k spent before the turn-end queue). Inclusive fuel per component; `self` excludes instrumented children.
"""
import argparse, collections, re, statistics, zipfile
from pathlib import Path

TYPES = "ryth vesper_vale vendetta cassi issac stellar prism marcella willow ren varg tavi heart_of_ruin".split()
COMPONENTS = ["world", "update", "observe", "track", "comms receive", "safety_ctor", "approach_walk", "channels",
              "ward_planned", "want_home", "support_work", "local_support", "retreat", "guard_steps", "captures",
              "holding", "strike_search", "post_search", "guard_steps2", "hold_capture", "carry_bag", "goal", "chase",
              "siege_kite", "farm", "see_revealed", "strike_after", "act_end", "turn_order", "publish_order",
              "turn end", "comms send", "queue", "field", "route", "safety", "attack_tiles", "approach",
              "farm.loop", "farm.post", "s.stand", "s.fight_of", "s.lethal", "s.bound", "wh.outmatched", "wh.camp_trapped",
              "read_vision", "rank_turns", "priorities", "champion", "champion_enemy", "camps", "altars", "scores",
              "static_camps", "init_beliefs", "build_static", "warm_up"]
DECIDE_LEVEL = ["channels", "ward_planned", "want_home", "support_work", "local_support", "retreat", "guard_steps",
                "captures", "holding", "strike_search", "post_search", "guard_steps2", "hold_capture", "carry_bag",
                "chase", "siege_kite", "farm", "goal", "see_revealed", "strike_after", "act_end", "approach_walk",
                "safety_ctor", "turn_order", "publish_order", "world", "comms receive", "turn end", "comms send",
                "debug", "queue"]


def bucket(r):
    return "1" if r == 1 else "2-10" if r <= 10 else "11-60" if r <= 60 else "61-300" if r <= 300 else "300+"


def mapclass(name):
    return re.sub(r"^(gen|mut)-", "", re.sub(r"-\d{6,}$", "", name))


def parse_line(l):
    head, _, comps = l.partition(" | ")
    if not _:
        head, comps = l.rstrip(" |"), ""
    p = head.split()
    d = dict(round=int(p[1]), champ=int(p[2]), type=TYPES[int(p[3][1:])] if p[3] != "t-1" else "?",
             late=p[4] == "late1", oof=p[5] == "oof1", start=int(p[7]), spent=int(p[9]), post=int(p[11]),
             ne=int(p[13]), nn=int(p[15]), na=int(p[17]), aw=int(p[19]), stack=head.split(" stack ", 1)[1].strip())
    c = {}
    for m in re.finditer(r"(\S[^=|]*?)=(\d+):(\d+):(\d+)", comps):
        c[m[1].strip()] = (int(m[2]), int(m[3]), int(m[4]))
    d["c"] = c
    return d


def load(dirs):
    rows = []
    for d in map(Path, dirs):
        for b in sorted(d.rglob("*.repl26a")):
            m = re.match(r"(.+)-([ab])$", b.parent.name)
            sides = [m[2]] if m else ["a", "b"]
            mapname = m[1] if m else b.stem
            with zipfile.ZipFile(b) as z:
                for s in sides:
                    out = z.read(f"team-{s}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
                    srch, branch = {}, {}
                    for l in out.splitlines():
                      try:
                        if l.startswith("SRCH "):
                            q = l.split()
                            f = dict(zip(q[3::2], q[4::2]))
                            srch[(int(q[1]), int(q[2]))] = f
                        elif l.startswith("D "):
                            q = l.split()
                            branch[(int(q[1]), int(q[2]))] = q[3]
                      except (IndexError, ValueError):
                        pass
                    for l in out.splitlines():
                        if l.startswith("CEN ") and " | " in l:
                            try:
                                r = parse_line(l)
                            except (IndexError, ValueError):
                                continue
                            r.update(map=mapname, cls=mapclass(mapname), game=str(b), side=s,
                                     srch=srch.get((r["round"], r["champ"])), branch=branch.get((r["round"], r["champ"]), "?"))
                            rows.append(r)
    return rows


def inc(r, k):
    return r["c"].get(k, (0, 0, 0))[0]


def pct(n, d):
    return f"{100 * n / max(1, d):.0f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    a = ap.parse_args()
    rows = load(a.dirs)
    groups = {"OOF-first": [r for r in rows if r["oof"] and not r["late"]],
              "OOF-late": [r for r in rows if r["oof"] and r["late"]],
              # The turn-end queue fills spare fuel by design: heavy means the work before it.
              "heavy-fine": [r for r in rows if not r["oof"] and r["spent"] - inc(r, "queue") >= 65000 and r["round"] > 1]}
    games = len({r["game"] + r["side"] for r in rows})
    print(f"games {games}; " + ", ".join(f"{k} {len(v)}" for k, v in groups.items()))
    oof = groups["OOF-first"] + groups["OOF-late"]
    first = groups["OOF-first"]

    def tab(title, key, rs, n=16):
        c = collections.Counter(key(x) for x in rs)
        print(f"  {title}: " + ", ".join(f"{k} {v} ({pct(v, len(rs))})" for k, v in c.most_common(n)))

    for name in ("OOF-first", "OOF-late", "heavy-fine"):
        rs = groups[name]
        print(f"\n== {name} ({len(rs)})")
        tab("bucket", lambda x: bucket(x["round"]), rs)
        tab("type", lambda x: x["type"], rs)
        tab("map class", lambda x: x["cls"], rs, 12)
        tab("visible enemies", lambda x: min(x["ne"], 6), rs)
        tab("enemies within 6", lambda x: min(x["nn"], 6), rs)
        tab("branch (D line; ? = abandoned)", lambda x: x["branch"], rs)

    print("\n== Component inclusive fuel: share of turns with it (>=1k), mean and median where present, mean over all")
    print(f"  {'component':16s}" + "".join(f"{g:>34s}" for g in groups))
    for k in COMPONENTS:
        line = f"  {k:16s}"
        for g, rs in groups.items():
            v = [inc(r, k) for r in rs]
            pres = [x for x in v if x > 0]
            line += f"{pct(len(pres), len(rs)):>7s} {statistics.fmean(pres) if pres else 0:8.0f} {statistics.median(pres) if pres else 0:8.0f} {statistics.fmean(v) if v else 0:8.0f}"
        print(line)

    print("\n== OOF-first: where fuel ran out")
    tab("innermost scope", lambda x: x["stack"].split("/")[-1], first, 20)
    tab("decide-level scope", lambda x: next((s for s in reversed(x["stack"].split("/")) if s in DECIDE_LEVEL), x["stack"].split("/")[-1]), first, 20)
    tab("innermost scope (OOF-late)", lambda x: x["stack"].split("/")[-1], groups["OOF-late"], 12)

    print("\n== OOF turns (first+late): heavy components (>= 15k inclusive) present, as a signature")
    heavy = ["world", "channels", "want_home", "retreat", "strike_search", "strike_after", "farm", "chase", "siege_kite",
             "turn_order", "carry_bag", "hold_capture", "local_support", "support_work", "guard_steps", "guard_steps2"]
    tab("signature", lambda x: "+".join(k for k in heavy if inc(x, k) >= 15000) or "(none >=15k)", oof, 25)
    tab("signature heavy-fine", lambda x: "+".join(k for k in heavy if inc(x, k) >= 15000) or "(none >=15k)", groups["heavy-fine"], 15)

    print("\n== Self fuel summed over OOF turns (first+late), top labels")
    tot = collections.Counter()
    for r in oof:
        for k, (i, s, c) in r["c"].items():
            tot[k] += s
    allf = sum(r["spent"] for r in oof)
    print("  " + ", ".join(f"{k} {pct(v, allf)}" for k, v in tot.most_common(25)))

    print("\n== By champion type, OOF turns: mean inclusive of key components")
    keys = ["world", "comms receive", "channels", "want_home", "retreat", "strike_search", "strike_after", "farm", "turn_order"]
    print(f"  {'type':14s} {'n':>4s}" + "".join(f"{k[:12]:>13s}" for k in keys))
    for t, n in collections.Counter(r["type"] for r in oof).most_common():
        rs = [r for r in oof if r["type"] == t]
        print(f"  {t:14s} {n:4d}" + "".join(f"{statistics.fmean(inc(r, k) for r in rs):13.0f}" for k in keys))

    srch = [r["srch"] for r in oof if r["srch"]]
    if srch:
        print(f"\n== SRCH lines on OOF turns: {len(srch)}")
        for f in ("fuel", "read", "grow", "price", "act", "tiles", "priced", "nodes", "foes"):
            v = [int(s[f]) for s in srch if f in s and s[f].isdigit() and int(s[f]) < 10**7]
            if v:
                print(f"  {f}: mean {statistics.fmean(v):.0f} median {statistics.median(v):.0f} max {max(v)}")


if __name__ == "__main__":
    main()
