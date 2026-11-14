"""Where an arm's dgate games flip against the base (diverse-panel.md "Flip analysis").
    python3 flips.py CAND [REF=variants/oc-base25] [--by hor|...]
Paired games are (seed, opponent, map, side) cells of the noise blocks (cached runs only). A flip is a game one bot
wins and the other loses: + for CAND. Each (map, side, opponent) cell has one draw per seed, so a cell's net over
seeds is a real per-cell effect only if it repeats: the odd-seed against even-seed correlation of per-cell nets
says whether conditioning on cells (maps, picks) can keep the winning cases."""
import argparse, collections, json, math, os, sys, numpy as np
T = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(T, '..', 'spar-tools')); sys.path.insert(0, T)
import local, live, dgate  # noqa: E402
# OLD_BODIES=1 reads the games against the bodies before 2026-11-09 (dgate --old-bodies).
dgate.NEW = os.environ.get("OLD_BODIES") != "1"

def matches(name):
    s = json.load(open(f'{local.R}replays/ab/{name}/summary.json'))
    for su in s['suites']:
        for m in json.load(open(local.R + su['batch'] + '/results.json'))['matches']:
            if m.get('winner') is None: continue
            yield (os.path.basename(m['map']).replace('.map26a', ''), 'a' if m['order'][0] == 0 else 'b'), m

def games(cand, ref, kmax=1000):
    out = {}  # (k, opp, map, side) -> (cand win, ref win, cand rounds, ref rounds)
    for k in range(1, kmax + 1):
        for b, o in dgate.block(k):
            nx, ny = dgate.rname(cand, b, o), dgate.rname(ref, b, o)
            if not (dgate.done(nx) and dgate.done(ny)): return out
            x, y = dict(matches(nx)), dict(matches(ny))
            for c in x.keys() & y.keys():
                out[(k, o, c[0], c[1])] = (x[c]['winner'] == 0, y[c]['winner'] == 0, x[c]['rounds'], y[c]['rounds'])
    return out

def table(rows, title):
    print(f'\n{title}')
    print(f'  {"group":34s} {"games":>6s} {"flips":>6s} {"+":>5s} {"-":>5s} {"net pts":>8s} {"z":>5s}')
    for g, (n, p, m) in sorted(rows.items(), key=lambda kv: -(kv[1][1] - kv[1][2])):
        z = (p - m) / math.sqrt(p + m) if p + m else 0
        print(f'  {str(g)[:34]:34s} {n:6d} {p + m:6d} {p:5d} {m:5d} {100 * (p - m) / n:+8.2f} {z:+5.1f}')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cand'); ap.add_argument('ref', nargs='?', default='variants/oc-base25')
    ap.add_argument('--top', type=int, default=12); a = ap.parse_args()
    G = games(a.cand, a.ref); D = live.drafts()
    seeds = max(k for k, *_ in G) if G else 0
    print(f'{a.cand} vs {a.ref}: {len(G)} paired games over {seeds} noise seeds')
    def group(key):
        rows = collections.defaultdict(lambda: [0, 0, 0])
        for (k, o, mp, s), (cw, rw, cr, rr) in G.items():
            g = key(k, o, mp, s, cr, rr)
            if g is None: continue
            r = rows[g]; r[0] += 1; r[1] += cw and not rw; r[2] += rw and not cw
        return rows
    picks = lambda o, mp, s: D.get((mp, s, o), ((), ()))
    table(group(lambda k, o, mp, s, cr, rr: o), 'by opponent picks (F = Fish, M = Mite)')
    table(group(lambda k, o, mp, s, cr, rr: (o, 'enemy HoR' if 'Heart of Ruin' in picks(o, mp, s)[0] else 'no enemy HoR')), 'by enemy Heart of Ruin')
    table(group(lambda k, o, mp, s, cr, rr: (o, 'our HoR' if 'Heart of Ruin' in picks(o, mp, s)[1] else 'no HoR of ours')), 'by our Heart of Ruin')
    table(group(lambda k, o, mp, s, cr, rr: (o, len(picks(o, mp, s)[1]))), 'by team size')
    table(group(lambda k, o, mp, s, cr, rr: ('<600' if min(cr, rr) < 600 else '<1200' if min(cr, rr) < 1200 else '1200+')),
          'by the shorter game of the pair (rounds)')
    # Per cell: does the net repeat across seeds?
    cell = collections.defaultdict(lambda: [0, 0])
    for (k, o, mp, s), (cw, rw, *_ ) in G.items():
        cell[(o, mp, s)][k % 2] += int(cw) - int(rw)
    ks = list(cell); x = np.array([cell[c][0] for c in ks]); y = np.array([cell[c][1] for c in ks])
    r = np.corrcoef(x, y)[0, 1] if len(ks) > 2 else float('nan')
    print(f'\nper-cell net, odd seeds against even seeds: r = {r:+.3f} over {len(ks)} cells '
          f'(0: cell effects are chaos; > 0: some cells carry a repeatable effect)')
    mapnet = collections.defaultdict(lambda: [0, 0, 0])
    for (k, o, mp, s), (cw, rw, *_ ) in G.items():
        m = mapnet[mp]; m[0] += 1; m[1] += cw and not rw; m[2] += rw and not cw
    rows = sorted(mapnet.items(), key=lambda kv: kv[1][1] - kv[1][2])
    table(dict(rows[:a.top] + rows[-a.top:]), f'maps: the {a.top} worst and best for CAND')

if __name__ == '__main__':
    main()
