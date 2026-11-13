"""Compact per-round trace of the 40 rounds before an early first Prism death, for reading.
    py research/mx-tethys/scripts/prism_trace.py ROWS.jsonl SRC [SRC ...]
"""
import gzip, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import prism_mech as pm

AB = {'Ryth': 'Ry', 'Vesper Vale': 'Ve', 'Prism': 'Pr', 'Stellar': 'St', 'Vendetta': 'Vd', 'Marcella': 'Ma', 'Tavi': 'Ta',
      'Willow': 'Wi', 'Ren': 'Rn', 'Varg': 'Va', 'Heart of Ruin': 'Ho', 'Cassi': 'Ca', 'Issac': 'Is'}
rows = {json.loads(l)['src']: json.loads(l) for l in open(sys.argv[1])}
for src in sys.argv[2:]:
    x = rows[src]; dd = pm.WT / 'replays/.analysis' / x['dir']
    m = json.loads((dd / 'meta.json').read_text())
    mp = json.loads((dd / m['mapFile']).resolve().read_text())
    R = json.load(gzip.open(dd / 'rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
    names = {c['id']: AB.get(c['name'], c['name'][:2]) for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    v, t, D = x['v'], x['vteam'], x['D']
    rix = {r: i for i, r in enumerate(R['round'])}; C = {c['id']: c for c in R['champions']}
    import zipfile, re
    z = zipfile.ZipFile(pm.WT / m['source']); br = {}
    for nm in ('team-a.stdout', 'team-b.stdout'):
        for r, cid, b, g, cl in pm.D_RE.findall(z.read(nm)): br[(int(r), int(cid))] = b.decode() + (g.decode() if g != b'-1' else '')
    home = pm.walkfield(mp, mp['spawn'][t]); ehome = pm.walkfield(mp, mp['spawn'][1 - t])
    print(f"=== {src} W{mp['width']} D={D} victim Prism#{v} team{t} killer {x['killer']} assists {x['assists']} bag {x['bag']} "
          f"winner {x['winner']} | own {x['picks']} | enemy {x['epicks']}")
    stunev = {}
    for e in ev:
        if D - 40 <= e['r'] <= D and v in (e.get('stun') or []): stunev.setdefault(e['r'], []).append(names[e['a']])
    dmg = {}
    for e in ev:
        if D - 40 <= e['r'] <= D and e['k'] in ('attack', 'cast'):
            for tid, a in e.get('dmg') or []:
                if tid == v: dmg.setdefault(e['r'], []).append(f"{names[e['a']]}{int(a)}")
            for tid, a in e.get('cdmg') or []:
                pass
        if D - 40 <= e['r'] <= D and e['k'] == 'camp_attack' and e.get('tgt') == v: dmg.setdefault(e['r'], []).append(f"camp{e['dmg']}")
    out = {}
    for e in ev:
        if D - 40 <= e['r'] <= D and e['k'] in ('attack', 'cast') and e.get('a') == v:
            tg = [f"{names[t_]}{int(a)}" for t_, a in e.get('dmg') or []] + [f"stun{names[t_]}" for t_ in e.get('stun') or []]
            if e.get('cdmg'): tg.append('camp')
            out.setdefault(e['r'], []).append(f"{e.get('ab', 'atk')}:{'/'.join(tg)}")
    lastkey = None
    for r in range(max(1, D - 40), D + 1):
        i = rix.get(r)
        if i is None or not C[v]['alive'][i]: 
            print(f"r{r} dead"); continue
        vp = (C[v]['x'][i], C[v]['y'][i])
        def d(c):
            if not C[c]['alive'][i] or C[c]['x'][i] is None: return 'x'
            return pm.cheb(vp, (C[c]['x'][i], C[c]['y'][i]))
        al = ' '.join(f"{names[c]}{d(c)}{br.get((r, c), '?')}" for c in sorted(C) if team[c] == t and c != v)
        en = ' '.join(f"{names[c]}{d(c)}{'*' if c in (C[v]['sees'][i] or []) else ''}" for c in sorted(C) if team[c] != t)
        st = 'STUNNED ' if C[v]['turn'][i] == 5 else ''
        ch = ''
        key = (br.get((r, v)), tuple(sorted(C[v]['sees'][i] or [])), round(C[v]['hp'][i]/C[v]['maxHp'][i], 2))
        if key == lastkey and r not in stunev and r not in dmg and r not in out and st == '' and r < D - 3: continue
        lastkey = key
        print(f"r{r} ({vp[0]},{vp[1]}) h{home[vp[0]][vp[1]]}/e{ehome[vp[0]][vp[1]]} hp{C[v]['hp'][i]/C[v]['maxHp'][i]:.2f} g{C[v]['gems'][i]} f{int(C[v]['foc'][i])} "
              f"{br.get((r, v), '?')} {st}{ch} | al {al} | en {en}"
              + (f" | stun<-{stunev[r]}" if r in stunev else '') + (f" | dmg {dmg[r]}" if r in dmg else '') + (f" | OUT {out[r]}" if r in out else ''))
    print()
