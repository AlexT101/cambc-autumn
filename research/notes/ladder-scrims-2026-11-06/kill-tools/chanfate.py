"""chanfate.py ROWS.json SIDE: per end, what became of the bag (banked later by the same body, lost at its death,
carried to the end), restarts within 3 rounds, and the state at a self-cancel."""
import collections, json, sys
R = [r for r in json.load(open(sys.argv[1])) if r['side'] == sys.argv[2]]
for N in (30, 60):
    s = [r for r in R if r['turns'] >= N]
    g = sum(r['bag'] for r in s)
    print(f'>= {N}: {len(s)} channels, {g} gems: eventually banked {100*sum(r["bag"] for r in s if r["fate"]=="banked")/g:.0f}%, '
          f'lost {100*sum(r["bag"] for r in s if r["fate"]=="lost")/g:.0f}%, carried {100*sum(r["bag"] for r in s if r["fate"]=="carried")/g:.0f}%')
    for end in ('done', 'manual', 'stun', 'lock', 'death', 'gameend'):
        t = [r for r in s if r['end'] == end]
        if not t:
            continue
        f = collections.Counter(r['fate'] for r in t)
        dt = sorted(r['fate_r'] - r['ended'] for r in t if r['fate'] == 'banked' and end != 'done')
        print(f"   {end:8s} {len(t):5d} restarted {100*sum(r['restarts']>0 for r in t)/len(t):3.0f}%  fate banked {100*f['banked']/len(t):3.0f}% lost {100*f['lost']/len(t):3.0f}% carried {100*f['carried']/len(t):3.0f}%"
              + (f"  (banked {dt[len(dt)//2]} rounds after, median)" if dt else ''))
    m = [r for r in s if r['end'] == 'manual']
    if m:
        e6 = collections.Counter(min(2, r['enemies6_end'] or 0) for r in m)
        e3 = sum((r['enemies3_end'] or 0) > 0 for r in m)
        print(f"   self-cancels: seen at the cancel {100*sum(bool(r['seen_end']) for r in m)/len(m):.0f}%, enemies within 6 "
              f"0/1/2+: {e6[0]}/{e6[1]}/{e6[2]}, an enemy within 3 {100*e3/len(m):.0f}%, ran {sorted(r['ended']-r['r'] for r in m)[len(m)//2]} rounds (median)")
