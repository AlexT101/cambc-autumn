"""Victim response to T's lock cuts of a victim (1-T) tribute: timed (<=2 turns left, 50+ gems) vs early cuts.
Per cut: lock broken (by anyone) within 10 rounds, round of break; victim team re-banks >=80% of the bag within 60;
carrier died within 15 (and killer team); victim lock hits in the 20 rounds after; T's locker (the placer) died within 15."""
import beh, json, sys, os, collections, statistics as st
from multiprocessing import Pool
import lockcut_run as L
def cuts(d, T):
    meta, rd, ev = beh.load(d)
    team = {c['id']: c['team'] for c in meta['champions']}
    starts = {}; out = []; lastlock = {}
    for i, e in enumerate(ev):
        k = e['k']
        if k == 'tribute_start': starts[e['a']] = e
        if k == 'lock_place': lastlock[(tuple(e['to']), e['team'])] = e
        if k == 'tribute_cancel' and e.get('cause') == 'lock' and team[e['a']] != T:
            s = starts.get(e['a'])
            if not s or s['gems'] < 50: continue
            alt = tuple(s['altar']); lp = lastlock.get((alt, T))
            rec = dict(r=e['r'], gems=s['gems'], dur=s['dur'], left=e.get('left', 0), timed=e.get('left', 99) <= 2,
                       broken=None, rebank=False, cdied=False, ldied=False, hits=0, win=int(meta['result']['winner'] == T),
                       late_game=e['r'] >= 600)
            locker = lp['a'] if lp and lp['r'] == e['r'] else None
            vteam = team[e['a']]; banked = 0
            for f in ev[i + 1:]:
                dr = f['r'] - e['r']
                if dr > 60: break
                fk = f['k']
                if fk == 'lock_destroyed' and tuple(f['at']) == alt and f['team'] == T and rec['broken'] is None: rec['broken'] = dr
                if fk == 'attack' and f.get('lock') and team.get(f['a']) == vteam and dr <= 20: rec['hits'] += 1
                if fk == 'tribute_end' and team[f['a']] == vteam: banked += f.get('gems', 0)
                if fk == 'death' and dr <= 15:
                    if f['v'] == e['a']: rec['cdied'] = True; rec['ckill_T'] = team.get(f.get('by'), -1) == T
                    if locker is not None and f['v'] == locker: rec['ldied'] = True
            rec['rebank'] = banked >= 0.8 * s['gems']; rec['locker'] = locker is not None
            out.append(rec)
    return out
def run(j):
    try: return (j[0], cuts(j[1], j[2]))
    except Exception as ex: return (j[0], [])
def summ(L2, n):
    if not L2: return 'none'
    br = [x['broken'] for x in L2 if x['broken'] is not None]
    lk = [x for x in L2 if x['locker']]
    return (f"n={len(L2)} ({len(L2)/n:.3f}/g) gems~{st.mean(x['gems'] for x in L2):.0f} dur~{st.mean(x['dur'] for x in L2):.0f} "
            f"broken<=10 {sum(b<=10 for b in br)/len(L2):.2f} (med {st.median(br) if br else -1}) hits20~{st.mean(x['hits'] for x in L2):.1f} "
            f"rebank80/60 {st.mean(x['rebank'] for x in L2):.2f} carrier died15 {st.mean(x['cdied'] for x in L2):.2f} "
            f"locker died15 {sum(x['ldied'] for x in lk)/max(1,len(lk)):.2f} Twin {st.mean(x['win'] for x in L2):.2f}")
if __name__ == '__main__':
    jobs = []
    if '--live' in sys.argv: jobs += L.jl()
    for a in sys.argv[1:]:
        if a.startswith('--'): continue
        p, b = a.rsplit(':', 1); jobs += [(os.path.basename(p) + f'-T{b}', d, T) for _, d, T in L.jloc(p, int(b))]
    with Pool(32) as pool: res = pool.map(run, jobs, chunksize=8)
    G = collections.defaultdict(list); n = collections.Counter()
    for k, c in res: G[k] += c; n[k] += 1
    for k in sorted(G):
        print(k, 'TIMED', summ([x for x in G[k] if x['timed']], n[k]))
        print(k, 'EARLY', summ([x for x in G[k] if not x['timed']], n[k]))
