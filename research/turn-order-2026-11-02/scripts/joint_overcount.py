"""How often Safety's per-enemy turn counts exceed what one enemy order allows, from ast-pwc-dx's SB traces
(safety-fuel.md, "Joint worst case").

Per SB read (our turn, live enemies within 4), with 2+ enemies listed:
- now(e): e still acts this round after us (visible: not acted).
- Safety's blow counts each enemy's next turn whatever its rank (a single strike even at turns_before_ours 0), and a
  second one (the two-turn widening) at turns_before_ours 2: its next-round turns before ours are eff - now, where
  eff = max(1, T).
- m: enemy slots before our next slot (rules rounds.champion_order), the most enemies that can act before it.
- Over-count: the listed enemies' next-round turns exceed m. Second-turn over-count: more than m enemies widened.
- `doubled` (Bound::doubled, damage_bound/damage_ceiling with double_unacted, may_escape, offer_escape): every
  visible listed enemy gets a next-round turn (unacted ones doubled or widened, acted ones their next strike), so it
  over-counts whenever the visible listed enemies outnumber m.
REF = last-read ranks (`old`), pwc = worst case (`new`).

usage: python3 joint_overcount.py EXTRACT_DIR
"""
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from tolib import G, index, stdout_lines, traced_team  # noqa: E402


def enemies_before(slot, n_us, n_them, them_start):
    n = 0
    for k in range(n_them):
        s = 2 * k + (0 if them_start else 1) if k < n_us else n_us + k
        n += s < slot
    return n


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
            r, me, slot_next = int(hh[1]), int(hh[2]), int(hh[5])
        except (ValueError, IndexError):
            continue
        if r >= trusted or r < 2 or me not in g.team:
            continue
        t = g.team[me]
        n_us, n_them = len(g.members[t]), len(g.members[1 - t])
        m = enemies_before(slot_next, n_us, n_them, g.starts(r + 1) == 1 - t)
        rows = []
        for x in ents.split():
            try:
                e, acted, vis, d, old, new = map(int, x.split(':'))
            except ValueError:
                continue
            rows.append((acted, vis, d, old, new))
        if len(rows) < 2:
            continue
        seen = all(v for _, v, _, _, _ in rows)
        k = ('2+', 'all seen' if seen else 'some unseen', f'n={min(len(rows), 4)}')
        c[k + ('reads',)] += 1
        c[('2+', 'reads')] += 1
        _, slot_n, _ = g.order(r + 1)
        for name, col in (('REF', 3), ('pwc', 4)):
            nxt = sum(max(1, row[col]) - (0 if row[0] else 1) for row in rows if row[1])
            wide = sum(row[col] >= 2 for row in rows)
            over = nxt > m
            c[k + (name, 'next>m')] += over
            c[('2+', name, 'next>m')] += over
            c[('2+', name, 'excess')] += max(0, nxt - m)
            c[('2+', name, 'wide>m')] += wide > m
            c[('2+', name, 'wide>=1')] += wide >= 1
            c[('2+', name, f'wide={min(wide, 3)}')] += 1
        c[('2+', f'm={min(m, 3)}')] += 1
        vis = sum(1 for row in rows if row[1])
        c[('2+', 'doubled next>m')] += vis > m
        c[('2+', 'doubled excess')] += max(0, vis - m)
        c[k + ('doubled next>m',)] += vis > m
        # The truth: listed enemies acting before our next slot next round.
        real = sum(1 for x in ents.split() if x.split(':')[0].isdigit() and int(x.split(':')[0]) in slot_n
                   and me in slot_n and slot_n[int(x.split(':')[0])] < slot_n[me])
        c[('2+', 'real next>m')] += real > m
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
