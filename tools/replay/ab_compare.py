"""Farm and capture metrics of the two bots of a local A/B, compared within the same games.

Run tools/replay/extract.mjs on the batches first.
usage: py tools/replay/ab_compare.py VARIANT_NAME BATCH_DIR [BATCH_DIR ...]
  VARIANT_NAME: the bot's name as run_batched.py reports it (its directory name), e.g. fix-31
  BATCH_DIR: replays/batch-... (or just batch-...)
"""
import gzip, json, os, sys, collections, statistics

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "replays")
AN = os.path.join(ROOT, ".analysis")
RANGED = {"vesper", "prism", "stellar", "tavi", "willow", "cassi"}

index = json.load(open(os.path.join(AN, "index.json"), encoding="utf-8"))["games"]
VARIANT = sys.argv[1]
want = [os.path.normcase(os.path.abspath(os.path.join(ROOT, os.path.basename(d.rstrip("/\\"))))) for d in sys.argv[2:]]
rows = [g for g in index if any(os.path.normcase(os.path.abspath(os.path.join(ROOT, '..', g['source']))).startswith(w) for w in want)]

def kind_of(name):
    n = name.lower()
    return "ranged" if any(r in n for r in RANGED) else "melee"

def suite_of(src):
    b = os.path.basename(src)
    return "central" if "-5302" in b else "gen" if "gen-" in b or "-5301" in b else "ladder"

agg = collections.defaultdict(lambda: collections.defaultdict(list))  # suite -> metric -> [(v0, v1)]
seen = set()
for row in rows:
    d = row["dir"]
    if (d, row["source"]) in seen: continue
    seen.add((d, row["source"]))
    meta = json.load(open(os.path.join(AN, d, "meta.json"), encoding="utf-8"))
    # -12: bot 0 is team A; -21: bot 0 is team B
    bot0_team = 0 if row["teams"][0] == VARIANT else 1
    team_of = {c["id"]: c["team"] for c in meta["champions"]}
    kind = {c["id"]: kind_of(c.get("name") or str(c.get("type"))) for c in meta["champions"]}
    ev = [json.loads(l) for l in gzip.open(os.path.join(AN, d, "events.jsonl.gz"), "rt", encoding="utf-8")]
    m = {t: collections.Counter() for t in (0, 1)}
    clears = {}  # g -> (round, team) of the latest clear
    holds = {}
    latency = {0: [], 1: []}
    for e in ev:
        k = e["k"]
        if k == "group_clear" and isinstance(e.get("by"), int) and e["by"] in team_of:
            t = team_of[e["by"]]
            clears[e["g"]] = (e["r"], t)
            m[t]["clears"] += 1
        elif k == "capture_hold":
            c = clears.get(e["g"])
            if c and c[1] == e["team"] and e["g"] not in holds:
                latency[e["team"]].append(e["r"] - c[0])
                holds[e["g"]] = True
        elif k == "capture":
            t = e["team"]
            m[t]["captures"] += 1
            m[t]["capture_gems"] += sum(s[1] for s in e["shares"])
            m[t]["capture_gold"] += sum(s[2] for s in e["shares"])
            if len(e["shares"]) > 1: m[t]["shared_captures"] += 1
            clears.pop(e["g"], None); holds.pop(e["g"], None)
        elif k == "capture_reset" and e.get("team") in (0, 1):
            m[e["team"]]["capture_resets"] += 1
            holds.pop(e["g"], None)
        elif k == "camp_attack" and e.get("tgt") in team_of:
            t = team_of[e["tgt"]]
            m[t]["camp_dmg"] += e["dmg"]
            m[t][f"camp_dmg_{kind[e['tgt']]}"] += e["dmg"]
        elif k == "cast" and e.get("camp") is not None and e.get("a") in team_of:
            m[team_of[e["a"]]]["camp_casts"] += 1
        elif k == "death" and e.get("v") in team_of:
            t = team_of[e["v"]]
            m[t]["deaths"] += 1
            if e.get("by") == "camp": m[t]["camp_deaths"] += 1; m[t]["gems_lost_to_camps"] += e.get("gems", 0)
        elif k == "tribute_end" and e.get("a") in team_of:
            m[team_of[e["a"]]]["tributed"] += e["gems"]
    s = suite_of(row["source"])
    for key in set(m[0]) | set(m[1]):
        agg[s][key].append((m[bot0_team][key], m[1 - bot0_team][key]))
        agg["all"][key].append((m[bot0_team][key], m[1 - bot0_team][key]))
    for t in (0, 1):
        for x in latency[t]:
            agg[s]["lat0" if t == bot0_team else "lat1"].append(x)
            agg["all"]["lat0" if t == bot0_team else "lat1"].append(x)

ORDER = ["clears", "captures", "capture_gems", "capture_gold", "shared_captures", "capture_resets", "tributed",
         "camp_dmg", "camp_dmg_ranged", "camp_dmg_melee", "camp_casts", "deaths", "camp_deaths", "gems_lost_to_camps"]
for s in ["ladder", "gen", "central", "all"]:
    if s not in agg: continue
    a = agg[s]
    n = len(a["captures"]) if "captures" in a else 0
    print(f"\n## {s} ({n} games): per game, variant vs base")
    for key in ORDER:
        if key not in a: continue
        v0 = sum(x for x, _ in a[key]) / n; v1 = sum(y for _, y in a[key]) / n
        print(f"  {key:20s} {v0:9.1f} {v1:9.1f}  {100 * (v0 - v1) / v1 if v1 else 0:+6.1f}%")
    if a.get("lat0") and a.get("lat1"):
        print(f"  {'clear->hold rounds':20s} {statistics.mean(a['lat0']):9.2f} {statistics.mean(a['lat1']):9.2f}  "
              f"(median {statistics.median(a['lat0'])} vs {statistics.median(a['lat1'])}; n {len(a['lat0'])} vs {len(a['lat1'])})")

print("\n## clear->hold latency buckets (share of pickups)")
for s in ["gen", "all"]:
    a = agg[s]
    for name, xs in (("variant", a["lat0"]), ("base", a["lat1"])):
        n = len(xs)
        b = [sum(x <= 1 for x in xs), sum(2 <= x <= 3 for x in xs), sum(4 <= x <= 10 for x in xs), sum(11 <= x <= 30 for x in xs), sum(x > 30 for x in xs)]
        print(f"  {s:4s} {name:8s} <=1 {100*b[0]/n:5.1f}%  2-3 {100*b[1]/n:5.1f}%  4-10 {100*b[2]/n:5.1f}%  11-30 {100*b[3]/n:5.1f}%  >30 {100*b[4]/n:5.1f}%   rounds lost past 1: {sum(max(0, x-1) for x in xs)/ (len(agg[s]['captures'])):.1f}/game")
