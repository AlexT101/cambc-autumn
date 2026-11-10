import json, sys, collections
L = [json.loads(l) for l in open(sys.argv[1])]
L = [x for x in L if x['created'] >= '2026-11-08']
US = 'stellar best girl'
for OPP in ['Intercontinental Fish', 'Mite']:
    G = [x for x in L if set(x['names']) == {US, OPP}]
    ng = len(set(x['mid'] for x in G))
    print(f"\n### us vs {OPP}: {ng} games")
    for who in (US, OPP):
        ab = [x for x in G if x['r'] is not None and x['names'][x['by']] == who]
        st = [x for x in ab if x['cap'] and x['cap'][1] != x['by']]
        low = [x for x in ab if x['frac'] < .5]
        stlow = [x for x in low if x['cap'] and x['cap'][1] != x['by']]
        val = sum(x['reward'][0] for x in st) / ng, sum(x['reward'][1] for x in st) / ng
        print(f"  {who:22s} abandons {len(ab)/ng:5.2f}/game (left<.5: {len(low)/ng:4.2f}); stolen by other {len(st)/ng:4.2f}/game ({len(stlow)/ng:4.2f} of left<.5) = {val[0]:5.1f} gems {val[1]:6.1f} gold /game")
        # reasons on low
        for nm, f in (('recalled', lambda x: x['recalled']), ('died', lambda x: x['died'])):
            print(f"      {nm}: all {sum(1 for x in ab if f(x))/max(1,len(ab)):.2f} low {sum(1 for x in low if f(x))/max(1,len(low)):.2f}  stolen-low {sum(1 for x in stlow if f(x))/max(1,len(stlow)):.2f}")
        tc = collections.Counter(tuple(sorted(set(x['types']))) for x in stlow)
        print('      stolen-low types', tc.most_common(6))
