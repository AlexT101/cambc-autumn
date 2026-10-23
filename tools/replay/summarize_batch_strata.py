#!/usr/bin/env python3
"""Summarize batch wins by map draft size using results and the matching mapgen index."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def draft_sizes(index_path):
    index = json.loads(Path(index_path).read_text(encoding="utf-8"))
    sizes = {}
    for row in index["maps"]:
        file_name = row["file"]
        picks = (row.get("spec") or {}).get("picks")
        if not isinstance(picks, int):
            picks = (row.get("metrics") or {}).get("picks")
        if not isinstance(picks, int):
            raise ValueError(f"mapgen index has no picks count for {file_name}")
        sizes[file_name] = picks
    return sizes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("--map-index", type=Path, required=True,
                        help="mapgen index.json for this exact fixed map pool")
    parser.add_argument("--native-audit", type=Path,
                        help="optional compact native-status audit to split rollovers by map pick count")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    batch = args.batch.resolve()
    results_path = batch / "results.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))
    sizes = draft_sizes(args.map_index)
    rows = results.get("matches", [])
    summary = {"schema": "batch-strata-summary/v1", "batch": str(batch),
               "results_sha256": sha256(results_path), "map_index": str(args.map_index.resolve()),
               "map_index_sha256": sha256(args.map_index), "scheduled": results.get("scheduled"),
               "completed": results.get("completed"), "runner_errors": results.get("errors"),
               "winner_semantics": "results.matches[].winner is bot index; no remapping through team order",
               "strata": {}, "validation": {},
               "scope_note": "This tool summarizes map-index draft-size strata only; use the validated replay extractor/reports for event attribution."}
    buckets = defaultdict(lambda: {"games": 0, "bot_wins": [0, 0], "runner_errors": 0,
                                  "map_names": set(), "orders": Counter()})
    missing = []
    for game in rows:
        map_name = Path(game["map"]).name
        if map_name not in sizes:
            missing.append(map_name)
            continue
        picks = sizes[map_name]
        bucket = buckets[str(picks)]
        bucket["games"] += 1
        bucket["map_names"].add(map_name)
        order = tuple(game.get("order", []))
        bucket["orders"]["".join(str(x) for x in order)] += 1
        if "error" in game:
            bucket["runner_errors"] += 1
        elif game.get("winner") in (0, 1):
            bucket["bot_wins"][game["winner"]] += 1
    for pick_count, bucket in sorted(buckets.items()):
        summary["strata"][pick_count] = {**bucket, "map_names": sorted(bucket["map_names"]),
                                         "orders": dict(bucket["orders"])}
    summary["validation"] = {"results_rows": len(rows), "missing_map_index_rows": missing,
                             "strata_games_sum": sum(v["games"] for v in buckets.values()),
                             "strata_wins_sum": [sum(v["bot_wins"][i] for v in buckets.values()) for i in (0, 1)],
                             "results_wins": results.get("wins"),
                             "ok": (not missing and len(rows) == results.get("scheduled")
                                    and sum(v["games"] for v in buckets.values()) == len(rows)
                                    and [sum(v["bot_wins"][i] for v in buckets.values()) for i in (0, 1)]
                                        == results.get("wins"))}
    if args.native_audit:
        native = json.loads(args.native_audit.read_text(encoding="utf-8"))
        native_buckets = defaultdict(lambda: {"games": 0, "rollovers_by_bot_index": [0, 0],
                                               "bot_errors_by_bot_index": [0, 0]})
        for game in native.get("matches", []):
            map_name = Path(game["map"]).name
            picks = sizes.get(map_name)
            if picks is None:
                raise ValueError(f"native audit map is absent from mapgen index: {map_name}")
            bucket = native_buckets[str(picks)]
            bucket["games"] += 1
            for side in game.get("counts", {}).get("by_side", []):
                bot_index = side.get("bot_index")
                if bot_index not in (0, 1):
                    raise ValueError(f"invalid bot_index in native audit row: {game.get('index')}")
                play = side.get("play", {})
                bucket["rollovers_by_bot_index"][bot_index] += play.get("rollover", 0)
                bucket["bot_errors_by_bot_index"][bot_index] += play.get("bot_error", 0)
        total_rollovers = [sum(b["rollovers_by_bot_index"][i] for b in native_buckets.values())
                           for i in (0, 1)]
        total_errors = [sum(b["bot_errors_by_bot_index"][i] for b in native_buckets.values())
                        for i in (0, 1)]
        audit_totals = [b.get("play", {}).get("rollover", 0) for b in native.get("bots", [])]
        audit_errors = [b.get("play", {}).get("bot_error", 0) for b in native.get("bots", [])]
        results_hash_matches = native.get("batch_results_sha256") == summary["results_sha256"]
        summary["native_rollovers_by_pick"] = dict(sorted(native_buckets.items()))
        native_ok = (len(audit_totals) == 2 and total_rollovers == audit_totals
                     and total_errors == audit_errors and results_hash_matches
                     and sum(b["games"] for b in native_buckets.values()) == native.get("games"))
        summary["native_rollover_validation"] = {"audit_games": native.get("games"),
                                                  "games_sum": sum(b["games"] for b in native_buckets.values()),
                                                  "results_hash_matches": results_hash_matches,
                                                  "rollovers_from_rows": total_rollovers,
                                                  "rollovers_from_audit_totals": audit_totals,
                                                  "bot_errors_from_rows": total_errors,
                                                  "bot_errors_from_audit_totals": audit_errors,
                                                  "ok": native_ok}
        summary["validation"]["ok"] = summary["validation"]["ok"] and native_ok
    output = args.out.resolve() if args.out else batch / "strata-summary.json"
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "output_sha256": sha256(output),
                      "validation": summary["validation"], "strata": summary["strata"]}, indent=2))
    return 0 if summary["validation"]["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
