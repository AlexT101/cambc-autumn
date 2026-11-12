"""Does BattleCats play differently against us (or Fish/Mite)? Map-and-side-matched comparison of its own behaviour.
Also: does its priority encoding or flag use change by opponent (a classifier-driven mode would show)."""
import collections, fl, math
G = fl.load(lambda g: g['ver'] == 'cur')
def feats(g):
    b = g['bc']; T = g['team']
    pv = collections.Counter()
    for cid, seq in g['pri'].items():
        for r, p, sb in seq: pv['flag' if p in (35, 38, 40) else 'neg' if p < 0 else 'quiet' if 8 <= p <= 20 else 'other'] += 1
    tot = sum(pv.values()) or 1
    tr = [x for x in g['tribs'] if T[x[1]] == b]
    f = {'locks': sum(1 for x in g['locks'] if x[2] == b),
         'locks_on_trib': sum(1 for x in g['locks'] if x[2] == b and x[4]),
         'first_lock<=400': int(any(x[2] == b and x[0] <= 400 for x in g['locks'])),
         'teleports': sum(1 for x in g['tps'] if T[x[1]] == b),
         'wards_r400': sum(1 for x in g['wards'] if T[x[1]] == b and x[0] <= 400),
         'tributes_r400': sum(1 for x in tr if x[0] <= 400),
         'trib_bag_r400': fl.mean(x[2] for x in tr if x[0] <= 400) if any(x[0] <= 400 for x in tr) else None,
         'caps_r300': sum(1 for c in g['caps'] if c[2] == b and c[0] <= 300),
         'enemy_side_caps_r400': None,
         'contact_rows_r400': sum(1 for f in g['fights'] if T[f[1]] == b and f[0] <= 400 and f[4] <= 3),
         'hits_r400': sum(1 for f in g['fights'] if T[f[1]] == b and f[0] <= 400 and f[9]),
         'prio_other_share': pv['other'] / tot, 'prio_flag_share': pv['flag'] / tot}
    return f
by = collections.defaultdict(lambda: collections.defaultdict(list))
for g in G: by[(g['map'], g['bc'])][g['oc']].append(feats(g))
keys = list(feats(G[0]).keys())
for cmp in ('us', 'Fish', 'Mite'):
    print(f'\n== BC vs {cmp} minus BC vs other teams, same map and side (mean of per-cell differences)')
    for k in keys:
        d = []
        for cell, D in by.items():
            a = [x[k] for x in D.get(cmp, []) if x[k] is not None]; o = [x[k] for x in D.get('other', []) if x[k] is not None]
            if a and o: d.append(sum(a) / len(a) - sum(o) / len(o))
        if len(d) < 5: continue
        m = sum(d) / len(d); sd = math.sqrt(sum((x - m) ** 2 for x in d) / max(1, len(d) - 1)); se = sd / math.sqrt(len(d))
        ref = [x[k] for D in by.values() for x in D.get('other', []) if x[k] is not None]
        print(f'  {k:22s} {m:+8.3f} ± {1.96 * se:.3f} (cells {len(d)}; vs-other mean {fl.mean(ref):.3f})')
