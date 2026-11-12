"""Combat: target choice, engage/retreat rules, kills and deaths. BattleCats against its opponents, measured the same way.
python3 combat.py [ver,...]"""
import sys, collections
import fl
vers = sys.argv[1].split(',') if len(sys.argv) > 1 else ['cur']
G = fl.load(lambda g: g['ver'] in vers)
print(len(G), 'games', vers, collections.Counter(g['oc'] for g in G))

# --- target choice among 2+ enemy champions in reach
for who in ('bc', 'opp'):
    st = collections.Counter(); typ_ch = collections.Counter(); typ_av = collections.Counter(); by_kind = collections.Counter()
    for g in G:
        t = g['bc'] if who == 'bc' else 1 - g['bc']
        for r, a, kind, tg, cands in g['targ']:
            if g['team'][a] != t or len(cands) < 2: continue
            ids = [c[0] for c in cands]
            if tg not in ids: continue
            ch = cands[ids.index(tg)]
            st['n'] += 1; st['exp'] += 1 / len(cands)
            st['minhp'] += ch[2] == min(c[2] for c in cands)
            st['minfrac'] += ch[1] == min(c[1] for c in cands)
            st['maxgems'] += ch[3] == max(c[3] for c in cands) and ch[3] > 0
            st['anygems'] += max(c[3] for c in cands) > 0
            st['nearest'] += ch[4] == min(c[4] for c in cands)
            st['ties_hp'] += sum(1 for c in cands if c[2] == ch[2]) > 1
            for c in cands: typ_av[c[5]] += 1 / len(cands)
            typ_ch[ch[5]] += 1
            by_kind[kind] += 1
    n = st['n']
    print(f'\n== {who} target choice, {n} attacks/casts with 2+ enemy champions in reach (random pick would match {st["exp"] / n:.2f}):')
    print(f'  lowest hp {fl.pct(st["minhp"], n)}, lowest hp fraction {fl.pct(st["minfrac"], n)}, nearest {fl.pct(st["nearest"], n)}, '
          f'most gems {fl.pct(st["maxgems"], st["anygems"])} of {st["anygems"]} with a carrier present')
    print('  chosen/expected by type:', ', '.join(f'{k} {typ_ch[k] / typ_av[k]:.2f}' for k in sorted(typ_av, key=lambda k: -typ_ch[k] / typ_av[k]) if typ_av[k] > 20))

# --- engage / retreat in contact, by hp and numbers
def bucket(h): return '<.25' if h < .25 else '<.5' if h < .5 else '<.75' if h < .75 else '>=.75'
for who in ('bc', 'opp'):
    tab = collections.defaultdict(collections.Counter)
    tab2 = collections.defaultdict(collections.Counter)
    for g in G:
        t = g['bc'] if who == 'bc' else 1 - g['bc']
        for f in g['fights']:
            r, c, hp, gems, dn, ne, na, da, ds, hit, alive, ehp, ahp = f
            if g['team'][c] != t or dn > 3: continue
            away = ds is not None and ds > dn
            s = tab[bucket(hp)]; s['n'] += 1; s['away'] += away; s['hit'] += hit; s['died'] += 1 - alive
            nd = max(-2, min(2, ne - (na + 1)))
            s2 = tab2[nd]; s2['n'] += 1; s2['away'] += away; s2['hit'] += hit; s2['died'] += 1 - alive
    print(f'\n== {who} with an enemy within 3 (round-start positions): P(moves away), P(hits a champion), P(dies this round)')
    for k in ('<.25', '<.5', '<.75', '>=.75'):
        s = tab[k]; n = s['n'] or 1
        print(f'  hp {k:6s} n={s["n"]:6d} away {s["away"] / n:.2f} hit {s["hit"] / n:.2f} died {s["died"] / n:.3f}')
    for k in sorted(tab2):
        s = tab2[k]; n = s['n'] or 1
        print(f'  enemies-allies within 5 = {k:+d} n={s["n"]:6d} away {s["away"] / n:.2f} hit {s["hit"] / n:.2f} died {s["died"] / n:.3f}')

# --- kills and deaths per game
print('\n== kills / deaths per game (BC perspective), and how')
for oc in ('us', 'Fish', 'Mite', 'other'):
    S = [g for g in G if g['oc'] == oc]
    if not S: continue
    k = d = camp = gl_bc = gl_op = 0
    killer = collections.Counter(); victim = collections.Counter(); bcvict = collections.Counter(); cause = collections.Counter()
    for g in S:
        for r, v, by, gems, hp, cs, ass, at, gto in g['deaths']:
            pair2 = g['name'][v] == 'Issac'  # C&I die together: count the pair once (as Cassi), add Issac's bag
            if g['team'][v] == g['bc']:
                gl_bc += gems or 0
                if pair2: continue
                d += 1; bcvict[g['name'][v].replace('Cassi', 'C&I')] += 1
                if by is None or by not in g['team']: camp += 1
            else:
                if by in g['team'] and g['team'][by] == g['bc']:
                    gl_op += gems or 0
                    if pair2: continue
                    k += 1; killer[g['name'][by]] += 1; victim[g['name'][v].replace('Cassi', 'C&I')] += 1; cause[cs] += 1
    n = len(S)
    print(f' vs {oc} ({n}): BC kills {k / n:.1f} (gems taken {gl_op / n:.0f}), BC deaths {d / n:.1f} (camp {camp / n:.2f}, gems lost {gl_bc / n:.0f})')
    print('   BC killers:', ', '.join(f'{a} {b / n:.2f}' for a, b in killer.most_common(6)), '| victims:', ', '.join(f'{a} {b / n:.2f}' for a, b in victim.most_common(6)))
    print('   BC dead:', ', '.join(f'{a} {b / n:.2f}' for a, b in bcvict.most_common(6)), '| kill cause:', dict(cause))
