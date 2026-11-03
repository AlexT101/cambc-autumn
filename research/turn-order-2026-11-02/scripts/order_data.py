"""Enemy-order prediction dataset from extracted replays (tools/replay/extract.mjs output).

One row per (round r, observing team T, enemy e) with e alive and within 4 (Chebyshev) of a live champion of T at
the start of round r. The observer o is T's nearest champion to e (ties: earlier slot in round r). Every feature is
one a bot of T could know at o's turn in round r: o's view of the order is the real one up to o's slot (an enemy
that acted before o has set its next priority, which is final), and last round's priority for the others.

Target: e's rank next round, and whether e acts before o next round (o's real next slot).

usage: python3 order_data.py EXTRACT_DIR OUT.pkl [--max N]
"""
import gzip
import json
import pickle
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def team_order(members, prio, r):
    """Ids of a team by rank in round r: priority set by the end of r-1 (0 before round 1), then id."""
    return sorted(members, key=lambda c: (-(prio[c][r - 2] if r >= 2 else 0), c))


def seq_of(orders, r):
    a, b = orders[0], orders[1]
    if r % 2 == 0:
        a, b = b, a
    seq = []
    for k in range(max(len(a), len(b))):
        seq += a[k:k + 1] + b[k:k + 1]
    return seq


def one(args):
    ex, row = args
    d = row['dir']
    try:
        R = json.load(gzip.open(f'{ex}/{d}/rounds.json.gz'))
    except Exception as e:  # noqa: BLE001
        return []
    C = R['champions']
    N = len(R['round'])
    team = {c['id']: c['team'] for c in C}
    members = [[c['id'] for c in C if c['team'] == t] for t in (0, 1)]
    prio = {c['id']: c['prio'] for c in C}
    col = {c['id']: c for c in C}
    names = row['teams']

    def pos(c, r):  # end of round r (r >= 1)
        x = col[c]
        i = r - 1
        if not x['alive'][i] or x['x'][i] is None or x['x'][i] < 0:
            return None
        return (x['x'][i], x['y'][i])

    rows = []
    # Online per enemy team (as seen by the other): in-contact champion-rounds, rank changes among them, moves up.
    stat = {t: defaultdict(int) for t in (0, 1)}
    estat = defaultdict(lambda: defaultdict(int))
    orders = {}

    def order(r):
        o = orders.get(r)
        if o is None:
            ords = [team_order(members[t], prio, r) for t in (0, 1)]
            seq = seq_of(ords, r)
            o = (ords, {c: k for k, c in enumerate(seq)}, {c: k for t in (0, 1) for k, c in enumerate(ords[t])})
            orders[r] = o
        return o

    for r in range(3, N):
        ords, slot, rank = order(r)
        ords1, slot1, rank1 = order(r + 1)
        start = {c: pos(c, r - 1) for c in team}
        for T in (0, 1):
            E = 1 - T
            ours = [c for c in members[T] if start[c] is not None]
            if not ours:
                continue
            for e in members[E]:
                pe = start[e]
                if pe is None:
                    continue
                near = sorted((cheb(pe, start[o]), slot[o], o) for o in ours)
                dmin, _, o = near[0]
                if dmin > 4:
                    continue
                so = slot[o]
                # o's view: enemies that acted before o have set their final next priority
                def view(x):
                    return prio[x][r - 1] if slot[x] < so else prio[x][r - 2]
                settled = {x: slot[x] < so for x in members[E]}
                key = lambda x: (-view(x), x)
                lr = sorted(members[E], key=key)
                lr_rank = lr.index(e)
                if settled[e]:
                    above = sum(1 for x in members[E] if x != e and settled[x] and key(x) < key(e))
                    earliest, latest = above, above + sum(1 for x in members[E] if not settled[x])
                else:
                    earliest, latest = 0, len(members[E]) - 1
                hp, mx = col[e]['hp'][r - 2], col[e]['maxHp'][r - 2]
                ohp, omx = col[o]['hp'][r - 2], col[o]['maxHp'][r - 2]
                n_ours4 = sum(1 for c in ours if cheb(pe, start[c]) <= 4)
                n_mates4 = sum(1 for c in members[E] if c != e and start[c] is not None and cheb(pe, start[c]) <= 4)
                low_ours = min((col[c]['hp'][r - 2] / max(1, col[c]['maxHp'][r - 2]) for c in ours if cheb(pe, start[c]) <= 4),
                               default=1.0)
                st, es = stat[E], estat[e]
                rows.append((
                    names[E], names[T], d, r, len(members[E]), len(members[T]),
                    int(settled[e]), lr_rank, rank[e], earliest, latest,
                    dmin, n_ours4, n_mates4, hp / max(1, mx), ohp / max(1, omx), low_ours,
                    rank[o], int(prio[e][r - 2] != prio[e][r - 3]),
                    st['contact'], st['moved'], st['up'], st['top'], st['changed'], es['contact'], es['moved'],
                    int((E == 0) == ((r + 1) % 2 == 1)),  # e's team starts r+1
                    rank1[e], int(slot1[e] < slot1[o]), rank1[o], slot1[o],
                ))
        # online stats after round r (known from round r+1 on): ranks for r+1 are final at r's end
        for E in (0, 1):
            T = 1 - E
            ours = [c for c in members[T] if start[c] is not None]
            for e in members[E]:
                pe = start[e]
                if pe is None or not ours or min(cheb(pe, start[c]) for c in ours) > 4:
                    continue
                st, es = stat[E], estat[e]
                st['contact'] += 1
                es['contact'] += 1
                mv = rank1[e] != rank[e]
                st['moved'] += mv
                es['moved'] += mv
                st['up'] += rank1[e] < rank[e]
                st['top'] += rank1[e] == 0
                st['changed'] += prio[e][r - 1] != prio[e][r - 2]
    return rows


COLS = ('team', 'obs_team', 'game', 'r', 'n', 'n_obs', 'settled', 'lr_rank', 'cur_rank', 'earliest', 'latest',
        'dmin', 'n_ours4', 'n_mates4', 'hp', 'obs_hp', 'low_ours', 'obs_rank', 'e_changed_last',
        'st_contact', 'st_moved', 'st_up', 'st_top', 'st_changed', 'es_contact', 'es_moved', 'starts_next',
        'y_rank', 'y_before', 'obs_rank_next', 'obs_slot_next')


def main():
    ex, out = sys.argv[1], sys.argv[2]
    mx = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else None
    games = json.load(open(f'{ex}/index.json'))['games']
    seen, rows_in = set(), []
    for g in games:
        if not g.get('ok') or g['dir'] in seen:
            continue
        seen.add(g['dir'])
        rows_in.append(g)
    if mx:
        rows_in = rows_in[:mx]
    allrows = []
    with ProcessPoolExecutor(40) as pool:
        for rs in pool.map(one, [(ex, g) for g in rows_in], chunksize=8):
            allrows.extend(rs)
    pickle.dump({'cols': COLS, 'rows': allrows}, open(out, 'wb'))
    print(len(rows_in), 'games', len(allrows), 'rows')


if __name__ == '__main__':
    main()
