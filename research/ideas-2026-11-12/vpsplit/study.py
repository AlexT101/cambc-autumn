"""V+P games: map value split (lateral to the spawn axis) vs where Vesper and Prism go and who holds what.
Usage: study.py TEAM_SUBSTR EXT_DIR..."""
import sys, json, gzip, glob, os, collections, math
sub = sys.argv[1]
rows = []
for d in sys.argv[2:]:
    for mp in glob.glob(f'{d}/**/meta.json', recursive=True):
        g = os.path.dirname(mp); m = json.load(open(mp))
        ts = [i for i, t in enumerate(m['teams']) if sub in t['name']]
        if len(ts) != 1: continue
        t = ts[0]
        name = {c['id']: c['name'] for c in m['champions']}; team = {c['id']: c['team'] for c in m['champions']}
        ours = {name[c]: c for c in name if team[c] == t}
        if not {'Vesper Vale', 'Prism'} <= set(ours): continue
        J = json.load(open(os.path.normpath(os.path.join(g, m['mapFile']))))
        sp = J['spawn']; S = [((s['minX']+s['maxX'])/2, (s['minY']+s['maxY'])/2) for s in sp]
        o, e = S[t], S[1-t]
        ux, uy = e[0]-o[0], e[1]-o[1]; L = math.hypot(ux, uy); ux, uy = ux/L, uy/L; nx, ny = -uy, ux
        val = {}; side = {}; lat = {}
        lv = rv = cv = 0
        for q in J['groups']:
            cx = sum(p[0] for p in q['tiles'])/len(q['tiles']); cy = sum(p[1] for p in q['tiles'])/len(q['tiles'])
            dO = math.hypot(cx-o[0], cy-o[1]); dE = math.hypot(cx-e[0], cy-e[1])
            if 'Monolith' in q.get('types', []): continue
            if dO >= dE: continue
            v = q['gems'] + 0.3*q['gold']
            la = (cx-o[0])*nx + (cy-o[1])*ny
            lat[q['id']] = la; val[q['id']] = v
            if la > 3: rv += v
            elif la < -3: lv += v
            else: cv += v
        tot = lv + rv + cv
        bal = min(lv, rv)/tot if tot else 0
        rd = json.load(gzip.open(f'{g}/rounds.json.gz', 'rt'))
        cs = {c['id']: c for c in rd['champions']}
        V, P = cs[ours['Vesper Vale']], cs[ours['Prism']]
        nR = len(rd['round'])
        ds = []; vl = []; pl = []
        for r in range(20, min(200, nR)):
            if V['alive'][r] and P['alive'][r]:
                ds.append(max(abs(V['x'][r]-P['x'][r]), abs(V['y'][r]-P['y'][r])))
                vl.append((V['x'][r]-o[0])*nx + (V['y'][r]-o[1])*ny); pl.append((P['x'][r]-o[0])*nx + (P['y'][r]-o[1])*ny)
        # opposite lateral sides fraction
        opp = sum(1 for a, b in zip(vl, pl) if a*b < 0 and abs(a) > 3 and abs(b) > 3)/max(1, len(vl))
        gm = {q['id']: q for q in J['groups']}
        H = collections.Counter()
        for line in gzip.open(f'{g}/events.jsonl.gz', 'rt'):
            ev = json.loads(line)
            if ev['k'] != 'capture' or ev['team'] != t or ev['r'] > 200: continue
            q = gm[ev['g']]; tot_s = sum(s[2] for s in ev['shares']) or 1
            for s in ev['shares']:
                who = name[s[0]]; who = who if who in ('Vesper Vale', 'Prism') else 'other'
                H['gold_'+who] += q['gold']*s[2]/tot_s; H['gems_'+who] += s[1]
                H['caps_'+who] += 1/len(ev['shares'])
        rows.append(dict(map=m['map']['name'], bal=bal, tot=tot, dist=sum(ds)/max(1, len(ds)), opp=opp, win=m['result']['winner'] == t, H=H,
                         vgold=V['earned'][min(200, nR)-1], gems=sum(c['stats']['collectedGems'] for c in m['champions'] if c['team'] == t)))
print(len(rows), 'V+P games')
def summ(rs, lab):
    if not rs: return
    n = len(rs); f = lambda k: sum(r['H'][k] for r in rs)/n
    gt = f('gold_Vesper Vale')+f('gold_Prism')+f('gold_other')
    print(f'{lab}: n={n} win {sum(r["win"] for r in rs)/n:.1%} VPdist {sum(r["dist"] for r in rs)/n:.1f} oppsides {sum(r["opp"] for r in rs)/n:.0%} '
          f'base gold r200 {gt:.0f} V {f("gold_Vesper Vale")/gt:.0%} P {f("gold_Prism")/gt:.0%}; gems V/P/o {f("gems_Vesper Vale"):.0f}/{f("gems_Prism"):.0f}/{f("gems_other"):.0f}; '
          f'caps V/P/o {f("caps_Vesper Vale"):.1f}/{f("caps_Prism"):.1f}/{f("caps_other"):.1f}; gems collected {sum(r["gems"] for r in rs)/n:.0f}')
summ(rows, 'all')
for lo, hi in ((0, .1), (.1, .2), (.2, .3), (.3, .6)):
    summ([r for r in rows if lo <= r['bal'] < hi], f'balance {lo}-{hi}')
