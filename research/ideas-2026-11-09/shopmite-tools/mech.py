"""Mechanism check on decoded local A/B replays: our side's (cand's) per-champion r600 stats, kills, deaths, Power/Bruiser
emblems bought; team kills/deaths, win. Usage: mech.py ANA_DIR [ANA_DIR ...] (one label per dir: LABEL=DIR)."""
import gzip, json, sys, glob, os, collections, re
from multiprocessing import Pool
def one(d):
    m = json.load(open(d + '/meta.json')); base = os.path.basename(m['source']).split('.')[0]
    us = 0 if base.endswith('-12') else 1
    ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    rd = json.load(gzip.open(d + '/rounds.json.gz')); idx = {r: i for i, r in enumerate(rd['round'])}
    nm = {c['id']: c['name'] for c in m['champions']}; tm = {c['id']: c['team'] for c in m['champions']}
    C = collections.Counter(); C['games'] += 1; C['win'] += m['result']['winner'] == us
    for c in m['champions']:
        if c['team'] != us: continue
        n = c['name']; C[(n, 'n')] += 1
        ib = c['stats']['itemsBought']; items = dict(zip(ib[0::2], ib[1::2]))
        for it, k in items.items():
            fam = it // 6; emb = it % 2 == 1
            if emb and fam == 1: C[(n, 'power')] += k
            if emb and fam == 6: C[(n, 'bruiser')] += k
            if emb and fam == 12: C[(n, 'greed')] += k
            if not emb and fam == 12: C[(n, 'greedsh')] += k
    for c in rd['champions']:
        if tm[c['id']] != us: continue
        n = nm[c['id']]
        for r in (400, 600, 800):
            i = idx.get(r)
            if i is None or c['foc'][i] is None: continue
            C[(n, r, 'n')] += 1
            for f in ('str', 'foc', 'maxHp', 'earned'): C[(n, r, f)] += c[f][i]
    for e in ev:
        if e['k'] != 'death': continue
        v = e['v']; by = e.get('by')
        if tm.get(v) == us:
            C['deaths'] += 1; C[(nm[v], 'deaths')] += 1
            if by is not None and by in tm: C['deaths_champ'] += 1
            if e['r'] <= 600: C['deaths600'] += 1
        elif by is not None and tm.get(by) == us:
            C['kills'] += 1; C[(nm[by], 'kills')] += 1
            if e.get('cause') == 'Cast ability': C[(nm[by], 'castkills')] += 1
    for e in ev:
        if e['k'] == 'cast' and tm.get(e['a']) == us and e.get('ab') not in ('Dash', 'Attack reset'): C[(nm[e['a']], 'casts')] += 1
    return C
if __name__ == '__main__':
    for arg in sys.argv[1:]:
        lab, A = arg.split('=')
        ds = [os.path.dirname(p) for p in glob.glob(f'{A}/*/meta.json')]
        T = collections.Counter()
        with Pool(int(os.environ.get('NP', 8))) as p:
            for c in p.imap_unordered(one, ds, chunksize=8): T.update(c)
        g = T['games']
        print(f"== {lab}: games {g} win {T['win']/g:.3f} kills/g {T['kills']/g:.2f} deaths/g {T['deaths']/g:.2f} deaths<=600 {T['deaths600']/g:.2f}")
        for n in sorted({k[0] for k in T if isinstance(k, tuple)}):
            k = T[(n, 'n')]
            if k < 20: continue
            m6 = T[(n, 600, 'n')]
            s600 = f"r600 S{T[(n,600,'str')]/m6:.0f} F{T[(n,600,'foc')]/m6:.0f} H{T[(n,600,'maxHp')]/m6:.0f} g{T[(n,600,'earned')]/m6:.0f}" if m6 else ''
            ck = T[(n, 'castkills')]; cs = T[(n, 'casts')]
            print(f"  {n:13s} n={k:4d} K {T[(n,'kills')]/k:.2f} D {T[(n,'deaths')]/k:.2f} power {T[(n,'power')]/k:.2f} bruiser {T[(n,'bruiser')]/k:.2f} greed {T[(n,'greed')]/k:.2f}/{T[(n,'greedsh')]/k:.1f}sh castkill/cast {ck/max(1,cs):.3f} ({cs/k:.0f}/g) {s600}")
