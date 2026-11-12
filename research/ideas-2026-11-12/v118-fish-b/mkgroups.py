"""Lay the v118-vs-Fish replays out as ladder group folders (replays/v118b/groups/<group8>/<pos>-<map>.repl26a plus a
synthesized group.json), so tools/replay/extract.mjs names the teams ("v118", "Fish"), the map and checks the result
against the rows file. Then: node tools/replay/extract.mjs replays/v118b/groups --out replays/v118b/analysis

    py research/ideas-2026-11-12/v118-fish-b/mkgroups.py     # after mkmanifest.py; rerun as bundles arrive"""
import json, os
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "replays/v118b"
rows = json.load((REPO / "replays/pulls/v118-fish-2026-11-12.json").open())
by = defaultdict(list)
for g in rows:
    by[g["group"]].append(g)
n = 0
for gid, gs in by.items():
    d = OUT / "groups" / gid[-8:]
    d.mkdir(parents=True, exist_ok=True)
    matches = []
    for g in sorted(gs, key=lambda g: g["position"]):
        key = f"{gid[-8:]}-{g['position']}"
        src = OUT / "ladder" / f"{key}.repl26a"
        dst = d / f"{g['position']}-{g['map']}.repl26a"
        if src.exists() and not dst.exists():
            os.link(src, dst)
        n += dst.exists()
        us = {"side": g["side"], "teamName": "v118", "teamId": "us", "score": g["our_gems"], "result": g["result"]}
        them = {"side": "b" if g["side"] == "a" else "a", "teamName": "Fish", "teamId": g["opp_id"], "score": g["opp_gems"],
                "result": "loss" if g["result"] == "win" else "win"}
        matches.append({"position": g["position"], "id": g["match"], "map": {"name": g["map"]}, "rounds": g["rounds"],
                        "sides": [us, them], "statistics": None})
    (d / "group.json").write_text(json.dumps({"group": {"id": gid, "kind": "unranked", "createdAt": gs[0]["created"], "sides": []},
                                              "matches": matches}, indent=1))
print(f"{n} replays in {len(by)} group folders under {OUT / 'groups'}")
