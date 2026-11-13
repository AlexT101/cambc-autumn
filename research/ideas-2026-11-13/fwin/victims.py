"""Per champion type on the opponent side of Fish: deaths a game (to champions / camps) by r500 and all game, killer
types, gold earned at r300, and gems lost; and the same for Fish's champions.   py victims.py EXT ROWS.json [TEAM]"""
import json, os, sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
from multiprocessing import Pool
def game(job):
    ext, d, fish = job
    meta, R, ev, mp = load(ext, d); typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    n = len(R['round']); out = {}
    for c in R['champions']:
        side = 'F' if c['team'] == fish else 'O'
        out[c['id']] = dict(side=side, t=typ[c['id']], d500=0, d=0, dc=0, k=0, k500=0, e300=c['earned'][min(300, n) - 1], vk=0)
    for e in ev:
        if e['k'] != 'death': continue
        v = out[e['v']]; v['d'] += 1; v['d500'] += e['r'] <= 500
        if 'camp' in e or e.get('by') not in out: v['dc'] += 1; continue
        k = out[e['by']]; k['k'] += 1; k['k500'] += e['r'] <= 500
        if k['t'] == 'Vesper Vale' and k['side'] == 'F': v['vk'] += 1
    return meta['result'].get('winner') == fish, list(out.values())
def main():
    ext, rows_f = sys.argv[1:3]; tm = sys.argv[3] if len(sys.argv) > 3 else None
    idx = json.load(open(ext + '/index.json'))['games']; rows = json.load(open(rows_f))
    with Pool(12) as p: res = p.map(game, [(ext, g['dir'], rows[m]['fish']) for g in idx for m in [os.path.basename(g['source'])[:-8]] if m in rows and (tm is None or rows[m].get('opp') == tm)])
    S = collections.defaultdict(lambda: collections.Counter())
    for fw, L in res:
        for x in L:
            s = S[(x['side'], x['t'])]; s['n'] += 1; s['fw'] += fw
            for k in ('d500', 'd', 'dc', 'k', 'k500', 'e300', 'vk'): s[k] += x[k]
    print(len(res), 'games')
    for k in sorted(S, key=lambda k: (k[0], -S[k]['n'])):
        s = S[k]; n = s['n']
        print(f"{k[0]} {k[1]:14s} n {n:4d} Fish wins {s['fw']/n:.2f} | deaths r500 {s['d500']/n:.2f} all {s['d']/n:.2f} (camp {s['dc']/n:.2f}, by Fish Vesper {s['vk']/n:.2f}) | kills r500 {s['k500']/n:.2f} all {s['k']/n:.2f} | earned r300 {s['e300']/n:5.0f}")
if __name__ == '__main__': main()
