"""Download replays of ladder matches from the 2026a ladder, ours or other teams'. Requires Python 3.10+.

All endpoints used here are public: /ladder lists the teams, /match-groups lists a team's
five-game groups (newest first, paged with a `<createdAt>_<id>` cursor), /match-groups/<id>
lists its matches, and /matches/<id>/bundle is a zip holding replay.repl26a."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SITE = "https://2026a.battlecode.co.uk"
API = SITE + "/api/v1"
MY_TEAM = "547efb5b-57e5-4355-8501-3b331f506d62"
WEB_COOKIE_FILE = Path(os.environ.get("APPDATA", Path.home())) / "cambc" / "web-cookie.txt"
HEADERS = {"User-Agent": "cambc-replay-fetch"}


def use_web_cookie(path):
    """The website's own session (not `cambc login`'s) fills in each side's submission id and version."""
    cookie = path.read_text(encoding="utf-8-sig").strip()
    if cookie.lower().startswith("cookie:"):
        cookie = cookie[7:].strip()
    HEADERS["Cookie"] = cookie
    me = get_json("/match-groups", scope="all", team=MY_TEAM)
    if not me["groups"] or not has_versions(get_json(f"/match-groups/{me['groups'][0]['id']}")):
        print(f"warning: {path} gave no submission versions; the cookie may be wrong or expired", file=sys.stderr)


def fetch(url, retries=8):
    for attempt in range(retries + 1):
        wait = 2 ** min(attempt, 5)
        try:
            with urlopen(Request(url, headers=HEADERS), timeout=60) as r:
                return r.read()
        except HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == retries:
                raise
            if e.headers.get("Retry-After", "").isdigit():
                wait = int(e.headers["Retry-After"]) + 1
        except URLError:
            if attempt == retries:
                raise
        sleep(wait)


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


def cli_bundle(match_id):
    """Since 2026-10-17 bundles need a signed-in session: `cambc matches download` uses `cambc login`'s."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "bundle.zip"
        for attempt in range(12):
            sleep(3)  # the CLI endpoint rate-limits bursts
            r = subprocess.run(["cambc", "matches", "download", match_id, "-o", str(out)], capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                return out.read_bytes()
            wait = re.search(r"retry after (\d+) seconds", r.stderr + r.stdout)
            sleep(int(wait.group(1)) + 1 if wait else 2 ** min(attempt, 5))
        raise RuntimeError(f"cambc matches download {match_id}: {(r.stderr or r.stdout).strip()[-300:]}")


def fetch_bundle(url, match_id, attempts=12):
    # Bundles are built on first request, which answers {"status":"pending"} until ready.
    for attempt in range(attempts):
        try:
            data = fetch(url)
        except HTTPError as e:
            if e.code != 401:
                raise
            return cli_bundle(match_id)
        if data[:2] == b"PK" or attempt == attempts - 1:
            return data
        sleep(min(2 + attempt * 2, 15))


def has_versions(detail):
    return any(s.get("version") for s in detail["group"]["sides"])


def download_group(out, g, replays=True):
    """With replays=False only group.json is written; a later run with replays fills in the games."""
    d = group_dir(out, g)
    meta = d / "group.json"
    old = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else None
    want_meta = old is None or ("Cookie" in HEADERS and not has_versions(old))
    want_replays = replays and not any(d.glob("*.repl26a"))
    if not want_meta and not want_replays:
        return d, 0
    detail = get_json(f"/match-groups/{g['id']}")
    d.mkdir(parents=True, exist_ok=True)
    count = 0
    for m in detail["matches"] if want_replays else []:
        if m["status"] != "finished" or not m.get("replayUrl"):
            continue
        with zipfile.ZipFile(io.BytesIO(fetch_bundle(SITE + m["replayUrl"], m["id"]))) as z:
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
    p.add_argument("--mine", action="store_true",
                   help="our team, every group of either kind, into replays/mine/ (unless overridden)")
    p.add_argument("--kind", choices=["ranked", "unranked", "all"])
    p.add_argument("--since", help="only groups created at or after this ISO time, e.g. 2026-10-13")
    p.add_argument("--max-groups", type=int, help="newest N groups per team, 0 for all (default 20)")
    p.add_argument("--out", type=Path)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--list", action="store_true", help="print the ladder and exit")
    p.add_argument("--no-replays", action="store_true", help="write only each group's group.json")
    p.add_argument("--web-cookie", type=Path, default=WEB_COOKIE_FILE,
                   help="file holding the website's Cookie header, used when it exists (default: %(default)s)")
    args = p.parse_args()
    if args.mine:
        args.team.append(MY_TEAM)
    args.kind = args.kind or ("all" if args.mine else "ranked")
    args.max_groups = args.max_groups if args.max_groups is not None else 0 if args.mine else 20
    args.out = args.out or ROOT / "replays" / ("mine" if args.mine else "ladder")
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    if args.web_cookie.exists():
        use_web_cookie(args.web_cookie)

    ladder = get_json("/ladder")
    if args.list:
        for t in ladder["teams"]:
            print(f"{t['rank']:>4}  {t['rating']:7.1f}  {t['wins']:>3}-{t['losses']:<3}  {t['teamId']}  {t['name']}")
        return
    teams = resolve_teams(ladder, args.team, args.top)
    if not teams:
        sys.exit("choose teams with --mine, --top N and/or --team NAME, or see them with --list")

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
        futures = {pool.submit(download_group, args.out, g, not args.no_replays): g for g in groups.values()}
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
