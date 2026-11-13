"""Paired mechanism metrics, base vs cand debug samples against a body: our deaths (by Hunter killers), gold fed,
our kills, the enemy carry's gold, by game paired on (map, side).
    python3 mech.py EXT_BASE EXT_CAND OURNAME_BASE OURNAME_CAND"""
import gzip, json, os, sys, collections, statistics as st
HUNTER = {61, 63, 65}
def load(ext, ours):
    out = {}
    for d in os.listdir(ext):
        p = f'{ext}/{d}'
        if not os.path.exists(p + '/meta.json'): continue
        m = json.load(open(p + '/meta.json'))
        us = [t['name'] for t in m['teams']].index(ours) if ours in [t['name'] for t in m['teams']] else None
        if us is None: continue
        key = os.path.basename(m['source']).split('-', 1)[1]
        R = json.load(gzip.open(p + '/rounds.json.gz', 'rt'))
        ch = {c['id']: c for c in R['champions']}
        name = {c['id']: c['name'] for c in m['champions']}
        x = collections.Counter()
        x['win'] = float(m['result']['winner'] == us) if m['result']['winner'] is not None else 0.5
        x['rounds'] = m['result']['rounds']
        for l in gzip.open(p + '/events.jsonl.gz', 'rt'):
            e = json.loads(l)
            if e.get('k') != 'death': continue
            v = e['v']; r = e['r']; k = e.get('by')
            if ch[v]['team'] == us:
                x['deaths'] += 1
                if r >= 450: x['deaths450'] += 1
                if k is not None and k in ch:
                    i = max(0, min(len(ch[k]['items']) - 1, r - 2))
                    it = ch[k]['items'][i] or []
                    hunt = bool({it[a] for a in range(0, len(it), 2)} & HUNTER)
                    x['hunter_deaths'] += hunt
                    x['gold_fed'] += e.get('gold', 0) or 0
                    x['vesper_kills'] += name[k] == 'Vesper Vale'
            else:
                x['kills'] += 1
                if name[v] == 'Vesper Vale': x['vesper_deaths'] += 1
        out[key] = x
    return out
B = load(sys.argv[1], sys.argv[3]); C = load(sys.argv[2], sys.argv[4])
keys = sorted(set(B) & set(C))
print(f'paired games {len(keys)}')
for f in ('win', 'deaths', 'deaths450', 'hunter_deaths', 'vesper_kills', 'gold_fed', 'kills', 'vesper_deaths', 'rounds'):
    b = [B[k][f] for k in keys]; c = [C[k][f] for k in keys]
    dd = [y - x for x, y in zip(b, c)]
    se = st.stdev(dd) / len(dd) ** 0.5 if len(dd) > 1 else 0
    print(f'{f:14s} base {st.mean(b):8.3f}  cand {st.mean(c):8.3f}  diff {st.mean(dd):+.3f} +- {se:.3f}')
