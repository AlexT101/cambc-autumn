"""Per game (live mode): tributed gems and earned gold of both teams at r200..r1200, our deaths by Fish's Vesper per
200-round window, and the result.   py traj.py EXT ROWS.json OUT.jsonl"""
import json, os, sys
from multiprocessing import Pool
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
CP = (200, 300, 400, 500, 600, 800, 1000, 1200)
def game(job):
    ext, d, fish, extra = job
    try: meta, R, ev, mp = load(ext, d)
    except Exception: return None
    n = len(R['round']); ch = R['champions']; typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    g = lambda t, r: R['gems'][t][min(r, n) - 1]
    e = lambda t, r: sum(c['earned'][min(r, n) - 1] for c in ch if c['team'] == t)
    vk = [0] * 10; ok = [0] * 10
    for x in ev:
        if x['k'] == 'death' and team[x['v']] != fish and x.get('by') in typ and team[x['by']] == fish:
            ok[min(x['r'] // 200, 9)] += 1
            if typ[x['by']] == 'Vesper Vale': vk[min(x['r'] // 200, 9)] += 1
    w = meta['result'].get('winner')
    return {**extra, 'rounds': n, 'fish_win': w == fish, 'gems_f': [g(fish, r) for r in CP], 'gems_o': [g(1 - fish, r) for r in CP],
            'gold_f': [e(fish, r) for r in CP], 'gold_o': [e(1 - fish, r) for r in CP], 'vkills': vk, 'fkills': ok,
            'has_v': any(typ[c['id']] == 'Vesper Vale' for c in ch if c['team'] == fish)}
def main():
    ext, rows_f, out = sys.argv[1:4]
    idx = json.load(open(ext + '/index.json'))['games']; rows = json.load(open(rows_f)); jobs = []
    for gg in idx:
        mid = os.path.basename(gg['source'])[:-8]
        if mid not in rows: continue
        r = rows[mid]; jobs.append((ext, gg['dir'], 1 if r['side'] == 'a' else 0, {'map': r['map'].replace('_', '-'), 'side': r['side'], 'version': r['version'], 'match': mid}))
    with Pool(12) as p: res = [x for x in p.map(game, jobs, chunksize=4) if x]
    with open(out, 'w') as fh:
        for x in res: fh.write(json.dumps(x) + '\n')
    print(len(res), '->', out)
if __name__ == '__main__': main()
