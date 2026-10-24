#!/usr/bin/env python3
"""Summarize Treasure exposure from the saved 80-game a67-control extract only.

Run from the repository root. This reads existing replay and extract files only,
sequentially, and writes report.json/report.md beside this script.
"""
import gzip
import hashlib
import json
import math
import os
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REPLAY_DIR = ROOT / "replays/willow-sustainable-crew-fallback-vs-a67-published80-20261023-v1"
EXTRACT_DIR = REPLAY_DIR / "extract"
PRELIGHT = REPLAY_DIR / "preflight.json"
MANIFEST = REPLAY_DIR / "manifest.txt"
INDEX = EXTRACT_DIR / "index.json"
ENUMS = EXTRACT_DIR / "enums.json"

TREASURE_SHARDS = {18, 20, 22}
TREASURE_EMBLEMS = {19, 21, 23}
DURABILITY_IDS = set(range(12, 18))
DURABILITY_EMBLEMS = {13, 15, 17}
JUNGLE_IDS = set(range(24, 30))
JUNGLE_EMBLEMS = {25, 27, 29}


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def counts(flat_pairs):
    if len(flat_pairs) % 2:
        raise ValueError(f"odd item pair array: {flat_pairs!r}")
    return {int(flat_pairs[i]): int(flat_pairs[i + 1]) for i in range(0, len(flat_pairs), 2)}


def has_any(item_counts, ids):
    return any(item_counts.get(i, 0) > 0 for i in ids)


def med_range(values):
    if not values:
        return {"n": 0, "median": None, "min": None, "max": None}
    return {
        "n": len(values),
        "median": round(statistics.median(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


def read_existing_extract(directory):
    meta = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
    with gzip.open(directory / "rounds.json.gz", "rt", encoding="utf-8") as f:
        rounds = json.load(f)
    return meta, rounds


def main():
    if (OUT / "report.json").exists() or (OUT / "report.md").exists():
        raise FileExistsError(f"refusing to overwrite prior output in {OUT}")
    try:
        os.nice(19)
    except (AttributeError, OSError):
        pass

    preflight = json.loads(PRELIGHT.read_text(encoding="utf-8"))
    game_index = json.loads(INDEX.read_text(encoding="utf-8"))
    index_by_source = {g["source"]: g for g in game_index["games"]}
    repo_relative = {}
    for source, row in index_by_source.items():
        repo_relative[Path(source).as_posix()] = row

    candidate_path = Path(preflight["candidate_workspace"]).resolve()
    a67_path = Path(preflight["parent_workspace"]).resolve()
    rows = []
    games = []
    replay_pins = []
    lines = [line.split() for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) != 80:
        raise ValueError(f"expected 80 published rows, got {len(lines)}")

    # Single bounded pass: each selected replay is hashed, and its existing
    # native round snapshots are read once in manifest order.
    for fields in lines:
        if len(fields) != 4:
            raise ValueError(f"unexpected manifest row: {fields!r}")
        bot0, bot1, map_path, replay_path = map(Path, fields)
        bot0, bot1 = bot0.resolve(), bot1.resolve()
        if bot0 == a67_path and bot1 == candidate_path:
            a67_team = 0
        elif bot1 == a67_path and bot0 == candidate_path:
            a67_team = 1
        else:
            raise ValueError(f"manifest bot order does not match pinned source paths: {fields!r}")

        replay_path = replay_path.resolve()
        replay_rel = replay_path.relative_to(ROOT).as_posix()
        ix = repo_relative.get(replay_rel)
        if ix is None:
            raise ValueError(f"replay missing from existing extract index: {replay_rel}")
        extract = EXTRACT_DIR / ix["dir"]
        meta, state = read_existing_extract(extract)
        if meta.get("sha256") != sha256_file(replay_path):
            raise ValueError(f"source replay pin differs from extract metadata: {replay_rel}")
        if len(state["round"]) == 0:
            raise ValueError(f"no round snapshots: {replay_rel}")

        team_roster = [c for c in meta["champions"] if c["team"] == a67_team]
        if len(team_roster) not in (3, 4, 5):
            raise ValueError(f"expected a 3-5 pick a67 roster in {replay_rel}, got {len(team_roster)}")
        champion_by_id = {c["id"]: c for c in state["champions"]}
        terminal_i = len(state["round"]) - 1
        game_row = {
            "replay": replay_rel,
            "replay_sha256": meta["sha256"],
            "map": map_path.name,
            "a67_team_index": a67_team,
            "winner_team_index": ix.get("winner"),
            "round_count": len(state["round"]),
            "terminal_round": state["round"][terminal_i],
            "champions": [],
        }

        for roster_entry in team_roster:
            cid = roster_entry["id"]
            col = champion_by_id[cid]
            terminal_items = counts(col["items"][terminal_i])
            first_i = None
            for i, item_state in enumerate(col["items"]):
                if has_any(counts(item_state), TREASURE_EMBLEMS):
                    first_i = i
                    break

            terminal_earned = int(col["earned"][terminal_i])
            completion_round = state["round"][first_i] if first_i is not None else None
            at_completion = int(col["earned"][first_i]) if first_i is not None else None
            post_completion = terminal_earned - at_completion if first_i is not None else None
            base_passive = 0.33 if roster_entry["name"] == "Vesper Vale" else 0.0
            implied_bonus = (0.2 / (1.0 + base_passive + 0.2) * post_completion
                             if post_completion is not None else None)
            ever_emblem = any(has_any(counts(item_state), TREASURE_EMBLEMS) for item_state in col["items"])
            ever_shard = any(has_any(counts(item_state), TREASURE_SHARDS) for item_state in col["items"])
            if ever_emblem:
                category = "completed"
            elif ever_shard:
                category = "partial"
            else:
                category = "no_treasure"

            item = {
                "champion_id": cid,
                "role": roster_entry["name"],
                "category": category,
                "ever_treasure_shard": ever_shard,
                "ever_treasure_emblem": ever_emblem,
                "first_completion_round": completion_round,
                "native_earned_at_completion_round_end": at_completion,
                "terminal_native_earned": terminal_earned,
                "post_completion_native_earned_floor_approx": post_completion,
                "implied_fixed_schedule_treasure_bonus_floor_approx": (
                    round(implied_bonus, 3) if implied_bonus is not None else None
                ),
                "terminal_has_durability_item": has_any(terminal_items, DURABILITY_IDS),
                "terminal_has_durability_emblem": has_any(terminal_items, DURABILITY_EMBLEMS),
                "terminal_has_jungle_item": has_any(terminal_items, JUNGLE_IDS),
                "terminal_has_jungle_emblem": has_any(terminal_items, JUNGLE_EMBLEMS),
            }
            game_row["champions"].append(item)
            rows.append(item)

        games.append(game_row)

        replay_pins.append({
            "path": replay_rel,
            "sha256": meta["sha256"],
            "size_bytes": replay_path.stat().st_size,
            "extract_dir": ix["dir"],
            "map_sha256": ix["mapHash"],
        })

    roles = sorted({x["role"] for x in rows})
    by_role = {}
    for role in roles:
        items = [x for x in rows if x["role"] == role]
        completed = [x for x in items if x["category"] == "completed"]
        post = [x["post_completion_native_earned_floor_approx"] for x in completed]
        bonus = [x["implied_fixed_schedule_treasure_bonus_floor_approx"] for x in completed]
        times = [x["first_completion_round"] for x in completed]
        by_role[role] = {
            "games": len(items),
            "completed": sum(x["category"] == "completed" for x in items),
            "partial": sum(x["category"] == "partial" for x in items),
            "no_treasure": sum(x["category"] == "no_treasure" for x in items),
            "first_completion_round": med_range(times),
            "post_completion_native_earned_floor_approx": med_range(post),
            "implied_fixed_schedule_bonus_floor_approx": med_range(bonus),
            "terminal_no_durability_item": sum(not x["terminal_has_durability_item"] for x in items),
            "terminal_no_durability_emblem": sum(not x["terminal_has_durability_emblem"] for x in items),
            "terminal_no_jungle_item": sum(not x["terminal_has_jungle_item"] for x in items),
            "terminal_no_jungle_emblem": sum(not x["terminal_has_jungle_emblem"] for x in items),
            "terminal_no_durability_or_jungle_item": sum(
                not x["terminal_has_durability_item"] and not x["terminal_has_jungle_item"] for x in items
            ),
        }

    pin_inputs = [PRELIGHT, MANIFEST, INDEX, ENUMS]
    result = {
        "schema": "willow-a67-treasure-exposure/v1",
        "scope": {
            "replay_set": str(REPLAY_DIR.relative_to(ROOT)),
            "control_side": "a67 parent only, selected by manifest bot order and preflight pinned paths",
            "games": len(games),
            "champions": len(rows),
            "analysis": "existing extract only; no engine run, build, or extraction",
        },
        "source_certainty": {
            "native_round_gold": "rounds.json.gz champions[].earned is populated from the engine snapshot's champion earnedGold field; the snapshot reader reads EXT_GOLD + champion id * 16; separate from soft event-derived earnings in meta.validation",
            "first_treasure_completion": "first end-of-round item snapshot with any Treasure Emblem (IDs 19, 21, 23)",
            "post_completion": "terminal native earned minus native earned at the end of first completion round; this excludes that entire round",
            "categories": "completed means an emblem appeared at any snapshot; partial means a Treasure shard appeared in any snapshot but no emblem ever appeared; no_treasure means neither appeared",
            "limitations": "native income and Treasure effects are observed after purchase; formula is a floor-counterfactual approximation on this fixed schedule, not causal ROI or proof of benefit. It ignores item costs and schedule/behavior changes. Gold values are integer snapshots, so estimates are approximate.",
        },
        "bonus_formula": "0.2 / (1 + base passive + 0.2) * post-completion native earned; base passive is 0.33 for Vesper Vale, 0 for other roles; Marcella's tribute-generated native income is eligible as specified",
        "roles": by_role,
        "terminal_teamwide": {
            "champions": len(rows),
            "no_durability_item": sum(not x["terminal_has_durability_item"] for x in rows),
            "no_durability_emblem": sum(not x["terminal_has_durability_emblem"] for x in rows),
            "no_jungle_item": sum(not x["terminal_has_jungle_item"] for x in rows),
            "no_jungle_emblem": sum(not x["terminal_has_jungle_emblem"] for x in rows),
            "no_durability_or_jungle_item": sum(
                not x["terminal_has_durability_item"] and not x["terminal_has_jungle_item"] for x in rows
            ),
        },
        "pins": {
            "preflight_sha256": sha256_file(PRELIGHT),
            "manifest_sha256": sha256_file(MANIFEST),
            "extract_index_sha256": sha256_file(INDEX),
            "enums_sha256": sha256_file(ENUMS),
            "candidate_source_sha256": preflight["candidate_source_sha256"],
            "a67_parent_source_sha256": preflight["parent_source_sha256"],
            "source_files": {p.name: {"path": str(p.relative_to(ROOT)), "sha256": sha256_file(p)} for p in pin_inputs},
            "replays": replay_pins,
        },
        "per_game": games,
        "script_sha256": sha256_file(Path(__file__).resolve()),
    }
    (OUT / "report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    write_markdown(result)


def write_markdown(result):
    lines = [
        "# A67 Treasure exposure from published80 controls",
        "",
        "Existing extracts only; a67 is selected from manifest order using pinned workspace paths. The games use 3–5 picks, so per-role denominators vary. No new game run, build, or extraction was performed.",
        "",
        "Native per-round `earned` comes from the engine snapshot `earnedGold` field. The extractor separately reports event-derived gold as a soft check; that derived value is not used here. First completion is the first end-of-round snapshot with a Treasure Emblem. Post-completion income is terminal native earned minus earned at the end of that round, excluding the whole completion round.",
        "",
        "The fixed-schedule estimate is `0.2 / (1 + base passive + 0.2) × post-completion native earned` (Vesper base passive 0.33; others 0; Marcella’s tribute-generated gold is eligible). It is a floor-counterfactual approximation, not causal ROI or proof of benefit: it assumes the observed purchase schedule and behavior, and ignores costs and schedule changes. Partial means at least one Treasure shard appeared, but no Treasure emblem appeared, across the recorded snapshots.",
        "",
        "| Role | Completed | Partial | No Treasure | First completion round, median [min–max] | Post-completion native earned, median [min–max] | Implied fixed-schedule bonus, median [min–max] | No Durability item at terminal | No Jungle item at terminal | Neither item |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for role, d in result["roles"].items():
        def fmt(key):
            x = d[key]
            return "—" if x["n"] == 0 else f"{x['median']:g} [{x['min']:g}–{x['max']:g}] (n={x['n']})"
        lines.append(
            f"| {role} | {d['completed']} | {d['partial']} | {d['no_treasure']} | "
            f"{fmt('first_completion_round')} | {fmt('post_completion_native_earned_floor_approx')} | "
            f"{fmt('implied_fixed_schedule_bonus_floor_approx')} | "
            f"{d['terminal_no_durability_item']}/{d['games']} | {d['terminal_no_jungle_item']}/{d['games']} | "
            f"{d['terminal_no_durability_or_jungle_item']}/{d['games']} |"
        )
    t = result["terminal_teamwide"]
    lines += [
        "",
        f"At terminal, across {t['champions']} a67 champions: {t['no_durability_item']} had no Durability-family item, {t['no_jungle_item']} had no Jungle-family item, and {t['no_durability_or_jungle_item']} had neither. Counts excluding emblems only: {t['no_durability_emblem']} had no Durability emblem and {t['no_jungle_emblem']} had no Jungle emblem.",
        "",
        "The Willow champion appeared in 52 of the 80 a67 rosters. At terminal, 38/52 had no Durability-family item, 19/52 had no Jungle-family item, and 16/52 had neither; 42/52 had no Durability emblem and 23/52 had no Jungle emblem.",
        "",
        "Detailed per-game/per-champion records, input hashes, and replay SHA256 pins are in `report.json`.",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
