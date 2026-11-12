"""Winning-bag tribute channels in one extract dir: starts, cancels by cause, the channel left, deaths and what
the Prism was doing just before (REF reading)."""
import sys, os, json, gzip, collections, statistics as st
from multiprocessing import Pool
def one(d):
    meta = json.load(open(d+'/meta.json')); R = json.load(gzip.open(d+'/rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(d+'/events.jsonl.gz', 'rt')]
    names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
    typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; S = R['gems']; rounds = R['round']; idx = {r: i for i, r in enumerate(rounds)}
    ps = [c for c in ch if typ[c] == 'Prism' and team[c] == us]
    if not ps: return None
    p = ps[0]; P = ch[p]
    win = lambda r: (i := idx.get(r)) is not None and P['gems'][i] + S[us][i] >= 1000 and S[us][i] < 1000
    out = collections.Counter(); left = []; deaths = []
    for e in ev:
        if e.get('a') == p and e['k'] == 'tribute_start' and e['gems'] + S[us][idx.get(e['r'], 0)] >= 1000:
            out['start'] += 1; out['start_dur'] += e['dur']
            out['start_hp_lt_full'] += P['hp'][idx[e['r']]] < P['maxHp'][idx[e['r']]] * 0.999
        if e.get('a') == p and e['k'] == 'tribute_cancel' and e['gems'] + S[us][idx.get(e['r'], 0)] >= 1000:
            out['cancel_' + e.get('cause', '?')] += 1; left.append(e.get('left', 0))
        if e['k'] == 'death' and e['v'] == p and e.get('gems', 0) + S[us][idx.get(e['r'] - 1, 0)] >= 1000:
            i = idx[e['r'] - 1]
            hist = [(P['chan'][j], round(P['hp'][j] / P['maxHp'][j], 2)) for j in range(max(0, i - 6), i + 1)]
            deaths.append((e['r'], e.get('cause'), typ.get(e.get('by'), 'camp'), len(e.get('assists') or []), hist))
    return dict(c=out, left=left, deaths=deaths, eprism='Prism' in meta['draft']['picks'][1 - us], win=meta['result']['winner'] == us)
def main():
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(16) as pool: rows = [r for r in pool.map(one, dirs, chunksize=8) if r]
    tot = collections.Counter(); left = []
    for r in rows: tot.update(r['c']); left += r['left']
    print('winning tribute channels:', dict(tot))
    if left: print('channel left at cancel: median', st.median(left), 'quartiles', st.quantiles(left, n=4))
    D = [d for r in rows for d in r['deaths']]
    print('winning-bag deaths', len(D), 'causes', collections.Counter(d[1] for d in D), 'killers', collections.Counter(d[2] for d in D))
    print('state 6 rounds before death (chan, hp share):')
    for d in D[:30]: print('  ', d[0], d[1], d[2], 'assists', d[3], d[4])
if __name__ == '__main__': main()
