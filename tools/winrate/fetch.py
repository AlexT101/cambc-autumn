"""Every ranked game on the ladder since a date, one compact JSON line per game, for winrate.mjs --games.

Lists groups ladder-wide (newest first) instead of per team, so each group is fetched once; groups
already in the file are skipped, so a rerun only adds new ones. About 500 bytes a game, against ~8 KB
on disk for each group.json folder fetch_replays.py writes."""

import argparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fetch_replays import ROOT, get_json  # noqa: E402


def groups_since(since):
    before = None
    while True:
        page = get_json("/match-groups", scope="all", kind="ranked", before=before)
        for g in page["groups"]:
            if g["createdAt"] < since:
                return
            yield g
        if not page.get("more") or not page["groups"]:
            return
        last = page["groups"][-1]
        before = page.get("next") or f"{last['createdAt']}_{last['id']}"


def game_lines(g):
    detail = get_json(f"/match-groups/{g['id']}")
    rating = {s["teamId"]: s["ratingBefore"] for s in detail["group"]["sides"]}
    out = []
    for m in detail["matches"]:
        sides = {s["side"]: s for s in m["sides"]}
        if m["status"] != "finished" or set(sides) != {"a", "b"}:
            continue
        out.append(json.dumps({
            "id": m["id"], "group": g["id"], "at": g["createdAt"], "map": m["map"],
            **{k: {"team": s["teamId"], "name": s["teamName"], "rating": rating.get(s["teamId"]), "draft": s["draft"],
                   "result": s["result"], "error": s["botError"]} for k, s in sides.items()},
        }, ensure_ascii=False, separators=(",", ":")))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--since", default="2026-10-22")
    p.add_argument("--out", type=Path, default=ROOT / "replays" / "winrate" / "games.jsonl")
    p.add_argument("--threads", type=int, default=8)
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    have = set()
    if args.out.exists():
        with args.out.open(encoding="utf-8") as f:
            have = {json.loads(line)["group"] for line in f if line.strip()}
    print(f"{len(have)} groups already in {args.out}", flush=True)

    done = failed = games = 0
    with args.out.open("a", encoding="utf-8") as f, ThreadPoolExecutor(args.threads) as pool:
        pending = deque()

        def finish():
            nonlocal done, failed, games
            g, future = pending.popleft()
            try:
                rows = future.result()
            except Exception as e:
                failed += 1
                print(f"FAILED {g['id']}: {e}", file=sys.stderr, flush=True)
                return
            f.write("".join(r + "\n" for r in rows))
            done += 1
            games += len(rows)
            if done % 1000 == 0:
                f.flush()
                print(f"{done} groups, {games} games, back to {g['createdAt'][:16]}", flush=True)

        # Unfinished groups (the round in progress) are left for a later run.
        for g in groups_since(args.since):
            if g["status"] != "finished" or g["id"] in have:
                continue
            pending.append((g, pool.submit(game_lines, g)))
            if len(pending) >= 4 * args.threads:
                finish()
        while pending:
            finish()
    print(f"{done} new groups ({games} games), {failed} failed", flush=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
