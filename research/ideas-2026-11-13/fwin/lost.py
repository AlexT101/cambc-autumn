"""Our gems lost to Fish kills, by our victim's type and Fish's killer type, and the bag sizes.   py lost.py EXT ROWS.json"""
import json, os, sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
from multiprocessing import Pool
def game(job):
    ext, d, fish = job
    try: meta, R, ev, mp = load(ext, d)
    except Exception: return None
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    out = []
    for e in ev:
        if e['k'] == 'death' and team[e['v']] != fish and e.get('gems', 0) > 0:
            out.append((typ[e['v']], typ.get(e.get('by'), 'camp') if 'camp' not in e else 'camp', e['gems'], e['r']))
    return meta['result'].get('winner') == fish, out
def main():
    ext, rows_f = sys.argv[1:3]
    team = sys.argv[3] if len(sys.argv) > 3 else None
    idx = json.load(open(ext + '/index.json'))['games']; rows = json.load(open(rows_f))
    jobs = [(ext, g['dir'], rows[os.path.basename(g['source'])[:-8]]['fish']) for g in idx if os.path.basename(g['source'])[:-8] in rows and (team is None or rows[os.path.basename(g['source'])[:-8]].get('opp') == team)]
    with Pool(8) as p: res = [x for x in p.map(game, jobs, chunksize=4) if x]
    for fw in (True, False):
        L = [o for w, o in res if w == fw]; n = len(L)
        by = collections.Counter(); byk = collections.Counter(); big = collections.Counter()
        for o in L:
            for v, k, g, r in o:
                by[v] += g; byk[k] += g
                if g >= 50: big[v] += 1
        print('Fish wins' if fw else 'Fish loses', n, 'games; our gems lost per game, by victim:', {k: round(v / n, 1) for k, v in by.most_common()})
        print('   by killer:', {k: round(v / n, 1) for k, v in byk.most_common()}, ' deaths with 50+ gems per game:', {k: round(v / n, 2) for k, v in big.most_common()})
if __name__ == '__main__': main()
