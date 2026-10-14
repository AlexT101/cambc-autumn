"""Download replays of other teams' matches from the 2026a ladder. Requires Python 3.10+.

All endpoints used here are public: /ladder lists the teams, /match-groups lists a team's
five-game groups (newest first, paged with a `<createdAt>_<id>` cursor), /match-groups/<id>
lists its matches, and /matches/<id>/bundle is a zip holding replay.repl26a."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import io
import json
from pathlib import Path
import re
import sys
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import zipfile


ROOT = Path(__file__).resolve().parent
SITE = "https://2026a.battlecode.co.uk"
API = SITE + "/api/v1"


def fetch(url, retries=4):
    for attempt in range(retries + 1):
        try:
            with urlopen(Request(url, headers={"User-Agent": "cambc-replay-fetch"}), timeout=60) as r:
                return r.read()
        except HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == retries:
                raise
        except URLError:
            if attempt == retries:
                raise
        sleep(2 ** attempt)


def get_json(path, **params):
    query = urlencode({k: v for k, v in params.items() if v is not None})
    data = json.loads(fetch(f"{API}{path}{'?' + query if query else ''}"))
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"{path}: {data['error']}")
    return data


def slug(name, fallback):
    s = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-")[:24]
    return s or fallback[:8]


def resolve_teams(ladder, wanted, top):
    teams = ladder["teams"] + ladder.get("unrated", [])
    chosen = {t["teamId"]: t for t in ladder["teams"][:top]}
    for w in wanted:
        hits = [t for t in teams if t["teamId"] == w or t["name"].casefold() == w.casefold()]
        if not hits:
            hits = [t for t in teams if w.casefold() in t["name"].casefold()]
        if len(hits) != 1:
            names = ", ".join(t["name"] for t in hits[:10]) or "none"
            sys.exit(f"--team {w!r} matched {len(hits)} teams ({names}); use the team id")
        chosen[hits[0]["teamId"]] = hits[0]
    return list(chosen.values())


def team_groups(team_id, kind, since, limit):
    before = None
    while True:
        page = get_json("/match-groups", scope="all", team=team_id, kind=kind, before=before)
        for g in page["groups"]:
            if since and g["createdAt"] < since:
                return
            if g["status"] == "finished":
                yield g
                limit -= 1
                if limit == 0:
                    return
        if not page.get("more") or not page["groups"]:
            return
        last = page["groups"][-1]
        before = page.get("next") or f"{last['createdAt']}_{last['id']}"


def group_dir(out, g):
    stamp = datetime.fromisoformat(g["createdAt"].replace("Z", "+00:00")).strftime("%Y%m%d-%H%M%S")
    a, b = sorted(g["sides"], key=lambda s: s["side"])
    return out / f"{stamp}-{slug(a['teamName'], a['teamId'])}-vs-{slug(b['teamName'], b['teamId'])}-{g['id'][:8]}"


def download_group(out, g):
    d = group_dir(out, g)
    if (d / "group.json").exists():
        return d, 0
    detail = get_json(f"/match-groups/{g['id']}")
    d.mkdir(parents=True, exist_ok=True)
    count = 0
    for m in detail["matches"]:
        if m["status"] != "finished" or not m.get("replayUrl"):
            continue
        with zipfile.ZipFile(io.BytesIO(fetch(SITE + m["replayUrl"]))) as z:
            for info in z.infolist():
                stem = f"{m['position']}-{m['map']}"
                name = f"{stem}.repl26a" if info.filename == "replay.repl26a" else f"{stem}.{Path(info.filename).name}"
                (d / name).write_bytes(z.read(info))
        count += 1
    # Written last so an interrupted group is retried next run.
    (d / "group.json").write_text(json.dumps(detail, indent=1, ensure_ascii=False), encoding="utf-8")
    return d, count


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--top", type=int, default=0, help="include the top N rated teams on the ladder")
    p.add_argument("--team", action="append", default=[], help="team name, name fragment or id (repeatable)")
    p.add_argument("--kind", choices=["ranked", "unranked", "all"], default="ranked")
    p.add_argument("--since", help="only groups created at or after this ISO time, e.g. 2026-10-13")
    p.add_argument("--max-groups", type=int, default=20, help="newest N groups per team, 0 for all (default 20)")
    p.add_argument("--out", type=Path, default=ROOT / "replays" / "ladder")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--list", action="store_true", help="print the ladder and exit")
    args = p.parse_args()
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    ladder = get_json("/ladder")
    if args.list:
        for t in ladder["teams"]:
            print(f"{t['rank']:>4}  {t['rating']:7.1f}  {t['wins']:>3}-{t['losses']:<3}  {t['teamId']}  {t['name']}")
        return
    teams = resolve_teams(ladder, args.team, args.top)
    if not teams:
        sys.exit("choose teams with --top N and/or --team NAME, or see them with --list")

    kind = None if args.kind == "all" else args.kind
    groups = {}
    for t in teams:
        found = list(team_groups(t["teamId"], kind, args.since, args.max_groups))
        print(f"{t['name']}: {len(found)} groups")
        for g in found:
            groups[g["id"]] = g
    print(f"{len(groups)} distinct groups -> {args.out}")

    args.out.mkdir(parents=True, exist_ok=True)
    done = failed = replays = 0
    with ThreadPoolExecutor(args.threads) as pool:
        futures = {pool.submit(download_group, args.out, g): g for g in groups.values()}
        for f, g in futures.items():
            try:
                d, n = f.result()
                replays += n
                done += 1
                print(f"[{done + failed}/{len(groups)}] {d.name}" + (f" ({n} replays)" if n else " (cached)"))
            except Exception as e:
                failed += 1
                print(f"[{done + failed}/{len(groups)}] FAILED {g['id']}: {e}", file=sys.stderr)
    print(f"{replays} new replays, {failed} failed groups")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
