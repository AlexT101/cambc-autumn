import json, sys, collections
for f in sys.argv[1:]:
    L = [json.loads(l) for l in open(f)]
    us = L[0]['names'][0] if not L[0]['names'][0].startswith('spar') else L[0]['names'][1]
    ng = len(set(x['mid'] for x in L))
    side = lambda x: x['names'].index(us)
    ab = [x for x in L if x['r'] is not None and x['by'] == side(x)]
    eab = [x for x in L if x['r'] is not None and x['by'] != side(x)]
    nf = [x for x in ab if x['dps'] > 0 and x['left'] / x['dps'] < 3]
    stolen = [x for x in ab if x['cap'] and x['cap'][1] != x['by']]
    steal = [x for x in eab if x['cap'] and x['cap'][1] == side(x)]
    caps = [x for x in L if x['cap'] and x['cap'][1] == side(x)]
    ecaps = [x for x in L if x['cap'] and x['cap'][1] != side(x)]
    g = lambda S, i: sum(x['reward'][i] for x in S) / ng
    print(f"{us:16s} games {ng}  abandon {len(ab)/ng:.2f}  near-fin {len(nf)/ng:.3f}  stolen-from-us {len(stolen)/ng:.3f} ({g(stolen,0):.1f} gems {g(stolen,1):.0f} gold)  we-steal {len(steal)/ng:.3f} ({g(steal,0):.1f} gems)  captures: us {len(caps)/ng:.1f} ({g(caps,0):.0f} gems {g(caps,1):.0f} gold) them {len(ecaps)/ng:.1f} ({g(ecaps,0):.0f} gems {g(ecaps,1):.0f} gold)")
