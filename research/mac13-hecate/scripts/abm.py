"""Per-bot metrics from an extract dir of an A/B: win%, Prism bag/Focus, team gold/score at checkpoints, kills, deaths,
gems lost at death, captures, Monolith captures. Usage: abm.py EXTRACT_DIR"""
import sys, json, gzip, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
CK = [150, 300, 450, 600]
def one(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
        mp = json.loads((d/meta['mapFile']).read_text())
    except Exception: return None
    names = [t['name'] for t in meta['teams']]
    sc = R['gems']; n = len(R['round'])
    win = 0 if sc[0][-1] > sc[1][-1] else 1 if sc[1][-1] > sc[0][-1] else None
    cname = {c['id']: c['name'] for c in meta['champions']}
    mono = {g['id'] for g in mp['groups'] if 'Monolith' in g['types']}
    out = {}
    for t in (0, 1):
        m = collections.Counter()
        m['games'] = 1; m['win'] = 1 if win == t else 0.5 if win is None else 0
        champs = [c for c in R['champions'] if c['team'] == t]
        for r in CK:
            i = min(r, n) - 1
            pr = [c for c in champs if cname[c['id']] == 'Prism']
            m[f'score{r}'] = sc[t][i]; m[f'gold{r}'] = sum(c['earned'][i] for c in champs)
            if pr: m[f'pbag{r}'] = pr[0]['gems'][i]; m[f'pfoc{r}'] = pr[0]['foc'][i]; m[f'pn{r}'] = 1
        m['rounds'] = n
        out[names[t]] = m
    for l in gzip.open(d/'events.jsonl.gz', 'rt'):
        e = json.loads(l); k = e.get('k')
        if k == 'death':
            v = e['v']; vt = next(c['team'] for c in R['champions'] if c['id'] == v)
            if e.get('linked'): continue
            out[names[vt]]['deaths'] += 1; out[names[vt]]['gems_lost'] += e.get('gems', 0)
            if cname[v] == 'Prism': out[names[vt]]['prism_deaths'] += 1
            if e.get('by') is not None and e['by'] in cname:
                kt = next(c['team'] for c in R['champions'] if c['id'] == e['by'])
                if kt != vt: out[names[kt]]['kills'] += 1
            else: out[names[vt]]['camp_deaths'] += 1
        elif k == 'capture':
            out[names[e['team']]]['captures'] += 1; out[names[e['team']]]['cap_gems'] += sum(s[1] for s in e['shares'])
            if e['g'] in mono: out[names[e['team']]]['mono_caps'] += 1; out[names[e['team']]]['mono_games_cap'] = 1
    return out, bool(mono)
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    tot = collections.defaultdict(collections.Counter); mtot = collections.defaultdict(collections.Counter)
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one, dirs, chunksize=8):
            if not o: continue
            o, mono = o
            for k, v in o.items():
                tot[k].update(v)
                if mono: mtot[k].update(v)
    for label, T in (('all', tot), ('monolith maps', mtot)):
        print('==', label)
        for k, v in T.items():
            g = v['games']
            if not g: continue
            items = [f"win {100*v['win']/g:.1f}%", f"games {g}"]
            for key in ['kills', 'deaths', 'prism_deaths', 'camp_deaths', 'gems_lost', 'captures', 'cap_gems', 'mono_caps', 'rounds']:
                items.append(f"{key} {v[key]/g:.2f}")
            for r in CK:
                items.append(f"r{r}: score {v[f'score{r}']/g:.0f} gold {v[f'gold{r}']/g:.0f} pbag {v[f'pbag{r}']/max(1,v[f'pn{r}']):.0f} pfoc {v[f'pfoc{r}']/max(1,v[f'pn{r}']):.0f}")
            print(k, '|', ' | '.join(items))
