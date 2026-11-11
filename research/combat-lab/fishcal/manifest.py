"""Harness manifest for one live version's scrims against Fish and Mite, from the scrim log.

    python3 research/combat-lab/fishcal/manifest.py v105 [--opps fish,mite]

Unzips each game's replay and our .fuel into replays/<version>/ladder/ and writes replays/<version>/manifest.json
in the harness's row format. The harness keys games by group[:8]-position, and scrim group ids share their
first 8 characters, so `group` holds the id's last 8 characters first (the full id is `group_id`)."""
import argparse, json, sys, zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
GAMES = REPO / "research/ladder-scrims-2026-11-06/data/games.jsonl"
OPPS = {"fish": "Intercontinental Fish", "mite": "Mite"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("version")
    ap.add_argument("--opps", default="fish,mite")
    a = ap.parse_args()
    num = int(a.version.lstrip("v"))
    want = {OPPS[o] for o in a.opps.split(",")}
    out = REPO / "replays" / a.version
    (out / "ladder").mkdir(parents=True, exist_ok=True)
    rows, seen = [], set()
    for line in GAMES.open():
        g = json.loads(line)
        if g["version"] != num or g["opp_name"] not in want or g["status"] != "finished" or not g.get("replay"):
            continue
        if g["match"] in seen:
            continue
        seen.add(g["match"])
        gid = g["group"]
        key = f"{gid[-8:]}-{g['position']}"
        rep, fuel = out / "ladder" / f"{key}.repl26a", out / "ladder" / f"{key}.team-{g['side']}.fuel"
        if not rep.exists() or not fuel.exists():
            with zipfile.ZipFile(REPO / g["replay"]) as z:
                rep.write_bytes(z.read("replay.repl26a"))
                fuel.write_bytes(z.read(f"team-{g['side']}.fuel"))
        ours, theirs = (g["our_gems"], g["opp_gems"])
        rows.append({
            "replay": rep.relative_to(REPO).as_posix(), "fuel": fuel.relative_to(REPO).as_posix(), "map": g["map"],
            "kind": "unranked", "group": f"{gid[-8:]}|{gid}", "group_id": gid, "match": g["match"], "position": g["position"],
            "our_side": g["side"], "result": g["result"], "rounds": g["rounds"], "end_reason": g["end_reason"],
            "our_score": ours, "opp_score": theirs, "our_draft": g["our_picks"], "opp_draft": g["opp_picks"],
            "opponent": g["opp_name"], "opp_rank": None, "opp_id": g["opp_id"], "refset": g.get("refset"),
            "created": g["created"], "seed": g["seed"], "source": "research/ladder-scrims-2026-11-06", "replay_exists": True,
            "our_kills": g.get("our_kills"), "opp_kills": g.get("opp_kills"),
        })
    keys = [f"{r['group'][:8]}-{r['position']}" for r in rows]
    if len(set(keys)) != len(keys):
        sys.exit("key collision")
    (out / "manifest.json").write_text(json.dumps({"version": num, "games": rows}, indent=1))
    print(f"{out / 'manifest.json'}: {len(rows)} games")


if __name__ == "__main__":
    main()
