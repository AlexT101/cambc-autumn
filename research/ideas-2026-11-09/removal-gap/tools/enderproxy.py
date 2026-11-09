"""Replay proxy for stop_game_ender: an enemy body whose bag ends the game (gems >= 1000 - its score) seen by our body.
Per (our body, ender) episode (gaps <= 3 rounds): ender channelling at the start or not; our body dies within 15
rounds of the episode's end; the ender dies (any cause) within 15; the ender's tribute lands within 60."""
import beh, json, sys, os, collections, statistics as st
from multiprocessing import Pool
import lockcut_run as L
def run(j):
    k, d, T = j
    try: meta, rd, ev = beh.load(d)
    except Exception: return (k, None)
    rounds = rd['round']; C = rd['champions']; team = {c['id']: c['team'] for c in meta['champions']}
    deaths = collections.defaultdict(list); lands = collections.defaultdict(list)
    for e in ev:
        if e['k'] == 'death': deaths[e['v']].append(e['r'])
        if e['k'] == 'tribute_end': lands[e['a']].append(e['r'])
    eps = collections.defaultdict(list)
    for i, r in enumerate(rounds):
        for c in C:
            if c['team'] == T or not c['alive'][i]: continue
            need = 1000 - rd['gems'][c['team']][i]
            if c['gems'][i] < need: continue
            for o in (c['seenBy'][i] or []):
                if team.get(o) == T: eps[(o, c['id'])].append((r, c['chan'][i] == 2, c['gems'][i]))
    out = []
    for (o, en), L2 in eps.items():
        cur = [L2[0]]
        for x in L2[1:] + [None]:
            if x is not None and x[0] - cur[-1][0] <= 3: cur.append(x); continue
            r0, r1 = cur[0][0], cur[-1][0]
            out.append(dict(trib=cur[0][1], gems=cur[0][2], died=any(r0 <= r <= r1 + 15 for r in deaths[o]), edied=any(r0 <= r <= r1 + 15 for r in deaths[en]),
                            landed=any(r0 <= r <= r1 + 60 for r in lands[en]), win=int(meta['result']['winner'] == T)))
            if x is not None: cur = [x]
    return (k, out)
if __name__ == '__main__':
    jobs = []
    if '--live' in sys.argv: jobs += L.jl()
    for a in sys.argv[1:]:
        if a.startswith('--'): continue
        p, b = a.rsplit(':', 1); jobs += [(os.path.basename(p) + f'-T{b}', d, T) for _, d, T in L.jloc(p, int(b))]
    with Pool(32) as pool: res = pool.map(run, jobs, chunksize=8)
    G = collections.defaultdict(list); n = collections.Counter()
    for k, o in res:
        if o is None: continue
        G[k] += o; n[k] += 1
    for k in sorted(G):
        for lab, X in (('channel', [x for x in G[k] if x['trib']]), ('walking', [x for x in G[k] if not x['trib']])):
            if X: print(f"{k:22} {lab:8} eps/g {len(X)/n[k]:.2f} gems~{st.mean(x['gems'] for x in X):.0f} we die<=15 {st.mean(x['died'] for x in X):.2f} ender dies {st.mean(x['edied'] for x in X):.2f} lands<=60 {st.mean(x['landed'] for x in X):.2f} we win {st.mean(x['win'] for x in X):.2f}")
