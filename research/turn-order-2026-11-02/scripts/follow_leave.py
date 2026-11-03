"""Was keeping a kill bid on the leave branch safe? For bound turns (FT lines) on the leave branch with the target
alive, visible and yet to act: whether we killed it that turn, and whether we died before our next turn, for two
traced runs on the same games (the base and the fix).

usage: python3 follow_leave.py EXTRACT_DIR RUN [RUN ...]   (EXTRACT_DIR: extract.mjs --out of the runs' batches)
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from follow_trace import key, lines, parse_ft, replays  # noqa: E402
from tolib import G, index  # noqa: E402


def main():
    ex, runs = sys.argv[1], sys.argv[2:]
    by_source = {key(r['source']): r['dir'] for r in index(ex) if r['ok']}
    for run in runs:
        c = Counter()
        for path in replays(run):
            recs = []
            for l in lines(path):
                if l.startswith('FT '):
                    try:
                        x = parse_ft(l)
                    except (ValueError, IndexError):
                        continue
                    if x['branch'] == 'R' and x['hp0'] > 0 and not x['acted'] and not x['stun'] and x['need'] >= x['hpbid']:
                        recs.append(x)
            if not recs:
                continue
            d = by_source.get(key(path))
            if d is None:
                continue
            g = G(ex, d)
            for x in recs:
                r, me = x['r'], x['me']
                if r + 1 > g.N:
                    continue
                killed = not x['alive'] or x['hp1'] == 0
                hit = killed or (x['vis'] and x['hp1'] < x['hp0'])
                # our death after our turn in r, before our turn in r + 1
                mine = [e['s'] for e in g.by_round[r] if e.get('a') == me and e['t'] >= 0]
                end = max(mine) if mine else -1
                de = g.death(me, r)
                died = de is not None and de['s'] > end
                if not died:
                    de = g.death(me, r + 1)
                    nxt = g.first[r + 1].get(me)
                    died = de is not None and (nxt is None or de['s'] < nxt)
                c['n'] += 1
                c['killed'] += killed
                c['hit'] += hit
                c['died'] += died
                c[('died', 'killed' if killed else 'hit' if hit else 'none')] += died
                c[('n', 'killed' if killed else 'hit' if hit else 'none')] += 1
        n = c['n']
        print(f"{run}: {n} leave-branch bound turns; killed it {c['killed']} ({100 * c['killed'] / n:.1f}%), hit {c['hit']};"
              f" we died before our next turn {c['died']} ({100 * c['died'] / n:.1f}%)")
        for k in ('killed', 'hit', 'none'):
            m = c[('n', k)]
            if m:
                print(f"  {k}: {m}, died {c[('died', k)]} ({100 * c[('died', k)] / m:.1f}%)")


if __name__ == '__main__':
    main()
