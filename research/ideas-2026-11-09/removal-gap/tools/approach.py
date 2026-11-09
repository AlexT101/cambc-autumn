"""Victim channels of 100+ gems: does a lock-carrying enemy come within 5 during the channel, and what does the
victim do? Outcome of the channel (end / manual cancel / lock / stun / death), manual cancel within 2 rounds of the
approach, restart within 10 rounds after a manual cancel, and how many of the victim's allies stand within 3 of the
altar at the start (guards)."""
import beh, json, sys, os, collections, statistics as st
from multiprocessing import Pool
import lockcut_run as L
def run(j):
    k, d, T = j
    try: meta, rd, ev = beh.load(d)
    except Exception: return (k, [])
    team = {c['id']: c['team'] for c in meta['champions']}
    rounds = rd['round']; ri = {r: i for i, r in enumerate(rounds)}
    ch = {c['id']: c for c in rd['champions']}
    out = []
    evs = sorted(ev, key=lambda e: e['s'])
    for i, e in enumerate(evs):
        if e['k'] != 'tribute_start' or team[e['a']] == T or e['gems'] < 100: continue
        a = e['a']; r0 = e['r']
        end = None; outcome = 'open'
        for f in evs[i + 1:]:
            if f['k'] == 'tribute_end' and f['a'] == a: end, outcome = f['r'], 'end'; break
            if f['k'] == 'tribute_cancel' and f['a'] == a: end, outcome = f['r'], f.get('cause'); break
            if f['k'] == 'death' and f['v'] == a: end, outcome = f['r'], 'death'; break
        if end is None: continue
        alt = e['altar']
        i0 = ri.get(r0)
        guards = 0
        if i0 is not None:
            for c in rd['champions']:
                if c['team'] != T and c['id'] != a and c['alive'][i0] and c['x'][i0] is not None and max(abs(c['x'][i0] - alt[0]), abs(c['y'][i0] - alt[1])) <= 3: guards += 1
        appr = None
        for r in range(r0, end + 1):
            ix = ri.get(r)
            if ix is None: continue
            ax, ay = ch[a]['x'][ix], ch[a]['y'][ix]
            if ax is None: continue
            for c in rd['champions']:
                if c['team'] == T and c['alive'][ix] and c['x'][ix] is not None and c['cons'][ix][2] > 0 and max(abs(c['x'][ix] - ax), abs(c['y'][ix] - ay)) <= 5:
                    appr = r; break
            if appr is not None: break
        restart = False
        if outcome == 'manual':
            restart = any(f['k'] == 'tribute_start' and f['a'] == a and 0 <= f['r'] - end <= 10 for f in evs[i + 1:i + 4000])
        out.append(dict(gems=e['gems'], dur=e['dur'], outcome=outcome, appr=appr is not None, appr_left=(e['dur'] - (appr - r0)) if appr is not None else None,
                        quick=(outcome == 'manual' and appr is not None and end - appr <= 2), restart=restart, guards=guards))
    return (k, out)
if __name__ == '__main__':
    jobs = []
    if '--live' in sys.argv: jobs += L.jl()
    for a in sys.argv[1:]:
        if a.startswith('--'): continue
        p, b = a.rsplit(':', 1); jobs += [(os.path.basename(p) + f'-T{b}', d, T) for _, d, T in L.jloc(p, int(b))]
    with Pool(32) as pool: res = pool.map(run, jobs, chunksize=8)
    G = collections.defaultdict(list); n = collections.Counter()
    for k, o in res: G[k] += o; n[k] += 1
    for k in sorted(G):
        X = G[k]; A = [x for x in X if x['appr']]
        oc = collections.Counter(x['outcome'] for x in X); oa = collections.Counter(x['outcome'] for x in A)
        f = lambda c, t: ' '.join(f'{o}:{c[o]/t:.2f}' for o in ('end', 'manual', 'lock', 'stun', 'death'))
        print(f"{k:20} 100+ channels/g {len(X)/n[k]:.2f} dur~{st.mean(x['dur'] for x in X):.0f} guards~{st.mean(x['guards'] for x in X):.2f} | all: {f(oc, len(X))}")
        print(f"{'':20} lock carrier within 5: {len(A)/max(1,len(X)):.2f} of channels; then {f(oa, max(1,len(A)))}; manual within 2 {sum(x['quick'] for x in A)/max(1,len(A)):.2f}; restart10 after manual {sum(x['restart'] for x in X if x['outcome']=='manual')/max(1,oc['manual']):.2f}")
