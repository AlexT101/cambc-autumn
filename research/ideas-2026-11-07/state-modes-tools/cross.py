"""At the first sample (r >= 100) with lead >= T: the lead's make-up and the next 200 rounds, by outcome.
usage: cross.py T SET.json..."""
import json, sys
import numpy as np

T = int(sys.argv[1])
for path in sys.argv[2:]:
    games = json.load(open(path))
    out = {0: [], 1: []}
    first_deaths = {0: [], 1: []}
    for g in games:
        ss = [s for s in g['samples'] if s['r'] >= 100]
        c = next((s for s in ss if s['lead'] >= T), None)
        if not c:
            continue
        r0 = c['r']
        later = [s for s in ss if r0 < s['r'] <= r0 + 200]
        dl = (later[-1]['lead'] - c['lead']) if later else 0
        ud = [x for x in g['deaths'] if x['us'] and r0 < x['r'] <= r0 + 200]
        td = [x for x in g['deaths'] if not x['us'] and r0 < x['r'] <= r0 + 200]
        carried = c['lead'] - c['trib']
        ourbag = c['beh'][0]['bag'] if c['beh'][0] else 0
        out[g['win']].append((r0, c['lead'], c['trib'], ourbag, c['gold'], len(ud), sum(x['gems'] >= 20 for x in ud), len(td), dl,
                              g['last'] - r0, c['tus'], c['tthem']))
        for x in [x for x in g['deaths'] if x['us'] and x['r'] > r0][:3]:
            first_deaths[g['win']].append(x)
    n = len(out[0]) + len(out[1])
    print(f'\n## {path}: lead >= {T} first reached in {n} games; lost {len(out[0])} ({100*len(out[0])/max(1,n):.1f}%)')
    print(f'{"":6}{"n":>4}{"round":>7}{"lead":>6}{"trib":>6}{"ourbag":>7}{"gold":>7}{"ourD":>6}{"our20+":>7}{"theirD":>7}{"dLead":>7}{"left":>6}{"us trib":>8}{"them":>6}  (next 200 rounds)')
    for w in (0, 1):
        if out[w]:
            m = np.mean(out[w], axis=0)
            print(f'{"won" if w else "lost":6}{len(out[w]):4}' + ''.join(f'{x:{wd}.{p}f}' for x, wd, p in zip(m, [7, 6, 6, 7, 7, 6, 7, 7, 7, 6, 8, 6], [0, 0, 0, 0, 0, 2, 2, 2, 0, 0, 0, 0])))
    for w in (0, 1):
        fd = first_deaths[w]
        if fd:
            print(f'  first 3 deaths after, {"won" if w else "lost"}: n {len(fd)}, bag {np.mean([x["gems"] for x in fd]):.1f} (20+ {100*np.mean([x["gems"]>=20 for x in fd]):.0f}%, 50+ {100*np.mean([x["gems"]>=50 for x in fd]):.0f}%), '
                  f'home {100*np.mean([x["home"] for x in fd]):.0f}%, alone {100*np.mean([x["near"]==0 for x in fd]):.0f}%, lead at death {np.mean([x["lead"] for x in fd]):.0f}')
