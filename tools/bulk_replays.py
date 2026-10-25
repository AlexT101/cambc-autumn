"""Unpack bulk replay/summary zips, keeping only ranked games between a day's top teams. Requires Python 3.10+.

Bulk zips (replays-YYYY-MM-DD-partN.zip of .repl26a, summaries-YYYY-MM-DD-partN.zip of .camstat, each
named by kind, match id and team ids) carry no team names, so the day's ranked groups are listed once through
the public API (cached under the day's folder), a Bradley-Terry fit over that day's ranked game results
picks the top teams, and the match ids of groups between two of them are fetched from each group's detail.
Kept games land in fetch_replays.py's layout (a folder per group with group.json and <n>-<map>.repl26a),
which tools/replay/extract.mjs reads team names from. Each zip is deleted once handled; its contents are
recorded in ledger.json, so the same zip dropped in again is deleted without extracting. A zip that yields no
games is kept and left out of the ledger."""

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import zipfile

from fetch_replays import API, HEADERS, group_dir

ROOT = Path(__file__).resolve().parents[1]
ZIP_NAME = re.compile(r"^(replays|summaries)-(\d{4}-\d{2}-\d{2})-.*\.zip$")
EXT = {"replays": ".repl26a", "summaries": ".camstat"}
# Entries are <ranked|unranked>_<match id>_<team A id>_vs_<team B id>.<ext>; the match id is the first uuid.
MATCH_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
MAX_ID = "ffffffff-ffff-ffff-ffff-ffffffffffff"


class Api:
    """Counts calls and 429s, so a run shows whether the API throttles it."""

    def __init__(self):
        self.lock = threading.Lock()
        self.calls = self.throttled = 0
        self.start = time.monotonic()

    def get(self, path, **params):
        url = f"{API}{path}?{urlencode(params)}" if params else f"{API}{path}"
        for attempt in range(10):
            try:
                with urlopen(Request(url, headers=HEADERS), timeout=60) as r:
                    data = json.loads(r.read())
                with self.lock:
                    self.calls += 1
                return data
            except HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504) or attempt == 9:
                    raise
                wait = int(e.headers["Retry-After"]) + 1 if e.headers.get("Retry-After", "").isdigit() else 2 ** min(attempt, 5)
                if e.code == 429:
                    with self.lock:
                        self.throttled += 1
                    print(f"  429 from {path}, waiting {wait}s", flush=True)
            except URLError:
                if attempt == 9:
                    raise
                wait = 2 ** min(attempt, 5)
            time.sleep(wait)

    def rate(self):
        t = time.monotonic() - self.start
        return f"{self.calls} calls in {t:.0f}s ({self.calls / max(t, 1e-9):.1f}/s), {self.throttled} throttled"


def last_sunday(year, month):
    d = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def london_midnight(day):
    """UTC instant of local midnight in London (BST from 01:00Z on the last Sunday of March to 01:00Z on
    the last Sunday of October); the bulk exports split days there."""
    utc = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    bst_start = datetime.combine(last_sunday(day.year, 3), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    bst_end = datetime.combine(last_sunday(day.year, 10), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    return utc - timedelta(hours=1) if bst_start <= utc - timedelta(hours=1) < bst_end else utc


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def list_slice(api, start, end):
    groups, before = [], f"{iso(end)}_{MAX_ID}"
    while True:
        page = api.get("/match-groups", scope="all", kind="ranked", before=before)
        for g in page["groups"]:
            if g["createdAt"] < iso(start):
                return groups
            groups.append(g)
        if not page.get("more") or not page["groups"]:
            return groups
        before = page["next"]


def ranked_groups(api, day, folder, threads):
    """Every finished ranked group created on the London day, listed in hourly slices in parallel."""
    cache = folder / "ranked-groups.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))["groups"]
    start, end = london_midnight(day), london_midnight(day + timedelta(days=1))
    if end > datetime.now(timezone.utc) - timedelta(minutes=30):
        sys.exit(f"{day} has not finished yet (London time); its ranked groups would be incomplete")
    slices = []
    t = start
    while t < end:
        slices.append((t, min(t + timedelta(hours=1), end)))
        t += timedelta(hours=1)
    print(f"{day}: listing ranked groups {iso(start)} to {iso(end)} in {len(slices)} slices", flush=True)
    found = {}
    with ThreadPoolExecutor(threads) as pool:
        for i, part in enumerate(pool.map(lambda s: list_slice(api, *s), slices)):
            for g in part:
                found[g["id"]] = g
            print(f"  slice {i + 1}/{len(slices)}: {len(found)} groups; {api.rate()}", flush=True)
    groups = sorted((g for g in found.values() if g["status"] == "finished"), key=lambda g: (g["createdAt"], g["id"]))
    folder.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"day": str(day), "start": iso(start), "end": iso(end), "groups": groups}), encoding="utf-8")
    return groups


def bradley_terry(groups, iterations=2000):
    """Game-level Bradley-Terry strengths by Hunter's MM updates. Each team also gets one win and one loss
    against a fixed opponent of strength 1, so unbeaten or winless teams stay finite."""
    wins = defaultdict(float)
    pair = defaultdict(float)
    games = defaultdict(int)
    names = {}
    for g in groups:
        a, b = sorted(g["sides"], key=lambda s: s["side"])
        for s in (a, b):
            names[s["teamId"]] = s["teamName"]
            wins[s["teamId"]] += s["wins"]
            games[s["teamId"]] += a["wins"] + b["wins"]
        key = tuple(sorted((a["teamId"], b["teamId"])))
        pair[key] += a["wins"] + b["wins"]
    opponents = defaultdict(list)
    for (x, y), n in pair.items():
        opponents[x].append((y, n))
        opponents[y].append((x, n))
    p = {t: 1.0 for t in names}
    for _ in range(iterations):
        new = {}
        for t in p:
            denom = sum(n / (p[t] + p[o]) for o, n in opponents[t]) + 2 / (p[t] + 1)
            new[t] = (wins[t] + 1) / denom
        shift = max(abs(new[t] / p[t] - 1) for t in p)
        p = new
        if shift < 1e-10:
            break
    return [{"teamId": t, "name": names[t], "strength": p[t], "games": games[t], "wins": wins[t]} for t in p]


def ranking(groups, folder, top, min_games):
    """The day's ranking, refit when --min-games changes; `teams` is its top `top`, rewritten when --top changes."""
    rank_file = folder / "ranking.json"
    old = json.loads(rank_file.read_text(encoding="utf-8")) if rank_file.exists() else None
    if old and old["minGames"] == min_games and old["top"] == top:
        return old
    if old and old["minGames"] == min_games:
        eligible = old["eligible"]
    else:
        teams = sorted(bradley_terry(groups), key=lambda r: -r["strength"])
        eligible = [r for r in teams if r["games"] >= min_games]
        for i, r in enumerate(eligible):
            r["rank"] = i + 1
    result = {"method": "Bradley-Terry over game results of the day's finished ranked groups",
              "top": top, "minGames": min_games, "teams": eligible[:top], "eligible": eligible}
    rank_file.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{folder.name}: top {top} of {len(eligible)} teams with {min_games}+ games:", flush=True)
    for r in result["teams"]:
        print(f"  {r['rank']:>3}  {r['wins']:>4.0f}/{r['games']:<4}  {r['name']}", flush=True)
    return result


def prune(folder, chosen, top):
    """Removes group folders left from a larger --top."""
    keep = {group_dir(folder, g).name for g in chosen}
    gone = [d for d in folder.iterdir() if d.is_dir() and d.name not in keep and (d / "group.json").exists()]
    for d in gone:
        for f in d.iterdir():
            f.unlink()
        d.rmdir()
    if gone:
        print(f"{folder.name}: removed {len(gone)} groups not between two top-{top} teams", flush=True)


def day_matches(api, day, out, args):
    """match id -> (group folder, file stem) for every match of a ranked group between two top teams."""
    folder = out / str(day)
    groups = ranked_groups(api, day, folder, args.threads)
    rank = ranking(groups, folder, args.top, args.min_games)
    top = {r["teamId"] for r in rank["teams"]}
    chosen = [g for g in groups if all(s["teamId"] in top for s in g["sides"])]
    prune(folder, chosen, args.top)

    def detail(g):
        d = group_dir(folder, g)
        meta = d / "group.json"
        if not meta.exists():
            data = api.get(f"/match-groups/{g['id']}")
            d.mkdir(parents=True, exist_ok=True)
            meta.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        return d, json.loads(meta.read_text(encoding="utf-8"))

    missing = sum(not (group_dir(folder, g) / "group.json").exists() for g in chosen)
    if missing:
        print(f"{day}: fetching {missing} of {len(chosen)} top-{args.top} group details", flush=True)
    keep = {}
    with ThreadPoolExecutor(args.threads) as pool:
        for d, data in pool.map(detail, chosen):
            for m in data["matches"]:
                keep[m["id"]] = (d, f"{m['position']}-{m['map']}")
    if missing:
        print(f"  {api.rate()}", flush=True)
    return keep


def zip_key(z):
    h = hashlib.sha256()
    for info in sorted(z.infolist(), key=lambda i: i.filename):
        h.update(f"{info.filename}\0{info.CRC}\0{info.file_size}\n".encode())
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--zips", type=Path, default=ROOT / "replay-bulk-zip", help="folder of bulk zips (default: %(default)s)")
    p.add_argument("--out", type=Path, default=ROOT / "replay-bulk", help="output folder (default: %(default)s)")
    p.add_argument("--top", type=int, default=15,
                   help="keep games between two of the day's top N teams (default 15); lowering it prunes extracted "
                        "groups, raising it cannot recover games from zips already deleted")
    p.add_argument("--min-games", type=int, default=10, help="ranked games that day to be ranked (default 10)")
    p.add_argument("--threads", type=int, default=8, help="parallel API requests (default 8)")
    p.add_argument("--keep-zips", action="store_true", help="do not delete zips after extracting")
    p.add_argument("--api-only", action="store_true", help="fetch the API data and ranking for the zips' days, extract nothing")
    args = p.parse_args()
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    args.out.mkdir(parents=True, exist_ok=True)
    ledger_file = args.out / "ledger.json"
    ledger = json.loads(ledger_file.read_text(encoding="utf-8")) if ledger_file.exists() else {"zips": {}}
    api = Api()
    days = {}
    zips = sorted(args.zips.glob("*.zip"), key=lambda f: [int(s) if s.isdigit() else s for s in re.split(r"(\d+)", f.name)])
    if args.api_only:
        for d in sorted({m.group(2) for f in zips if (m := ZIP_NAME.match(f.name))}):
            day_matches(api, date.fromisoformat(d), args.out, args)
        return
    for f in zips:
        m = ZIP_NAME.match(f.name)
        if not m:
            print(f"skip {f.name}: not replays-/summaries-YYYY-MM-DD-*.zip", flush=True)
            continue
        kind, day = m.group(1), date.fromisoformat(m.group(2))
        with zipfile.ZipFile(f) as z:
            key = zip_key(z)
            if key in ledger["zips"]:
                print(f"{f.name}: already extracted as {ledger['zips'][key]['name']}", flush=True)
            else:
                if day not in days:
                    days[day] = day_matches(api, day, args.out, args)
                keep = days[day]
                kept = 0
                for info in z.infolist():
                    mid = MATCH_ID.search(Path(info.filename).name)
                    target = mid and keep.get(mid.group(0))
                    if target:
                        d, stem = target
                        (d / f"{stem}{EXT[kind]}").write_bytes(z.read(info))
                        kept += 1
                if not kept:
                    # Some top-team game should be in every part, so none means the entry names don't match the ids.
                    sample = ", ".join(i.filename for i in z.infolist()[:3])
                    print(f"{f.name}: kept 0 of {len(z.infolist())}; left in place, not in the ledger. "
                          f"Entries look like: {sample}", flush=True)
                    continue
                ledger["zips"][key] = {"name": f.name, "day": str(day), "kind": kind, "entries": len(z.infolist()),
                                       "kept": kept, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                ledger_file.write_text(json.dumps(ledger, indent=1), encoding="utf-8")
                print(f"{f.name}: kept {kept} of {len(z.infolist())}", flush=True)
        if not args.keep_zips:
            f.unlink()
    for day, keep in sorted(days.items()):
        for kind, ext in EXT.items():
            have = sum((d / f"{stem}{ext}").exists() for d, stem in keep.values())
            print(f"{day}: {have} of {len(keep)} top-team {kind} present", flush=True)


if __name__ == "__main__":
    main()
