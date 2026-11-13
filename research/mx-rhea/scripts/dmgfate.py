"""Fate of camp damage: for each champion type, its camp damage split by who captured that group's cycle next
(self, ally Prism, other ally, enemy, nobody before respawn/game end). Usage: py dmgfate.py DIR"""
import gzip, json, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def game(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text())
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
        mp = json.loads((d/meta['mapFile']).resolve().read_text())
    except Exception:
        return None
    names = {c['id']: c['name'] for c in meta['champions']}
    team = {c['id']: c['team'] for c in meta['champions']}
    camp_group = {c['id']: c['group'] for c in mp['camps']}
    pending = defaultdict(lambda: defaultdict(float))  # group -> champion -> damage this cycle
    out = defaultdict(float)
    def settle(g, capt_team, holders):
        for cid, dmg in pending[g].items():
            n = names.get(cid, '?')
            if capt_team is None: k = 'nobody'
            elif capt_team != team.get(cid): k = 'enemy'
            elif cid in holders: k = 'self'
            elif any(names.get(h) == 'Prism' for h in holders): k = 'ally-prism'
            else: k = 'ally-other'
            out[(n, k)] += dmg
        pending[g].clear()
    for e in ev:
        k = e['k']
        if k in ('attack', 'cast') and 'camp' in e and 'a' in e:
            for item in (e.get('cdmg') or []):
                try: camp, dmg = item
                except Exception: continue
                g = camp_group.get(camp)
                if g is not None: pending[g][e['a']] += dmg
        elif k == 'capture':
            settle(e['g'], e['team'], {s[0] for s in e['shares']})
        elif k == 'group_respawn':
            settle(e['g'], None, set())
    for g in list(pending): settle(g, None, set())
    return dict(out)

def main():
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p/'meta.json').exists()]
    T = defaultdict(float)
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, dirs, chunksize=4):
            if o:
                for k, v in o.items(): T[k] += v
    types = sorted({k[0] for k in T}, key=lambda n: -sum(v for k, v in T.items() if k[0] == n))
    for n in types:
        tot = sum(v for k, v in T.items() if k[0] == n) or 1
        print(f'{n:13s} dmg/game {tot/len(dirs):8.0f}', ' '.join(f'{k}:{100*T[(n,k)]/tot:4.1f}%' for k in ('self', 'ally-prism', 'ally-other', 'enemy', 'nobody')))

if __name__ == '__main__':
    main()
