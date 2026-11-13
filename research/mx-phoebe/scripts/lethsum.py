"""Summary of lethal.py output: per team name, exposures per game, next-turn death rates, causes.

usage: lethsum.py OUT.json [--detail]
"""
import json, sys
from collections import Counter, defaultdict

res = json.load(open(sys.argv[1]))
detail = '--detail' in sys.argv
teams = sorted({n for g in res for n in g['name']})
for tn in teams:
    games = [(g, g['name'].index(tn)) for g in res if tn in g['name']]
    if len(set(g['name'][0] for g, _ in games)) == 1 and len(teams) == 1: pass
    ng = sum(1 if g['name'][0] != g['name'][1] else 2 for g, _ in games)
    recs = [r for g, _ in games for r in g['recs'] if r['name'] == tn]
    L = [r for r in recs if r['lethal']]
    nl = [r for r in recs if not r['lethal']]
    def rate(xs): return f"{len(xs)/ng:.2f}/g died {sum(r['died'] for r in xs)} ({100*sum(r['died'] for r in xs)/max(1,len(xs)):.1f}%)"
    print(f"== {tn}: {ng} team-games")
    print('  lethal all  ', rate(L))
    print('  lethal pre  ', rate([r for r in L if r['pre']]))
    print('  nonlethal<=5', rate(nl))
    for cls in ('C&I', 'Prism', 'other'):
        f = (lambda r: r['x'] in ('Cassi', 'Issac')) if cls == 'C&I' else (lambda r: r['x'] == 'Prism') if cls == 'Prism' else (lambda r: r['x'] not in ('Cassi', 'Issac', 'Prism'))
        print(f'  {cls:6} lethal', rate([r for r in L if f(r)]), ' pre', rate([r for r in L if f(r) and r['pre']]))
    # deaths per game
    dc = Counter()
    for g, _ in games:
        for t in (0, 1):
            if g['name'][t] != tn: continue
            for d in g['deaths']:
                if d['team'] == t and not d['linked']:
                    dc['C&I' if d['v'] in ('Cassi', 'Issac') else d['v'] if d['v'] == 'Prism' else 'other'] += 1
    print('  deaths/g', {k: round(v / ng, 2) for k, v in sorted(dc.items())})
    gems = sum(g['gems'][str(t)] if str(t) in g['gems'] else g['gems'][t] for g, _ in games for t in (0, 1) if g['name'][t] == tn)
    print(f'  capture gems/team-game {gems/ng:.0f}')
    wins = sum(1 for g, _ in games for t in (0, 1) if g['name'][t] == tn and g['winner'] == t)
    print(f'  win {100*wins/ng:.1f}%')
    if detail:
        print('  causes (lethal, pre-first-kill):')
        P = [r for r in L if r['pre'] or '--all' in sys.argv]
        def key(r):
            how = 'walked-in' if r['walked_in'] else ('P-in' if r['p_in'] else 'stayed')
            return how
        for k, v in Counter(key(r) for r in P).most_common():
            sub = [r for r in P if key(r) == k]
            print(f'    {k:10} {len(sub):5} died {sum(r["died"] for r in sub):4}  branches', Counter(r['br'] for r in sub).most_common(8))
        print('    kind', Counter(r['kind'] for r in P).most_common(), ' died', Counter(r['kind'] for r in P if r['died']).most_common())
        print('    seen', Counter(r['seen'] for r in P).most_common(), ' died', Counter(r['seen'] for r in P if r['died']).most_common())
        print('    d', sorted(Counter(r['d'] for r in P).items()), ' died', sorted(Counter(r['d'] for r in P if r['died']).items()))
        print('    moved(stayed)', Counter(r['moved'] for r in P if not r['walked_in']).most_common())
        print('    killers', Counter(r['killer'] for r in P if r['died']).most_common())
        print('    branch died', Counter(r['br'] for r in P if r['died']).most_common(10))
