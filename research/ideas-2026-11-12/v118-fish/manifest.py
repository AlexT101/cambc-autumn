"""Harness manifest for v118's 345 Fish r8 games, from the pulled rows instead of the scrim log.

    py research/ideas-2026-11-12/v118-fish/manifest.py

tools/replay/harness/scrim_manifest.py reads research/ladder-scrims-2026-11-06/data/games.jsonl, which held 85 of
these games when this ran; replays/pulls/v118-fish-2026-11-12.json has all 345. Same row format and keys (the group
id's last 8 characters, then the position). Only bundles already on disk are listed, so rerun it as the download
catches up; replays/v118/manifest.json and replays/v118/ladder/ are rewritten idempotently."""
import json, sys, zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ROWS = REPO / "replays/pulls/v118-fish-2026-11-12.json"
OUT = REPO / "replays/v118"


def main():
    (OUT / "ladder").mkdir(parents=True, exist_ok=True)
    rows, missing = [], 0
    for g in json.loads(ROWS.read_text()):
        assert g["version"] == 118 and g["status"] == "finished" and g["opp_name"] == "Intercontinental Fish"
        if not (REPO / g["replay"]).exists():
            missing += 1
            continue
        gid = g["group"]
        key = f"{gid[-8:]}-{g['position']}"
        rep, fuel = OUT / "ladder" / f"{key}.repl26a", OUT / "ladder" / f"{key}.team-{g['side']}.fuel"
        if not rep.exists() or not fuel.exists():
            try:
                with zipfile.ZipFile(REPO / g["replay"]) as z:
                    rb, fb = z.read("replay.repl26a"), z.read(f"team-{g['side']}.fuel")
            except (zipfile.BadZipFile, KeyError):  # still being written
                missing += 1
                continue
            rep.write_bytes(rb); fuel.write_bytes(fb)
        rows.append({
            "replay": rep.relative_to(REPO).as_posix(), "fuel": fuel.relative_to(REPO).as_posix(), "map": g["map"],
            "kind": "unranked", "group": f"{gid[-8:]}|{gid}", "group_id": gid, "match": g["match"], "position": g["position"],
            "our_side": g["side"], "result": g["result"], "rounds": g["rounds"], "end_reason": g["end_reason"],
            "our_score": g["our_gems"], "opp_score": g["opp_gems"], "our_draft": g["our_picks"], "opp_draft": g["opp_picks"],
            "opponent": g["opp_name"], "opp_rank": None, "opp_id": g["opp_id"], "refset": g.get("refset"),
            "created": g["created"], "seed": None, "source": ROWS.relative_to(REPO).as_posix(), "replay_exists": True,
            "task": g["task"], "set": g["set"], "part": g["part"],
        })
    keys = [f"{r['group'][:8]}-{r['position']}" for r in rows]
    if len(set(keys)) != len(keys):
        sys.exit("key collision")
    (OUT / "manifest.json").write_text(json.dumps({"version": 118, "games": rows}, indent=1))
    print(f"{OUT / 'manifest.json'}: {len(rows)} games, {missing} bundles not on disk yet")


if __name__ == "__main__":
    main()
