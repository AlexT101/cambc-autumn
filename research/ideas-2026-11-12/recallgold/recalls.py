"""Recall and gold facts from extracted replays (tools/replay/extract.mjs --out DIR) of OUR bot against the rt bodies.

    python3 recalls.py EXTDIR [EXTDIR ...]

Per side (ours / body): kept recalls (channel left <= 3 when it ended or was cancelled) that landed or were cancelled
by an enemy champion's blow, with the victim's carried gold, lifetime earned gold and round; what a landed recall
went on to spend in the shop within 2 rounds; carried gold at death and at game end.
"""
import sys, os, json, gzip, collections, statistics as st
from multiprocessing import Pool


def one(d):
    try:
        meta = json.load(open(d + '/meta.json')); R = json.load(gzip.open(d + '/rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
    team = {c['id']: c['team'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; rounds = R['round']; idx = {r: i for i, r in enumerate(rounds)}
    side = lambda a: 'ours' if team[a] == us else 'body'
    at = lambda a, r, k: ch[a][k][idx.get(r, idx.get(r - 1, 0))]
    out = collections.defaultdict(list)
    prev = None; start = {}
    shops = collections.defaultdict(list)
    for e in ev:
        if e['k'] == 'shop': shops[e['a']].append((e['r'], -e.get('gold', 0)))
    for e in ev:
        k = e['k']
        if k == 'recall_start': start[e['a']] = e['r']
        elif k == 'recall_end':
            a = e['a']; r0 = start.get(a, e['r'])
            g = at(a, r0, 'gold'); spent = sum(x for (r, x) in shops[a] if e['r'] <= r <= e['r'] + 2)
            out[side(a) + '_land'].append((e['r'], g, at(a, r0, 'earned'), spent))
        elif k == 'recall_cancel' and e.get('cause') in ('damage', 'stun') and prev is not None and prev['s'] == e['s'] \
                and prev['k'] in ('attack', 'cast') and prev.get('a') in team and team[prev['a']] != team[e['a']]:
            a = e['a']
            out[side(a) + '_cut'].append((e['r'], at(a, e['r'], 'gold'), at(a, e['r'], 'earned'), e.get('left', -1), e.get('gems', 0)))
        elif k == 'death':
            a = e['v']; out[side(a) + '_death_gold'].append(at(a, e['r'] - 1, 'gold'))
        prev = e
    last = len(rounds) - 1
    for a in ch:
        out[side(a) + '_end_gold'].append(ch[a]['gold'][last])
        out[side(a) + '_end_earned'].append(ch[a]['earned'][last])
    return dict(out)


def q(xs):
    if not xs: return 'n=0'
    xs = sorted(xs); n = len(xs)
    return f'n={n} mean={sum(xs)/n:.1f} p25={xs[n//4]} med={xs[n//2]} p75={xs[3*n//4]} p90={xs[9*n//10]}'


def main():
    for root in sys.argv[1:]:
        dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
        with Pool(12) as pool: rows = [r for r in pool.map(one, dirs, chunksize=8) if r]
        T = collections.defaultdict(list)
        for r in rows:
            for k, v in r.items(): T[k] += v
        print(f'== {root}: {len(rows)} games')
        for s in ('body', 'ours'):
            cut = T[s + '_cut']; kept = [c for c in cut if c[3] <= 3]
            print(f' {s}: champion-cancelled recalls {len(cut)} ({len(cut)/len(rows):.2f}/game), kept (left<=3) {len(kept)} ({len(kept)/len(rows):.2f}/game)')
            print('   kept-cancel gold', q([c[1] for c in kept]))
            print('   kept-cancel earned', q([c[2] for c in kept]))
            print('   kept-cancel gold/earned', f'{sum(c[1] for c in kept)/max(1,sum(c[2] for c in kept)):.3f}')
            print('   kept-cancel round', q([c[0] for c in kept]))
            print('   all-cancel gold', q([c[1] for c in cut]))
            land = T[s + '_land']
            print(f'   landed recalls {len(land)} ({len(land)/len(rows):.2f}/game): gold', q([l[1] for l in land]), '| spent<=2r', q([l[3] for l in land]))
            print(f'   landed gold/earned {sum(l[1] for l in land)/max(1,sum(l[2] for l in land)):.3f}; share spending >=30: {sum(l[3]>=30 for l in land)/max(1,len(land)):.2f}')
            print('   death gold', q(T[s + '_death_gold']))
            print('   end gold', q(T[s + '_end_gold']), '| end earned', q(T[s + '_end_earned']))
        # gold by round bucket on landed body recalls and kept cuts
        for s in ('body',):
            for lo in (0, 300, 600, 1000, 1500):
                xs = [c for c in T[s + '_cut'] if c[3] <= 3 and lo <= c[0] < lo + (300 if lo < 600 else 400 if lo < 1000 else 500)]
                print(f'   {s} kept cuts r{lo}+: n={len(xs)} gold mean {sum(c[1] for c in xs)/max(1,len(xs)):.0f} earned mean {sum(c[2] for c in xs)/max(1,len(xs)):.0f}')


if __name__ == '__main__': main()
