"""Blown leads and comebacks: how the lead moved from its peak (trough) to the end, by source; deaths by lead.
usage: blown.py SET.json..."""
import json, sys
import numpy as np

for path in sys.argv[1:]:
    games = json.load(open(path))
    N = len(games); losses = sum(1 - g['win'] for g in games); wins = N - losses
    print(f'\n######## {path}: {N} games, {wins} won, {losses} lost')
    cats = {}
    for g in games:
        ss = [s for s in g['samples'] if s['r'] >= 100]
        if not ss:
            continue
        pk = max(ss, key=lambda s: s['lead']); tr = min(ss, key=lambda s: s['lead'])
        for thr in (100, 150, 300):
            if pk['lead'] >= thr:
                cats.setdefault(('ahead', thr, g['win']), []).append((g, pk))
            if tr['lead'] <= -thr:
                cats.setdefault(('behind', thr, g['win']), []).append((g, tr))
    for thr in (100, 150, 300):
        a_l = len(cats.get(('ahead', thr, 0), [])); a_w = len(cats.get(('ahead', thr, 1), []))
        b_l = len(cats.get(('behind', thr, 0), [])); b_w = len(cats.get(('behind', thr, 1), []))
        print(f'lead >= {thr} at some point (r>=100): {a_w+a_l} games, lost {a_l} ({100*a_l/max(1,a_w+a_l):.1f}%) = {100*a_l/max(1,losses):.1f}% of all losses')
        print(f'deficit >= {thr} at some point:        {b_w+b_l} games, won {b_w} ({100*b_w/max(1,b_w+b_l):.1f}%) = {100*b_w/max(1,wins):.1f}% of all wins')
    print('From the peak (blown/held) or trough (comeback/cooked) to the end, means a game, threshold 150:')
    print(f'{"":22}{"n":>5}{"dLead":>8}{"farm":>8}{"kills x2":>9}{"camp":>7}{"our d":>7}{"their d":>8}{"rounds":>7}{"at round":>9}{"lead":>6}')
    for name, key in [('blown (ahead, lost)', ('ahead', 150, 0)), ('held (ahead, won)', ('ahead', 150, 1)),
                      ('comeback (behind, won)', ('behind', 150, 1)), ('cooked (behind, lost)', ('behind', 150, 0))]:
        rows = []
        for g, s in cats.get(key, []):
            c0, c1 = s['cum'], g['final_cum']
            d = [b - a for a, b in zip(c0, c1)]
            farm = d[0] - d[1]; kill = 2 * (d[2] - d[3]); camp = d[5] - d[4]
            ud = sum(1 for x in g['deaths'] if x['us'] and x['r'] > s['r']); td = sum(1 for x in g['deaths'] if not x['us'] and x['r'] > s['r'])
            rows.append((farm + kill + camp, farm, kill, camp, ud, td, g['last'] - s['r'], s['r'], s['lead']))
        if rows:
            m = np.mean(rows, axis=0)
            print(f'{name:22}{len(rows):5}' + ''.join(f'{x:8.0f}' if i < 4 else f'{x:7.1f}' for i, x in enumerate(m[:6])) + f'{m[6]:7.0f}{m[7]:9.0f}{m[8]:6.0f}')
    # Deaths by our lead at the time.
    print('Deaths by lead at the time (per death): share at home, bag, camp kills, allies within 4')
    bins = [(-10**9, -150), (-150, -50), (-50, 50), (50, 150), (150, 10**9)]
    for who in (1, 0):
        for lo, hi in bins:
            ds = [x for g in games for x in g['deaths'] if x['us'] == who and lo <= x['lead'] < hi and x['r'] >= 50]
            if not ds: continue
            print(f'  {"our" if who else "their"} deaths, lead {lo:>6}..{hi:<6}: n {len(ds):4}, home {100*np.mean([x["home"] for x in ds]):4.0f}%, '
                  f'bag {np.mean([x["gems"] for x in ds]):5.1f} (20+: {100*np.mean([x["gems"]>=20 for x in ds]):3.0f}%), camp {100*np.mean([x["camp"] for x in ds]):3.0f}%, '
                  f'alone {100*np.mean([x["near"]==0 for x in ds]):3.0f}%')
