"""Our ranked games against Fish since 11-12 09:00Z, matched to our pinned Fish r8 scrims on the same map/side cell.

Usage: python3 ranked_vs_scrim.py RANKEDFISH.csv GAMES.jsonl
Versions active (sched.log): v118 11:21-11:50, v115 11:50-12:51, v118 12:51-13:27, v115 13:27-~14:10 (PAUSE at 14:09:
"live v115 selected, expected v118"), v118 from ~14:10, v117 15:14-16:10, v118 16:10-23:32, v119 23:32-23:38,
v118 23:38-00:33, v119 00:33-00:40, v118 after. The platform takes ~5 min to switch, so the picks decide.
"""
import csv, json, sys, collections

PICKS = ['Ryth', 'Vesper Vale', 'Vendetta', 'Cassi & Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg',
         'Tavi', 'Heart of Ruin']
US = '547efb5b-57e5-4355-8501-3b331f506d62'
TIMELINE = [('2026-11-12T09', 115), ('2026-11-12T11:21', 118), ('2026-11-12T11:50', 115), ('2026-11-12T12:51', 118),
            ('2026-11-12T13:27', 115), ('2026-11-12T14:10', 118), ('2026-11-12T15:14', 117), ('2026-11-12T16:10', 118),
            ('2026-11-12T23:32', 119), ('2026-11-12T23:38', 118), ('2026-11-13T00:33', 119), ('2026-11-13T00:40', 118)]


def sched_version(t):
    v = None
    for s, ver in TIMELINE:
        if t >= s:
            v = ver
    return v


ranked = []
for r in csv.DictReader(open(sys.argv[1])):
    side = 'a' if r['team_a'] == US else 'b'
    ours = json.loads(r['picks_a'] if side == 'a' else r['picks_b'])
    theirs = json.loads(r['picks_b'] if side == 'a' else r['picks_a'])
    win = (r['result_a'] == 'win') == (side == 'a')
    ranked.append(dict(t=r['created_at'], map=r['map'], side=side, win=win, ours=[PICKS[i] for i in ours],
                       theirs=[PICKS[i] for i in theirs], sched=sched_version(r['created_at'])))

scrim = collections.defaultdict(dict)  # version -> (map, side) -> record (Fish r8 pin)
for l in open(sys.argv[2]):
    g = json.loads(l)
    if g.get('opp_name') != 'Intercontinental Fish' or g.get('refset') != 'r8' or g.get('status') != 'finished':
        continue
    scrim[g['version']][(g['map'], g['side'])] = g

ranked.sort(key=lambda x: x['t'])
rows = []
for g in ranked:
    cell = (g['map'], g['side'])
    match = []
    for v, cells in scrim.items():
        s = cells.get(cell)
        if s and s['our_picks'] == g['ours']:
            match.append(v)
    s118 = scrim.get(118, {}).get(cell)
    rows.append(dict(g, pick_match=match, in118=s118 is not None,
                     s118_win=(s118['result'] == 'win') if s118 else None,
                     s118_theirs_same=(s118['opp_picks'] == g['theirs']) if s118 else None))

print('time              map              side sched  win  picks-match  v118-cell: win  Fish picks same')
for x in rows:
    print(f"{x['t'][5:16]}  {x['map'][:16]:16s} {x['side']}    v{x['sched']}  {int(x['win'])}    {str(x['pick_match']):12s} "
          f"{'' if x['s118_win'] is None else int(x['s118_win'])!s:4s}  {x['s118_theirs_same']}")


def summ(sel, label):
    n = len(sel)
    w = sum(x['win'] for x in sel)
    c = [x for x in sel if x['in118']]
    cw = sum(x['s118_win'] for x in c)
    agree = sum(x['win'] == x['s118_win'] for x in c)
    print(f'{label:46s} ranked {w}/{n} = {w / max(n, 1):.2f}   in v118 r8 cells {len(c)}: scrim wins there {cw}/{len(c)} = '
          f'{cw / max(len(c), 1):.2f}, outcome agrees {agree}/{len(c)}')


print()
summ(rows, 'all ranked vs Fish since 09:00Z')
summ([x for x in rows if x['t'] >= '2026-11-12T12'], 'since 12:00Z')
for v in (115, 117, 118, 119):
    summ([x for x in rows if x['sched'] == v], f'scheduler says v{v}')
v118 = [x for x in rows if 118 in x['pick_match']]
summ(v118, 'picks equal v118 scrim picks on the cell')
summ([x for x in v118 if x['s118_theirs_same']], '  ... and Fish picks equal too')
summ([x for x in rows if x['sched'] == 118 and 118 not in x['pick_match']], 'scheduler v118 but picks differ')
