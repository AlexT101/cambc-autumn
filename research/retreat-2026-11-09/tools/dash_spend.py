import json, gzip, zipfile, collections, sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from retreat_audit import load_stdout_decisions
rows = [json.loads(l) for l in open(sys.argv[1])]
ex = 'replays/retreat-analysis'
idx = {g['source']: g for g in json.load(open(f'{ex}/index.json'))['games']}
cache = {}
def game(src):
    if src not in cache:
        g = idx[src]
        ev = [json.loads(l) for l in gzip.open(f"{ex}/{g['dir']}/events.jsonl.gz", 'rt')]
        R = json.load(gzip.open(f"{ex}/{g['dir']}/rounds.json.gz"))
        cache.clear(); cache[src] = (ev, R, {t: load_stdout_decisions(src, 'ab'[t]) for t in (0, 1) if g['teams'][t] == 'ocean'})
    return cache[src]
def spend_table(sel, label):
    br = collections.Counter(); gap = collections.Counter(); seen_then = collections.Counter()
    for r in sel:
        ev, R, dec = game(r['src'])
        ridx = {x: i for i, x in enumerate(R['round'])}
        last = None
        for e in ev:
            if e['k'] == 'cast' and e.get('a') == r['champ'] and e.get('ab', '').lower().startswith('dash') and e['r'] < r['r0'] and e['r'] >= r['r0'] - 9:
                last = e
        if not last: br['(none found in 9 rounds)'] += 1; continue
        b = dec[r['team']].get((last['r'], r['champ']), '?')
        br[b] += 1
        gap[r['r0'] - last['r']] += 1
        i = ridx.get(last['r'])
        seen_then['enemy seen at cast' if i is not None and R['champions'][[c['id'] for c in R['champions']].index(r['champ'])]['sees'][i] else 'no enemy seen at cast'] += 1
    print(label, len(sel)); print('  branch at the dash:', br.most_common()); print('  rounds before r0:', sorted(gap.items())); print(' ', seen_then)
rows.sort(key=lambda r: r['src'])
Dc = [r for r in rows if r['died'] and r['killer'] not in (None, 'camp')]
dv = [r for r in Dc if r['cdU'] is not None and r['cdU'] > 0 and r['opt_walk']['act'] is not None]
spend_table([r for r in dv if r['opt_dash_ready']['act'] == 0 and r['opt_dash']['act'] > 0], 'deaths where a kept dash escapes')
spend_table(dv, 'all dasher deaths with dash cooling')
