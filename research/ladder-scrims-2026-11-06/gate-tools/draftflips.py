"""draftflips.py A B: draft-focused comparison of version B against A on the paired set games (core + ext)."""
import collections, json, sys
sys.path.insert(0, '/home/ubuntu/cambc-autumn/tools')
import ladder_scrims as ls
G = __import__('os').environ.get('GATE_DIR', '/tmp/gate')
cls = json.load(open(f'{G}/mapclass.json'))
a, b = int(sys.argv[1]), int(sys.argv[2])
SH = {'Cassi & Issac': 'C&I', 'Heart of Ruin': 'HoR', 'Vesper Vale': 'Vesp'}
sh = lambda p: SH.get(p, p[:4])
team = lambda ps: '+'.join(sorted(sh(p) for p in ps))
key = lambda r: (r['opp_name'][:4], r['map'], r['side'])
ra = {key(r): r for r in ls.games(a) if r['purpose'] == 'set'}
rb = {key(r): r for r in ls.games(b) if r['purpose'] == 'set'}
both = sorted(set(ra) & set(rb))
W = lambda r: r['result'] == 'win'
same = [k for k in both if ra[k]['our_picks'] == rb[k]['our_picks']]
print(f'v{b} against v{a}: {len(both)} paired; our draft identical in {len(same)}, changed in {len(both) - len(same)}; '
      f'opponent draft changed in {sum(ra[k]["opp_picks"] != rb[k]["opp_picks"] for k in both)}')
for lab, ks in (('draft same', same), ('draft changed', [k for k in both if k not in same])):
    for opp in ('Inte', 'Mite'):
        kk = [k for k in ks if k[0] == opp]
        up = sum(W(rb[k]) and not W(ra[k]) for k in kk); dn = sum(W(ra[k]) and not W(rb[k]) for k in kk)
        print(f'  {lab:<14} {opp}: {len(kk):>3} games, v{a} {sum(W(ra[k]) for k in kk)} v{b} {sum(W(rb[k]) for k in kk)} wins, flips +{up} -{dn}')
print('\nflips (map side class | ours A -> B | opp A -> B):')
for k in both:
    if W(ra[k]) == W(rb[k]): continue
    A, B = ra[k], rb[k]
    tag = 'SAME' if A['our_picks'] == B['our_picks'] else '    '
    opp = team(A['opp_picks']) + ('' if A['opp_picks'] == B['opp_picks'] else ' -> ' + team(B['opp_picks']))
    print(f"  {'+' if W(B) else '-'} {tag} {k[0]} {k[1]}-{k[2]} [{cls[k[1]]}] | {team(A['our_picks'])} -> {team(B['our_picks'])} | {opp}")
print('\nper champion (our pick), by version and opponent: games-wins')
champs = sorted({sh(p) for k in both for r in (ra[k], rb[k]) for p in r['our_picks']})
for opp in ('Inte', 'Mite'):
    print(f'  {opp}:')
    for c in champs:
        row = []
        for v, rr in ((a, ra), (b, rb)):
            g = [rr[k] for k in both if k[0] == opp and c in [sh(p) for p in rr[k]['our_picks']]]
            row.append(f'v{v} {len(g):>3}g {sum(map(W, g)):>3}w ({100 * sum(map(W, g)) / max(len(g), 1):4.0f}%)')
        print(f'    {c:<6} ' + '   '.join(row))
print('\nflips by champion added (in B, not A) / removed: net flips for B')
add, rem = collections.Counter(), collections.Counter()
for k in both:
    if W(ra[k]) == W(rb[k]): continue
    s = 1 if W(rb[k]) else -1
    pa, pb = {sh(p) for p in ra[k]['our_picks']}, {sh(p) for p in rb[k]['our_picks']}
    for c in pb - pa: add[c] += s
    for c in pa - pb: rem[c] += s
n_add = collections.Counter(c for k in both for c in {sh(p) for p in rb[k]['our_picks']} - {sh(p) for p in ra[k]['our_picks']})
n_rem = collections.Counter(c for k in both for c in {sh(p) for p in ra[k]['our_picks']} - {sh(p) for p in rb[k]['our_picks']})
for c in champs:
    if n_add[c] or n_rem[c]:
        print(f'  {c:<6} added in {n_add[c]:>3} games (net flips {add[c]:+d}), removed in {n_rem[c]:>3} (net flips {rem[c]:+d})')
print('\nour team composition by version (top by games):')
for v, rr in ((a, ra), (b, rb)):
    c = collections.Counter(); w = collections.Counter()
    for k in both:
        t = team(rr[k]['our_picks']); c[t] += 1; w[t] += W(rr[k])
    print(f'  v{v}: ' + '; '.join(f'{t} {w[t]}/{n}' for t, n in c.most_common(8)))
print('\nflips by map (both opponents/sides): net for B')
m = collections.Counter()
for k in both:
    if W(ra[k]) != W(rb[k]): m[k[1]] += 1 if W(rb[k]) else -1
print('  ' + ', '.join(f'{x} {y:+d}' for x, y in sorted(m.items(), key=lambda t: t[1]) if abs(y) >= 2))
