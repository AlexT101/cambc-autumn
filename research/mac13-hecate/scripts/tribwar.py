# tribwar.py EXTRACT_DIR [MIN_GEMS]: the tribute war -- big tribute attempts, their outcomes and context
import gzip, json, glob, sys, collections
D = sys.argv[1]; MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 150
st = collections.Counter(); ctx = collections.defaultdict(list); n = 0
winby = collections.Counter(); endr = []
for d in glob.glob(D + '/*/'):
    try:
        M = json.load(open(d + 'meta.json')); R = json.load(gzip.open(d + 'rounds.json.gz'))
    except Exception: continue
    n += 1
    team = {c['id']: c['team'] for c in M['champions']}; name = {c['id']: c['name'] for c in M['champions']}
    ch = {c['id']: c for c in R['champions']}
    r0 = R['round'][0]
    def pos(i, r):
        c = ch[i]; k = r - r0
        if k < 0 or k >= len(c['x']): return None
        x, y = c['x'][k], c['y'][k]
        return None if x is None or x < 0 else (x, y)
    def alive(i, r):
        c = ch[i]; k = r - r0
        if 'alive' in c: return k < len(c['alive']) and c['alive'][k]
        return pos(i, r) is not None
    g = R['gems']; last = len(R['round']) - 1
    fin = (g[0][last], g[1][last]); W = 0 if fin[0] > fin[1] else 1
    endr.append(R['round'][last])
    ev = [json.loads(l) for l in gzip.open(d + 'events.jsonl.gz', 'rt')]
    open_ = {}
    for e in ev:
        k = e['k']
        if k == 'tribute_start' and e['gems'] >= MIN:
            a = e['a']; r = e['r']; p = pos(a, r)
            ens = [i for i in team if team[i] != team[a]]
            ea = [i for i in ens if alive(i, r)]
            dmin = min([max(abs(pos(i, r)[0] - p[0]), abs(pos(i, r)[1] - p[1])) for i in ea if pos(i, r) and p] or [99])
            open_[a] = dict(r=r, gems=e['gems'], dur=e['dur'], who=name[a], ea=len(ea), ne=len(ens), dmin=dmin, win=team[a] == W)
        elif k in ('tribute_end', 'tribute_cancel') and e['a'] in open_:
            o = open_.pop(e['a']); out = 'end' if k == 'tribute_end' else e.get('cause')
            st[out] += 1; o['out'] = out; ctx[out].append(o)
    # what the winner's last big tribute looked like
for out, L in ctx.items():
    import statistics as S
    print(out, len(L) / n, 'gems', S.median(x['gems'] for x in L), 'dur', S.median(x['dur'] for x in L),
          'enemies alive', round(S.mean(x['ea'] / x['ne'] for x in L), 2), 'nearest enemy', S.median(x['dmin'] for x in L),
          'by winner', round(sum(x['win'] for x in L) / len(L), 2), collections.Counter(x['who'] for x in L).most_common(3))
# completion rate by enemies-alive fraction and nearest enemy
allL = [x for L in ctx.values() for x in L]
for lo, hi in ((0, .5), (.5, .99), (.99, 1.01)):
    s = [x for x in allL if lo <= x['ea'] / x['ne'] < hi]
    if s: print('alive frac', lo, hi, len(s) / n, 'complete', round(sum(x['out'] == 'end' for x in s) / len(s), 2))
for lo, hi in ((0, 9), (9, 17), (17, 99), (99, 100)):
    s = [x for x in allL if lo <= x['dmin'] < hi]
    if s: print('nearest', lo, hi, len(s) / n, 'complete', round(sum(x['out'] == 'end' for x in s) / len(s), 2))
import statistics as S
print('games', n, 'end round median', S.median(endr))
