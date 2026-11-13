"""scard.py EXT...: survival card of the candidate (team vfish*) per extract: deaths, kills, captures, gold by round; who dies to whom by r300."""
import json, gzip, os, sys, collections, statistics as st
def card(ext):
    idx = json.load(open(ext + '/index.json'))['games']
    A = collections.defaultdict(list); vict = collections.Counter(); kil = collections.Counter()
    for g in idx:
        cand = 0 if g['teams'][0].startswith('vfish') else 1
        p = f"{ext}/{g['dir']}"; meta = json.load(open(p + '/meta.json')); R = json.load(gzip.open(p + '/rounds.json.gz'))
        typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
        win = g['winner'] == cand; A['win'].append(win); n = len(R['round'])
        ev = [json.loads(l) for l in gzip.open(p + '/events.jsonl.gz', 'rt')]
        d = {0: [], 1: []}; caps = {0: [], 1: []}; capgold = {0: [], 1: []}
        for e in ev:
            if e['k'] == 'death' and 'linked' not in e:
                side = 0 if team[e['v']] == cand else 1; d[side].append(e['r'])
                if side == 0 and e['r'] <= 300:
                    by = e.get('by'); vict[typ[e['v']]] += 1; kil[typ[by] if by in typ and team[by] != cand else 'camp'] += 1
            elif e['k'] == 'capture':
                side = 0 if e['team'] == cand else 1; caps[side].append(e['r']); capgold[side].append((e['r'], sum(s[2] for s in e['shares']), sum(s[1] for s in e['shares'])))
        for rr in (100, 200, 300, 450, 600):
            if n < rr: continue
            for k in ('', 'W' if win else 'L'):
                A[f'cd{rr}{k}'].append(sum(1 for x in d[0] if x <= rr)); A[f'rd{rr}{k}'].append(sum(1 for x in d[1] if x <= rr))
                A[f'cc{rr}{k}'].append(sum(1 for x in caps[0] if x <= rr)); A[f'rc{rr}{k}'].append(sum(1 for x in caps[1] if x <= rr))
                A[f'cg{rr}{k}'].append(sum(x[2] for x in capgold[0] if x[0] <= rr)); A[f'rg{rr}{k}'].append(sum(x[2] for x in capgold[1] if x[0] <= rr))
        ves = [c for c in R['champions'] if typ[c['id']] == 'Vesper Vale' and c['team'] == cand]
        if ves and n >= 300: A['vg300'].append(ves[0]['earned'][299])
    m = lambda k: (sum(A[k]) / len(A[k]) if A[k] else float('nan'))
    print(f"== {os.path.basename(ext)}: games {len(A['win'])} win {m('win'):.3f}  Vesper gold r300 {m('vg300'):.0f}")
    for k, lab in (('', 'all'), ('W', 'wins'), ('L', 'losses')):
        print(f"  {lab:6}: our deaths r100/200/300/450 " + ' / '.join(f"{m(f'cd{rr}{k}'):.2f}" for rr in (100, 200, 300, 450))
              + " | their deaths " + ' / '.join(f"{m(f'rd{rr}{k}'):.2f}" for rr in (100, 200, 300, 450))
              + " | our captures r100/300 " + ' / '.join(f"{m(f'cc{rr}{k}'):.1f}" for rr in (100, 300)) + " theirs " + ' / '.join(f"{m(f'rc{rr}{k}'):.1f}" for rr in (100, 300))
              + " | capture gems r300 ours " + f"{m(f'cg300{k}'):.0f} theirs {m(f'rg300{k}'):.0f}")
    tot = sum(vict.values()); print('  victims r<=300:', ', '.join(f'{a} {b / tot:.2f}' for a, b in vict.most_common(7)), '| killers:', ', '.join(f'{a} {b / tot:.2f}' for a, b in kil.most_common(7)))
for x in sys.argv[1:]: card(x)
