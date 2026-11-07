"""(1) How often ocean's cooked gate (enemy tributed >= 400 and >= 150 ahead, off under 100) fires for us.
(2) From the first time we trail by 150+ (total gems, before round 1000), the next 200 rounds of behaviour,
comebacks against losses. usage: behind.py SET.json..."""
import json, sys
import numpy as np
for path in sys.argv[1:]:
    games = json.load(open(path))
    fired, fired_win, frac_rounds, first = 0, 0, [], []
    rows = {0: [], 1: []}
    for g in games:
        on, n_on = False, 0
        for s in g['samples']:
            gap = s['tthem'] - s['tus']
            on = (gap >= 100) if on else (s['tthem'] >= 400 and gap >= 150)
            n_on += on
            if on and n_on == 1: first.append(s['r'])
        if n_on:
            fired += 1; fired_win += g['win']; frac_rounds.append(n_on / len(g['samples']))
        c = next((s for s in g['samples'] if 100 <= s['r'] < 1000 and s['lead'] <= -150), None)
        if not c: continue
        r0 = c['r']
        nxt = [s for s in g['samples'] if r0 <= s['r'] < r0 + 200]
        b = [s['beh'][0] for s in nxt if s['beh'][0]]; t = [s['beh'][1] for s in nxt if s['beh'][1]]
        ud = [x for x in g['deaths'] if x['us'] and r0 <= x['r'] < r0 + 200]
        td = [x for x in g['deaths'] if not x['us'] and r0 <= x['r'] < r0 + 200]
        rows[g['win']].append((r0, c['lead'], c['gold'], 100 * np.mean([x['far'] for x in b]), np.mean([x['nn'] for x in b if x['nn'] is not None] or [np.nan]),
                               np.mean([x['bag'] for x in b]), np.mean([x['maxbag'] for x in b]), 100 * np.mean([x['far'] for x in t]),
                               len(ud), sum(x['home'] for x in ud), sum(x['gems'] for x in ud), len(td), sum(x['gems'] for x in td)))
    print(f'\n## {path}: cooked fires in {fired}/{len(games)} games ({100*fired/len(games):.0f}%), we win {100*fired_win/max(1,fired):.1f}% of those; '
          f'on for {100*np.mean(frac_rounds):.0f}% of their rounds; first fires at round {np.median(first):.0f} (median)')
    print(f'  first trail by 150+ before round 1000, next 200 rounds (means):')
    print(f'  {"":9}{"n":>4}{"round":>7}{"lead":>6}{"gold":>6}{"far%":>6}{"nn":>5}{"bags":>6}{"maxbag":>7}{"their far%":>11}{"ourD":>6}{"home":>6}{"gemsLost":>9}{"theirD":>7}{"gemsTaken":>10}')
    for w, name in ((1, 'comeback'), (0, 'lost')):
        if rows[w]:
            m = np.nanmean(rows[w], axis=0)
            print(f'  {name:9}{len(rows[w]):4}{m[0]:7.0f}{m[1]:6.0f}{m[2]:6.0f}{m[3]:6.1f}{m[4]:5.1f}{m[5]:6.0f}{m[6]:7.0f}{m[7]:11.1f}{m[8]:6.2f}{m[9]:6.2f}{m[10]:9.0f}{m[11]:7.2f}{m[12]:10.0f}')
