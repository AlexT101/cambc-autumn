"""scard2.py EXT...: whole-game deaths by killer class, kills, Prism tributes, length."""
import json, gzip, os, sys, collections, statistics as st
def card(ext):
    idx = json.load(open(ext + '/index.json'))['games']
    A = collections.defaultdict(list)
    for g in idx:
        cand = 0 if g['teams'][0].startswith('vfish') else 1
        p = f"{ext}/{g['dir']}"; meta = json.load(open(p + '/meta.json'))
        typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
        win = g['winner'] == cand; A['win'].append(win); A['rounds'].append(g['rounds'])
        pr = [i for i in typ if typ[i] == 'Prism' and team[i] != cand]
        d = collections.Counter(); pt = 0; ptg = 0; pstart = 0
        for l in gzip.open(p + '/events.jsonl.gz', 'rt'):
            if '"death"' in l:
                e = json.loads(l)
                if e['k'] != 'death' or 'linked' in e: continue
                by = e.get('by')
                if team[e['v']] == cand:
                    d['ours'] += 1; d['ours_prism' if by in pr else 'ours_camp' if (by not in typ or team.get(by) == cand) else 'ours_other'] += 1
                    if typ[e['v']] == 'Vesper Vale': d['ours_vesper'] += 1
                    d['ours_gems'] += e.get('gems', 0)
                else:
                    d['theirs'] += 1
                    if e['v'] in pr: d['theirs_prism'] += 1; d['prism_bag'] += e.get('gems', 0)
            elif '"tribute_' in l and pr:
                e = json.loads(l)
                if e.get('a') in pr:
                    if e['k'] == 'tribute_end' and e.get('gems', 0) >= 100: pt += 1; ptg += e['gems']
                    elif e['k'] == 'tribute_start' and e.get('gems', 0) >= 100: pstart += 1
        for k in ('ours', 'ours_prism', 'ours_camp', 'ours_other', 'ours_vesper', 'theirs', 'theirs_prism', 'ours_gems', 'prism_bag'): A[k].append(d[k])
        if pr: A['pt'].append(pt); A['ptg'].append(ptg); A['pstart'].append(pstart)
    m = lambda k: (sum(A[k]) / len(A[k]) if A[k] else float('nan'))
    print(f"== {os.path.basename(ext)}: games {len(A['win'])} win {m('win'):.3f} median rounds {st.median(A['rounds'])}")
    print(f"   our deaths a game {m('ours'):.2f}: to the Prism {m('ours_prism'):.2f}, camps {m('ours_camp'):.2f}, other champions {m('ours_other'):.2f}; Vesper's {m('ours_vesper'):.2f}; gems lost {m('ours_gems'):.0f}")
    print(f"   their deaths {m('theirs'):.2f}: Prism's {m('theirs_prism'):.2f} (bag taken {m('prism_bag'):.0f}) | Prism tributes of 100+: started {m('pstart'):.2f} completed {m('pt'):.2f} ({m('ptg'):.0f} gems)")
for x in sys.argv[1:]: card(x)
