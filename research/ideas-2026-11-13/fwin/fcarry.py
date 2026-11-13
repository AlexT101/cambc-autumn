"""Fish's 100+ bags by carrier type: rounds a game, share seen by us, 100+ tributes a game, and killed with 100+.
    py fcarry.py EXT ROWS.json [TEAM]"""
import json, os, sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
from multiprocessing import Pool
def game(job):
    ext, d, fish = job
    meta, R, ev, mp = load(ext, d); typ = {c['id']: c['name'] for c in meta['champions']}
    fids = {c['id'] for c in R['champions'] if c['team'] == fish}
    S = collections.Counter(); T = collections.Counter(); tr = collections.Counter(); kl = collections.Counter()
    for c in R['champions']:
        if c['team'] != fish: continue
        for i in range(len(R['round'])):
            if c['alive'][i] and (c['gems'][i] or 0) >= 100:
                S[typ[c['id']]] += 1
                if any(x not in fids for x in (c['seenBy'][i] or [])): T[typ[c['id']]] += 1
    for e in ev:
        if e['k'] == 'tribute_end' and e['gems'] >= 100 and e['a'] in fids: tr[typ[e['a']]] += 1
        if e['k'] == 'death' and e['v'] in fids and e.get('gems', 0) >= 100: kl[typ[e['v']]] += 1
    return S, T, tr, kl
def main():
    ext, rows_f = sys.argv[1:3]; team = sys.argv[3] if len(sys.argv) > 3 else None
    idx = json.load(open(ext + '/index.json'))['games']; rows = json.load(open(rows_f))
    with Pool(12) as p: res = p.map(game, [(ext, g['dir'], rows[m]['fish']) for g in idx for m in [os.path.basename(g['source'])[:-8]] if m in rows and (team is None or rows[m].get('opp') == team)])
    S, T, tr, kl = [sum((r[k] for r in res), collections.Counter()) for k in range(4)]
    n = len(res)
    for k, v in S.most_common(): print(f'{k:14s} 100+ rounds/game {v/n:6.1f}  seen by opp {T[k]/v:.2f}  100+ tributes/game {tr[k]/n:.2f}  killed with 100+/game {kl[k]/n:.3f}')
if __name__ == '__main__': main()
