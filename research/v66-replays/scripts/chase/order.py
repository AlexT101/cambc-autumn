# Turn order from priorities, validated against event turn indices.
import sys; sys.path.insert(0, 'research/v66-replays/scripts/extract')
from common import *
def order(R, i, lag):
    rr = R['round'][i]; CH = R['champions']; k = max(0, i - lag)
    teams = [sorted([c for c in CH if c['team'] == t], key=lambda c: (-c['prio'][k], c['id'])) for t in (0, 1)]
    first = 0 if rr % 2 == 1 else 1
    seq = []; a, b = teams[first], teams[1 - first]
    for n in range(max(len(a), len(b))):
        if n < len(a): seq.append(a[n]['id'])
        if n < len(b): seq.append(b[n]['id'])
    return seq
if __name__ == '__main__':
    for g in games()[:6]:
        d = g['dir']; R = rounds(d); rix = {r: i for i, r in enumerate(R['round'])}
        seen = defaultdict(dict)
        for e in events(d):
            if 'a' in e and 't' in e and e['r'] in rix: seen[rix[e['r']]][e['a']] = e['t']
        for lag in (0, 1):
            ok = tot = 0
            for i, m in seen.items():
                seq = order(R, i, lag); pos = {c: n for n, c in enumerate(seq)}
                obs = sorted(m, key=lambda a: m[a]); pred = sorted(m, key=lambda a: pos[a])
                tot += 1; ok += obs == pred
            print(d[:8], 'lag', lag, '%.3f' % (ok / tot))
