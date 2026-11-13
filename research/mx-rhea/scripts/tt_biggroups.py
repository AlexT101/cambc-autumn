"""Big groups (Golem or Monolith members): first round either team hit one, first capture, who captured and whether
the first capturer won; plus how many rounds a team's champions spent walking to small groups (<= 20 gems) farther
than the big group while it stood up and asleep. Usage: py tt_biggroups.py ANALYSIS_DIR"""
import gzip, json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def game(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text())
        mp = json.loads((d/meta['mapFile']).resolve().read_text())
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    big = {g['id']: ('Monolith' if 'Monolith' in g['types'] else 'Golem') for g in mp['groups'] if 'Monolith' in g['types'] or 'Golem' in g['types']}
    if not big: return None
    camp_g = {c['id']: c['group'] for c in mp['camps']}
    team = {c['id']: c['team'] for c in meta['champions']}
    first_hit = {}; first_cap = {}
    for e in ev:
        if e['k'] in ('attack', 'cast') and 'camp' in e:
            g = camp_g.get(e['camp'])
            if g in big and g not in first_hit: first_hit[g] = (e['r'], team.get(e['a']))
        elif e['k'] == 'capture' and e['g'] in big and e['g'] not in first_cap:
            first_cap[e['g']] = (e['r'], e['team'], sum(s[1] for s in e['shares']))
    w = meta['result']['winner']
    rows = []
    for g, kind in big.items():
        gg = next(x for x in mp['groups'] if x['id'] == g)
        rows.append((kind, gg['side'], gg['gems'], first_hit.get(g, (None, None)), first_cap.get(g, (None, None, 0)), w, meta['result']['rounds']))
    return rows


if __name__ == '__main__':
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p/'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, dirs, chunksize=8):
            if o: rows.extend(o)
    for kind in ('Golem', 'Monolith'):
        s = [r for r in rows if r[0] == kind]
        if not s: continue
        hit = [r[3][0] for r in s if r[3][0]]
        cap = [r for r in s if r[4][0]]
        never = sum(1 for r in s if r[4][0] is None)
        def q(xs, p): xs = sorted(xs); return xs[int(p * (len(xs) - 1))] if xs else None
        print(f'{kind}: {len(s)} groups in {len(set((r[6], r[2]) for r in s))} games; first hit median r{q(hit, .5)} (p25 {q(hit, .25)}, p75 {q(hit, .75)}), '
              f'never hit {len(s) - len(hit)}; captured {len(cap)}, never captured {never}; first capture median r{q([r[4][0] for r in cap], .5)}')
        by_side = Counter()
        for r in cap:
            rel = 'mid' if r[1] == -1 else ('own' if r[1] == r[4][1] else 'enemy')
            by_side[(rel, r[4][1] == r[5])] += 1
        print('   first capture by side of capturer and capturer won:', dict(by_side))
        early = [r for r in cap if r[4][0] <= 300]
        print(f'   first captured by r300: {len(early)}; capturer won {sum(1 for r in early if r[4][1] == r[5])}')
