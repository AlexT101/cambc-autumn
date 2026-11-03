"""kill-value.md's traces (bots/variants/ast-kill-meas*): kills taken when offered, and kill bids with no legal plan.

usage: python3 kill_trace.py RUN [RUN ...]   (ab.py run names whose CAND is a traced bot)

KV r me offered killed hit bound   a strike search (not keep_bid's) that offered a plan killing some foe on an
                                   unguarded end tile: masks by enemy index of foes some offered plan kills, foes dead
                                   and foes hit after the chosen plan; the bid-bound foe or -1
FK r me target in bound kept kept_any keep_only chosen
                                   a strike search on a turn our kill bid binds: target among the foes; above the
                                   health to leave (bound); a keeping plan offered on an unguarded (kept) or any
                                   (kept_any) end tile
KB r me target                     a kill bid won at our turn end on an enemy that had acted
KO r me target d real ok           a kill offer at our turn end: distance, real_distance, kept after it
"""
import os
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from follow_trace import lines, replays  # noqa: E402


def one(path):
    kv, fk, kb, ko = {}, defaultdict(list), [], {}
    for l in lines(path):
        h = l.split()
        try:
            if l.startswith('KV '):
                k = (int(h[1]), int(h[2]))
                o, d, t = int(h[3], 16), int(h[4], 16), int(h[5], 16)
                p = kv.get(k, (0, 0, 0, -1))
                kv[k] = (p[0] | o, p[1] | d, p[2] | t, max(p[3], int(h[6])))
            elif l.startswith('FK '):
                fk[(int(h[1]), int(h[2]))].append([int(x) for x in h[3:]])
            elif l.startswith('KB '):
                kb.append((int(h[1]), int(h[2]), int(h[3])))
            elif l.startswith('KO '):
                ko[(int(h[1]), int(h[2]), int(h[3]))] = (int(h[4]), int(h[5]), int(h[6]))
        except (ValueError, IndexError):
            continue
    c = Counter()
    for (r, me), (o, d, t, b) in kv.items():
        c['kv'] += 1
        c['kv took offered'] += (o & d) != 0
        c['kv killed any'] += d != 0
        c['kv hit other, no offered kill'] += (o & d) == 0 and (t & ~o) != 0
        c['kv hit offered, short'] += (o & d) == 0 and (t & o) != 0
        c['kv nothing'] += d == 0 and t == 0
        if b >= 0 and o >> b & 1:
            c['kv bound offered'] += 1
            c['kv bound killed'] += d >> b & 1
    for r, me, t in kb:
        c['bids'] += 1
        d, real, ok = ko.get((r, me, t), (-1, -1, -1))
        far = real > 6
        c['bids real>d'] += real > d
        c['bids real unreachable'] += far
        s = fk.get((r + 1, me))
        if not s:
            c['bound no search'] += 1
            continue
        rows = [x for x in s if x[0] == t]
        if not any(x[2] for x in rows):  # never above the health to leave: dead, unseen or hit already
            c['bound target not bound'] += 1
            continue
        c['bound searched'] += 1
        legal = any(x[4] for x in rows)
        c['bound no legal plan'] += not legal
        c['bound no unguarded plan'] += not any(x[3] for x in rows)
        if far:
            c['unreachable bids searched'] += 1
            c['unreachable bids with no plan'] += not legal
        elif real > d:
            c['farther bids searched'] += 1
            c['farther bids with no plan'] += not legal
    return c


def main():
    for run in sys.argv[1:]:
        paths = list(replays(run))
        c = Counter()
        with Pool(16) as pool:
            for x in pool.imap_unordered(one, paths, chunksize=8):
                c.update(x)
        n = len(paths)
        print(f'== {run}: {n} games')
        kv = c['kv']
        print(f'searches offering a kill: {kv} ({kv / n:.2f} a game); took an offered kill {100 * c["kv took offered"] / kv:.1f}%, '
              f'killed any {100 * c["kv killed any"] / kv:.1f}%, hit an offered target short {100 * c["kv hit offered, short"] / kv:.1f}%, '
              f'hit only others {100 * c["kv hit other, no offered kill"] / kv:.1f}%, hit nothing {100 * c["kv nothing"] / kv:.1f}%')
        if c['kv bound offered']:
            print(f'  bid-bound target killable: {c["kv bound offered"]}, killed {100 * c["kv bound killed"] / c["kv bound offered"]:.1f}%')
        b = c['bids']
        print(f'kill bids on acted targets: {b} ({b / n:.2f} a game); real distance farther {c["bids real>d"]}, unreachable {c["bids real unreachable"]}')
        bs = c['bound searched']
        print(f'  bound turns searched with the target bound: {bs}; no legal keeping plan {c["bound no legal plan"]} '
              f'({100 * c["bound no legal plan"] / max(bs, 1):.1f}%), none on an unguarded tile {c["bound no unguarded plan"]} '
              f'({100 * c["bound no unguarded plan"] / max(bs, 1):.1f}%); no search {c["bound no search"]}, target not bound {c["bound target not bound"]}')
        if c['unreachable bids searched'] or c['farther bids searched']:
            print(f'  of those, real_distance unreachable: {c["unreachable bids searched"]} ({c["unreachable bids with no plan"]} with no plan); '
                  f'farther: {c["farther bids searched"]} ({c["farther bids with no plan"]} with no plan)')


if __name__ == '__main__':
    main()
