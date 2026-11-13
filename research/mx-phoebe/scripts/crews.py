"""Camp-hit turns by crew size (distinct teammates hitting the same group within +-2 rounds), by group type, r<=RMAX.
Also each clear's champion-turns vs the same map group's solo clears (paired by group across games' clears).

    python3 crews.py EXTRACT_DIR [--rmax 300] [--by-bot NAME]
"""
import argparse, gzip, json
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

PRIMARY = ['Monolith', 'Golem', 'Elk', 'Wolf', 'Gem cluster', 'Gold cluster']


def gtype(types):
    for t in PRIMARY:
        if t in types:
            return t
    return '?'


def one(args):
    d, rmax, bot = args
    d = Path(d)
    try:
        meta = json.loads((d / 'meta.json').read_text())
        mp = json.loads((d / meta['mapFile']).resolve().read_text())
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = [t['name'] for t in meta['teams']]
    camp_group = {c['id']: c['group'] for c in mp['camps']}
    gt = {g['id']: gtype(g['types']) for g in mp['groups']}
    team_of = {c['id']: c['team'] for c in meta['champions']}
    typ = {c['id']: c['name'] for c in meta['champions']}
    hits = defaultdict(set)  # (team, group, round) -> champions
    for e in ev:
        if e['k'] in ('attack', 'cast') and 'camp' in e and e['r'] <= rmax and e['a'] in team_of:
            hits[(team_of[e['a']], camp_group.get(e['camp']), e['r'])].add(e['a'])
    out = Counter()
    for (t, g, r), who in hits.items():
        if bot and names[t] != bot:
            continue
        crew = set()
        for dr in range(-2, 3):
            crew |= hits.get((t, g, r + dr), set())
        n = len(crew)
        k = min(n, 4)
        for a in who:
            out[(gt[g], k)] += 1
            out[('all', k)] += 1
            out[('type:' + typ[a], k)] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--rmax', type=int, default=300)
    ap.add_argument('--by-bot')
    a = ap.parse_args()
    dirs = [p.parent for p in Path(a.dir).glob('*/meta.json')]
    tot = Counter()
    n = 0
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(one, [(str(x), a.rmax, a.by_bot) for x in dirs], chunksize=8):
            if r is not None:
                tot.update(r)
                n += 1
    teams = n if a.by_bot else 2 * n
    print(f'{n} games; camp-hit champion-turns per team-game by crew size (1,2,3,4+), r<={a.rmax}')
    keys = sorted(set(k for k, _ in tot))
    for k in keys:
        row = [tot[(k, s)] / teams for s in (1, 2, 3, 4)]
        s = sum(row)
        print(f'{k:22s} ' + ' '.join(f'{x:7.1f}' for x in row) + f'   total {s:7.1f}  crew2+ {100 * (s - row[0]) / max(s, 1e-9):5.1f}%')


if __name__ == '__main__':
    main()
