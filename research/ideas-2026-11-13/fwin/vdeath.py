"""Fish's Vesper deaths: round, killer type, cause (champion/camp), her bag, how many of ours within 4, and whether the
game was won.   py vdeath.py EXT ROWS.json [TEAM]"""
import json, os, sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
from multiprocessing import Pool
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def game(job):
    ext, d, fish = job
    meta, R, ev, mp = load(ext, d); typ = {c['id']: c['name'] for c in meta['champions']}; ch = R['champions']
    V = [c for c in ch if c['team'] == fish and typ[c['id']] == 'Vesper Vale']
    if not V: return None
    v = V[0]; out = []
    for e in ev:
        if e['k'] == 'death' and e['v'] == v['id']:
            i = max(0, e['r'] - 2); at = tuple(e['at']) if 'at' in e else (v['x'][i], v['y'][i])
            near = sum(1 for x in ch if x['team'] != fish and x['alive'][i] and x['x'][i] is not None and cheb((x['x'][i], x['y'][i]), at) <= 4)
            fnear = sum(1 for x in ch if x['team'] == fish and x['id'] != v['id'] and x['alive'][i] and x['x'][i] is not None and cheb((x['x'][i], x['y'][i]), at) <= 4)
            sp = mp['spawn']; ds = cheb(at, ((sp[fish]['minX'] + sp[fish]['maxX']) // 2, (sp[fish]['minY'] + sp[fish]['maxY']) // 2)); do = cheb(at, ((sp[1 - fish]['minX'] + sp[1 - fish]['maxX']) // 2, (sp[1 - fish]['minY'] + sp[1 - fish]['maxY']) // 2))
            out.append({'r': e['r'], 'by': 'camp' if 'camp' in e else typ.get(e.get('by'), '?'), 'gems': e.get('gems', 0), 'near': near, 'fnear': fnear, 'half': 'fish' if ds < do else 'ours', 'str': v['str'][i], 'maxhp': v['maxHp'][i]})
    return meta['result'].get('winner') == fish, out
def main():
    ext, rows_f = sys.argv[1:3]; team = sys.argv[3] if len(sys.argv) > 3 else None
    idx = json.load(open(ext + '/index.json'))['games']; rows = json.load(open(rows_f))
    with Pool(12) as p: res = [x for x in p.map(game, [(ext, g['dir'], rows[m]['fish']) for g in idx for m in [os.path.basename(g['source'])[:-8]] if m in rows and (team is None or rows[m].get('opp') == team)]) if x]
    n = len(res); D = [(fw, d) for fw, o in res for d in o]
    print(n, 'games with Fish Vesper;', len(D), 'deaths;', 'per game in Fish wins', sum(1 for fw, d in D if fw) / max(1, sum(1 for fw, _ in res if fw)), 'in Fish losses', sum(1 for fw, d in D if not fw) / max(1, sum(1 for fw, _ in res if not fw)))
    for key in ('by', 'near', 'fnear', 'half'):
        c = collections.Counter(d[key] for _, d in D); print(' ', key, dict(c.most_common(8)))
    for lo, hi in ((0, 200), (200, 400), (400, 600), (600, 900), (900, 2001)):
        L = [d for _, d in D if lo <= d['r'] < hi]; print(f'  r{lo}-{hi}: {len(L)} deaths, median str {sorted(x["str"] for x in L)[len(L)//2] if L else 0:.0f}, by {dict(collections.Counter(x["by"] for x in L).most_common(4))}')
    # first Vesper death round vs result
    for lo, hi in ((0, 300), (300, 500), (500, 800), (800, 2001)):
        g = [fw for fw, o in res if o and lo <= o[0]['r'] < hi]; print(f'  first death r{lo}-{hi}: {len(g)} games, opp wins {sum(not x for x in g)/max(1,len(g)):.2f}')
    g = [fw for fw, o in res if not o]; print(f'  never dies: {len(g)} games, opp wins {sum(not x for x in g)/max(1,len(g)):.2f}')
if __name__ == '__main__': main()
