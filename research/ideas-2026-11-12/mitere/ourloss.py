"""Our games against Mite r7: what differs in the games Mite wins."""
import fl, collections
G = fl.load(lambda g: g['vg'] == 'r7')
def stats(g):
    M = g['mite']; U = 1 - M
    d = {}
    ud = [x for x in g['deaths'] if x[9] == U]; md = [x for x in g['deaths'] if x[9] == M]
    d['our deaths'] = len([x for x in ud if g['name'][x[1]] != 'Issac'])
    d['Mite deaths'] = len([x for x in md if g['name'][x[1]] != 'Issac'])
    d['gems we lose to kills'] = sum(x[3] or 0 for x in ud if x[2] is not None)
    d['gems Mite loses to kills'] = sum(x[3] or 0 for x in md if x[2] is not None)
    d['our Prism deaths'] = sum(1 for x in ud if g['name'][x[1]] == 'Prism')
    d['gems our Prism loses'] = sum(x[3] or 0 for x in ud if g['name'][x[1]] == 'Prism')
    d['our deaths by r300'] = sum(1 for x in ud if x[0] <= 300 and g['name'][x[1]] != 'Issac')
    ut = [x for x in g['tribs'] if x[2] == U and x[3] >= 100]
    d['our 100+ tributes completed'] = sum(1 for x in ut if x[6] == 'end')
    d['our 100+ tributes stunned'] = sum(1 for x in ut if x[6] == 'stun')
    d['our 100+ tributes locked'] = sum(1 for x in ut if x[6] == 'lock')
    d['our 100+ tributes cancelled by us'] = sum(1 for x in ut if x[6] == 'manual')
    d['our 100+ tributes died'] = sum(1 for x in ut if x[6] == 'death')
    mt = [x for x in g['tribs'] if x[2] == M and x[3] >= 100]
    d['Mite 100+ tributes completed'] = sum(1 for x in mt if x[6] == 'end')
    d['Mite tributes completed (all)'] = sum(1 for x in g['tribs'] if x[2] == M and x[6] == 'end')
    for r in ('400', '600'):
        if r in g['ck']:
            d[f'earned gold r{r} (Mite-us)'] = g['ck'][r]['earned'][M] - g['ck'][r]['earned'][U]
            d[f'banked r{r} (Mite-us)'] = g['ck'][r]['gems'][M] - g['ck'][r]['gems'][U]
            d[f'our carry r{r}'] = g['ck'][r]['carry'][U]
    d['rounds'] = g['rounds']
    return d
W = [stats(g) for g in G if g['win']]; L = [stats(g) for g in G if not g['win']]
print(f'Mite wins {len(W)}, our wins {len(L)}')
for k in W[0]:
    print(f'  {k:38s} {fl.mean(x.get(k, 0) for x in W if k in x):8.2f} {fl.mean(x.get(k, 0) for x in L if k in x):8.2f}')
# by map class
c = collections.defaultdict(lambda: [0, 0])
for g in G:
    c[('alt', min(g['nalt'], 4))][0] += 1; c[('alt', min(g['nalt'], 4))][1] += g['win']
    mp = 'Prism' if 'Prism' in [g['name'][x] for x, t in g['team'].items() if t == g['mite']] else 'noPrism'
    c[('mitePrism', mp)][0] += 1; c[('mitePrism', mp)][1] += g['win']
    c[('picks', len(g['mpicks']))][0] += 1; c[('picks', len(g['mpicks']))][1] += g['win']
for k, v in sorted(c.items(), key=str): print(k, f'Mite wins {v[1]}/{v[0]} = {v[1]/v[0]:.2f}')
bym = collections.defaultdict(lambda: [0, 0])
for g in G: bym[g['map']][0] += 1; bym[g['map']][1] += g['win']
print('maps Mite wins most (n>=3):', ', '.join(f'{m} {v[1]}/{v[0]}' for m, v in sorted(bym.items(), key=lambda kv: -kv[1][1] / kv[1][0]) if v[0] >= 3 and v[1] / v[0] >= .75))
