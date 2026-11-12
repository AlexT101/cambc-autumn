"""Fish-side extras per game from extract.mjs output (live mode as mitefit/mstats.py: ROWS maps match id -> our side).
    py fishx.py EXT ROWS.json OUT.jsonl
Per Fish champion: type, earned gold at r100/300/600/end, kills, deaths, gems tributed, final shard-equivalents per
item family-stat, Strength at r300/600/900, max bag. Priority: share of Fish's distinct priority writes that fit its
11-09 rank code (bcexploit det3.fish_token), and the values themselves (first 40 distinct per body)."""
import gzip, json, os, sys, collections
from multiprocessing import Pool
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/bcexploit')
from mstats import load
import det3
FAM = ['Monster', 'Power', 'Durability', 'Treasure', 'Jungle', 'Home', 'Bruiser', 'Tribute', 'Capture', 'Prospector', 'Hunter', 'Skirmish', 'Greed', 'Collectors']
ST = ['S', 'F', 'H']

def item_name(i):
    f, r = divmod(i, 6); s, e = divmod(r, 2)
    return f'{FAM[f]}-{ST[s]}', (5 if e else 1)

def game(job):
    ext, d, fish, extra = job
    try: meta, R, ev, mp = load(ext, d)
    except Exception: return None
    ch = R['champions']; n = len(R['round'])
    mc = {c['id']: c for c in meta['champions']}
    out = []
    roster = [mc[c['id']]['name'] for c in ch if c['team'] == fish]
    lo, rank = det3.setup(roster)
    trib = collections.Counter()
    for e in ev:
        if e['k'] == 'tribute_end': trib[e['a']] += e['gems']
    j = 0
    for c in ch:
        if c['team'] != fish: continue
        m = mc[c['id']]
        it = collections.Counter()
        L = c['items'][-1] or []
        for i, k in zip(L[::2], L[1::2]):
            nm, w = item_name(i); it[nm] += w * k
        vals = []; last = None; fit = core = cnt = 0
        for i in range(n):
            v = c['prio'][i]
            if v != last:
                last = v
                if v != 0:
                    cnt += 1
                    t = det3.fish_token(v, len(roster), rank[j], c['hp'][i], c['maxHp'][i] or 1, c['shield'][i] or 0, c['gems'][i])
                    fit += t > 0; core += t == 2
                    if len(vals) < 40: vals.append((i + 1, v))
        out.append({'type': m['name'], 'earned': [c['earned'][min(r, n) - 1] for r in (100, 300, 600, n)],
                    'kills': m['stats'].get('kills'), 'deaths': m['stats'].get('deaths'), 'trib': trib[c['id']],
                    'dmg_champ': m['stats'].get('championDamageDone'), 'items': dict(it),
                    'str': [c['str'][min(r, n) - 1] for r in (300, 600, 900)], 'maxbag': max(c['gems']),
                    'prio_n': cnt, 'prio_fit': fit, 'prio_core': core, 'prio_vals': vals})
        j += 1
    w = meta['result'].get('winner') if isinstance(meta.get('result'), dict) else None
    return {'dir': d, 'rounds': n, 'fish_team': fish, 'fish_win': (w == fish) if w is not None else None, 'champs': out, **extra}

def main():
    ext, rows_f, out = sys.argv[1:4]
    idx = json.load(open(ext + '/index.json'))['games']; rows = json.load(open(rows_f)); jobs = []
    for g in idx:
        mid = os.path.basename(g['source'])[:-8]
        if mid not in rows: continue
        r = rows[mid]; fish = 1 if r['side'] == 'a' else 0
        jobs.append((ext, g['dir'], fish, {'map': r['map'].replace('_', '-'), 'side': r['side'], 'version': r['version'], 'match': mid, 'task': r.get('task')}))
    with Pool(int(os.environ.get('OMP_NUM_THREADS', '8'))) as p: res = [x for x in p.map(game, jobs, chunksize=4) if x]
    with open(out, 'w') as fh:
        for x in res: fh.write(json.dumps(x) + '\n')
    print(len(res), 'games ->', out)

if __name__ == '__main__': main()
