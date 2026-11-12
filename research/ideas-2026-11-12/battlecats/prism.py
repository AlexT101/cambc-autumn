"""BattleCats' Prism bank: bag over time, the big tribute (when, where, guarded, outcome), and what stops it."""
import bl, collections, sys, fl as F
lim = int(sys.argv[1]) if len(sys.argv) > 1 else 10**9
ck = [100, 200, 300, 400, 500, 600, 800, 1000]
bag = collections.defaultdict(list); rows = []; nogames = 0; n = 0
for g in bl.games(filt=lambda g: g['ver'] == 'cur', limit=lim):
    names = {c['id']: c['name'] for c in g['meta']['champions']}
    pr = [c for c in g['rd']['champions'] if c['team'] == g['bc'] and names[c['id']] == 'Prism']
    if not pr: continue
    n += 1; p = pr[0]; R = len(p['gems'])
    for r in ck:
        if r <= R: bag[r].append(p['gems'][r - 1] if p['alive'][r - 1] else -1)
    C = g['rd']['champions']; en = [c for c in C if c['team'] != g['bc']]; al = [c for c in C if c['team'] == g['bc'] and c is not p]
    trib = [e for e in g['ev'] if e['k'] == 'tribute_start' and e['a'] == p['id']]
    ends = {}
    for e in g['ev']:
        if e['k'] in ('tribute_end', 'tribute_cancel') and e['a'] == p['id']: ends.setdefault(e['r'], e)
    if not trib: nogames += 1
    for t in trib:
        r = t['r']; i = r - 1
        end = next((ends[x] for x in sorted(ends) if x >= r), None)
        dE = min([max(abs(e['x'][i] - p['x'][i]), abs(e['y'][i] - p['y'][i])) for e in en if e['alive'][i] and e['x'][i] is not None] or [99])
        nA = sum(1 for a in al if a['alive'][i] and max(abs(a['x'][i] - p['x'][i]), abs(a['y'][i] - p['y'][i])) <= 3)
        tot = g['rd']['gems'][g['bc']][i - 1] if i > 0 else 0
        rows.append(dict(r=r, gems=t['gems'], dur=t['dur'], dE=dE, nA=nA, banked=tot, need=1000 - tot,
                         out=(end['k'].split('_')[1] + ('/' + end.get('cause', '') if end['k'] == 'tribute_cancel' else '')) if end else 'none',
                         win=g['win'], oc=F.oppclass(g['opp'])))
print(n, 'cur games with BC Prism;', nogames, 'with no Prism tribute')
print('Prism bag at round (median, p75; -1 = dead):', {r: (F.med(v), sorted(v)[int(.75 * (len(v) - 1))]) for r, v in bag.items()})
big = [x for x in rows if x['gems'] >= 100]
print(f'Prism tributes {len(rows)}; 100+ gems {len(big)}')
for lo, hi in ((100, 300), (300, 600), (600, 5000)):
    S = [x for x in big if lo <= x['gems'] < hi]
    if not S: continue
    oc = collections.Counter(x['out'] for x in S)
    print(f' bag {lo}-{hi}: n={len(S)} start round median {F.med([x["r"] for x in S])}, channel turns median {F.med([x["dur"] for x in S])}, '
          f'banked before median {F.med([x["banked"] for x in S])}, bag >= gems still needed {F.pct(sum(x["gems"] >= x["need"] for x in S), len(S))}, '
          f'nearest enemy median {F.med([x["dE"] for x in S])}, allies within 3 median {F.med([x["nA"] for x in S])}; outcome {dict(oc)}; BC wins {F.pct(sum(1 for x in S if x["win"]), len(S))}')
for oc in ('us', 'other', 'Fish', 'Mite'):
    S = [x for x in big if x['oc'] == oc]
    if S: print(f'  vs {oc}: {len(S)} big Prism tributes, completed {F.pct(sum(x["out"] == "end" for x in S), len(S))}, outcomes {dict(collections.Counter(x["out"] for x in S))}')
