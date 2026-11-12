"""Fish's Vesper per game (live mode): her share of Fish's capture gold (r100 / r300 / all), captures she holds alone,
the round she first owns a Greed emblem, her gold banked while saving, Strength, deaths and kills, and the share of
our deaths she makes.   py vesper.py EXT ROWS.json OUT.jsonl"""
import gzip, json, os, sys, collections
from multiprocessing import Pool
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
GREED = {12 * 6 + 2 * s + 1 for s in range(3)}  # Greed emblems of S/F/H

def game(job):
    ext, d, fish, extra = job
    try: meta, R, ev, mp = load(ext, d)
    except Exception: return None
    ch = R['champions']; n = len(R['round']); team = {c['id']: c['team'] for c in meta['champions']}
    typ = {c['id']: c['name'] for c in meta['champions']}
    V = [c for c in ch if c['team'] == fish and typ[c['id']] == 'Vesper Vale']
    out = {'has_v': bool(V), **extra, 'rounds': n}
    g = collections.Counter(); solo = tot = 0
    for e in ev:
        if e['k'] != 'capture' or e['team'] != fish: continue
        sh = e['shares']; tot += 1
        for cid, gm, go in sh:
            iv = typ[cid] == 'Vesper Vale'
            for lim in (100, 300, 10 ** 6):
                if e['r'] <= lim: g[(lim, 'all')] += go; g[(lim, 'v')] += go * iv
        if len(sh) == 1 and typ[sh[0][0]] == 'Vesper Vale': solo += 1
    for lim, lab in ((100, 'r100'), (300, 'r300'), (10 ** 6, 'all')):
        out['vshare_' + lab] = g[(lim, 'v')] / g[(lim, 'all')] if g[(lim, 'all')] else None
    out['caps'] = tot; out['vsolo'] = solo
    kills_by = collections.Counter(); our_deaths = 0
    for e in ev:
        if e['k'] == 'death' and team[e['v']] != fish:
            our_deaths += 1
            if e.get('by') in typ: kills_by[typ[e['by']]] += 1
    out['our_deaths'] = our_deaths; out['killers'] = dict(kills_by)
    if V:
        c = V[0]; gr = None
        for i in range(n):
            L = c['items'][i] or []
            if any(L[k] in GREED for k in range(0, len(L), 2)): gr = i + 1; break
        out['greed_round'] = gr; out['v_str'] = [c['str'][min(r, n) - 1] for r in (200, 400, 600, 900)]
        out['v_gold_max_before_greed'] = max(c['gold'][:gr]) if gr else max(c['gold'])
        out['v_hp'] = [c['maxHp'][min(r, n) - 1] for r in (200, 400, 600, 900)]
        out['v_deaths'] = c['deaths'][-1]; out['v_kills'] = c['kills'][-1]
    w = meta['result'].get('winner') if isinstance(meta.get('result'), dict) else None
    out['fish_win'] = w == fish
    return out

def main():
    ext, rows_f, out = sys.argv[1:4]
    idx = json.load(open(ext + '/index.json'))['games']; rows = json.load(open(rows_f)); jobs = []
    for g in idx:
        mid = os.path.basename(g['source'])[:-8]
        if mid not in rows: continue
        r = rows[mid]; fish = 1 if r['side'] == 'a' else 0
        jobs.append((ext, g['dir'], fish, {'map': r['map'].replace('_', '-'), 'side': r['side'], 'version': r['version'], 'match': mid}))
    with Pool(int(os.environ.get('OMP_NUM_THREADS', '8'))) as p: res = [x for x in p.map(game, jobs, chunksize=4) if x]
    with open(out, 'w') as fh:
        for x in res: fh.write(json.dumps(x) + '\n')
    print(len(res), 'games ->', out)

if __name__ == '__main__': main()
