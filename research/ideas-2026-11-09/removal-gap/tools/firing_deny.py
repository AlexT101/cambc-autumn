"""Games where bot 0 cancelled (lock or stun) an enemy non-winning channel of 100+ gems, paired with the mirror.
usage: firing_deny.py ANA_DIR ARM_RESULTS MIRROR_RESULTS [ANA_MIRROR]"""
import json, sys, os, collections, statistics as st
from multiprocessing import Pool
import beh, lockcut_run as L
def run(j):
    _, d, T = j
    try: meta, rd, ev = beh.load(d)
    except Exception: return None
    team = {c['id']: c['team'] for c in meta['champions']}; ri = {r: i for i, r in enumerate(rd['round'])}
    starts = {}; cuts = []
    for e in ev:
        if e['k'] == 'tribute_start': starts[e['a']] = e
        if e['k'] == 'tribute_cancel' and e.get('cause') in ('lock', 'stun') and team[e['a']] != T:
            s = starts.get(e['a'])
            if not s or s['gems'] < 100: continue
            i = ri.get(s['r'], 0); sc = rd['gems'][1 - T][i]
            if sc + s['gems'] >= 1000: continue
            cuts.append((s['gems'], e.get('cause'), e.get('left', 0), s['dur']))
    return (d, T, cuts)
def stem_key(stem):
    parts = stem.split('-', 1)[1].rsplit('-', 1)
    return (parts[0] + '.map26a', (0, 1) if parts[1].startswith('12') else (1, 0))
if __name__ == '__main__':
    A, R, M = sys.argv[1:4]
    def lm(p): return {(os.path.basename(m['map']), tuple(m['order'])): m['winner'] for m in json.load(open(p))['matches']}
    arm, mir = lm(R), lm(M)
    for lab, AD in (('arm', A),) + ((('mirror', sys.argv[4]),) if len(sys.argv) > 4 else ()):
        idx = json.load(open(AD + '/index.json'))['games']; src = {g['dir']: os.path.basename(g['source']) for g in idx}
        with Pool(32) as p: res = [r for r in p.map(run, L.jloc(AD, 0), chunksize=8) if r]
        allc = [c for _, _, cs in res for c in cs]
        print(f'{lab}: non-winning 100+ channels cut by bot0: {len(allc)/len(res):.3f}/g gems~{st.mean(c[0] for c in allc):.0f} lock {sum(c[1]=="lock" for c in allc)/len(res):.3f}/g stun {sum(c[1]=="stun" for c in allc)/len(res):.3f}/g ran~{st.mean(c[3]-c[2] for c in allc):.1f} of {st.mean(c[3] for c in allc):.1f}')
        if lab != 'arm': continue
        rows = []
        for d, T, cs in res:
            k = stem_key(src[d.rsplit('/', 1)[1]])
            if k in arm and k in mir: rows.append((len(cs), int(arm[k] == 0) - int(mir[k] == 0)))
        F = [r for r in rows if r[0] > 0]; N = [r for r in rows if r[0] == 0]
        print(f'  games with such a cut {len(F)}/{len(rows)}: paired delta {st.mean(r[1] for r in F):+.3f} (+{sum(r[1]>0 for r in F)} -{sum(r[1]<0 for r in F)}); elsewhere {st.mean(r[1] for r in N):+.3f}')
