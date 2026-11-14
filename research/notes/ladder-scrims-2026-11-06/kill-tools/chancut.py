"""chancut.py ROWS.json SIDE: completion by channel length and sight; winning bags (bag + tributed >= 1000) that
failed, and the games the channeller's side lost."""
import collections, json, sys
R = [r for r in json.load(open(sys.argv[1])) if r['side'] == sys.argv[2]]
bins = [(10, 19), (20, 29), (30, 59), (60, 99), (100, 10000)]
print('turns      n  done | seen-by-enemy n done | unseen n done | we see an enemy n done | we see none n done')
for lo, hi in bins:
    s = [r for r in R if lo <= r['turns'] <= hi]
    def d(x):
        return f"{len(x):5d} {100 * sum(r['end'] == 'done' for r in x) / max(1, len(x)):3.0f}%"
    print(f"{lo:3d}-{hi:<5d} {d(s)} | {d([r for r in s if r['seen']])} | {d([r for r in s if r['seen'] is False])} | "
          f"{d([r for r in s if r['sees']])} | {d([r for r in s if r['sees'] is False])}")
w = [r for r in R if r['trib'] is not None and r['bag'] + r['trib'] >= 1000 and r['turns'] >= 10]
print(f"winning bags (>= 10 turns): {len(w)}, done {sum(r['end']=='done' for r in w)}, ends {dict(collections.Counter(r['end'] for r in w))}, "
      f"side won {sum(r['won'] for r in w)}; failed in lost games {sum(1 for r in w if r['end']!='done' and not r['won'])} "
      f"({len({r['game'] for r in w if r['end']!='done' and not r['won']})} games)")
lost = [r for r in R if not r['won'] and r['turns'] >= 30]
print(f"lost games: {len({r['game'] for r in lost})} with a 30+ channel; {len(lost)} channels, ends {dict(collections.Counter(r['end'] for r in lost))}, "
      f"fates {dict(collections.Counter(r['fate'] for r in lost if r['end']!='done'))}, seen {sum(bool(r['seen']) for r in lost)}")
g = collections.Counter(r['game'] for r in R)
print('games', len({r['game'] for r in R}))
