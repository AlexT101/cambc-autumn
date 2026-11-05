"""Compact per-turn rows from the five Fish caches, for the misc_* analyses (MISC.md).

    python3 tools/fish/misc_rows.py OUT.jsonl.gz [--jobs 6]

One row per recorded Fish turn: cohort, game, map, side, round, actor, type, the actor's own
start/end state, turn-start visible enemies (count, nearest Chebyshev distance), on-own-spawn
flags, nearest altar distance, and the turn's actions (kind, target, before-state gems/gold/pos
where saved). Only the actor's own perspective is used. Refuses to overwrite OUT.
"""
import argparse, gzip, json, os, re, sys
from multiprocessing import Pool
from pathlib import Path

COHORTS = [('model', 'replays/fish-model', 'manifest.json'),
           ('confirm', 'replays/fish-confirm', 'confirmation-manifest.json'),
           ('third', 'replays/fish-third', 'third-manifest.json'),
           ('fourth', 'replays/fish-fourth', 'fourth-manifest.json'),
           ('fifth', 'replays/fish-fifth', 'fifth-manifest.json')]
RES = Path('research/fish-2026-11-05')


def mirror(m, x, y):
    W, H = m['width'], m['height']
    s = m['symmetry']
    if s == 'horizontal': return W - 1 - x, y
    if s == 'vertical': return x, H - 1 - y
    return W - 1 - x, H - 1 - y


def spawn_tiles(m, side):
    a = m['spawnA']
    tiles = {(x, y) for x in range(a['minX'], a['maxX'] + 1) for y in range(a['minY'], a['maxY'] + 1)}
    return tiles if side == 0 else {mirror(m, x, y) for x, y in tiles}


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def me_state(c):
    return {k: c.get(k) for k in ('alive', 'x', 'y', 'hp', 'maxHp', 'gems', 'gold', 'channelType', 'channelTimer', 'priority', 'cd', 'buffs')}


def one(job):
    cohort, path, entry = job
    with gzip.open(path) as f: g = json.load(f)
    m, side = g['map'], g['side']
    own, foe = spawn_tiles(m, side), spawn_tiles(m, 1 - side)
    altars = [tuple(a) for a in m['altars']]
    names = {c['id']: c['name'] for c in g['roster']}
    rows = []
    for t in g['turns']:
        s, e = t['start'], t.get('end') or t['start']
        me = s['me']
        pos = (me.get('x'), me.get('y'))
        epos = (e['me'].get('x'), e['me'].get('y'))
        en = [x for x in s['enemies'] if x.get('alive')]
        acts = []
        for a in t['actions']:
            r = {'k': a['kind'], 'to': a['to']}
            if 'before' in a:
                b = a['before']['me']; r['b'] = [b.get('x'), b.get('y'), b.get('gems'), b.get('gold'), b.get('hp')]
                r['be'] = [[x['id'], x['x'], x['y']] for x in a['before']['enemies'] if x.get('alive')]
            if 'value' in a: r['v'] = a['value']
            if 'slot' in a: r['slot'] = a['slot']
            acts.append(r)
        rows.append({'c': cohort, 'g': entry['sha256'][:16], 'grp': entry.get('group') or entry.get('match'), 'map': entry.get('map'),
                     'side': side, 'r': t['round'], 'id': t['id'], 'name': names[t['id']], 'n': m['champsPerTeam'],
                     's': me_state(me), 'e': me_state(e['me']), 'spawn0': pos in own, 'spawn1': epos in own,
                     'alt': min(cheb(pos, a) for a in altars) if altars and pos[0] is not None else None,
                     'ne': len(en), 'ed': min((cheb(pos, (x['x'], x['y'])) for x in en), default=None) if pos[0] is not None else None,
                     'en': [[x['id'], x['type'], x['x'], x['y'], x['hp'], x['maxHp'], x.get('gems', 0), x.get('channelType', 0), x.get('channelTimer', 0)] for x in en],
                     'grs': s['groups'], 'cps': [[c['id'], c['group'], c['type'], c['x'], c['y'], c['hp'], c['awake']] for c in s['camps']],
                     'al': [[x['id'], x['type'], x['x'], x['y'], x['hp'], x['maxHp'], x.get('gems', 0), x.get('channelType', 0)] for x in s['allies']],
                     'score': s['score'], 'fin': t.get('finish'), 'a': acts})
    return {'game': entry['sha256'][:16], 'cohort': cohort, 'map': entry.get('map'), 'side': side,
            'static': {'own': sorted(own), 'foe': sorted(foe), 'altars': altars, 'bushes': m['bushes'], 'walls': m['walls'],
                       'holes': m['holes'], 'W': m['width'], 'H': m['height'], 'camps': m['camps'], 'groups': m['groups'],
                       'symmetry': m['symmetry'], 'n': m['champsPerTeam']}, 'rows': rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out'); p.add_argument('--jobs', type=int, default=6)
    a = p.parse_args()
    if os.path.exists(a.out): sys.exit(f'refusing to overwrite {a.out}')
    jobs = []
    for cohort, d, man in COHORTS:
        for e in json.load(open(RES / man)):
            f = Path(d) / f"{e['sha256'][:16]}.json.gz"
            if f.exists(): jobs.append((cohort, str(f), e))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    tmp = a.out + '.part'
    with Pool(a.jobs) as pool, gzip.open(tmp, 'wt') as out:
        for i, res in enumerate(pool.imap_unordered(one, jobs)):
            out.write(json.dumps(res) + '\n')
            if i % 50 == 0: print(f'{i}/{len(jobs)}', file=sys.stderr)
    os.rename(tmp, a.out)
    print(f'{len(jobs)} games -> {a.out}', file=sys.stderr)


if __name__ == '__main__':
    main()
