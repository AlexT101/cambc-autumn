"""Do teammates out of sight come to a fight? Live v115 games against Fish and Mite (extract.mjs output).

    py live_converge.py ~/tmp-offload/comms2/live-ana ~/tmp-offload/comms2/live-index.json

An engagement starts when an enemy champion damages X after 10 rounds with no champion damage to or by X. For each
living teammate Y then 10-25 tiles from X (beyond the sight radius of 8) that sees no enemy itself: how much nearer to
X's tile Y is 8 rounds later (post), against how much nearer it got over the 8 rounds before (pre). A team that calls
help through its shared bytes shows post well above pre; one that does not shows the same drift both sides.
Also, per team: allies within 5 of X at the start and 8 rounds on, and whether X survives 15 rounds.
"""
import collections, gzip, json, os, sys

def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

def game(d, who, T):
    R = json.load(gzip.open(d + '/rounds.json.gz'))
    rounds = R['round']; ri = {r: i for i, r in enumerate(rounds)}
    champs = R['champions']; team = {c['id']: c['team'] for c in champs}
    def pos(c, r):
        i = ri.get(r)
        return (c['x'][i], c['y'][i]) if i is not None and c['alive'][i] else None
    hits = collections.defaultdict(list)  # champion -> rounds it dealt or took champion damage
    first = []                            # (round, victim) of enemy champion damage
    deaths = collections.defaultdict(list)
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] in ('attack', 'cast') and 'dmg' in e and 'a' in e and e['a'] in team:
            for v, _ in e['dmg']:
                if v in team and team[v] != team[e['a']]:
                    first.append((e['r'], v)); hits[v].append(e['r']); hits[e['a']].append(e['r'])
        elif e['k'] == 'death': deaths[e['v']].append(e['r'])
    byid = {c['id']: c for c in champs}
    last = {}
    for r, v in sorted(first):
        quiet = all(not (r - 10 <= h < r) for h in hits[v])
        if not quiet or last.get(v, -99) >= r - 10: continue
        last[v] = r
        X = byid[v]; px = pos(X, r)
        if px is None or r < 20: continue
        t = who[team[v]]
        T[t, 'fights'] += 1
        T[t, 'victim-dies15'] += any(r <= dr <= r + 15 for dr in deaths[v])
        near0 = near8 = 0
        for Y in champs:
            if Y['team'] != team[v] or Y['id'] == v: continue
            p0, pm, p8 = pos(Y, r), pos(Y, r - 8), pos(Y, r + 8)
            if p0 is None: continue
            near0 += cheb(p0, px) <= 5
            if p8 is not None: near8 += cheb(p8, px) <= 5
            i = ri[r]
            if not (10 <= cheb(p0, px) <= 25) or pm is None or p8 is None: continue
            if any(team.get(s) != team[v] for s in (Y['sees'][i] or [])): continue  # busy with its own enemy
            if any(r - 10 <= h <= r for h in hits[Y['id']]): continue
            T[t, 'far'] += 1
            pre, post = cheb(pm, px) - cheb(p0, px), cheb(p0, px) - cheb(p8, px)
            T[t, 'pre'] += pre; T[t, 'post'] += post
            T[t, 'pre4'] += pre >= 4; T[t, 'post4'] += post >= 4
        T[t, 'near0'] += near0; T[t, 'near8'] += near8

if __name__ == '__main__':
    root, index = sys.argv[1], json.load(open(sys.argv[2]))
    T = collections.Counter()
    for d in sorted(os.listdir(root)):
        m = os.path.join(root, d, 'meta.json')
        if not os.path.exists(m): continue
        name = json.load(open(m))['map']['name']
        g = index.get(name)
        if not g: continue
        ours = 0 if g['side'] == 'a' else 1
        who = {ours: 'ocean vs ' + g['opp'], 1 - ours: g['opp']}
        game(os.path.join(root, d), who, T); T['games', g['opp']] += 1
    print({k[1]: v for k, v in T.items() if k[0] == 'games'})
    print('| team | engagements | far teammates | nearer over 8 rounds before | after | 4+ nearer before | after | allies within 5 at start | 8 rounds on | victim dead within 15 |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for t in sorted({k[0] for k in T if k[0] != 'games'}):
        f, n = T[t, 'fights'], max(1, T[t, 'far'])
        print(f'| {t} | {f} | {T[t, "far"]} | {T[t, "pre"] / n:+.2f} | {T[t, "post"] / n:+.2f} | {100 * T[t, "pre4"] / n:.1f}% | {100 * T[t, "post4"] / n:.1f}% |'
              f' {T[t, "near0"] / f:.2f} | {T[t, "near8"] / f:.2f} | {100 * T[t, "victim-dies15"] / f:.1f}% |')
