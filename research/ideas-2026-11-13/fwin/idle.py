"""Idle bodies: per champion type and team, the share of alive rounds in r1-R spent on own spawn, and in long parks
(the same 3x3 for 40+ rounds off spawn), and its earned gold at R.   py idle.py EXT ROWS.json [R] [TEAM]"""
import json, os, sys, collections
from multiprocessing import Pool
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
RR = int(sys.argv[3]) if len(sys.argv) > 3 else 300
def game(job):
    ext, d, fish = job
    try: meta, R, ev, mp = load(ext, d)
    except Exception: return None
    typ = {c['id']: c['name'] for c in meta['champions']}; n = min(RR, len(R['round']))
    sp = mp['spawn']; out = []
    for c in R['champions']:
        t = c['team']; s = sp[t]; alive = home = park = 0; run = []; 
        for i in range(n):
            if not c['alive'][i] or c['x'][i] is None: run = []; continue
            alive += 1; p = (c['x'][i], c['y'][i])
            if s['minX'] <= p[0] <= s['maxX'] and s['minY'] <= p[1] <= s['maxY']: home += 1; run = []; continue
            run.append(p)
            while run and max(abs(run[0][0] - p[0]), abs(run[0][1] - p[1])) > 1: run.pop(0)
            if len(run) >= 40: park += 1
        out.append(('f' if t == fish else 'o', typ[c['id']], alive, home, park, c['earned'][n - 1]))
    return meta['result'].get('winner') == fish, out
def main():
    ext, rows_f = sys.argv[1:3]; team = sys.argv[4] if len(sys.argv) > 4 else None
    idx = json.load(open(ext + '/index.json'))['games']; rows = json.load(open(rows_f))
    jobs = [(ext, g['dir'], rows[m]['fish']) for g in idx for m in [os.path.basename(g['source'])[:-8]] if m in rows and (team is None or rows[m].get('opp') == team)]
    with Pool(8) as p: res = [x for x in p.map(game, jobs, chunksize=4) if x]
    S = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    for fw, o in res:
        for side, ty, a, h, pk, e in o:
            k = (side, ty); S[k][0] += 1; S[k][1] += a; S[k][2] += h; S[k][3] += pk; S[k][4] += e
    print(len(res), 'games; to round', RR)
    for k in sorted(S, key=lambda k: (k[0], -S[k][0])):
        n, a, h, pk, e = S[k]
        print(f'{k[0]} {k[1]:14s} n {n:4d}  alive {a/n:5.0f}  home {h/max(a,1):.2f}  parked {pk/max(a,1):.2f}  earned {e/n:6.0f}')
if __name__ == '__main__': main()
