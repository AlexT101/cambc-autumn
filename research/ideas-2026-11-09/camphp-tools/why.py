import json, sys, collections
L = [json.loads(l) for l in open(sys.argv[1])]
L = [x for x in L if x['created'] >= '2026-11-08' and x['r'] is not None]
US = 'stellar best girl'
def reason(x):
    if x['died']: return 'died'
    if x['hhp'] is not None and x['hhp'] < 0.35: return 'lowhp'
    if x['recalled']: return 'recall'
    if x['edist'] is not None and x['edist'] <= 6: return 'enemy<=6'
    if (x['hgems'] or 0) >= 60: return 'bag60+'
    return 'other'
for T in [US, 'Intercontinental Fish', 'Mite']:
    ab = [x for x in L if x['names'][x['by']] == T]
    ng = len(set(x['mid'] for x in L if T in x['names']))
    print(f"\n== {T}: {len(ab)} abandonments, {ng} games")
    for lo, hi in ((0, 3), (3, 8), (8, 20), (20, 1e9)):
        b = [x for x in ab if x['dps'] > 0 and lo <= x['left'] / x['dps'] < hi]
        rc = collections.Counter(reason(x) for x in b)
        st = sum(1 for x in b if x['cap'] and x['cap'][1] != x['by'])
        stv = sum(x['reward'][0] for x in b if x['cap'] and x['cap'][1] != x['by'])
        print(f"  ttf {lo}-{hi}: {len(b)/ng:5.2f}/game  stolen {100*st/max(1,len(b)):4.1f}% ({stv/ng:4.1f} gems/game)  " + ' '.join(f"{k}:{100*v/len(b):.0f}%" for k, v in rc.most_common()) if b else '')
    b = [x for x in ab if x['dps'] > 0 and x['left'] / x['dps'] < 3 and reason(x) == 'other']
    ty = collections.Counter(tuple(sorted(set(t for t, h in x['rem']))) for x in b)
    print('   ttf<3 other: remaining member types', ty.most_common(6))
    print('   ttf<3 other: hdist3 (hitter dist to group 3r later)', collections.Counter(min(x['hdist3'], 9) if x['hdist3'] is not None else None for x in b).most_common(8))
    print('   ttf<3 other: next', collections.Counter(('same' if x['next_team']==x['by'] else 'enemy' if x['next_team'] is not None else 'never') for x in b), 'median gap', sorted(x['resume']-x['r'] for x in b if x['resume'])[len(b)//2] if b else None)
