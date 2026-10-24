"""Build a version's manifest from downloaded replay folders: every finished game our submission
`<version>` played, ladder or scrim.

    py tools/replay/harness/build_manifest.py --version v47 [FOLDER_GLOB ...] [--no-api]

FOLDER_GLOB defaults to replays/mine/* and replays/scrims/*/*: group folders as tools/fetch_replays.py
and tools/scrim_ladder.py write them (group.json plus <position>-<map>.repl26a and .team-<side>.fuel).
Groups created before the version's `since` (versions.py) are skipped unread. A group.json without
submission versions (scrim_ladder.py downloads without the website cookie) is resolved through the
website with the cookie that fetch_replays.py uses; answers are cached in <dir>/group-versions.json.
Opponent ranks come from the current public ladder. Writes <dir>/manifest.json (rows as in the v38
manifest.json); rerunning after more downloads adds the new games.
"""
import argparse
import glob
import json
import sys
from datetime import datetime
from pathlib import Path

import versions

REPO = versions.REPO
sys.path.insert(0, str(REPO / "tools"))
import fetch_replays as F  # noqa: E402


def iso(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    versions.add_arg(ap)
    ap.add_argument("folders", nargs="*", default=["replays/mine/*", "replays/scrims/*/*"])
    ap.add_argument("--no-api", action="store_true", help="no website calls: groups without versions are skipped, ranks left empty")
    args = ap.parse_args()
    cfg = versions.get(args.version)
    since = versions.VERSIONS[cfg.name].get("since")
    since = iso(since) if since else None
    cache_p = cfg.dir / "group-versions.json"
    cache = json.loads(cache_p.read_text(encoding="utf-8")) if cache_p.exists() else {}
    api = False

    def our_version(detail):
        nonlocal api
        g = detail["group"]
        side = next(s for s in g["sides"] if s["teamId"] == F.MY_TEAM)
        if side.get("version") is not None:
            return side["version"]
        if g["id"] not in cache and not args.no_api:
            if not api:
                if not F.WEB_COOKIE_FILE.exists():
                    sys.exit(f"{F.WEB_COOKIE_FILE} missing: needed for groups without submission versions (or --no-api)")
                F.use_web_cookie(F.WEB_COOKIE_FILE)
                api = True
            d = F.get_json(f"/match-groups/{g['id']}")
            cache[g["id"]] = next(s for s in d["group"]["sides"] if s["teamId"] == F.MY_TEAM).get("version")
        return cache.get(g["id"])

    ranks = {}
    if not args.no_api:
        try:
            ranks = {t["teamId"]: t["rank"] for t in F.get_json("/ladder")["teams"]}
        except Exception as e:  # ranks are informational
            print(f"ladder ranks unavailable: {e}", file=sys.stderr)

    groups_done = set()
    rows, seen_groups, skipped = [], 0, {"old": 0, "other_version": 0, "no_version": 0, "missing_files": 0, "not_ours": 0}
    dirs = sorted({Path(p) for pat in args.folders for p in glob.glob(str(REPO / pat)) if (Path(p) / "group.json").exists()})
    for d in dirs:
        # Folder names start with the group's creation time: skip old groups without reading them.
        try:
            stamp = datetime.strptime(d.name[:15], "%Y%m%d-%H%M%S").replace(tzinfo=since.tzinfo) if since else None
        except ValueError:
            stamp = None
        if since and stamp and stamp < since.replace(second=0, microsecond=0):
            skipped["old"] += 1
            continue
        detail = json.loads((d / "group.json").read_text(encoding="utf-8"))
        g = detail["group"]
        if g["id"] in groups_done:  # fetch_replays --mine also downloads our scrims
            continue
        if since and iso(g["createdAt"]) < since:
            skipped["old"] += 1
            continue
        if not any(s["teamId"] == F.MY_TEAM for s in g["sides"]):
            skipped["not_ours"] += 1
            continue
        v = our_version(detail)
        if v is None:
            skipped["no_version"] += 1
            continue
        if v != cfg.number:
            skipped["other_version"] += 1
            continue
        seen_groups += 1
        groups_done.add(g["id"])
        for m in sorted(detail["matches"], key=lambda m: m["position"]):
            if m["status"] != "finished":
                continue
            ours = next(s for s in m["sides"] if s["teamId"] == F.MY_TEAM)
            theirs = next(s for s in m["sides"] if s["teamId"] != F.MY_TEAM)
            stem = d / f"{m['position']}-{m['map']}"
            replay, fuel = stem.with_suffix(".repl26a"), Path(f"{stem}.team-{ours['side']}.fuel")
            if not replay.exists() or not fuel.exists():
                skipped["missing_files"] += 1
                continue
            rows.append({
                "replay": replay.relative_to(REPO).as_posix(), "fuel": fuel.relative_to(REPO).as_posix(),
                "map": m["map"], "kind": m.get("kind") or g["kind"], "group": g["id"], "match": m["id"], "position": m["position"],
                "our_side": ours["side"], "result": ours["result"], "rounds": m["rounds"], "end_reason": m.get("endReason"),
                "our_score": ours["score"], "opp_score": theirs["score"], "our_draft": ours.get("draft"), "opp_draft": theirs.get("draft"),
                "opponent": theirs["teamName"], "opp_rank": ranks.get(theirs["teamId"]), "opp_id": theirs["teamId"],
                "created": g["createdAt"], "source": d.parent.relative_to(REPO).as_posix(), "replay_exists": True,
            })
    cfg.dir.mkdir(parents=True, exist_ok=True)
    if cache:
        cache_p.write_text(json.dumps(cache, indent=1))
    keys = [f"{r['group'][:8]}-{r['position']}" for r in rows]
    if len(set(keys)) != len(keys):
        sys.exit("two groups share an 8-character id prefix: keys would collide")
    old = json.loads(cfg.manifest.read_text(encoding="utf-8"))["games"] if cfg.manifest.exists() else []
    cfg.manifest.write_text(json.dumps({"version": cfg.number, "games": rows}, indent=1, ensure_ascii=False), encoding="utf-8")
    new = len({k for k in keys} - {f"{r['group'][:8]}-{r['position']}" for r in old})
    print(f"{cfg.manifest.relative_to(REPO)}: {len(rows)} games in {seen_groups} groups ({new} new); skipped groups {skipped}")


if __name__ == "__main__":
    main()
