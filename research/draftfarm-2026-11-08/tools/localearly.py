"""Early-game outcomes of CAND in ab.py runs: extract the replays, then per (map, cand side) gold, owned gems, captures
and deaths at fixed rounds for CAND's team and the opponent's.  localearly.py RUN [RUN...] -> pickle per run."""
import json, gzip, os, sys, subprocess, collections, pickle, numpy as np
R = '/home/ubuntu/cambc-autumn/'
OUT = os.path.expanduser('~/tmp-offload/draftfarm/ana-local')
RS = [25, 50, 75, 100, 150, 200, 300]
def matches(name):
    s = json.load(open(f'{R}replays/ab/{name}/summary.json'))
    for su in s['suites']:
        for m in json.load(open(R + su['batch'] + '/results.json'))['matches']:
            if m.get('winner') is None or not m.get('replay') or not os.path.exists(m['replay'] if m['replay'].startswith('/') else R + m['replay']): continue
            yield m
def run(name):
    ms = list(matches(name)); paths = [m['replay'] if m['replay'].startswith('/') else R + m['replay'] for m in ms]
    lst = OUT + f'/{name}.list'; os.makedirs(OUT, exist_ok=True); open(lst, 'w').write('\n'.join(paths))
    subprocess.run(['python3', R + 'tools/pooled.py', '16', '--', 'node', R + 'tools/replay/extract.mjs', *paths, '--threads', '16', '--out', OUT], check=False, stdout=subprocess.DEVNULL)
    idx = json.load(open(OUT + '/index.json'))['games']; dirs = {}
    for g in idx:
        if g.get('ok', True): dirs[os.path.realpath(g['source'] if g['source'].startswith('/') else os.path.join(R, g['source']))] = g['dir']
    rows = []
    for m, p in zip(ms, paths):
        d = dirs.get(os.path.realpath(p))
        if not d: continue
        d = OUT + '/' + d; cand = m['order'].index(0)  # cand's team index (0 = A)
        R_ = json.load(gzip.open(d + '/rounds.json.gz')); rr = np.array(R_['round'])
        meta = json.load(open(d + '/meta.json')); ch = {c['id']: c for c in meta['champions']}
        row = dict(map=os.path.basename(m['map']).replace('.map26a', ''), side='a' if cand == 0 else 'b', win=m['winner'] == 0)
        for r in RS:
            i = min(np.searchsorted(rr, r), len(rr) - 1)
            for t, nm in ((cand, 'u'), (1 - cand, 'o')):
                row[f'gold{r}{nm}'] = sum(c['earned'][i] for c in R_['champions'] if c['team'] == t)
                row[f'own{r}{nm}'] = R_['gems'][t][i] + sum(c['gems'][i] for c in R_['champions'] if c['team'] == t)
        deaths = []
        for l in gzip.open(d + '/events.jsonl.gz'):
            e = json.loads(l)
            if e['r'] > 300: break
            if e['k'] == 'death' and 'linked' not in e: deaths.append((e['r'], ch[e['v']]['team'] == cand, e.get('by') in ch))
        row['deaths'] = deaths
        rows.append(row)
    pickle.dump(rows, open(OUT + f'/{name}.pkl', 'wb'))
    return rows
def summary(rows, label):
    w = np.mean([r['win'] for r in rows])
    out = [f'{label}: n {len(rows)} win {w:.3f}']
    for r in (50, 100, 150, 200):
        out.append(f' r{r} gold {np.mean([x[f"gold{r}u"] for x in rows]):.0f}/{np.mean([x[f"gold{r}o"] for x in rows]):.0f} gems {np.mean([x[f"own{r}u"] for x in rows]):.1f}/{np.mean([x[f"own{r}o"] for x in rows]):.1f}')
    for lim in (100, 150):
        out.append(f' deaths<=r{lim} {np.mean([sum(1 for d in x["deaths"] if d[0] <= lim and d[1]) for x in rows]):.2f}/{np.mean([sum(1 for d in x["deaths"] if d[0] <= lim and not d[1]) for x in rows]):.2f}')
    return '\n'.join(out)
if __name__ == '__main__':
    for n in sys.argv[1:]:
        print(summary(run(n), n), flush=True)
