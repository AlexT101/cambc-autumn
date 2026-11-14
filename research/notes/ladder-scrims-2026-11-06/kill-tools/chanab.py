"""chanab.py ROWS.json...: before/after channel fates of ab-mode rows (us = CAND, them = REF): per side, the ends of
30+ and 60+ turn channels, winning bags' completion, and bag gems later lost at a death per game."""
import collections, json, sys
for f in sys.argv[1:]:
    R = json.load(open(f))
    games = len({r['game'] for r in R}) or 1
    print(f'== {f} ({games} games with a 10+ channel)')
    for side, label in (('us', 'CAND'), ('them', 'REF')):
        S = [r for r in R if r['side'] == side]
        out = []
        for N in (30, 60):
            s = [r for r in S if r['turns'] >= N]
            c = collections.Counter(r['end'] for r in s)
            n = max(1, len(s))
            out.append(f"{N}+: {len(s):5d} done {100*c['done']/n:3.0f} stun {100*c['stun']/n:3.0f} lock {100*c['lock']/n:3.0f} "
                       f"self {100*c['manual']/n:3.0f} died {100*c['death']/n:3.0f}")
        w = [r for r in S if r['trib'] is not None and r['bag'] + r['trib'] >= 1000 and r['turns'] >= 10]
        lost = sum(r['bag'] for r in S if r['end'] != 'done' and r['fate'] == 'lost' and r['turns'] >= 30)
        print(f"  {label}: " + ' | '.join(out) + f" | winning bags {len(w)} done {100*sum(r['end']=='done' for r in w)/max(1,len(w)):.0f}%"
              f" | 30+ bags later lost {lost / games:.0f} gems/game")
