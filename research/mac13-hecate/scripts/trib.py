import sys, json, gzip, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def one(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
    except Exception: return None
    names = [t['name'] for t in meta['teams']]; team = {c['id']: c['team'] for c in meta['champions']}
    out = {n: collections.Counter() for n in names}
    sc = R['gems']; win = 0 if sc[0][-1] > sc[1][-1] else 1
    for t in (0,1):
        o = out[names[t]]; o['games'] = 1; o['win'] = win == t; o['final'] = sc[t][-1]
        o['win_by_1000'] = win == t and sc[t][-1] >= 1000; o['r2000'] = len(R['round']) >= 2000
        o['carried_end'] = sum(c['gems'][-1] for c in R['champions'] if c['team']==t)
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e = json.loads(l); k = e.get('k')
        if k == 'tribute_start': o = out[names[team[e['a']]]]; o['t_start'] += 1; o['t_start_gems'] += e.get('gems',0); o['big_start'] += e.get('gems',0) >= 200
        elif k == 'tribute_end': o = out[names[team[e['a']]]]; o['t_end'] += 1; o['t_end_gems'] += e.get('gems',0); o['big_end'] += e.get('gems',0) >= 200
        elif k == 'tribute_cancel': o = out[names[team[e['a']]]]; o['t_cancel'] += 1
        elif k == 'lock_place': out[names[team[e['a']]]]['locks'] += 1
    return out
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    tot = collections.defaultdict(collections.Counter)
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one, dirs, chunksize=8):
            if o:
                for k, v in o.items(): tot[k].update(v)
    for k, v in tot.items():
        g = v['games']; print(k, ' '.join(f"{x} {v[x]/g:.2f}" for x in sorted(v) if x != 'games'))
