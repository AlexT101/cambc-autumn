"""Same map and side, different opponents: do BattleCats' moves diverge before its bodies see any enemy?
If its play reacted only to what it sees (and randomness), trajectories stay identical until first sight; earlier
divergence means it reads something else (enemy picks, priorities via ... no: nothing else is visible) or is random."""
import bl, collections, fl as F
cells = collections.defaultdict(list)
for d in bl.dirs():
    g = bl.load(d, rounds=False, events=False)
    if g and g['ver'] == 'cur': cells[(g['mapname'], g['bc'])].append(d)
res = collections.Counter(); ex = []
for cell, ds in cells.items():
    if len(ds) < 2: continue
    G = [bl.load(d, events=False) for d in ds[:6]]
    def traj(g):
        bc = sorted([c for c in g['rd']['champions'] if c['team'] == g['bc']], key=lambda c: c['id'])
        en_ids = {c['id'] for c in g['rd']['champions'] if c['team'] != g['bc']}
        R = len(g['rd']['round'])
        # first round any BC body sees an enemy (enemy's seenBy contains a BC id)
        bcids = {c['id'] for c in bc}
        fs = next((i + 1 for i in range(R) if any(set(c['seenBy'][i] or []) & bcids for c in g['rd']['champions'] if c['team'] != g['bc'])), R)
        return [[(c['x'][i], c['y'][i]) for c in bc] for i in range(R)], fs, [x['name'] for x in g['meta']['champions'] if x['team'] != g['bc']]
    T = [traj(g) for g in G]
    for a in range(len(T)):
        for b in range(a + 1, len(T)):
            ta, fa, pa = T[a]; tb, fb, pb = T[b]
            if len(ta[0]) != len(tb[0]): continue
            dv = next((i + 1 for i in range(min(len(ta), len(tb))) if ta[i] != tb[i]), None)
            fs = min(fa, fb)
            same_picks = sorted(pa) == sorted(pb)
            k = ('same enemy team' if same_picks else 'different enemy team', 'identical to end' if dv is None else 'diverge before first sight' if dv < fs else 'diverge at/after first sight')
            res[k] += 1
            if dv is not None and dv < fs and len(ex) < 8: ex.append((cell, dv, fs, pa, pb))
for k, v in sorted(res.items()): print(k, v)
for e in ex: print(e)
