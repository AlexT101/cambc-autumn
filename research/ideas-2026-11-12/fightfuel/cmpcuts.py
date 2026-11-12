"""Shortcuts and out-of-fuel turns a game of profiled copies on the same games: python3 cmpcuts.py NAME=BATCHGLOB ..."""
import sys, collections
import fzread
if __name__ == '__main__':
    cols = {}
    for a in sys.argv[1:]:
        name, g = a.split('=', 1)
        R = fzread.rows([g])
        games = len({r['game'] for r in R})
        R = [r for r in R if r['round'] > 2 and r['hp'] >= 0]
        F = [r for r in R if r['seen'] > 0]
        c = collections.Counter(x for r in F for x in r['cuts'])
        c['OUT OF FUEL (all turns)'] = sum(1 for r in R if r['oof'] is not None)
        c['OUT OF FUEL (enemy in sight)'] = sum(1 for r in F if r['oof'] is not None)
        c['fight turns'] = len(F)
        c['guard asked (fight turns)'] = sum(1 for r in F if 88 in r['sc'])
        c['guard new sims'] = sum(r['sc'].get(72, (0, 0))[1] for r in F)
        c['left after decide < 5k (fight)'] = sum(1 for r in F if r['oof'] is None and r['left_decide'] < 5000)
        c['left after decide < 10k (fight)'] = sum(1 for r in F if r['oof'] is None and r['left_decide'] < 10000)
        cols[name] = {k: v / games for k, v in c.items()}
    keys = sorted({k for c in cols.values() for k in c}, key=lambda k: -max(c.get(k, 0) for c in cols.values()))
    print(f'{"a game (fight turns unless said)":36s}' + ''.join(f'{n:>12s}' for n in cols))
    for k in keys: print(f'{k:36s}' + ''.join(f'{c.get(k, 0):12.2f}' for c in cols.values()))
