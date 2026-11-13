"""Q2: each game's first Prism death to a champion, the 20 rounds before (pd_rows.pkl); Q3: branch at Prism contact onsets."""
import pickle
from collections import Counter

G = pickle.load(open('research/mx-rhea/scripts/pd_rows.pkl', 'rb'))
D = [g for g in G if g['death']]
def pct(a, b): return f'{a}/{b} ({100 * a / b:.1f}%)' if b else f'{a}/0'
def rate(sel, f): return pct(sum(1 for x in sel if f(x)), len(sel))
TRIB = set('Tt'); HOLD = set('PQ'); ALTAR = set('WUB'); AGGR = set('CAGX'); RET = set('Rr')

rows = []
for g in D:
    d = g['death']; w = d['win']
    pre = w[-21:-1]  # the 20 rounds before the death round
    last = [x for x in pre if x['b'] not in '-?']
    lb = last[-1]['b'] if last else '?'
    last5 = ''.join(x['b'] for x in pre[-5:])
    # onset: start of the contiguous stretch with the enemy Prism within 6 that ends at the death (searched over 40 rounds)
    on = None
    if w[-1]['dist'] is not None and w[-1]['dist'] <= 6:
        k = len(w) - 1
        while k > 0 and w[k - 1]['dist'] is not None and w[k - 1]['dist'] <= 6: k -= 1
        on = w[k]
    else:
        # nearest-in-time contact within 6 over the 20 rounds, if any
        c = [x for x in pre if x['dist'] is not None and x['dist'] <= 6]
        on = c[0] if c else None
    ref = on or pre[-1]
    stronger = ref['fV'] >= ref['fE']
    stunned = any(x['stun'] or x['stunev'] for x in pre[-5:]) or w[-1]['stunev']
    trib = any(x['b'] in TRIB or x['chan'] == 2 for x in pre[-5:])
    hold = any(x['b'] in HOLD for x in pre[-5:])
    altar = any(x['b'] in ALTAR for x in pre[-5:])
    aggr = any(x['b'] in AGGR for x in pre[-10:])
    ret5 = sum(1 for x in pre[-5:] if x['b'] in RET)
    en, al = pre[-1]['en'], pre[-1]['al']
    mind = min((x['dist'] for x in pre if x['dist'] is not None), default=None)
    # who closed the distance: victim's own path distance to spawn rising over the last 10 rounds = victim walked away from home
    dsp = [x['dsp'] for x in pre[-10:] if x['dsp'] is not None]
    outbound = len(dsp) >= 2 and dsp[-1] > dsp[0]
    rows.append(dict(g=g, d=d, lb=lb, last5=last5, on=on, onb=on['b'] if on else None, stronger=stronger, stunned=stunned,
                     trib=trib, hold=hold, altar=altar, aggr=aggr, ret5=ret5, en=en, al=al, mind=mind, outbound=outbound,
                     ratio=ref['fE'] / ref['fV'], hp_on=ref['hp'], dsp=pre[-1]['dsp'], first_r=None))

def classify(x):
    d = x['d']
    if x['trib']: return '1 caught tributing'
    if x['hold']: return '2 caught holding a capture'
    if x['altar']: return '3 at/going to altar (bank/wait/guard)'
    if not d['byPrism'] and (x['mind'] is None or x['mind'] > 8): return '4 ganked with enemy Prism absent'
    if x['aggr'] and x['en'] >= 3: return '5 chased into enemies (C/A/G/X, 3+ enemies within 8)'
    if not x['stronger'] and x['onb'] in ('F', 'C', 'A', 'G', 'X', 'E', 'H', 'S'): return '6 weaker Prism met stronger while farming/chasing'
    if x['stronger']: return '7 stronger Prism lost (numbers/hp)'
    if x['ret5'] >= 3: return '8 weaker, caught retreating'
    return '9 other'

print('first Prism deaths to a champion:', len(D), 'of', len(G), 'games with both Prisms; victim team lost', rate(D, lambda g: not g['death']['vwin']))
print('killer:', Counter(g['death']['killer_type'] for g in D).most_common(6))
print('round: <200', sum(g['death']['rd'] < 200 for g in D), ' 200-399', sum(200 <= g['death']['rd'] < 400 for g in D), ' >=400', sum(g['death']['rd'] >= 400 for g in D))
print('victim stronger (Focus >= enemy Prism\'s at onset/last round):', rate(rows, lambda x: x['stronger']))
print('  stronger & killed by Prism', rate([x for x in rows if x['stronger']], lambda x: x['d']['byPrism']), ' weaker & by Prism', rate([x for x in rows if not x['stronger']], lambda x: x['d']['byPrism']))
print('enemy Focus / victim Focus (at onset):', Counter('<0.8' if r < .8 else '0.8-1' if r < 1 else '1-1.2' if r < 1.2 else '1.2-2' if r < 2 else '2+' for r in (x['ratio'] for x in rows)))
print('stunned in last 5 rounds:', rate(rows, lambda x: x['stunned']))
print('branch in last 20 rounds (share of rounds):')
c = Counter(b['b'] for x in rows for b in x['d']['win'][-21:-1]); t = sum(c.values())
print('  ', ' '.join(f'{k}:{100 * v / t:.1f}' for k, v in c.most_common(12)))
print('last branch before death:', Counter(x['lb'] for x in rows).most_common(10))
print('branch at onset (enemy Prism first within 6):', Counter(x['onb'] for x in rows).most_common(12))
print('enemies within 8 at last round:', sorted(Counter(min(x['en'], 5) for x in rows).items()), ' allies:', sorted(Counter(min(x['al'], 5) for x in rows).items()))
print('en - al at last round:', sorted(Counter(max(-3, min(3, x['en'] - x['al'])) for x in rows).items()))
print('min distance to enemy Prism in 20 rounds:', sorted(Counter('none' if x['mind'] is None else min(x['mind'], 9) for x in rows).items(), key=str))
print('victim moving away from home over last 10 rounds:', rate(rows, lambda x: x['outbound']))
print('distance trajectory (median dist to enemy Prism by rounds before death):')
import statistics
for k in (20, 15, 10, 5, 3, 1):
    v = [x['d']['win'][-1 - k]['dist'] for x in rows if len(x['d']['win']) > k and x['d']['win'][-1 - k]['dist'] is not None]
    print(f'  t-{k}: median {statistics.median(v)}  within 6: {sum(1 for a in v if a <= 6)}/{len(v)}')
print('\nclasses:')
cl = Counter(classify(x) for x in rows)
for k in sorted(cl):
    sel = [x for x in rows if classify(x) == k]
    print(f'  {k:55s} {cl[k]:4d} ({100 * cl[k] / len(rows):.1f}%)  byPrism {rate(sel, lambda x: x["d"]["byPrism"])}  stronger {rate(sel, lambda x: x["stronger"])}  stunned {rate(sel, lambda x: x["stunned"])}  r>=400 {rate(sel, lambda x: x["d"]["rd"] >= 400)}  onset {Counter(x["onb"] for x in sel).most_common(3)}')
pickle.dump([(x['g']['dir'], x['d']['rd'], classify(x)) for x in rows], open('research/mx-rhea/scripts/pd_classes.pkl', 'wb'))

# Q3: branch at contact onsets, winner vs loser Prism
print('\nQ3 contact onsets (both Prisms alive, distance drops to <= 6):')
for lab, sel in (('all onsets', lambda g, o: True), ('onsets before the first Prism death', lambda g, o: not g['death'] or o['r'] <= g['death']['rd'])):
    W = Counter(); L = Counter(); n = 0
    for g in G:
        for o in g['onsets']:
            if not sel(g, o): continue
            n += 1; W[o['b'][g['winner']]] += 1; L[o['b'][1 - g['winner']]] += 1
    print(f'  {lab}: n={n}')
    print('    winner Prism:', ' '.join(f'{k}:{100 * v / n:.1f}' for k, v in W.most_common(9)))
    print('    loser  Prism:', ' '.join(f'{k}:{100 * v / n:.1f}' for k, v in L.most_common(9)))
# the killer's branch at the fatal onset
kb = Counter(x['on']['be'] for x in rows if x['on']); vb = Counter(x['on']['b'] for x in rows if x['on'])
n = sum(kb.values())
print(f'  fatal onset (first Prism death), n={n}: enemy Prism', ' '.join(f'{k}:{100 * v / n:.1f}' for k, v in kb.most_common(8)))
print('                               victim     ', ' '.join(f'{k}:{100 * v / n:.1f}' for k, v in vb.most_common(8)))
# onset death rates by the branch each side had
print('  P(that Prism dies within 20 | its branch at onset), all onsets before first death:')
B = Counter(); Dd = Counter()
for g in G:
    for o in g['onsets']:
        if g['death'] and o['r'] > g['death']['rd']: continue
        for t in (0, 1):
            weaker = o['f'][t] < o['f'][1 - t]
            B[(o['b'][t], weaker)] += 1; Dd[(o['b'][t], weaker)] += o['died'][t]
for b in 'FRCPTBEU':
    print(f'    {b}: stronger {pct(Dd[(b, False)], B[(b, False)])}   weaker {pct(Dd[(b, True)], B[(b, True)])}')
