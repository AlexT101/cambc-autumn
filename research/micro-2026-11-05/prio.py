"""Priority-channel analysis: per team, how priority is set, which bits vary, and which state each bit field tracks.

    python3 -I research/micro-2026-11-05/prio.py replays/micro/ladder --out research/micro-2026-11-05/out [--procs 24] [--teams A,B]
"""
import argparse
import collections
import glob
import gzip
import json
import math
import multiprocessing as mp
import os

CH = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HoR']


def per_game(path):
    d = json.load(gzip.open(path))
    teams, roster = d['teams'], {c['id']: c for c in d['roster']}
    # Round-start state by (round, id): x, y, hp, maxHp, alive, gold, gems.
    st = {}
    for rows in d['rounds']:
        for row in rows:
            st[(row[0], row[1])] = row
    out = collections.defaultdict(list)
    order = collections.defaultdict(list)  # (team) -> per round, champion acting order index
    last_r, idx = None, collections.Counter()
    for a in d['acts']:
        if a['k'] != 9:
            continue
        c = roster[a['a']]
        s = st.get((a['r'], a['a']))
        if not s:
            continue
        # Enemy and ally state at round start, for "who is it talking about".
        foes = [st.get((a['r'], o)) for o, oc in roster.items() if oc['team'] != c['team']]
        foes = [f for f in foes if f]
        out[teams[c['team']]].append([a['r'], CH[c['type']], a['a'], a['pr'], s[2], s[3], s[4], s[5], s[6], s[7], s[8],
                                      d['map']['w'], d['map']['h'], c['team'], d['key'],
                                      [[f[2], f[3], f[4], f[6]] for f in foes]])
    return out


def bitstats(vals):
    n = len(vals)
    ones = [sum((v >> b) & 1 for v in vals) / n for b in range(32)]
    return ones


def corr(xs, ys):
    n = len(xs)
    if n < 30:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--out', required=True)
    ap.add_argument('--procs', type=int, default=24)
    ap.add_argument('--sample', type=int, default=0, help='games to read (0 all)')
    o = ap.parse_args()
    files = sorted(glob.glob(os.path.join(o.dir, '*.json.gz')))
    if o.sample:
        files = files[:o.sample]
    R = collections.defaultdict(list)
    with mp.Pool(o.procs) as pool:
        for res in pool.imap_unordered(per_game, files, chunksize=8):
            for t, L in res.items():
                R[t].extend(L)
    os.makedirs(o.out, exist_ok=True)
    rep = []
    for t in sorted(R, key=lambda t: -len(R[t])):
        L = R[t]
        if len(L) < 200:
            continue
        vals = [r[3] & 0xFFFFFFFF for r in L]
        distinct = collections.Counter(r[3] for r in L)
        ones = bitstats(vals)
        varying = [b for b in range(32) if 0.01 < ones[b] < 0.99]
        rep.append(f"## {t}\n\nsets {len(L)}, distinct values {len(distinct)}; top values {distinct.most_common(8)}")
        rep.append(f"varying bits: {varying}")
        rep.append('bit p(1): ' + ' '.join(f"{b}:{ones[b]:.2f}" for b in range(31, -1, -1) if ones[b] > 0.001))
        # Correlate contiguous bit fields of the varying bits with the champion's own state and nearest foe.
        if varying:
            fields = []
            lo = varying[0]
            prev = lo
            for b in varying[1:] + [99]:
                if b != prev + 1:
                    fields.append((lo, prev))
                    lo = b
                prev = b
            # also all 4/8-bit aligned windows within varying range
            cand = set(fields)
            for w in (1, 2, 3, 4, 5, 6, 7, 8):
                for s in range(min(varying), max(varying) - w + 2):
                    cand.add((s, s + w - 1))
            feats = {
                'x': lambda r: r[4], 'y': lambda r: r[5], 'hp': lambda r: r[6], 'hpfrac': lambda r: r[6] / max(1, r[7]),
                'alive': lambda r: r[8], 'gold': lambda r: r[9], 'gems': lambda r: r[10], 'round': lambda r: r[0],
                'foe_vis_x': lambda r: min((f[0] for f in r[15] if f[0] >= 0), default=-1),
                'nfoes_alive': lambda r: sum(f[3] for f in r[15]),
            }
            best = []
            for (b0, b1) in cand:
                mask = (1 << (b1 - b0 + 1)) - 1
                fv = [((r[3] & 0xFFFFFFFF) >> b0) & mask for r in L[:20000]]
                if len(set(fv)) < 2:
                    continue
                for name, f in feats.items():
                    c = corr(fv, [f(r) for r in L[:20000]])
                    best.append((abs(c), c, b0, b1, name))
            best.sort(reverse=True)
            seen = set()
            lines = []
            for ac, c, b0, b1, name in best:
                if (b0, b1) in seen or ac < 0.3:
                    continue
                seen.add((b0, b1))
                lines.append(f"bits {b0}-{b1} ~ {name} r={c:+.2f}")
                if len(lines) >= 8:
                    break
            rep.append('field correlations: ' + ('; '.join(lines) if lines else 'none above 0.3'))
        # Change cadence: per champion, consecutive sets that change value.
        by = collections.defaultdict(list)
        for r in L:
            by[(r[14], r[2])].append(r)
        ch = sum(1 for k, v in by.items() for a, b in zip(v, v[1:]) if a[3] != b[3])
        tot = sum(max(0, len(v) - 1) for v in by.values())
        rep.append(f"consecutive sets that change value: {ch}/{tot}")
        # Example sequence.
        k0 = max(by, key=lambda k: len(by[k]))
        ex = by[k0][:40]
        rep.append(f"example {k0[0]} champion {k0[1]} ({ex[0][1]}): " + ', '.join(
            f"r{r[0]}:{r[3] & 0xFFFFFFFF:#x}@({r[4]},{r[5]}) hp{r[6]:.0f} g{r[10]}" for r in ex))
        rep.append('')
    open(os.path.join(o.out, 'priority.md'), 'w').write('\n'.join(rep))
    print('\n'.join(rep))


if __name__ == '__main__':
    main()
