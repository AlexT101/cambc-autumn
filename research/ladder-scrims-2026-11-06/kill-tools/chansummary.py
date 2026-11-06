"""chansummary.py ROWS.json [SIDE] [OPP]: tables of chanforensics.py rows (SIDE us/them, OPP a prefix or 'all')."""
import collections, json, sys
rows = json.load(open(sys.argv[1]))
side = sys.argv[2] if len(sys.argv) > 2 else 'us'
opp = sys.argv[3] if len(sys.argv) > 3 else 'all'
rows = [r for r in rows if r['side'] == side and (opp == 'all' or r['opp'].startswith(opp))]
ENDS = ['done', 'death', 'stun', 'lock', 'manual', 'gameend']


def line(label, s):
    if not s:
        return
    c = collections.Counter(r['end'] for r in s)
    n = len(s)
    gems = sum(r['bag'] for r in s)
    banked = sum(r['bag'] for r in s if r['end'] == 'done')
    print(f"{label:34s} {n:5d} " + ' '.join(f"{100 * c[e] / n:5.0f}" for e in ENDS)
          + f"  gems {gems:7d} banked {100 * banked / max(1, gems):4.0f}%  won {100 * sum(r['won'] for r in s) / n:4.0f}%")


print(f"{'':34s} {'n':>5s} " + ' '.join(f"{e[:5]:>5s}" for e in ENDS))
for N in (10, 30, 60):
    s = [r for r in rows if r['turns'] >= N]
    print(f"-- >= {N} turns")
    line('all', s)
    line('  Prism', [r for r in s if r['a'] == 'Prism'])
    line('  not Prism', [r for r in s if r['a'] != 'Prism'])
    line('  seen at start', [r for r in s if r['seen']])
    line('  unseen at start', [r for r in s if r['seen'] is False])
    line('  no ally within 6', [r for r in s if r['ours6'] == 0])
    line('  1 ally within 6', [r for r in s if r['ours6'] == 1])
    line('  2+ allies within 6', [r for r in s if r['ours6'] >= 2])
    line('  1+ ally within 3', [r for r in s if r['ours3'] >= 1])
    line('  enemy within 6 at start', [r for r in s if r['enemies6'] > 0])
    line('  no enemy within 6, unseen', [r for r in s if r['enemies6'] == 0 and r['seen'] is False])
    line('  our lock on the altar', [r for r in s if r['lock']])
    line('  margin >= 100 (ahead)', [r for r in s if r['margin'] is not None and r['margin'] >= 100])
    line('  margin -100..100', [r for r in s if r['margin'] is not None and -100 < r['margin'] < 100])
    line('  margin <= -100 (behind)', [r for r in s if r['margin'] is not None and r['margin'] <= -100])
    line('  round < 1000', [r for r in s if r['r'] < 1000])
    line('  round 1000-1599', [r for r in s if 1000 <= r['r'] < 1600])
    line('  round >= 1600', [r for r in s if r['r'] >= 1600])
    line('  game ends within turns+20', [r for r in s if r['last'] - r['r'] <= r['turns'] + 20])
    d = [r for r in s if r['end'] == 'death']
    if d:
        k = collections.Counter(r['killer'] for r in d)
        e = collections.Counter(min(3, r['enemies_at_death'] or 0) for r in d)
        print(f"  deaths: killers {dict(k.most_common(5))}; enemies within 6 at death (3 = 3+) {dict(sorted(e.items()))}")
    ran = [r['ended'] - r['r'] for r in s if r['end'] not in ('done', 'gameend')]
    if ran:
        ran.sort()
        print(f"  failed channels ran {ran[len(ran) // 2]} rounds (median) of median {sorted(r['turns'] for r in s)[len(s) // 2]} turns")
