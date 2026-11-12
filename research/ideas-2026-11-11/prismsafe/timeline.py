"""Where a winning bag's rounds go (REF): per game with a winning bag, rounds from W to the final tribute start,
the channel, Prism's state, and for lost bags the last rounds."""
import sys, os, json, gzip, collections, statistics as st
from multiprocessing import Pool
cheb = lambda a, b: max(abs(a[0]-b[0]), abs(a[1]-b[1]))
def one(d):
    meta = json.load(open(d+'/meta.json')); R = json.load(gzip.open(d+'/rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(d+'/events.jsonl.gz', 'rt')]
    mpf = meta['mapFile']; mpf = mpf if os.path.isabs(mpf) else os.path.normpath(os.path.join(d, mpf))
    mp = json.load(open(mpf)); altars = [(a['x'], a['y']) if isinstance(a, dict) else tuple(a[:2]) for a in mp['altars']]
    names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
    typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; S = R['gems']; rounds = R['round']
    ps = [c for c in ch if typ[c] == 'Prism' and team[c] == us]
    if not ps: return None
    p = ps[0]; P = ch[p]; W = None
    for i, r in enumerate(rounds):
        if P['alive'][i] and P['gems'][i] + S[us][i] >= 1000 and S[us][i] < 1000: W = i; break
    if W is None: return None
    en = [c for c in ch if team[c] != us]
    states = collections.Counter(); lost = None
    for i in range(W, len(rounds)):
        if not P['alive'][i]: lost = rounds[i]; break
        if P['gems'][i] + S[us][i] < 1000: break
        pos = (P['x'][i], P['y'][i]); da = min(cheb(pos, a) for a in altars) - 1
        ne = sum(1 for c in en if ch[c]['alive'][i] and cheb(pos, (ch[c]['x'][i], ch[c]['y'][i])) <= 8)
        c = P['chan'][i]
        states[('chan%d' % c) if c else ('atalt' if da <= 0 else 'walk') + ('+E' if ne else '')] += 1
    tstarts = [e for e in ev if e['k'] == 'tribute_start' and e['a'] == p and e['r'] >= rounds[W]]
    tc = [e for e in ev if e['k'] == 'tribute_cancel' and e['a'] == p and e['r'] >= rounds[W]]
    pos = (P['x'][W], P['y'][W])
    return dict(W=rounds[W], end=meta['result']['rounds'], win=meta['result']['winner'] == us, lost=lost, states=states,
                dist=min(cheb(pos, a) for a in altars) - 1, gems=P['gems'][W], ntrib=len(tstarts), ncancel=len(tc),
                first_trib=tstarts[0]['r'] - rounds[W] if tstarts else None, hp=P['hp'][W] / P['maxHp'][W])
def main():
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(16) as pool: rows = [r for r in pool.map(one, dirs, chunksize=8) if r]
    print(len(rows), 'winning-bag games')
    tot = collections.Counter()
    for r in rows: tot.update(r['states'])
    n = sum(tot.values()); print('Prism rounds while carrying the winning bag, by state:', {k: round(v / len(rows), 1) for k, v in tot.most_common()})
    print('median dist to altar at W', st.median(r['dist'] for r in rows), 'median bag', st.median(r['gems'] for r in rows))
    ft = [r['first_trib'] for r in rows if r['first_trib'] is not None]
    print('rounds W -> first tribute start: median', st.median(ft), 'mean', round(st.mean(ft), 1), 'tributes started per game', round(st.mean(r['ntrib'] for r in rows), 2), 'cancels', round(st.mean(r['ncancel'] for r in rows), 2))
    L = [r for r in rows if r['lost']]
    print('lost:', len(L), 'rounds W->death median', st.median(r['lost'] - r['W'] for r in L), 'hp at W median', round(st.median(r['hp'] for r in L), 2), 'dist at W median', st.median(r['dist'] for r in L))
    for r in L[:25]: print('  W', r['W'], 'death', r['lost'], 'bag', r['gems'], 'hp %.2f' % r['hp'], 'dist', r['dist'], 'win', r['win'], 'trib', r['ntrib'], 'cancel', r['ncancel'], dict(r['states']))

if __name__ == '__main__':
    main()
