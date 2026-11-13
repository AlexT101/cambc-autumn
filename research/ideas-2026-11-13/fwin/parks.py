"""Games where one of our champions parks (stays within a 3x3 off spawn for 60+ rounds while alive) before round R:
how many, the parked rounds, earned gold, and the result.   py parks.py EXT ROWS.json [R]"""
import json, os, sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
from multiprocessing import Pool
RR = int(sys.argv[3]) if len(sys.argv) > 3 else 600
def game(job):
    ext, d, fish, mapn = job
    meta, R, ev, mp = load(ext, d); typ = {c['id']: c['name'] for c in meta['champions']}
    n = min(RR, len(R['round'])); out = []
    for c in R['champions']:
        side = 'F' if c['team'] == fish else 'U'; sp = mp['spawn'][c['team']]; run = []; best = 0; tot = 0
        for i in range(n):
            if not c['alive'][i] or c['x'][i] is None: run = []; continue
            p = (c['x'][i], c['y'][i])
            if sp['minX'] <= p[0] <= sp['maxX'] and sp['minY'] <= p[1] <= sp['maxY']: run = []; continue
            run.append((i, p))
            while run and max(abs(run[0][1][0] - p[0]), abs(run[0][1][1] - p[1])) > 1: run.pop(0)
            if len(run) == 60: tot += 60
            elif len(run) > 60: tot += 1
        if tot: out.append((side, typ[c['id']], tot))
    return mapn, meta['result'].get('winner') == fish, out
def main():
    ext, rows_f = sys.argv[1:3]
    idx = json.load(open(ext + '/index.json'))['games']; rows = json.load(open(rows_f))
    with Pool(12) as p: res = p.map(game, [(ext, g['dir'], rows[m]['fish'], rows[m]['map']) for g in idx for m in [os.path.basename(g['source'])[:-8]] if m in rows])
    for side in 'UF':
        P = [(m, fw, [x for x in o if x[0] == side]) for m, fw, o in res]
        hit = [x for x in P if x[2]]
        print(side, 'games with a 60+ park before r', RR, ':', len(hit), 'of', len(P), '; opp win there', sum(not fw for _, fw, _ in hit) / max(1, len(hit)), 'elsewhere', sum(not fw for _, fw, o in P if not o) / max(1, len(P) - len(hit)))
        c = collections.Counter(t for _, _, o in hit for _, t, _ in o); print('   by type', dict(c.most_common()))
        print('   ', sorted(((sum(r for _, _, r in o), m) for m, _, o in hit), reverse=True)[:12])
if __name__ == '__main__': main()
