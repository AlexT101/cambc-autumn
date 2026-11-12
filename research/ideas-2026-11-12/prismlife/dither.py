"""Deaths after rounds spent below the recall line: python3 dither.py EXTROOT/TAG [LINE]
For each Prism death (deaths.py rows, the 8 rounds before): the rounds it had been below LINE (default 0.32) of its
health, and the steps it came nearer our spawn meanwhile (Chebyshev, to the spawn's box)."""
import sys, collections
import deaths


def main():
    line = float(sys.argv[2]) if len(sys.argv) > 2 else 0.32
    G = [g for g in deaths.load(sys.argv[1]) if g['prism']]
    D = [(g, d) for g in G for d in g['deaths'] if not d['camp']]
    print(f'{len(D)} Prism deaths to champions in {len(G)} Prism games')
    rows = []
    for g, d in D:
        S = d['steps']
        low = [s for s in S if s['hp'] < line and s['home']]
        if not low: rows.append((0, 0, 0, d, g)); continue
        # the last unbroken run below the line
        run = []
        for s in reversed(S):
            if s['hp'] < line and s['home']: run.append(s)
            else: break
        run.reverse()
        if not run: rows.append((0, 0, 0, d, g)); continue
        h0 = max(run[0]['home']); h1 = max(run[-1]['home'])
        stun = sum(1 for s in run if s['turn'] == 5)
        rows.append((len(run), h0 - h1, stun, d, g))
    c = collections.Counter(min(r[0], 8) for r in rows)
    print('rounds below the line before death (8 = 8 or more, the window):', ', '.join(f'{k}: {v}' for k, v in sorted(c.items())))
    for lo in (3, 4, 6):
        s = [r for r in rows if r[0] >= lo]
        slow = [r for r in s if r[1] <= (r[0] - 1 - r[2]) / 2]
        print(f'  {lo}+ rounds below: {len(s)} deaths ({100 * len(s) / len(rows):.1f}%); of them home progress at most half its free turns: {len(slow)} ({100 * len(slow) / len(rows):.1f}% of deaths); '
              f'mean home distance at the run start {sum(max(r[3]["steps"][-r[0]]["home"]) for r in s) / max(1, len(s)):.1f}')
    if '--dump' in sys.argv:
        for r in [r for r in rows if r[0] >= 6][:12]:
            print(r[4]['dir'], r[3]['r'], 'below', r[0], 'progress', r[1], 'stunned', r[2], 'bag', r[3]['gems'])


if __name__ == '__main__':
    main()
