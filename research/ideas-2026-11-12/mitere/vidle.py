"""Live r7: the victim-rounds of vstretch.py's 'seen/inrange/none' class (the last 8 rounds before Mite's Vesper kills
one of ours; at the round's start the victim sees her within its basic-attack range and then attacks no one), taken
apart at the victim's own turn: her position replayed through her moves and dashes before that turn (event slot t),
and whether the victim died before its turn, was stunned, kept a channel, cast at her or another, walked, or did nothing.
Usage: vidle.py [--examples N]"""
import sys, os, collections
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ml
RANGED = {'Vesper Vale', 'Prism', 'Stellar', 'Tavi', 'Willow', 'Cassi'}
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def one(sd):
    g = ml.load(sd)
    if g is None: return None
    m = g['mite']; o = 1 - m; rd = g['rd']; bush = {tuple(b) for b in g['map']['bushes']}
    name = {c['id']: c['name'] for c in g['meta']['champions']}; team = {c['id']: c['team'] for c in g['meta']['champions']}
    C = {c['id']: c for c in rd['champions']}
    V = [c for c in name if team[c] == m and name[c] == 'Vesper Vale']
    if not V: return None
    v = V[0]; nR = len(rd['round'])
    def at(c, i):
        cc = C[c]
        return (cc['x'][i], cc['y'][i]) if 0 <= i < nR and cc['alive'][i] and cc['x'][i] is not None else None
    byr = collections.defaultdict(list)
    for e in g['ev']: byr[e['r']].append(e)
    T = collections.Counter(); ex = []
    for e in g['ev']:
        if e['k'] != 'death' or e.get('by') != v or team.get(e.get('v')) != o or e.get('linked') is not None: continue
        x = e['v']; r = e['r']
        if r < 12: continue
        rng = 3 if name[x] in RANGED else 1
        for rr in range(r - 7, r + 1):
            i = rr - 2; p, q = at(x, i), at(v, i)
            if not p or not q or cheb(p, q) > rng or v not in (C[x]['sees'][i] or []): continue
            E = byr[rr]
            mine = [y for y in E if y.get('a') == x]
            if any(y['k'] == 'attack' for y in mine): continue
            T['n'] += 1
            slot = mine[0]['t'] if mine else None
            # her position at our turn: start plus her walks and dashes in slots before ours
            hq = q; hdead = False
            for y in E:
                if y.get('a') == v and slot is not None and y['t'] < slot and y['k'] in ('move', 'cast') and y.get('to') and y.get('ab', 'Dash') == 'Dash':
                    hq = tuple(y['to'])
            died = next((y for y in E if y['k'] == 'death' and y.get('v') == x), None)
            casts = [y for y in mine if y['k'] == 'cast']
            moved = [y for y in mine if y['k'] == 'move']
            if died and (slot is None or died['t'] < slot or not [y for y in mine if y['k'] not in ('recall_cancel',)]):
                k = 'killed before its turn'
            elif C[x]['stun'][i] > 0 or (i >= 0 and C[x]['stun'][max(0, i)] > 0):
                k = 'stunned'
            elif casts:
                k = 'cast ' + ('at her' if any(y.get('tgt') == v for y in casts) else '/'.join(sorted({y.get('ab', '?') for y in casts})))
            elif slot is None:
                k = 'no events (lost turn?)'
            elif any(y['k'] in ('tribute_start', 'teleport_start') for y in mine) or (C[x]['chan'][i] == 2):
                k = 'tribute/teleport'
            elif cheb(p if not moved else tuple(moved[-1]['f']), hq) > rng:
                k = 'she moved out of range first'
            elif hq in bush and hq != q:
                k = 'she moved into a bush first'
            elif moved:
                ma = tuple(moved[-1]['to'])
                k = 'walked ' + ('away' if cheb(ma, hq) > cheb(p, hq) else 'toward' if cheb(ma, hq) < cheb(p, hq) else 'sideways') + (', ends in range' if cheb(ma, hq) <= rng else ', ends out of range')
            elif any(y['k'] == 'recall_cancel' for y in mine) or C[x]['chan'][i] == 1 and not any(y['k'] == 'recall_cancel' for y in mine):
                k = 'stood (recall kept)' if not any(y['k'] == 'recall_cancel' for y in mine) else 'stood, recall cancelled, no attack'
            else:
                k = 'stood, nothing'
            k = ('ranged ' if rng == 3 else 'melee ') + k
            T[k] += 1
            if 'walked' in k: T[k + ' [no turn-end recall]'] += not any(y['k'] == 'recall_start' for y in mine)
            T[('vic', name[x], k.split(' ',1)[1])] += 1
            if len(ex) < 3 and 'walked' in k or 'stood' in k: ex.append((g['mid'], rr, name[x], k, p, q, hq))
    return T, ex
if __name__ == '__main__':
    T = collections.Counter(); EX = []
    with Pool(8) as P:
        for res in P.imap_unordered(one, ml.dirs('live'), chunksize=4):
            if res: T.update(res[0]); EX.extend(res[1])
    n = T.pop('n')
    print(n, 'victim-rounds: sees her in its range at the round start, attacks no one')
    for k, c in T.most_common():
        if isinstance(k, str): print(f'  {k:52s} {c:5d} {c / n:6.1%}')
    V = collections.Counter({k: c for k, c in T.items() if not isinstance(k, str)})
    for k, c in V.most_common(16): print('   ', k[1], '|', k[2], c)
    for e in EX[:12]: print(' ', e)
