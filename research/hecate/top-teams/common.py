import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools' / 'replay'))
from analysis.data import Game, chebyshev, ANALYSIS  # noqa: E402

TOP5 = ['Intercontinental Fish', 'Nyxius', 'Mite', 'procless', 'new team(4)']
ALSO = ['Sneaky Bush Campers', 'Univardisty of Shingtonwash']
TOP = TOP5 + ALSO
US = 'PTN Hyperion'
SHORT = {'Intercontinental Fish': 'Fish', 'Nyxius': 'Nyxius', 'Mite': 'Mite', 'procless': 'procless',
         'new team(4)': 'nt4', 'Sneaky Bush Campers': 'SBC', 'Univardisty of Shingtonwash': 'Univ', US: 'PTN'}


def games(since='2026-10-16T08:00', dirs=('replays/ladder', 'replays/mine'), need_top=True, until=None):
    idx = json.loads((ANALYSIS / 'index.json').read_text(encoding='utf-8'))['games']
    by_src = {r['source']: r for r in idx}
    out, seen = [], set()
    for d in dirs:
        for folder in sorted((ROOT / d).iterdir()):
            gj = folder / 'group.json'
            if not gj.exists():
                continue
            try:
                g = json.loads(gj.read_text(encoding='utf-8'))
            except Exception:
                continue
            created = g['group']['createdAt']
            if created < since or (until and created >= until):
                continue
            for m in g['matches']:
                sides = {s['side']: s for s in m['sides']}
                if 'a' not in sides or 'b' not in sides:
                    continue
                names = [sides['a']['teamName'], sides['b']['teamName']]
                if need_top and not any(n in TOP for n in names):
                    continue
                src = f"{d}/{folder.name}/{m['position']}-{m['map']}.repl26a"
                r = by_src.get(src)
                if not r or not r['ok'] or r['dir'] in seen:
                    continue
                seen.add(r['dir'])
                out.append({'dir': r['dir'], 'folder': folder.name, 'created': created, 'names': names,
                            'map': m['map'], 'pos': m['position'],
                            'winner': 0 if sides['a']['result'] == 'win' else 1 if sides['b']['result'] == 'win' else -1})
    return out


def load(rec):
    g = Game(rec['dir'])
    g.names = rec['names']
    g.rec = rec
    return g


def ref(rec, r=None):
    s = f"{rec['folder']}/{rec['pos']}-{rec['map']}"
    return s + (f' r{r}' if r is not None else '')
