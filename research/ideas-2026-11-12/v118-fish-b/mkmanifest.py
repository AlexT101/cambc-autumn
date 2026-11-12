"""The harness manifest for v118's 345 games against Fish r8, from the rows file (the scrim log is partial).

    py research/ideas-2026-11-12/v118-fish-b/mkmanifest.py

Unzips each bundle on disk into replays/v118b/ladder/<key>.repl26a (+ our .fuel) and writes replays/v118b/manifest.json
(scrim_manifest.py's row format). Rerun as bundles arrive; games whose bundle is missing are left out and counted."""
import json, sys, zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ROWS = REPO / "replays/pulls/v118-fish-2026-11-12.json"
OUT = REPO / "replays/v118b"

rows = json.load(ROWS.open())
(OUT / "ladder").mkdir(parents=True, exist_ok=True)
games, missing, bad = [], 0, 0
for g in rows:
    gid = g["group"]
    key = f"{gid[-8:]}-{g['position']}"
    z = REPO / g["replay"]
    rep, fuel = OUT / "ladder" / f"{key}.repl26a", OUT / "ladder" / f"{key}.team-{g['side']}.fuel"
    if not rep.exists() or not fuel.exists():
        if not z.exists():
            missing += 1
            continue
        try:
            with zipfile.ZipFile(z) as zf:
                a, b = zf.read("replay.repl26a"), zf.read(f"team-{g['side']}.fuel")
        except Exception as e:  # a bundle still being written
            bad += 1
            continue
        rep.write_bytes(a); fuel.write_bytes(b)
    games.append({
        "replay": rep.relative_to(REPO).as_posix(), "fuel": fuel.relative_to(REPO).as_posix(), "map": g["map"],
        "kind": "unranked", "group": f"{gid[-8:]}|{gid}", "group_id": gid, "match": g["match"], "position": g["position"],
        "our_side": g["side"], "result": g["result"], "rounds": g["rounds"], "end_reason": g["end_reason"],
        "our_score": g["our_gems"], "opp_score": g["opp_gems"], "our_draft": g["our_picks"], "opp_draft": g["opp_picks"],
        "opponent": g["opp_name"], "opp_rank": None, "opp_id": g["opp_id"], "refset": g.get("refset"),
        "created": g["created"], "seed": None, "source": "replays/pulls/v118-fish-2026-11-12.json", "replay_exists": True,
        "set": g["set"], "part": g["part"], "task": g["task"],
    })
keys = [f"{r['group'][:8]}-{r['position']}" for r in games]
if len(set(keys)) != len(keys):
    sys.exit("key collision")
(OUT / "manifest.json").write_text(json.dumps({"version": 118, "games": games}, indent=1))
print(f"{OUT / 'manifest.json'}: {len(games)} games, {missing} bundles missing, {bad} unreadable")
