"""At r=RC: per champion and side, shard-equivalents gained per shard spent (stats minus base over growth), and fight power
raw_output*maxHp per gold, in bins of gold spent."""
import gzip, json, os, collections
from multiprocessing import Pool
import numpy as np
A = os.environ['MA']; F = os.environ['MF']; RC = int(os.environ.get('RC', 600))
BASE = {'Vesper Vale': ((35,5),(100,10),(1000,100)), 'Marcella': ((40,3.5),(60,10),(1200,100)), 'Heart of Ruin': ((30,3),(80,9),(1000,100)),
        'Vendetta': ((65,6),(100,10),(900,100)), 'Tavi': ((45,5),(110,10),(900,75)), 'Prism': ((35,2.5),(90,8),(700,65)),
        'Cassi': ((30,3),(100,13),(600,65)), 'Issac': ((45,3),(100,10),(900,80)), 'Ren': ((35,5),(100,9),(900,100)), 'Varg': ((50,5),(100,10),(1000,100)),
        'Ryth': ((45,4.5),(100,10),(1200,100)), 'Stellar': ((30,3.5),(85,8.5),(650,65)), 'Willow': ((55,3),(140,5),(700,50))}
G = [json.loads(l) for l in open(F)]
G = list({g['mid']: g for g in G if 'err' not in g}.values())
def one(g):
    d = g['dir']; meta = json.load(open(f'{A}/{d}/meta.json')); ms = g['ms']
    rd = json.load(gzip.open(f'{A}/{d}/rounds.json.gz')); idx = {r: i for i, r in enumerate(rd['round'])}
    i = idx.get(RC); out = []
    if i is None: return out
    nm = {c['id']: c['name'] for c in meta['champions']}
    for c in rd['champions']:
        if c['foc'][i] is None or nm[c['id']] not in BASE: continue
        out.append(('M' if c['team'] == ms else 'O', nm[c['id']], c['str'][i], c['foc'][i], c['maxHp'][i], c['earned'][i], c['gold'][i]))
    return out
if __name__ == '__main__':
    L = [g for g in G if g['cr'] >= os.environ.get('LO', '2026-11-09T12') and g['opp'] == 'stellar best girl']
    rows = []
    with Pool(8) as p:
        for o in p.imap_unordered(one, L, chunksize=4): rows += o
    for ch in sorted(BASE):
        for s in 'MO':
            R = [r for r in rows if r[0] == s and r[1] == ch]
            if len(R) < 30: continue
            (s0, sg), (f0, fg), (h0, hg) = BASE[ch]
            S = np.array([r[2] for r in R]); Fo = np.array([r[3] for r in R]); H = np.array([r[4] for r in R]); E = np.array([r[5] for r in R]); Gd = np.array([r[6] for r in R])
            if ch == 'Ryth': S = S - 0.01 * (H - h0)
            spent = E - Gd
            eq = (S - s0) / sg + (Fo - f0) / fg + (H - h0) / hg
            ok = spent >= 150
            print(f"{s} {ch:14s} n={len(R):5d} earned {E.mean():6.0f} held {Gd.mean():5.0f} spent {spent.mean():6.0f} eq/shard {np.sum(eq[ok])/np.sum(spent[ok]/30):.3f}  "
                  f"share S/F/H {np.sum((S-s0)/sg)/np.sum(eq):.2f}/{np.sum((Fo-f0)/fg)/np.sum(eq):.2f}/{np.sum((H-h0)/hg)/np.sum(eq):.2f}")
