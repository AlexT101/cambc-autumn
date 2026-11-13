"""F/R flips and THREAT trace counts from a debug A/B batch, by side (CAND = bots[0], REF = bots[1]).
A pursuit is a maximal run of a champion's D lines on one farm group >= 0; its flips are its F->R steps
(as tt_pursuit.py). A strict flip is F on g, a run of R (still g), then F on g within 3 turns of the last R.
Usage: py c3_flips.py BATCH_DIR"""
import json, sys, zipfile
from collections import Counter, defaultdict
from pathlib import Path


def side_lines(z, side):
    try:
        return z.read(f'team-{side}.stdout').decode(errors='replace').splitlines()
    except KeyError:
        return []


def main():
    batch = Path(sys.argv[1])
    res = json.loads((batch / 'results.json').read_text())
    tot = {b: Counter() for b in (0, 1)}
    games = {0: 0, 1: 0}
    for m in res['matches']:
        if not m.get('replay') or not Path(m['replay']).exists():
            continue
        z = zipfile.ZipFile(m['replay'])
        for t, side in enumerate('ab'):
            bot = m['order'][t]
            lines = side_lines(z, side)
            if not lines:
                continue
            games[bot] += 1
            c = tot[bot]
            c['win'] += int(m['winner'] == bot)
            D = defaultdict(list)
            for l in lines:
                p = l.lstrip('\x00').split()
                if not p:
                    continue
                if p[0] == 'D' and len(p) >= 6:
                    D[int(p[2])].append((int(p[1]), p[3], int(p[4])))
                elif p[0] == 'THREAT' and len(p) >= 5:
                    c['threat ' + p[1].lower()] += 1
                    if p[1] == 'CLEAR':
                        c['clear ' + p[5]] += 1
            for h, seq in D.items():
                seq.sort()
                j = 0
                while j < len(seq):
                    g = seq[j][2]
                    if g < 0:
                        j += 1
                        continue
                    k = j
                    while k + 1 < len(seq) and seq[k + 1][2] == g:
                        k += 1
                    brs = [x[1] for x in seq[j:k + 1]]
                    flips = sum(1 for a, b in zip(brs, brs[1:]) if a == 'F' and b == 'R')
                    c['pursuits'] += 1
                    c['flips'] += flips
                    if flips >= 2:
                        c['pursuits 2+ flips'] += 1
                        c['rounds in 2+ flip pursuits'] += seq[k][0] - seq[j][0] + 1
                    j = k + 1
                # strict flips
                n = len(seq)
                for i in range(1, n):
                    if seq[i][1] == 'R' and seq[i - 1][1] == 'F' and seq[i - 1][2] >= 0 and seq[i][2] == seq[i - 1][2]:
                        g = seq[i][2]
                        e = i
                        while e + 1 < n and seq[e + 1][1] == 'R' and seq[e + 1][2] == g:
                            e += 1
                        if any(seq[x][1] == 'F' and seq[x][2] == g for x in range(e + 1, min(n, e + 4))):
                            c['strict flips'] += 1
    names = res.get('bots')
    for b in (0, 1):
        n = max(1, games[b])
        print(f'== {"CAND" if b == 0 else "REF"} {names[b] if names else ""}: {games[b]} team-games, wins {tot[b]["win"]}')
        for k in sorted(tot[b]):
            if k == 'win':
                continue
            print(f'  {k:28s} {tot[b][k]:7d}  {tot[b][k] / n:8.2f} per team-game')


if __name__ == '__main__':
    main()
