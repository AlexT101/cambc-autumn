"""Completed big Prism tributes: who saw it, what stops existed, what they did."""
import json, gzip, os, sys, collections, statistics as st
ext = sys.argv[1]; idx = json.load(open(ext + '/index.json'))['games']
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
STUN = {'Ryth':0, 'Tavi':1, 'Ren':0, 'Heart of Ruin':1, 'Cassi':1, 'Marcella':0}
cls = collections.Counter(); det = []
allrows = []
for g in idx:
    mid = os.path.basename(g['source'])[:-8]; cand = 0 if mid.endswith('-12') else 1
    p = f"{ext}/{g['dir']}"; meta = json.load(open(p + '/meta.json')); R = json.load(gzip.open(p + '/rounds.json.gz'))
    typ = {c['id']: c['name'] for c in meta['champions']}
    ch = R['champions']; n = len(R['round'])
    P = [c for c in ch if c['team'] != cand and typ[c['id']] == 'Prism']
    if not P: continue
    P = P[0]; pid = P['id']
    ev = [json.loads(l) for l in gzip.open(p + '/events.jsonl.gz', 'rt')]
    ours = [c for c in ch if c['team'] == cand]; oid = {c['id'] for c in ours}
    theirs = [c for c in ch if c['team'] != cand and c['id'] != pid]
    s = None
    for e in ev:
        if e['k'] == 'tribute_start' and e['a'] == pid: s = e
        elif e['k'] in ('tribute_end', 'tribute_cancel') and e['a'] == pid and s:
            if s['gems'] >= 100:
                i0 = s['r'] - 1; i1 = min(e['r'], n) - 1; L = i1 - i0 + 1
                seen_rounds = sum(1 for i in range(i0, i1 + 1) if any(x in oid for x in P['seenBy'][i]))
                first_seen = next((i - i0 for i in range(i0, i1 + 1) if any(x in oid for x in P['seenBy'][i])), None)
                seers = set(x for i in range(i0, i1 + 1) for x in P['seenBy'][i] if x in oid)
                alive0 = [c for c in ours if c['alive'][i0]]
                d0 = sorted((cheb((c['x'][i0], c['y'][i0]), s['at']), typ[c['id']]) for c in alive0 if c['x'][i0] is not None)
                # stun bodies alive: closest stun body's distance at start; min distance any stun body reached
                stun_min = min([cheb((c['x'][i], c['y'][i]), s['at']) for c in ours if typ[c['id']] in STUN for i in range(i0, i1 + 1) if c['alive'][i] and c['x'][i] is not None] or [99])
                any_min = min([cheb((c['x'][i], c['y'][i]), s['at']) for c in ours for i in range(i0, i1 + 1) if c['alive'][i] and c['x'][i] is not None] or [99])
                lock_any = max(sum(1 for c in ours if c['alive'][i] and c['cons'][i][2] > 0) for i in range(i0, i1 + 1))
                guards = st.mean(sum(1 for c in theirs if c['alive'][i] and c['x'][i] is not None and cheb((c['x'][i], c['y'][i]), s['at']) <= 6) for i in range(i0, i1 + 1))
                # prism was seen by ours shortly before start (within 10 rounds)?
                pre = any(any(x in oid for x in P['seenBy'][i]) for i in range(max(0, i0 - 10), i0))
                row = dict(game=g['dir'], r0=s['r'], L=L, gems=s['gems'], done=e['k'] == 'tribute_end', cause=e.get('cause'), seen=seen_rounds, first_seen=first_seen, seers=[typ[x] for x in seers],
                           d0=d0, stun_min=stun_min, any_min=any_min, lock=lock_any, guards=guards, pre=pre, win=R['gems'][1 - cand][i0] + s['gems'] >= 1000, alive=len(alive0),
                           php=P['hp'][i0], pfoc=P['foc'][i0], won=(g['winner'] == cand))
                allrows.append(row)
            s = None
json.dump(allrows, open(sys.argv[2], 'w'))
D = [r for r in allrows if r['done']]
print('completed', len(D))
c = collections.Counter()
for r in D:
    if r['alive'] == 0: k = '0 none of ours alive at start'
    elif r['seen'] == 0: k = '1 never seen during the channel'
    elif r['any_min'] > 4: k = '2 seen, nobody came within 4'
    else: k = '3 seen and somebody within 4'
    c[k] += 1; r['cls'] = k
for k, v in sorted(c.items()): 
    rs = [r for r in D if r['cls'] == k]
    print(k, v, 'gems', st.median(r['gems'] for r in rs), 'L', st.median(r['L'] for r in rs), 'win', sum(r['win'] for r in rs), 'pre-seen', sum(r['pre'] for r in rs), 'alive', st.mean(r['alive'] for r in rs), 'nearest0', st.median(r['d0'][0][0] if r['d0'] else 99 for r in rs), 'guards', round(st.mean(r['guards'] for r in rs), 2), 'lock', sum(r['lock'] > 0 for r in rs))
print('--- seen cases')
for r in D:
    if r['cls'][0] in '23': print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items() if k not in ('cls',)})
print('--- cancelled, all: seen share', st.mean(r['seen'] > 0 for r in allrows if not r['done']), 'lock carried', st.mean(r['lock'] > 0 for r in allrows if not r['done']))
print('locks carried at any big tribute', st.mean(r['lock'] > 0 for r in allrows))
