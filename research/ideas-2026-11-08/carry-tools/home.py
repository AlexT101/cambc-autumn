"""Trips home: completed recalls (health at start, gems), spawn arrivals by walking, per type; live opp vs spar opp."""
import json, gzip, os, sys, collections, numpy as np
sys.path.insert(0, os.path.expanduser('~/tmp-offload/carry'))
from econ import load, H
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools'); import live, local
RW = int(os.environ.get('RW', 600))
def f(d, team):
    meta = json.load(open(d + '/meta.json')); ch = {c['id']: c for c in meta['champions']}; name = {i: c['name'] for i, c in ch.items()}
    R = json.load(gzip.open(d + '/rounds.json.gz')); rr = R['round']; ri = {r: j for j, r in enumerate(rr)}
    C = {c['id']: c for c in R['champions']}
    o = collections.defaultdict(float); starts = {}
    for l in gzip.open(d + '/events.jsonl.gz'):
        e = json.loads(l)
        if e['r'] > RW: break
        a = e.get('a')
        if a is None or ch[a]['team'] != team: continue
        if e['k'] == 'recall_start':
            j = ri.get(e['r'], None)
            if j is not None: starts[a] = (C[a]['hp'][j] / max(1, C[a]['maxHp'][j]), e['gems'])
        elif e['k'] == 'recall_end':
            hp, gm = starts.get(a, (np.nan, 0)); nm = name[a]
            o['recalls'] += 1; o['rec_' + nm] += 1; o['rec_hp'] += hp if hp == hp else 0; o['rec_hp_n'] += hp == hp
            o['rec_gems'] += e['gems']; o['rec_gemless'] += e['gems'] == 0
            if hp == hp and hp >= 0.6: o['rec_healthy'] += 1
            if hp == hp and hp < 0.35: o['rec_low'] += 1
    return o
if __name__ == '__main__':
    L = load(H + 'bigl/ana', False); S = load(H + 'spar/ana')
    games = json.load(open(H + 'bigl/games.json')); liveg = {}
    for mid, g in games.items():
        if g['version'] != 89 or mid not in L: continue
        liveg[(g['map'].replace('_', '-'), g['side'], live.OPP[g['opp_name']])] = (L[mid], g)
    acc = collections.defaultdict(lambda: collections.defaultdict(list))
    for o in 'FM':
        for mp, side, m in local.matches(f'spar-c27-o29{o}'):
            k = os.path.basename(os.path.dirname(m['replay'])) + '/' + os.path.basename(m['replay']).split('.')[0]
            if k not in S or (mp, side, o) not in liveg: continue
            ot = 1 if side == 'a' else 0; ld, g = liveg[(mp, side, o)]
            for nm, d, t in (('live', H + 'bigl/ana/' + ld, ot), ('spar', H + 'spar/ana/' + S[k], ot), ('us_live', H + 'bigl/ana/' + ld, 1 - ot)):
                ff = f(d, t)
                for kk in set(ff) | {'recalls'}: acc[(o, nm)][kk].append(ff.get(kk, 0))
    for (o, nm), dd in sorted(acc.items()):
        n = len(dd['recalls'])
        print(o, nm, f"recalls/g {np.mean(dd['recalls']):.1f} hp@start {np.sum(dd['rec_hp'])/max(1,np.sum(dd['rec_hp_n'])):.2f} gemless {np.sum(dd['rec_gemless'])/n:.1f} healthy(>=.6) {np.sum(dd['rec_healthy'])/n:.1f} low(<.35) {np.sum(dd['rec_low'])/n:.1f} gems/recall {np.sum(dd['rec_gems'])/max(1,np.sum(dd['recalls'])):.1f}",
              ' '.join(f"{k[4:]} {np.sum(v)/n:.1f}" for k, v in sorted(dd.items()) if k.startswith('rec_') and k[4:] in ('Vesper Vale','Heart of Ruin','Marcella','Cassi','Issac','Tavi','Vendetta','Willow','Prism')))
