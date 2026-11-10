import sys, json, collections
D = [json.loads(l) for l in open(sys.argv[1])]
print('deaths', len(D))
def bins(g): return '0' if g == 0 else '1-49' if g < 50 else '50-149' if g < 150 else '150+'
C = collections.defaultdict(list)
for d in D: C[bins(d['gems'])].append(d)
for b in ['0', '1-49', '50-149', '150+']:
    X = C[b]
    if not X: continue
    # turns spent alive below line L before death; and whether those turns had an enemy within 4
    res = []
    for L in (0.3, 0.45, 0.6, 0.75):
        t = [sum(1 for s in d['T'] if s['hp'] < L) for d in X]
        res.append(f"L{L}: >=1 {sum(x>=1 for x in t)/len(X):.2f} >=2 {sum(x>=2 for x in t)/len(X):.2f}")
    # last-turn hp: one-shot share (hp at r-1 >= .8)
    one = sum(1 for d in X if d['T'] and d['T'][0]['hp'] >= .8) / len(X)
    last_abs = sorted(d['T'][0]['hpabs'] for d in X if d['T'])
    # the final round's damage relative to maxhp
    print(f"gems {b:7} n {len(X):3}  hp(r-1)>=.8 {one:.2f}  hp(r-1) median abs {last_abs[len(last_abs)//2]}  " + ' | '.join(res))
# turn-before-death: did the Prism move toward spawn (sd shrink) on the turns while below 0.45?
fl = collections.Counter()
for d in D:
    T = d['T']
    for a, b in zip(T[1:], T[:-1]):  # a: earlier (k+1), b: later (k)
        if a['hp'] < 0.45 and a['ne'] <= 5:
            fl['below,enemy<=5'] += 1
            fl['retreat' if b['sd'] < a['sd'] else 'same' if b['sd'] == a['sd'] else 'advance'] += 1
            fl['attacked/cast'] += bool(set(b['act']) & {'attack', 'cast'})
print(fl)
