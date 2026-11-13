#!/usr/bin/env python3
"""s3: the end of the race. For every game's loser: its score, its Prism's bag and channel at the end, and the
team's carried gems; whether the gems to win were already carried (score + bags >= 1000) when the winner's last
tribute landed. Also the winner's last tribute (its bag and channel length) and the stop-ender stalls.
Writes replays/.s3cache/endrace.pkl."""
import collections, os, pickle, sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import Game, files, load, CACHE


def one(f):
    G = Game(load(f))
    T = G.T
    w = G.winner
    lo = 1 - w
    ev = G.g['ev']
    tl = sorted((e['r'], G.team[e['a']], e['gems'], e['a']) for e in ev if e['k'] == 'tribute_end')
    ts = [e for e in ev if e['k'] == 'tribute_start']
    tc = [e for e in ev if e['k'] == 'tribute_cancel']

    def score(t, r):
        return sum(g for rr, tt, g, a in tl if tt == t and rr < r)
    i = T - 1
    row = dict(sha=G.g['sha'], T=T, winner=w, gems=G.g['result']['gems'], rl=T >= 2000)
    lp = [p for p in G.prisms if G.team[p] == lo]
    wp = [p for p in G.prisms if G.team[p] == w]
    row['lo_prism'] = bool(lp)
    row['w_prism'] = bool(wp)
    # state before the winning round's tribute (index T-2 = end of the round before)
    j = max(0, T - 2)
    row['lo_score'] = score(lo, T)
    row['lo_bags'] = sum(G.ch[c]['gems'][j] for c in G.ch if G.team[c] == lo and G.alive(c, j))
    if lp:
        p = lp[0]
        row['lo_p_bag'] = G.ch[p]['gems'][j] if G.alive(p, j) else 0
        row['lo_p_alive'] = G.alive(p, j)
        row['lo_p_chan'] = G.ch[p]['chan'][j]
        row['lo_p_chanT'] = G.ch[p]['chanT'][j]
        st = [e for e in ts if e['a'] == p]
        row['lo_p_last_start'] = (st[-1]['r'], st[-1]['gems'], st[-1]['dur']) if st else None
        row['lo_p_br_last30'] = ''.join((G.branch(p, q) or ('.',))[0] for q in range(max(0, T - 30), T))
        # first round its bag (with the team score) would have won
        ws = None
        for q in range(T):
            if G.alive(p, q) and G.ch[p]['gems'][q] + score(lo, q + 1) >= 1000:
                ws = q + 1
                break
        row['lo_p_winbag_from'] = ws
        row['lo_p_cancels'] = [(e['r'], e.get('cause'), e.get('gems')) for e in tc if e['a'] == p and e.get('cause') in ('stun', 'lock')]
    # the winner's last tribute(s)
    wl = [x for x in tl if x[1] == w]
    if wl:
        r, t, g, a = wl[-1]
        row['w_last'] = (r, g, G.names[a])
        st = [e for e in ts if e['a'] == a and e['r'] <= r]
        row['w_last_dur'] = st[-1]['dur'] if st else None
    if wp:
        p = wp[0]
        row['w_p_cancels'] = [(e['r'], e.get('cause'), e.get('gems')) for e in tc if e['a'] == p and e.get('cause') in ('stun', 'lock')]
        ws = None
        for q in range(T):
            if G.alive(p, q) and G.ch[p]['gems'][q] + score(w, q + 1) >= 1000:
                ws = q + 1
                break
        row['w_p_winbag_from'] = ws
        row['w_p_tributes'] = [(e['r'], e['gems']) for e in ev if e['k'] == 'tribute_end' and e['a'] == p]
    # every team's Prism tributes (count and sizes) for the bag-size profile
    row['prism_tributes'] = {G.team[p]: [(e['r'], e['gems']) for e in ev if e['k'] == 'tribute_end' and e['a'] == p] for p in G.prisms}
    row['prism_starts'] = {G.team[p]: [(e['r'], e['gems'], e['dur']) for e in ts if e['a'] == p] for p in G.prisms}
    row['prism_cancels'] = {G.team[p]: [(e['r'], e.get('cause'), e.get('gems'), e.get('left')) for e in tc if e['a'] == p] for p in G.prisms}
    return row


if __name__ == '__main__':
    with Pool(16) as p:
        rows = p.map(one, files(), chunksize=4)
    pickle.dump(rows, open(os.path.join(CACHE, 'endrace.pkl'), 'wb'))
    print(len(rows))
