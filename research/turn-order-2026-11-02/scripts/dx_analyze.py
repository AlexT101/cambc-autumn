"""Diagnosis of the worst-case model from ast-pwc-dx's traces (KB, SB lines) against the real turn order.

SB r me flag slot_now slot_next | e:acted:visible:dist:old:new  -- Safety's turns_before_ours, last-read ranks (old)
                                                                and worst case (new), live enemies within 4.
KB r me flag e acted our_slot their_old their_new old_ok new_ok value -- kill bids under each rule.

The truth for SB: e's real turns before our next turn (this round after ours, next round before ours), and whether
e hit us before our next turn.

usage: python3 dx_analyze.py EXTRACT_DIR
"""
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from tolib import G, index, stdout_lines, traced_team  # noqa: E402


def one(args):
    ex, row = args
    try:
        g = G(ex, row['dir'])
    except Exception:  # noqa: BLE001
        return Counter()
    us = traced_team(row['source'])
    raw = stdout_lines(row['source'], us)
    c = Counter()
    trusted = g.N - 1
    if sum(len(l) + 1 for l in raw) > 1_000_000:
        for l in reversed(raw):
            p = l.split()
            if len(p) > 1 and p[1].isdigit():
                trusted = int(p[1]) - 1
                break
    for l in raw:
        if not l.startswith('SB ') or l.count('|') != 1:
            continue
        h, ents = l.split('|')
        hh = h.split()
        try:
            r, me = int(hh[1]), int(hh[2])
        except ValueError:
            continue
        if r >= trusted or r < 2:
            continue
        _, slot_r, _ = g.order(r)
        _, slot_n, _ = g.order(r + 1)
        if me not in slot_r:
            continue
        # our next turn's first actor step: hits before it count
        t_next = g.first[r + 1].get(me, 10 ** 12)
        t_now = g.first[r].get(me, -1)
        for x in ents.split():
            try:
                e, acted, vis, d, old, new = map(int, x.split(':'))
            except ValueError:
                continue
            if e not in slot_r:
                continue
            now = slot_r[e] > slot_r[me]
            nxt = slot_n[e] < slot_n[me]
            truth = int(now) + int(nxt)
            hit = False
            for rr, lo, hi in ((r, t_now, 10 ** 12), (r + 1, -1, t_next)):
                for ev in g.by_round[rr]:
                    if ev['s'] <= lo or ev['s'] >= hi:
                        continue
                    if ev.get('a') == e and ev['k'] in ('attack', 'cast') and any(v == me for v, _ in ev.get('dmg') or []):
                        hit = True
                        break
            truth = min(truth, 2)
            key = ('vis' if vis else 'unseen', 'acted' if acted else 'yet')
            c[key + ('n',)] += 1
            c[key + ('old_right',)] += old == truth
            c[key + ('new_right',)] += new == truth
            c[key + ('old_under',)] += old < truth
            c[key + ('new_under',)] += new < truth
            if old != new:
                k2 = key + (f'{old}->{new}',)
                c[k2 + ('n',)] += 1
                c[k2 + ('truth=new',)] += truth == new
                c[k2 + ('truth=old',)] += truth == old
                c[k2 + ('hit',)] += hit
                c[k2 + ('hit', 'truth=new')] += hit and truth == new
                c[k2 + ('hit', 'truth=old')] += hit and truth == old
                c[k2 + ('next_before',)] += nxt
            else:
                c[key + ('same', 'n')] += 1
                c[key + ('same', 'hit')] += hit
                c[key + ('same', 'right')] += truth == new
                c[key + ('same', 'hit', 'right')] += hit and truth == new
    for l in raw:
        if not l.startswith('KB '):
            continue
        p = l.split()
        if len(p) != 12:
            continue
        r, me, flag, e, acted, ours, t_old, t_new, old_ok, new_ok, val = map(int, p[1:])
        if r >= trusted:
            continue
        _, slot_n, _ = g.order(r + 1)
        c[('KB', flag, old_ok, new_ok)] += 1
        if old_ok != new_ok:
            c[('KBflip', 'before')] += slot_n.get(me, 99) < slot_n.get(e, -1)
            c[('KBflip', 'died')] += g.died_in(e, r + 1)
    return c


def main():
    ex = sys.argv[1]
    rows = [r for r in index(ex) if r.get('ok')]
    tot = Counter()
    with ProcessPoolExecutor(40) as pool:
        for c in pool.map(one, [(ex, r) for r in rows], chunksize=4):
            tot.update(c)
    print(len(rows), 'games')
    for k in sorted(tot, key=str):
        print(k, tot[k])


if __name__ == '__main__':
    main()
