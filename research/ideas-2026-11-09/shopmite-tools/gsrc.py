"""Gold sources to r600 per champion and side: capture shares, kill gold, Marcella tribute gold (2/gem x bonus), captures held."""
import gzip, json, os, collections
from multiprocessing import Pool
A = os.environ['MA']; F = os.environ['MF']; R = 600
G = [json.loads(l) for l in open(F)]
G = list({g['mid']: g for g in G if 'err' not in g}.values())
def one(g):
    d = g['dir']; meta = json.load(open(f'{A}/{d}/meta.json')); ms = g['ms']
    nm = {c['id']: c['name'] for c in meta['champions']}; tm = {c['id']: c['team'] for c in meta['champions']}
    S = lambda c: 'M' if tm[c] == ms else 'O'
    C = collections.Counter()
    for c in meta['champions']: C[(S(c['id']), c['name'], 'n')] += 1
    for l in gzip.open(f'{A}/{d}/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['r'] > R: break
        if e['k'] == 'capture':
            for cid, gems, gold in e['shares']: k = (S(cid), nm[cid]); C[k + ('cap',)] += gold; C[k + ('capn',)] += 1; C[k + ('capgems',)] += gems
        elif e['k'] == 'death' and e.get('by') in tm and 'gold' in e: C[(S(e['by']), nm[e['by']], 'kill')] += e['gold']
        elif e['k'] == 'tribute_end' and nm[e['a']] == 'Marcella': C[(S(e['a']), 'Marcella', 'trib')] += 2 * e['gems']; C[(S(e['a']), 'Marcella', 'tribgems')] += e['gems']
        elif e['k'] == 'tribute_end': C[(S(e['a']), nm[e['a']], 'tribgems')] += e['gems']
    return C
if __name__ == '__main__':
    L = [g for g in G if g['cr'] >= os.environ.get('LO', '2026-11-09T12') and g['opp'] == 'stellar best girl']
    T = collections.Counter()
    with Pool(8) as p:
        for c in p.imap_unordered(one, L, chunksize=4): T.update(c)
    for ch in ('Marcella', 'Heart of Ruin', 'Vesper Vale', 'Vendetta', 'Tavi', 'Prism', 'Cassi'):
        for s in 'MO':
            n = T[(s, ch, 'n')]
            if n < 30: continue
            k = lambda x: T[(s, ch, x)] / n
            print(f"{s} {ch:13s} n={n:5d} to r{R}: capture gold {k('cap'):6.0f} ({k('capn'):.1f} shares, {k('capgems'):.0f} gems) kill gold {k('kill'):5.0f} tribute gold {k('trib'):4.0f} gems tributed {k('tribgems'):.0f}")
