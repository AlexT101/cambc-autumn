"""Game selection shared by the optimality scripts (replays/.analysis, built by tools/replay/extract.mjs).

Every script built on it takes:
  --src PREFIX...   sources by path prefix as index.json records them, e.g. replays/ladder or
                    replays/batch-20261017-091937-928141 (default: every ladder game)
  --since STAMP     ladder groups from this folder stamp on (YYYYMMDD or YYYYMMDD-HHMMSS, default 20261016);
                    batch games are never filtered by it
  --team NAME...    teams to report: ladder team names, or bot folder names for local batches (nemesis, rival)
  --vs NAME         only games against this team
  --together        only games in which every --team team plays
  --limit N         the first N games (by analysis dir)
  --copies          one row per source file instead of per analysis dir (the same ladder game downloaded twice
                    counts twice; byte-identical batch rematches count once each)
"""
import argparse
import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'replays', '.analysis'))
REPO = os.path.dirname(os.path.dirname(ROOT))
TOPS = ['Intercontinental Fish', 'Mite', 'Sneaky Bush Campers', 'Univardisty of Shingtonwash', 'procless', 'PTN Hyperion']


def parser(doc, team=None, limit=None, copies=False):
    p = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--src', nargs='+')
    p.add_argument('--since', default='20261016')
    p.add_argument('--team', nargs='+', default=team)
    p.add_argument('--vs')
    p.add_argument('--together', action='store_true')
    p.add_argument('--limit', type=int, default=limit)
    p.add_argument('--copies', action=argparse.BooleanOptionalAction, default=copies)
    p.add_argument('--threads', type=int, default=16)
    return p


def _prefix(p):
    p = p.replace('\\', '/')
    if os.path.isabs(p):
        p = os.path.relpath(p, REPO).replace('\\', '/')
    return p.removeprefix('./').rstrip('/')


def select(a, team_filter=True):
    """[(analysis dir, [team A name, team B name])], sorted by dir; names come from index.json, not meta.json."""
    rows = json.load(open(os.path.join(ROOT, 'index.json'), encoding='utf-8'))['games']
    prefixes = [_prefix(p) for p in a.src] if a.src else None
    out = []
    for g in rows:
        if not g['ok']:
            continue
        src = g['source']
        if prefixes is not None:
            if not any(src == p or src.startswith(p + '/') for p in prefixes):
                continue
        elif g['kind'] != 'ladder':
            continue
        if g['kind'] == 'ladder' and a.since and src.split('/')[2][:len(a.since)] < a.since:
            continue
        teams = g['teams']
        if a.vs and a.vs not in teams:
            continue
        if team_filter and a.team:
            if a.together and not all(t in teams for t in a.team):
                continue
            if not a.together and not any(t in teams for t in a.team):
                continue
        out.append((g['dir'], teams))
    if not a.copies:
        first = {}
        for d, teams in out:
            first.setdefault(d, teams)
        out = list(first.items())
    out.sort(key=lambda x: x[0])
    return out[:a.limit] if a.limit else out


def maps(games):
    """{map name: map hash} of the selected games."""
    dirs = {d for d, _ in games}
    rows = json.load(open(os.path.join(ROOT, 'index.json'), encoding='utf-8'))['games']
    return {g['map']: g['mapHash'] for g in rows if g['dir'] in dirs}


def games_per_team(games):
    n = {}
    for _, teams in games:
        for t in set(teams):
            n[t] = n.get(t, 0) + 1
    return n
