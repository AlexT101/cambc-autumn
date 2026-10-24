"""Per-opponent record of one of our submission versions over every game it played, from the website API.
Needs the website cookie (fetch_replays.py --web-cookie): without it the API hides submission versions.

    py tools/version_record.py 50                 # all kinds
    py tools/version_record.py 50 51 --kind ranked
    py tools/version_record.py 51 --json out.json

Groups are read newest first and paging stops once every group on a page is older than the oldest version asked."""

import argparse
import collections
import json
import sys
from concurrent.futures import ThreadPoolExecutor

import fetch_replays as F


def our_side(sides):
    return next((s for s in sides if s["teamId"] == F.MY_TEAM), None)


def groups_of(versions, kind):
    """Our match groups whose side ran one of `versions`, newest first."""
    out, before, low = [], None, min(versions)
    while True:
        page = F.get_json("/match-groups", scope="all", team=F.MY_TEAM, kind=kind, before=before)
        seen = [our_side(g["sides"]) for g in page["groups"]]
        out += [g for g, s in zip(page["groups"], seen) if s and s.get("version") in versions]
        older = all(s and s.get("version") is not None and s["version"] < low for s in seen)
        if not page.get("more") or not page["groups"] or older:
            return out
        last = page["groups"][-1]
        before = page.get("next") or f"{last['createdAt']}_{last['id']}"


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("versions", type=int, nargs="+", help="our submission versions")
    p.add_argument("--kind", choices=("ranked", "unranked"), help="default: both")
    p.add_argument("--web-cookie", default=F.WEB_COOKIE_FILE, help="file holding the website's Cookie header")
    p.add_argument("--json", help="also write the per-game rows here")
    args = p.parse_args()
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    F.use_web_cookie(F.Path(args.web_cookie))

    groups = groups_of(set(args.versions), args.kind)
    with ThreadPoolExecutor(4) as pool:
        details = list(pool.map(lambda g: F.get_json(f"/match-groups/{g['id']}"), groups))
    rows = []
    for d in details:
        for m in d["matches"]:
            us = our_side(m["sides"])
            them = next(s for s in m["sides"] if s is not us)
            rows.append({"team": them["teamName"], "kind": m["kind"], "version": us["version"], "side": us["side"],
                         "picks": len(us["draft"]) or None, "map": m["map"], "result": us["result"],
                         "status": m["status"], "group": d["group"]["id"], "match": m["id"]})
    done = [r for r in rows if r["result"] in ("win", "loss")]
    print(f"versions {', '.join(map(str, args.versions))}: {len(groups)} groups, {len(rows)} games, "
          f"{len(done)} finished ({len(rows) - len(done)} pending or failed)")

    def rec(rs):
        w = sum(r["result"] == "win" for r in rs)
        return f"{w}-{len(rs) - w}" + (f" {100 * w / len(rs):3.0f}%" if rs else "")

    by_team = collections.defaultdict(list)
    for r in done:
        by_team[r["team"]].append(r)
    cols = [("all", lambda r: True), ("ranked", lambda r: r["kind"] == "ranked"), ("unranked", lambda r: r["kind"] == "unranked"),
            ("3-pick", lambda r: r["picks"] == 3), ("4-pick", lambda r: r["picks"] == 4), ("5-pick", lambda r: r["picks"] == 5),
            ("side A", lambda r: r["side"] == "a"), ("side B", lambda r: r["side"] == "b")]
    print(f"\n{'team':<28}" + "".join(f"{c:>12}" for c, _ in cols))
    for team, rs in sorted(by_team.items(), key=lambda kv: -len(kv[1])):
        print(f"{team[:27]:<28}" + "".join(f"{rec([r for r in rs if f(r)]) if any(f(r) for r in rs) else '-':>12}" for _, f in cols))
    print(f"{'total':<28}" + "".join(f"{rec([r for r in done if f(r)]):>12}" for _, f in cols))
    if args.json:
        F.Path(args.json).write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
