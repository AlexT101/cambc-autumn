import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools' / 'replay'))
from analysis.data import Game, load_index  # noqa

US = 'PTN Hyperion'
SINCE = '2026-10-17T13:00'
STRONG = ['Intercontinental Fish', 'Nyxius', 'Mite', 'procless', 'new team(4)', 'new team (4)', 'AlphaSlop',
          'Sneaky Bush Campers', 'Univardisty of Shingtonwash']


def our_games(since=SINCE, roots=('replays/mine', 'replays/ladder')):
    """[(Game, our team, created, kind, source)] for nemesis-era games, one per distinct replay."""
    idx = load_index()
    out, seen = [], set()
    for r in idx:
        if not r['ok'] or not any(r['source'].startswith(x + '/') for x in roots):
            continue
        if US not in r['teams'] or r['dir'] in seen:
            continue
        g = Game(r['dir'])
        src = next((s for s in g.meta['sources'] if s['source'] == r['source']), g.meta['sources'][0])
        created = (src.get('group') or {}).get('createdAt') or ''
        if created < since:
            continue
        us = r['teams'].index(US)
        picks = g.picks[us]
        if picks[:2] != ['Cassi & Issac', 'Varg']:
            continue
        seen.add(r['dir'])
        g.us, g.them = us, 1 - us
        g.opp = r['teams'][1 - us]
        g.created = created
        g.gkind = (src.get('group') or {}).get('kind')
        g.src = r['source']
        g.gdir = r['source'].split('/')[2]
        out.append(g)
    out.sort(key=lambda g: (g.created, g.src))
    return out


def strong(name):
    n = name.lower().replace(' ', '')
    return any(s.lower().replace(' ', '') in n for s in STRONG)
