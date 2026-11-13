import sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from prismduel2 import g
if __name__ == '__main__':
    dirs = [d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: E = [x for r in ex.map(g, dirs, chunksize=8) for x in r]
    E = [e for e in E if e['r0'] < 600]
    print('encounters r<600', len(E), 'smaller dies', sum(e['smdead'] and not e['bigdead'] for e in E), 'bigger dies', sum(e['bigdead'] and not e['smdead'] for e in E))
    for lab, sel in (('smaller dies', lambda e: e['smdead'] and not e['bigdead']), ('bigger dies', lambda e: e['bigdead'] and not e['smdead']), ('no death', lambda e: not e['smdead'] and not e['bigdead'])):
        S = [e for e in E if sel(e)]
        m = lambda f: round(sum(f(e) for e in S)/len(S), 3)
        print(f'== {lab}: n {len(S)}')
        print('  round median', sorted(e['r0'] for e in S)[len(S)//2], ' gems small/big median', sorted(e['gs'] for e in S)[len(S)//2], sorted(e['gb'] for e in S)[len(S)//2])
        print('  focus ratio big/small median', sorted(e['fb']/max(1,e['fs']) for e in S)[len(S)//2], ' hp small', m(lambda e: e['hs']), 'hp big', m(lambda e: e['hb']))
        print('  small saw big at r0', m(lambda e: bool(e['seen'])), ' at r0-1', m(lambda e: e['seen_prev']))
        print('  small steps in', m(lambda e: e['sm_in']), ' big steps in', m(lambda e: e['big_in']))
        print('  allies near small', m(lambda e: e['as_']), ' near big', m(lambda e: e['ab']), ' min dist', m(lambda e: e['dmin']))
        print('  small branch r0', collections.Counter(e['brs'] for e in S).most_common(8))
        print('  small branch r0-2', collections.Counter(e['brs_prev'] for e in S).most_common(8))
    bins = collections.defaultdict(lambda: [0, 0, 0])
    for e in E:
        fr = e['fb']/max(1, e['fs'])
        k = '<1.15' if fr < 1.15 else '1.15-1.4' if fr < 1.4 else '1.4-2' if fr < 2 else '2-3' if fr < 3 else '3+'
        bins[k][0] += 1; bins[k][1] += e['smdead'] and not e['bigdead']; bins[k][2] += e['bigdead'] and not e['smdead']
    for k in sorted(bins): print('  focus ratio', k, 'n', bins[k][0], 'small dies', round(bins[k][1]/bins[k][0], 3), 'big dies', round(bins[k][2]/bins[k][0], 3))
