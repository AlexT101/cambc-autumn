import json, sys, collections, statistics as st
rows = [json.loads(l) for l in open(sys.argv[1])]
deaths_all = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else None
print('episodes', len(rows))
D = [r for r in rows if r['died']]
Dc = [r for r in D if r['killer'] not in (None, 'camp')]
print('episodes ending in death', len(D), 'to champions', len(Dc))
# model validity: damage taken by exposure bucket
b = collections.defaultdict(list)
for r in rows:
    e = r['act']; k = 0 if e == 0 else 1 if e <= 2 else 2 if e <= 5 else 3 if e <= 10 else 4
    b[k].append(r)
for k in sorted(b):
    v = b[k]; print(f"  act exposure bucket {k}: n={len(v)} mean taken={st.mean(x['taken'] for x in v):.0f} death rate={sum(1 for x in v if x['died'])/len(v):.3f}")
def g(r, key, s): v = r[key][s] if isinstance(r[key], dict) else None; return v
print('\n== death episodes (to champions) ==')
cnt = collections.Counter()
for r in Dc:
    a = r['act']; w = g(r, 'opt_walk', 'act'); d = g(r, 'opt_dash', 'act'); w0 = g(r, 'opt_walk', '0'); wany = g(r, 'opt_walk', 'any')
    cnt['n'] += 1
    if w is None: cnt['no path at same progress'] += 1; continue
    if a == 0: cnt['act exposure 0 (model blind)'] += 1
    if w == 0 and a > 0: cnt['walk escape w/ same progress, ocean exposed'] += 1
    if w > 0 and d == 0: cnt['only dash escapes (same progress)'] += 1
    if w > 0 and d > 0: cnt['no zero-exposure escape at same progress'] += 1
    if w < a: cnt['walk optimum < actual'] += 1
    if d < a: cnt['dash optimum < actual'] += 1
    if w0 is not None and w < w0: cnt['detour (ocean progress) beats shortest-path-progress'] += 1
    if wany == 0: cnt['zero exposure if progress ignored'] += 1
for k, v in cnt.items(): print(f'  {k}: {v} ({v/cnt["n"]:.1%})')
print('\n  victims', collections.Counter(r['type'] for r in Dc).most_common())
print('  killers', collections.Counter(r['killer'] for r in Dc).most_common())
dash_v = [r for r in Dc if r['cdU'] is not None]
print(f"\n  dasher victims: {len(dash_v)}; dash ready at r0: {sum(r['cdU']==0 for r in dash_v)}; all pursuers non-dashers: {sum(not any(r['pdash']) for r in dash_v)}")
for nm, sel in (('dasher, non-dasher pursuers', [r for r in dash_v if not any(r['pdash'])]),):
    w = [r for r in sel if r['opt_walk']['act'] is not None]
    print(f"  {nm}: n={len(sel)}, dash-only escapes {sum(r['opt_walk']['act']>0 and r['opt_dash']['act']==0 for r in w)}, dash cuts exposure {sum(r['opt_dash']['act'] < r['opt_walk']['act'] for r in w)}")
print('\n  hp share at r0: median', st.median(r['hp']/r['maxhp'] for r in Dc), ' K median', st.median(r['K'] for r in Dc), ' gems mean', st.mean(r['gems'] for r in Dc))
print('  pursuers at r0:', collections.Counter(len(r['purs']) for r in Dc).most_common(), ' nearest dist:', collections.Counter(min(r['pdist']) for r in Dc).most_common())
print('\n== bushes ==')
for nm, sel in (('death', Dc), ('survived', [r for r in rows if not r['died'] and r['act'] > 0])):
    av = [r for r in sel if r['bush_avail'] > 0]
    print(f"  {nm}: n={len(sel)} hidden bush adjacent on some turn {len(av)} ({len(av)/max(1,len(sel)):.1%}); stood in a bush on some turn {sum(r['bush_used']>0 for r in sel)}; of those with one adjacent, used {sum(r['bush_used']>0 for r in av)}")
print('\n== camp wake ==')
for nm, sel in (('death', Dc), ('survived exposed', [r for r in rows if not r['died'] and r['act'] > 0])):
    print(f"  {nm}: wake opportunity on some turn {sum(r['wake_opp']>0 for r in sel)} of {len(sel)}")
print('\n== allies ==')
for nm, sel in (('death', Dc), ('survived exposed', [r for r in rows if not r['died'] and r['act'] > 0])):
    am = [r['ally_min'] for r in sel if r['ally_min'] is not None]
    print(f"  {nm}: ally within 4 at r0 {sum(a<=4 for a in am)/len(sel):.1%}, within 8 {sum(a<=8 for a in am)/len(sel):.1%}, median nearest {st.median(am) if am else None}")
print('\n== controls (death episodes to champions) ==')
free = [r for r in Dc if r['stunned'] == 0]
print(f"  never stunned in window: {len(free)} of {len(Dc)}")
for nm, sel in (('all', Dc), ('free', free)):
    w = [r for r in sel if r['opt_walk']['act'] is not None]
    z = [r for r in w if r['opt_walk']['act'] == 0 and r['act'] > 0]
    print(f"  {nm}: walk zero-exposure escape at same progress while ocean exposed: {len(z)} ({len(z)/len(sel):.1%}); walk optimum <= half of actual: {sum(r['opt_walk']['act'] <= r['act']/2 and r['act']>0 for r in w)/len(sel):.1%}")
    fe = [r for r in sel if r['first_expo'] is not None and r['min_first'] is not None]
    print(f"     first step: ocean's first tile had more exposure than the least-exposed neighbour in {sum(r['first_expo'] > r['min_first'] for r in fe)/len(fe):.1%}")
    print(f"     still turns median {st.median(r['still'] for r in sel)}, K median {st.median(r['K'] for r in sel)}")
dv = [r for r in Dc if r['cdU'] is not None and r['cdU'] > 0 and r['opt_walk']['act'] is not None]
print(f"\n  dasher deaths with dash on cooldown at r0: {len(dv)}; a ready dash would give zero exposure: {sum(r['opt_dash_ready']['act']==0 for r in dv)}; where the actual dash timing gives none: {sum(r['opt_dash_ready']['act']==0 and r['opt_dash']['act']>0 for r in dv)}")
print(f"  ... cuts exposure vs dash as it was: {sum(r['opt_dash_ready']['act'] < r['opt_dash']['act'] for r in dv)}")
