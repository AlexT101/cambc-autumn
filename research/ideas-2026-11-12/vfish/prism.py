"""The reference's Prism against the candidate (bot 1): its bag over time, its tributes (size, length, who of ours was near,
how they ended), its kills and deaths, and Vesper-Prism proximity."""
import json, gzip, os, sys, collections, statistics as st
ext = sys.argv[1]; idx = json.load(open(ext + '/index.json'))['games']
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
A = collections.defaultdict(list)
for g in idx:
    mid = os.path.basename(g['source'])[:-8]; cand = 0 if mid.endswith('-12') else 1
    p = f"{ext}/{g['dir']}"; meta = json.load(open(p + '/meta.json')); R = json.load(gzip.open(p + '/rounds.json.gz'))
    typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    ch = R['champions']; n = len(R['round'])
    P = [c for c in ch if c['team'] != cand and typ[c['id']] == 'Prism']
    if not P: continue
    ev = [json.loads(l) for l in gzip.open(p + '/events.jsonl.gz', 'rt')]
    P = P[0]; pid = P['id']; V = [c for c in ch if c['team'] == cand and typ[c['id']] == 'Vesper Vale'][0]
    ours = [c for c in ch if c['team'] == cand]
    w = meta['result'].get('winner') if isinstance(meta.get('result'), dict) else meta.get('winner')
    k = 'W' if w == cand else 'L'; A['n' + k].append(1)
    for rr in (100, 200, 300, 450, 600, 750):
        if rr <= n:
            A[f'bag{rr}{k}'].append(P['gems'][rr - 1]); A[f'foc{rr}{k}'].append(P['foc'][rr - 1]); A[f'php{rr}{k}'].append(P['maxHp'][rr - 1])
            A[f'vstr{rr}{k}'].append(V['str'][rr - 1]); A[f'vhp{rr}{k}'].append(V['maxHp'][rr - 1])
    # tributes by the Prism
    starts = {}
    for e in ev:
        if e['k'] == 'tribute_start' and e['a'] == pid: starts = {'r': e['r'], 'gems': e['gems'], 'dur': e['dur'], 'at': e['at']}
        elif e['k'] in ('tribute_end', 'tribute_cancel') and e['a'] == pid and starts:
            big = starts['gems'] >= 100
            if big:
                near = []; vnear = 0
                for i in range(starts['r'] - 1, min(e['r'], n)):
                    near.append(sum(1 for c in ours if c['alive'][i] and c['x'][i] is not None and cheb((c['x'][i], c['y'][i]), starts['at']) <= 8))
                    vnear += V['alive'][i] and V['x'][i] is not None and cheb((V['x'][i], V['y'][i]), starts['at']) <= 8
                A['trib_gems' + k].append(starts['gems']); A['trib_len' + k].append(e['r'] - starts['r']); A['trib_round' + k].append(starts['r'])
                A['trib_done' + k].append(e['k'] == 'tribute_end'); A['trib_near' + k].append(max(near) if near else 0); A['trib_vnear' + k].append(vnear > 0)
                if e['k'] == 'tribute_cancel': A['cancel_cause' + k].append(e.get('cause'))
            starts = {}
    pk = [e for e in ev if e['k'] == 'death' and e.get('by') == pid and team[e['v']] == cand and 'linked' not in e]
    A['pkills' + k].append(len(pk)); A['pkill_gems' + k].append(sum(e.get('gems', 0) for e in pk))
    for e in pk: A['pk_victim'].append(typ[e['v']]); A['pk_round'].append(e['r']); A['pk_cause'].append(e.get('cause'))
    pd = [e for e in ev if e['k'] == 'death' and e['v'] == pid]
    A['pdeaths' + k].append(len(pd))
    for e in pd: A['pd_round'].append(e['r']); A['pd_bag'].append(e.get('gems', 0)); A['pd_by'].append(typ.get(e.get('by'), 'camp'))
    # Vesper within 6 of Prism: rounds, and damage exchanged in those windows
    close = sum(1 for i in range(n) if V['alive'][i] and P['alive'][i] and V['x'][i] is not None and P['x'][i] is not None and cheb((V['x'][i], V['y'][i]), (P['x'][i], P['y'][i])) <= 6)
    A['vclose' + k].append(close)
    vhits = sum(1 for e in ev if e['k'] in ('attack',) and e['a'] == V['id'] and e.get('tgt') == pid or (e['k'] == 'attack' and e['a'] == V['id'] and any(d[0] == pid for d in e.get('dmg', []))))
    phits = sum(1 for e in ev if e['k'] in ('attack', 'cast') and e['a'] == pid and (e.get('tgt') == V['id'] or any(d[0] == V['id'] for d in e.get('dmg', []))))
    A['vhits' + k].append(vhits); A['phits' + k].append(phits)
m = lambda k: (sum(A[k]) / len(A[k]) if A[k] else float('nan'))
for k in 'WL':
    print(f"== {k}: {len(A['n'+k])} games with a ref Prism")
    for rr in (100, 200, 300, 450, 600, 750): print(f"   r{rr}: Prism bag {m(f'bag{rr}{k}'):.0f} Focus {m(f'foc{rr}{k}'):.0f} maxhp {m(f'php{rr}{k}'):.0f} | our Vesper str {m(f'vstr{rr}{k}'):.0f} hp {m(f'vhp{rr}{k}'):.0f}  n={len(A[f'bag{rr}{k}'])}")
    print(f"   Prism kills of ours {m('pkills'+k):.2f} (gems taken {m('pkill_gems'+k):.0f}); Prism deaths {m('pdeaths'+k):.2f}")
    print(f"   Prism tributes of 100+: {len(A['trib_gems'+k]) / max(1, len(A['n'+k])):.2f} a game, median {st.median(A['trib_gems'+k]) if A['trib_gems'+k] else 0} gems at r{st.median(A['trib_round'+k]) if A['trib_round'+k] else 0}, {m('trib_len'+k):.1f} rounds; completed {m('trib_done'+k):.2f}; any of ours within 8 during it {sum(1 for x in A['trib_near'+k] if x > 0) / max(1, len(A['trib_near'+k])):.2f} (Vesper {m('trib_vnear'+k):.2f}); cancel causes {dict(collections.Counter(A['cancel_cause'+k]))}")
    print(f"   rounds Vesper within 6 of Prism {m('vclose'+k):.1f}; Vesper attacks on Prism {m('vhits'+k):.2f}; Prism hits on Vesper {m('phits'+k):.2f}")
print('Prism kill victims:', collections.Counter(A['pk_victim']).most_common(8), 'median round', st.median(A['pk_round']), 'causes', collections.Counter(A['pk_cause']).most_common(4))
print('Prism deaths: n', len(A['pd_round']), 'median round', st.median(A['pd_round']) if A['pd_round'] else None, 'median bag', st.median(A['pd_bag']) if A['pd_bag'] else None, 'by', collections.Counter(A['pd_by']).most_common(5))
q = sorted(A['pk_round']); print('Prism kill rounds quartiles', q[len(q)//4], q[len(q)//2], q[3*len(q)//4])
