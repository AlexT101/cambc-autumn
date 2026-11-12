"""Paired subset read on fresh maps of the vp split against a base (same map, side, member). Usage: vpmech.py EXT_ROOT BASE ARM...
Split on/off per game is the bot's rule replicated (lateral value balance >= 0.5 on our half)."""
import sys, json, gzip, glob, os, re, collections, math
root, base, arms = sys.argv[1], sys.argv[2], sys.argv[3:]
BAL = float(os.environ.get('BAL', '0.5'))
def ctile(ts):
    mx = int(sum(p[0] for p in ts) / len(ts)); my = int(sum(p[1] for p in ts) / len(ts))
    return min(ts, key=lambda p: (p[0]-mx)**2 + (p[1]-my)**2)
def split_of(J, t):
    box = lambda s: [(x, y) for y in range(s['minY'], s['maxY']+1) for x in range(s['minX'], s['maxX']+1)]
    s = J['spawn'][t]; o = ctile(box(s)); e = ctile(box(J['spawn'][1-t]))
    dx, dy = e[0]-o[0], e[1]-o[1]; L = math.hypot(dx, dy)
    band = math.ceil((abs(dy)*(s['maxX']-s['minX']) + abs(dx)*(s['maxY']-s['minY']))/(2*L))
    def side(c):
        ox, oy, ex, ey = c[0]-o[0], c[1]-o[1], c[0]-e[0], c[1]-e[1]
        if ox*ox+oy*oy >= ex*ex+ey*ey: return 0
        off = (oy*dx - ox*dy)/L
        return 1 if off > band else -1 if off < -band else 0
    val = {1: 0, -1: 0}; gold = {1: 0, -1: 0}; gems = {1: 0, -1: 0}; sides = {}
    for q in J['groups']:
        if 'Monolith' in q.get('types', []): sides[q['id']] = 0; continue
        sd = side(ctile([tuple(p) for p in q['tiles']])); sides[q['id']] = sd
        if sd: val[sd] += q['gems'] + 0.3*q['gold']; gold[sd] += q['gold']; gems[sd] += q['gems']
    on = max(val.values()) > 0 and min(val.values()) >= BAL*max(val.values())
    v = (1 if gold[1] > gold[-1] else -1) if gold[1] != gold[-1] else (1 if gems[1] <= gems[-1] else -1)
    return on, {g: sd*v for g, sd in sides.items()}, o, (dx/L, dy/L)
def load(bot):
    out = {}
    for mp in glob.glob(f'{root}/{bot}/*/meta.json'):
        g = os.path.dirname(mp); m = json.load(open(mp))
        src = m['source']; k = re.search(r'-ab-vpsub-.*?-(fr8-g25|mf-c2)-', src).group(1); stem = os.path.basename(src).split('-', 1)[1]
        t = [i for i, x in enumerate(m['teams']) if x['name'] == bot][0]
        name = {c['id']: c['name'] for c in m['champions']}; team = {c['id']: c['team'] for c in m['champions']}
        ours = {name[c]: c for c in name if team[c] == t}
        comp = 'V+P' if {'Vesper Vale', 'Prism'} <= set(ours) else 'other'
        s = collections.Counter(); s['win'] = m['result']['winner'] == t
        if comp == 'V+P':
            J = json.load(open(os.path.normpath(os.path.join(g, m['mapFile']))))
            on, sides, o, u = split_of(J, t); comp += ' split' if on else ' nosplit'
            gm = {q['id']: q for q in J['groups']}
            for line in gzip.open(f'{g}/events.jsonl.gz', 'rt'):
                e = json.loads(line)
                if e['k'] != 'capture' or e['team'] != t: continue
                q = gm[e['g']]; tot = sum(x[2] for x in e['shares']) or 1
                for sh in e['shares']:
                    who = {'Vesper Vale': 'V', 'Prism': 'P'}.get(name[sh[0]], 'o')
                    for lim in (100, 200):
                        if e['r'] <= lim:
                            s[f'bgold{lim}_{who}'] += q['gold']*sh[2]/tot; s[f'caps{lim}_{who}'] += 1/len(e['shares'])
                            if lim == 200: s[f'gems200_{who}'] += sh[1]; s[f'ownside200_{who}'] += (sides.get(e['g'], 0) == (1 if who == 'V' else -1 if who == 'P' else 9))/len(e['shares'])
            rd = json.load(gzip.open(f'{g}/rounds.json.gz', 'rt')); cs = {c['id']: c for c in rd['champions']}; nR = len(rd['round'])
            for lim in (100, 200): s[f'earned{lim}'] = sum(cs[c]['earned'][min(lim, nR)-1] for c in ours.values())
            V, P = cs[ours['Vesper Vale']], cs[ours['Prism']]
            nx, ny = -u[1], u[0]; n = 0
            for r in range(20, min(200, nR)):
                if V['alive'][r] and P['alive'][r]:
                    n += 1; s['vpdist'] += max(abs(V['x'][r]-P['x'][r]), abs(V['y'][r]-P['y'][r]))
                    a = (V['x'][r]-o[0])*nx + (V['y'][r]-o[1])*ny; b = (P['x'][r]-o[0])*nx + (P['y'][r]-o[1])*ny
                    s['opp'] += a*b < 0 and abs(a) > 3 and abs(b) > 3
            if n: s['vpdist'] /= n; s['opp'] /= n
            for who, C in (('V', V), ('P', P)):
                s['steps_' + who] = sum(1 for r in range(1, min(200, nR)) if C['alive'][r] and C['alive'][r-1] and (C['x'][r], C['y'][r]) != (C['x'][r-1], C['y'][r-1]))
            for c in m['champions']:
                if c['team'] != t: continue
                s['collected'] += c['stats']['collectedGems']; s['submitted'] += c['stats']['submittedGems']; s['deaths'] += c['stats']['deaths']
                if c['name'] == 'Prism': s['P_sub'] += c['stats']['submittedGems']; s['P_deaths'] += c['stats']['deaths']
                if c['name'] == 'Vesper Vale': s['V_sub'] += c['stats']['submittedGems']; s['V_deaths'] += c['stats']['deaths']
        out[(k, stem)] = (comp, s)
    return out
B = load(base)
for arm in arms:
    A = load(arm)
    for comp in ('all', 'other', 'V+P split', 'V+P nosplit'):
        ks = [k for k in A if k in B and comp in ('all', B[k][0])]
        if not ks: continue
        n = len(ks); wa = sum(A[k][1]['win'] for k in ks); wb = sum(B[k][1]['win'] for k in ks); fl = sum(A[k][1]['win'] != B[k][1]['win'] for k in ks)
        d = [(A[k][1]['win'] - B[k][1]['win']) for k in ks]; sd = (sum(x*x for x in d)/n - (sum(d)/n)**2)**.5 / n**.5
        print(f'{arm} {comp}: {n} pairs, win {wa/n:.1%} vs {wb/n:.1%} ({(wa-wb)/n*100:+.1f} ±{sd*100:.1f}, flips {fl})')
        if not comp.startswith('V+P'): continue
        def avg(D, f): return sum(f(D[k][1]) for k in ks) / n
        def share(D, lim, who):
            tot = sum(D[k][1][f'bgold{lim}_{w}'] for k in ks for w in 'VPo') or 1
            return sum(D[k][1][f'bgold{lim}_{who}'] for k in ks) / tot
        for lim in (100, 200):
            print(f'   base gold r{lim}: {avg(B, lambda s: sum(s[f"bgold{lim}_"+w] for w in "VPo")):.0f} -> {avg(A, lambda s: sum(s[f"bgold{lim}_"+w] for w in "VPo")):.0f}; '
                  f'V/P/o share {share(B, lim, "V"):.0%}/{share(B, lim, "P"):.0%}/{share(B, lim, "o"):.0%} -> {share(A, lim, "V"):.0%}/{share(A, lim, "P"):.0%}/{share(A, lim, "o"):.0%}; '
                  f'earned {avg(B, lambda s: s[f"earned{lim}"]):.0f} -> {avg(A, lambda s: s[f"earned{lim}"]):.0f}')
        for lab, f in (('caps r200 V', lambda s: s['caps200_V']), ('caps r200 P', lambda s: s['caps200_P']), ('caps r200 other', lambda s: s['caps200_o']),
                       ('V caps on own side', lambda s: s['ownside200_V']), ('P caps on own side', lambda s: s['ownside200_P']),
                       ('capture gems r200 V', lambda s: s['gems200_V']), ('capture gems r200 P', lambda s: s['gems200_P']), ('capture gems r200 other', lambda s: s['gems200_o']),
                       ('team gems collected', lambda s: s['collected']), ('team gems submitted', lambda s: s['submitted']), ('P submitted', lambda s: s['P_sub']), ('V submitted', lambda s: s['V_sub']),
                       ('V-P distance r20-200', lambda s: s['vpdist']), ('V,P opposite sides', lambda s: s['opp']), ('V steps r200', lambda s: s['steps_V']), ('P steps r200', lambda s: s['steps_P']),
                       ('deaths', lambda s: s['deaths']), ('V deaths', lambda s: s['V_deaths']), ('P deaths', lambda s: s['P_deaths'])):
            print(f'   {lab}: {avg(B, f):.2f} -> {avg(A, f):.2f}')
