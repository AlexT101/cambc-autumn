import json
from collections import Counter
res = json.load(open('/tmp/mxi-study/retreats.json'))
F = {json.loads(l)['dir']: json.loads(l) for l in open('/tmp/mxi-study/farmwin.jsonl')}
N = len(res)
gap = sum(f['parts']['farm'] for f in F.values())
for team in 'WL':
    tot_all = tot_gw = 0
    n_all = n_gw = 0
    ex = []
    for g in res:
        sa, sg = {}, {}
        for x in g['rows']:
            if x['team'] != team or not x['start']: continue
            for rr, gg, gems in x['ecap']:
                sa[(rr, gg)] = gems
                if not x['before'] and x['en'] > 0 and x['al'] >= x['en']:
                    sg[(rr, gg)] = gems
        tot_all += sum(sa.values()); tot_gw += sum(sg.values()); n_all += len(sa); n_gw += len(sg)
        ex.append((sum(sg.values()), g['dir']))
    print(team, f'unique enemy captures within 8 / 20 rounds after a retreat start: {n_all/N:.2f}/game {tot_all/N:.1f} gems/game ({tot_all/gap:.0%} of gap); '
          f'after a give-way start (no hit in the 5 before, not outnumbered within 8): {n_gw/N:.2f}/game {tot_gw/N:.1f} gems/game ({tot_gw/gap:.0%})')
    if team == 'L':
        ex.sort(reverse=True)
        print('  top give-way games', ex[:8])
