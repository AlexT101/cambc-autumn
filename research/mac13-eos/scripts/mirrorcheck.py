"""A no-op A/B's games mirror: each map's two games (sides swapped) have the same winning side, rounds
and per-side out-of-fuel turns. py mirrorcheck.py BATCH_DIR"""
import json, sys, collections
r = json.load(open(sys.argv[1] + "/results.json"))
by = collections.defaultdict(list)
for m in r["matches"]:
    by[m["map"]].append(m)
bad = 0
for mp, ms in sorted(by.items()):
    if len(ms) != 2:
        print("unpaired", mp, len(ms)); bad += 1; continue
    a, b = ms
    sa, sb = a["order"].index(a["winner"]), b["order"].index(b["winner"])
    # out-of-fuel turns by side: oof_turns is by bot index
    oa = [a["oof_turns"][a["order"][s]] for s in (0, 1)]
    ob = [b["oof_turns"][b["order"][s]] for s in (0, 1)]
    if sa != sb or a["rounds"] != b["rounds"] or oa != ob:
        bad += 1
        print("MISMATCH", mp.rsplit("/", 1)[-1], "side", sa, sb, "rounds", a["rounds"], b["rounds"], "oof", oa, ob)
print(f"{len(by)} maps, {bad} not mirrored")
