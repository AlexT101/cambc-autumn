"""Games where CAND's (bot 0's) timed lock fired (a CAND lock cuts an enemy channel of 50+ gems with <=2 turns left), paired
with the mirror's result on the same (map, order). usage: firing.py ANA_DIR ARM_RESULTS MIRROR_RESULTS [--deny]"""
import json, sys, os, collections, statistics as st
from multiprocessing import Pool
import beh, lockcut_run as L
def run(j):
    _, d, T = j
    try: meta, rd, ev = beh.load(d)
    except Exception: return None
    team = {c['id']: c['team'] for c in meta['champions']}; name = {c['id']: c['name'] for c in meta['champions']}
    starts = {}; timed = []; early = []
    for e in ev:
        if e['k'] == 'tribute_start': starts[e['a']] = e
        if e['k'] == 'tribute_cancel' and e.get('cause') == 'lock' and team[e['a']] != T:
            s = starts.get(e['a'])
            if s and s['gems'] >= 50: (timed if e.get('left', 99) <= 2 else early).append((s['gems'], name[e['a']], e['r']))
    return (d, T, timed, early)
if __name__ == '__main__':
    A, R, M = sys.argv[1:4]
    idx = json.load(open(A + '/index.json'))['games']; src = {g['dir']: os.path.basename(g['source']) for g in idx}
    jobs = L.jloc(A, 0)
    with Pool(32) as p: res = [r for r in p.map(run, jobs, chunksize=8) if r]
    def lm(p): return {(os.path.basename(m['map']), tuple(m['order'])): m['winner'] for m in json.load(open(p))['matches']}
    arm, mir = lm(R), lm(M)
    rows = []
    for d, T, timed, early in res:
        stem = src[d.rsplit('/', 1)[1]]; parts = stem.split('-', 1)[1].rsplit('-', 1)
        mp = parts[0] + '.map26a'; order = (0, 1) if parts[1].startswith('12') else (1, 0)
        k = (mp, order)
        if k not in arm or k not in mir: continue
        rows.append((len(timed), len(early), int(arm[k] == 0) - int(mir[k] == 0), timed))
    F = [r for r in rows if r[0] > 0]; N = [r for r in rows if r[0] == 0]
    print(f'kept games {len(rows)}; with a timed cut {len(F)} ({len(F)/len(rows):.3f}); paired win delta there {st.mean(r[2] for r in F):+.3f} (+{sum(r[2]>0 for r in F)} -{sum(r[2]<0 for r in F)}); elsewhere {st.mean(r[2] for r in N):+.3f} (+{sum(r[2]>0 for r in N)} -{sum(r[2]<0 for r in N)})')
    c = collections.Counter(t[1] for r in F for t in r[3]); print('timed-cut victims by type', c.most_common(6), 'gems med', st.median([t[0] for r in F for t in r[3]]))
