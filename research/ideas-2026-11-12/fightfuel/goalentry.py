"""Turns by the fuel left when decide reaches its goal steps (profile v4, mark 90) and each later step: how many run out,
and where the unscoped out-of-fuel turns stood (the last mark passed): python3 goalentry.py BATCHGLOB"""
import sys, collections
import fzread
from instr_ids import IDS
if __name__ == '__main__':
    R = fzread.rows(sys.argv[1:])
    games = len({r['game'] for r in R})
    R = [r for r in R if r['round'] > 2 and r['hp'] >= 0]
    edges = [0, 2000, 4000, 6000, 8000, 10000, 15000, 20000, 30000, 10**9]
    for name, key in (('the goal steps (after the strike search and guards)', 90), ('farm', 82), ('siege/kite', 73), ('chase', 94), ('wants_shop', 92), ('the turn order', 75)):
        S = [r for r in R if key in r['sc'] and (r['seen'] > 0 or r['prism'] or r['oof'] is not None)]
        print(f'\n{name}: {len(S) / games:.1f} turns a game (fight turns, the Prism\'s calm turns, and every out-of-fuel turn)')
        for lo, hi in zip(edges, edges[1:]):
            T = [r for r in S if lo <= r['sc'][key][0] < hi]
            if not T: continue
            o = [r for r in T if r['oof'] is not None]
            where = collections.Counter(('.'.join(IDS.get(i, str(i)) for i in r['oof'][1:2]) or 'decide@' + IDS.get(r['sc'].get(79, (0,))[0], '?')) for r in o)
            dec = collections.Counter(r['dec'] for r in T if r['oof'] is None)
            print(f'  fuel {lo:6d}-{hi if hi < 10**9 else "":>6}: {len(T) / games:8.3f} a game; ran out {100 * len(o) / len(T):5.1f}%  in: ' + ', '.join(f'{k} {n}' for k, n in where.most_common(4)) + ';  finished as: ' + ' '.join(f'{k}{n}' for k, n in dec.most_common(5)))
    O = [r for r in R if r['oof'] is not None and len(r['oof']) <= 1]
    print(f'\nout-of-fuel turns outside every scope but decide: {len(O) / games:.2f} a game; last mark passed: ' + ', '.join(f'{IDS.get(k, k)} {n / games:.2f}' for k, n in collections.Counter(r['sc'].get(79, (0,))[0] for r in O).most_common(8)))
