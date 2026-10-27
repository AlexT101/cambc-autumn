"""Per-state audit over a batch of instrument.py's copy (python3 audit.py replays/BATCH): does running a state strictly bring us closer to its own goal set,
and does the next turn keep that goal set? Plus every A->B->A cycle by cause."""
import sys, glob, zipfile, json, collections
batch = sys.argv[1]
res = json.load(open(batch + "/results.json"))
moves = collections.defaultdict(collections.Counter)
nexts = collections.defaultdict(collections.Counter)
cycles = collections.Counter(); cyc_rounds = collections.Counter(); ex = collections.defaultdict(list)
games = 0
for m in res['matches']:
    ours = 'team-a' if m['order'] == [0, 1] else 'team-b'
    try: z = zipfile.ZipFile(m['replay'])
    except Exception: continue
    names = z.namelist()
    if ours + '.stdout' not in names: continue
    games += 1
    T = {}
    for line in z.read(ours + '.stdout').decode('latin1').replace('\0', '').splitlines():
        p = line.split()
        if len(p) not in (10, 11) or p[0] != 'AUD': continue
        try:
            r, i = int(p[1]), int(p[2])
            T[(i, r)] = dict(s=p[3], fr=tuple(map(int, p[4].split(','))), to=tuple(map(int, p[5].split(','))), d0=int(p[6]), d1=int(p[7]), n=int(p[8]), h=int(p[9]))
        except ValueError: pass
    mapname = m['map'].split('/')[-1].replace('.map26a', '')
    for (i, r), a in T.items():
        s = a['s']; moved = a['fr'] != a['to']
        if moved:
            if a['d0'] == -3: moves[s]['moved, no goal call'] += 1
            elif a['d0'] < 0 or a['d1'] < 0: moves[s]['moved, goals unreachable/empty'] += 1
            elif a['d1'] < a['d0']: moves[s]['closer'] += 1
            elif a['d1'] == a['d0']: moves[s]['same distance'] += 1
            else: moves[s]['FARTHER'] += 1
        else:
            moves[s]['stayed' + (' (at goal)' if a['d0'] == 0 else ' (goal call, no move)' if a['d0'] > 0 else '')] += 1
        b = T.get((i, r + 1))
        if b and moved and a['n'] > 0:
            if b['s'] != s: nexts[s]['next turn: other state ' + b['s']] += 1
            elif b['n'] == 0: nexts[s]['next turn: same state, no goal call'] += 1
            elif b['h'] == a['h']: nexts[s]['next turn: same goals'] += 1
            else: nexts[s]['next turn: GOALS CHANGED'] += 1
        c = T.get((i, r + 2))
        if b and c and moved and b['fr'] == a['to'] and c['fr'] == a['fr'] and b['to'] == a['fr']:
            if b['s'] != s: k = f'state swap {s}/{b["s"]}'
            elif a['n'] == 0 or b['n'] == 0: k = f'{s}: a move with no goal call'
            elif a['h'] != b['h']: k = f'{s}: goals changed'
            else:
                k = f'{s}: same goals, ' + ('first move not closer' if a['d1'] >= a['d0'] else 'second move not closer' if b['d1'] >= b['d0'] else 'both closer (walls/units moved)')
            cycles[k] += 1
            if len(ex[k]) < 4: ex[k].append((mapname, i, r, a['fr'], a['to'], (a['d0'], a['d1']), (b['d0'], b['d1'])))
print('games', games)
print('\n== each state\'s moves, judged by static distance to its own goal set')
for s, c in sorted(moves.items(), key=lambda kv: -sum(kv[1].values())):
    tot = sum(v for k, v in c.items() if not k.startswith('stayed'))
    print(f'{s:9} moves {tot:6}', ', '.join(f'{k} {v} ({100*v/max(1,tot):.1f}%)' if not k.startswith('stayed') else f'{k} {v}' for k, v in c.most_common()))
print('\n== after a move with goals, the next turn')
for s, c in sorted(nexts.items(), key=lambda kv: -sum(kv[1].values())):
    tot = sum(c.values())
    print(f'{s:9} {tot:6}', ', '.join(f'{k} {v} ({100*v/tot:.1f}%)' for k, v in c.most_common(6)))
print('\n== A->B->A cycles (each counted at its first turn)', sum(cycles.values()))
for k, v in cycles.most_common(25): print(f'{v:6} {k}')
print()
for k, es in sorted(ex.items(), key=lambda kv: -cycles[kv[0]])[:12]:
    for e in es[:2]: print('   ex', k, e)
