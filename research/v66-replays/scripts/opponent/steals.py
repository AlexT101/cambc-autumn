# How contested camps are won: for contested cycles (both teams >=10% of camp damage, or both held),
# who captured, whether the loser lost a champion within 10 tiles of the group during the cycle,
# whether the loser left after doing most damage, class, side. Per-map consistency. Examples.
import sys, json, glob, gzip
from collections import defaultdict, Counter
from multiprocessing import Pool
S = 'replays/v66-analysis'
sys.path.insert(0, S + '/an')
from common import *


def one(path):
    f = json.load(open(path))
    d = f['dir']; us = f['us']
    ev = [json.loads(l) for l in gzip.open(f'{EX}/{d}/events.jsonl.gz', 'rt')]
    m = meta(d); mj = mapj(m)
    team = {c['id']: c['team'] for c in m['champions']}
    gt = {g['id']: [tuple(t) for t in g['tiles']] for g in mj['groups']}
    deaths = [e for e in ev if e['k'] == 'death']
    rows = []
    for c in f['cycles']:
        tot = sum(c['dmg'])
        contested = (tot > 0 and min(c['dmg']) >= 0.1 * tot) or len(c['holds']) == 2
        if not contested: continue
        cap = c['cap']; lo = 1 - cap
        r0 = min(x for x in c['first_dmg_r'] if x is not None) if any(x is not None for x in c['first_dmg_r']) else c['clear_r'] or c['cap_r']
        dl = [e for e in deaths if r0 <= e['r'] <= c['cap_r'] and min(cheb(tuple(e['at']), t) for t in gt[c['g']]) <= 10]
        lo_died = sum(1 for e in dl if team[e['v']] == lo)
        cap_died = sum(1 for e in dl if team[e['v']] == cap)
        rows.append(dict(cap='us' if cap == us else 'them', cls=c['cls'], gems=c['gems'], rel=c['rel'][us], r=c['cap_r'], r0=r0,
                         lo_majority=c['dmg'][lo] > 0.5 * tot, lo_died=lo_died, cap_died=cap_died, cleared_by_loser=c['clearer'] == lo))
    return dict(dir=d, opp=f['opp'], map=f['map'], source=f['source'], rows=rows)


if __name__ == '__main__':
    with Pool(40) as p:
        R = p.map(one, glob.glob(S + '/opp/feat/*.json'))
    json.dump(R, open(S + '/opp/steals.json', 'w'))
    by = defaultdict(list)
    for x in R: by[x['opp']].append(x)
    pct = lambda a, b: f'{a/b*100:.0f}%' if b else '-'
    for o in ['Fish', 'Mite', 'UoS', 'PBG']:
        rows = [(x, r) for x in by[o] for r in x['rows']]
        print(f'== {o}: contested cycles {len(rows)}')
        for who in ('us', 'them'):
            mine = [r for x, r in rows if r['cap'] == who]
            print(f"  captured by {who}: {len(mine)} ({pct(len(mine),len(rows))}), gems {sum(r['gems'] for r in mine)} | loser did >50% dmg {pct(sum(r['lo_majority'] for r in mine),len(mine))} | loser lost a champion within 10 tiles during cycle {pct(sum(1 for r in mine if r['lo_died']),len(mine))} | capturer lost one {pct(sum(1 for r in mine if r['cap_died']),len(mine))}")
        for side in ('own', 'mid', 'enemy'):
            s = [r for x, r in rows if r['rel'] == side]
            print(f"   on our-frame side {side}: n={len(s)} we capture {pct(sum(1 for r in s if r['cap']=='us'),len(s))}")
        for cl in ('wolf', 'elk', 'gem', 'golem', 'mono'):
            s = [r for x, r in rows if r['cls'] == cl]
            if s: print(f"   class {cl}: n={len(s)} we capture {pct(sum(1 for r in s if r['cap']=='us'),len(s))}")
        # without any death: pure race
        s = [r for x, r in rows if not r['lo_died'] and not r['cap_died']]
        print(f"   no death near either side: n={len(s)} we capture {pct(sum(1 for r in s if r['cap']=='us'),len(s))}")
        pm = defaultdict(lambda: [0, 0])
        for x, r in rows: pm[x['map']][r['cap'] == 'us'] += 1
        print(f"   maps where they capture more contested cycles than we do: {sum(1 for a,b in pm.values() if a>b)}/{len(pm)} (ties {sum(1 for a,b in pm.values() if a==b)})")
        exs = [(x['source'], r['r0'], r['r'], r['cls'], r['rel']) for x, r in rows if r['cap'] == 'them' and r['lo_majority'] and not r['lo_died']][:3]
        print('   examples (they took a camp we did most damage to, no death):', exs)
