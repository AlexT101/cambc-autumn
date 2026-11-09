#!/usr/bin/env python3
"""Parse cg_instrument.py traces (CG / CGO lines) from debug batches of CAND (bot 1) against REF (bot 2).

usage: cg_parse.py BATCH_DIR [BATCH_DIR ...]
Prints OOF turns by checkpoint and phase per bot, the chase builds and their callers, and the hazard (share of
turns that ran out) by the fuel left after chase_aim, with and without an aim build."""
import sys, glob, zipfile
from collections import Counter, defaultdict

AIM = {4, 5}


def rows(out):
    for l in out.replace('\x00', '').splitlines():
        if l.startswith('CG ') or l.startswith('CGO '):
            p = l.split()
            try:
                n = int(p[10])
                b = [tuple(map(int, x.split(':'))) for x in p[11:11 + n]]
                yield dict(oof=p[0] == 'CGO', round=int(p[1]), ck=int(p[3]), branch=int(p[4]), aim=int(p[5]),
                           aim_end=int(p[6]), search_end=int(p[7]), prey=int(p[8]), last=p[9], b=b,
                           gated=int(p[11 + n]), gated_at=int(p[12 + n]))
            except (IndexError, ValueError):
                continue  # cut by the stdout cap


games = Counter()
oof = {1: Counter(), 2: Counter()}
oof_phase = {1: Counter(), 2: Counter()}
ck_turns = {1: Counter(), 2: Counter()}
builds = Counter()
build_cost = defaultdict(list)
oof_with_build = Counter()
# hazard at the fuel left after chase_aim: [turns, oof] by (bot, built-in-aim, bucket)
haz = defaultdict(lambda: [0, 0])
# hazard by fuel left after a prey build (last build of the turn, callers 1-3 / 11-13)
haz_prey = defaultdict(lambda: [0, 0])
gated = Counter()
oof_branch = {1: Counter(), 2: Counter()}
for d in sys.argv[1:]:
    for f in glob.glob(f'{d}/*.repl26a'):
        order = f.rsplit('-', 1)[1][:2]
        try:
            z = zipfile.ZipFile(f)
        except zipfile.BadZipFile:
            continue
        for team in 'ab':
            bot = 1 if (team == 'a') == (order == '12') else 2
            games[bot] += 1
            out = z.read(f'team-{team}.stdout').decode(errors='replace')
            for r in rows(out):
                aim_b = [x for x in r['b'] if x[0] in AIM]
                prey_b = [x for x in r['b'] if x[0] not in AIM]
                if r['oof']:
                    oof[bot][r['ck']] += 1
                    oof_phase[bot][r['last']] += 1
                    oof_branch[bot][r['branch']] += 1
                    if r['b']:
                        oof_with_build[(bot, 'aim' if aim_b else 'prey', r['ck'])] += 1
                    elif r['gated']:
                        oof_with_build[(bot, 'gated', r['ck'])] += 1
                for c, at, cost in r['b']:
                    builds[(bot, c)] += 1
                    build_cost[c].append(cost)
                if r['gated']:
                    gated[bot] += 1
                if r['aim_end']:
                    key = (bot, bool(aim_b), r['aim_end'] // 2000 * 2)
                    haz[key][0] += 1
                    haz[key][1] += r['oof'] and r['ck'] >= 3
                if prey_b:
                    c, at, cost = prey_b[-1]
                    x = (at - cost) // 2000 * 2
                    haz_prey[(bot, x)][0] += 1
                    haz_prey[(bot, x)][1] += r['oof'] and r['ck'] >= 6

g = games[1]
print(f'team-games: CAND {games[1]}, REF {games[2]}')
print('OOF turns (traced) by last checkpoint, per 100 team-games:')
for k in sorted(set(oof[1]) | set(oof[2])):
    print(f'  ck {k:2d}: CAND {100 * oof[1][k] / games[1]:7.1f}  REF {100 * oof[2][k] / games[2]:7.1f}')
print(f'  all  : CAND {100 * sum(oof[1].values()) / games[1]:7.1f}  REF {100 * sum(oof[2].values()) / games[2]:7.1f}')
print('OOF by phase per 100 team-games:')
for k in sorted(set(oof_phase[1]) | set(oof_phase[2])):
    print(f'  {k:20s} CAND {100 * oof_phase[1][k] / games[1]:7.1f}  REF {100 * oof_phase[2][k] / games[2]:7.1f}')
print('OOF by branch per 100 team-games:')
for k in sorted(set(oof_branch[1]) | set(oof_branch[2])):
    print(f'  {k:3d} CAND {100 * oof_branch[1][k] / games[1]:7.1f}  REF {100 * oof_branch[2][k] / games[2]:7.1f}')
print('CAND OOF turns with a chase build (or gated ask), by kind and checkpoint, per 100 team-games:')
for k, v in sorted(oof_with_build.items()):
    if k[0] == 1: print(f'  {k[1]:6s} ck {k[2]:2d}: {100 * v / g:6.1f}')
print('CAND chase builds per team-game by caller, mean cost:')
for (bot, c), v in sorted(builds.items()):
    if bot == 1:
        cs = sorted(build_cost[c])
        print(f'  caller {c:2d}: {v / g:6.2f}  mean {sum(cs) / len(cs):7.0f}  p90 {cs[len(cs) * 9 // 10]}')
print(f'CAND gated asks per team-game: {gated[1] / g:.2f}')
print('Hazard of running out after chase_aim, by fuel left after it (k): turns, OOF % ; CAND with aim build | CAND none | REF')
for x in range(0, 100, 2):
    cells = []
    for key in ((1, True, x), (1, False, x), (2, False, x)):
        t, o = haz[key]
        cells.append(f'{t:7d} {100 * o / t:6.2f}%' if t else ' ' * 15)
    if any(haz[k][0] for k in ((1, True, x), (1, False, x), (2, False, x))):
        print(f'  {x:3d}-{x + 2:<3d} ' + ' | '.join(cells))
print('Hazard after a prey build by fuel left after it (CAND): turns, OOF %')
for x in range(0, 100, 2):
    t, o = haz_prey[(1, x)]
    if t: print(f'  {x:3d}-{x + 2:<3d} {t:7d} {100 * o / t:6.2f}%')
