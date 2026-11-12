"""Mite lock and crystal carrying over time (rounds 'cons' = carried consumables [crystal, ?, lock, ?]) and lock placement
next to own tributes (r7 live)."""
import ml, collections, fl
from multiprocessing import Pool
def one(sd):
    g = ml.load(sd)
    if g is None: return None
    C = g['rd']['champions']; nR = len(g['rd']['round']); team = {c['id']: c['team'] for c in g['meta']['champions']}
    out = {'first_lock': [], 'carry_lock': collections.Counter(), 'carry_cry': collections.Counter(), 'n': collections.Counter(), 'near_own_trib': [0, 0]}
    for c in C:
        if c['team'] != g['mite']: continue
        f = next((i + 1 for i in range(nR) if c['cons'][i] and c['cons'][i][2] > 0), None)
        out['first_lock'].append(f)
        for i in range(0, nR, 10):
            b = i // 200; out['n'][b] += 1
            if c['cons'][i]: out['carry_lock'][b] += c['cons'][i][2] > 0; out['carry_cry'][b] += c['cons'][i][0] > 0
    tr = [(e['r'], e['a'], tuple(e['altar'])) for e in g['ev'] if e['k'] == 'tribute_start' and team[e['a']] == g['mite']]
    for e in g['ev']:
        if e['k'] == 'lock_place' and e['team'] == g['mite']:
            out['near_own_trib'][0] += 1
            out['near_own_trib'][1] += any(t[1] == e['a'] and t[2] == tuple(e['to']) and abs(t[0] - e['r']) <= 3 for t in tr)
    return out
if __name__ == '__main__':
    fs = []; cl = collections.Counter(); cc = collections.Counter(); n = collections.Counter(); nt = [0, 0]
    with Pool(8) as P:
        for o in P.imap_unordered(one, ml.dirs('live'), chunksize=4):
            if not o: continue
            fs += o['first_lock']; cl.update(o['carry_lock']); cc.update(o['carry_cry']); n.update(o['n']); nt[0] += o['near_own_trib'][0]; nt[1] += o['near_own_trib'][1]
    have = [f for f in fs if f]
    print('bodies that ever carry a lock', len(have), '/', len(fs), '; first carried round p10/25/50/75', fl.q(have, .1), fl.q(have, .25), fl.med(have), fl.q(have, .75))
    print('share of alive bodies carrying a lock by 200-round bucket', ' '.join(f'r{b*200}:{cl[b]/n[b]:.2f}' for b in sorted(n)))
    print('share carrying a crystal by bucket', ' '.join(f'r{b*200}:{cc[b]/n[b]:.2f}' for b in sorted(n)))
    print('Mite locks placed within 3 rounds of its own tribute start at that altar (same body):', nt[1], '/', nt[0])
