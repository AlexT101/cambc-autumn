"""Winning-bag episodes: runs of rounds where a living champion's bag plus its team's score reaches 1000.
Per episode (carrier team = us or op relative to T): enemies within 3 / 8 of the carrier (max at once, and
body-rounds), enemy deaths within 6 of it, carrier death (by a champion), the episode ending in a completed win."""
import beh, json, sys, os, collections
from multiprocessing import Pool
import lockcut_run as L
def eps(d, T):
    meta, rd, ev = beh.load(d)
    mp = json.load(open(os.path.join(d, meta['mapFile']))) if 'mapFile' in meta else None
    alt = mp['altars'] if mp else []
    pts = [tuple(a) if isinstance(a, (list, tuple)) else (a['x'], a['y']) for a in alt]
    one = bool(pts) and all(any(max(abs(p[0]-q[0]), abs(p[1]-q[1])) <= 3 for q in pts if q != p) or len(pts) == 1 for p in pts)
    ch = rd['champions']; R = rd['round']; n = len(R); score = rd['gems']
    deaths = collections.defaultdict(list)
    for e in ev:
        if e['k'] == 'death': deaths[e['r']].append(e)
    out = []
    for c in ch:
        t = c['team']; i = 0
        while i < n:
            if not (c['alive'][i] and c['gems'][i] + score[t][i] >= 1000): i += 1; continue
            j = i; m3 = m8 = 0; br3 = 0; ed = 0; cd = 0; dur = 0
            while j < n and c['alive'][j] and c['gems'][j] + score[t][j] >= 1000:
                near3 = near8 = 0
                for o in ch:
                    if o['team'] == t or not o['alive'][j]: continue
                    dd = max(abs(o['x'][j] - c['x'][j]), abs(o['y'][j] - c['y'][j]))
                    near3 += dd <= 3; near8 += dd <= 8
                m3 = max(m3, near3); m8 = max(m8, near8); br3 += near3; dur += 1
                for e in deaths.get(R[j], []):
                    v = e['v']; vc = next(x for x in ch if x['id'] == v)
                    if vc['team'] != t and e.get('at') and max(abs(e['at'][0] - c['x'][j]), abs(e['at'][1] - c['y'][j])) <= 6: ed += 1
                j += 1
            died = j < n and not c['alive'][j]
            won = meta['result']['winner'] == t and j >= n - 1
            out.append({'one': one, 'side': 'us' if t == T else 'op', 'dur': dur, 'm3': m3, 'm8': m8, 'br3': br3, 'ed': ed, 'died': died, 'won': won, 'gamewin': meta['result']['winner'] == t})
            i = j + 1
    return out
def run(j):
    k, d, T = j
    try: return (k, eps(d, T))
    except Exception as e: return (k, [])
if __name__ == '__main__':
    A = sys.argv[1]; jobs = L.jl() + (L.jloc(A, 1) if A != '-' else [])
    with Pool(40) as p: res = p.map(run, jobs, chunksize=4)
    G = collections.defaultdict(list); N = collections.Counter()
    for k, o in res: G[k] += o; N[k] += 1
    import statistics as st
    for k, E in G.items():
        for side in ('us', 'op'):
          for one in (True, False):
            S = [e for e in E if e['side'] == side and e['dur'] >= 2 and e['one'] == one]
            if not S: continue
            print(f"{k:14} {'one-site' if one else 'multi   '} carrier={side} eps {len(S)/N[k]:.2f}/g dur {st.mean(e['dur'] for e in S):.1f}  max enemies<=3 {st.mean(e['m3'] for e in S):.2f} <=8 {st.mean(e['m8'] for e in S):.2f}  enemy body-rounds<=3 {st.mean(e['br3'] for e in S):.1f}"
                  f"  enemy deaths near {st.mean(e['ed'] for e in S):.2f}  carrier died {st.mean(e['died'] for e in S):.3f}  ep->win {st.mean(e['won'] for e in S):.2f}")
