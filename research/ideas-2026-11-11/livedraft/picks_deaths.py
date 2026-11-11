"""From picks to early deaths: v115's 520 decoded live games (overruns' deaths.pkl) and the same bot against the
bodies (deaths_local.pkl). Per champion of ours: early deaths a game it is in, how often it is our first death,
and the win share with and without an early death of it.
    py picks_deaths.py [EARLY=250]"""
import pickle, sys, collections, numpy as np
E = int(sys.argv[1]) if len(sys.argv) > 1 else 250
AN = '/home/ubuntu/tmp-offload/overruns/an/'
def nm(t): return 'Cassi & Issac' if t in ('Cassi', 'Issac') else t
def read(path, opp):
    G = [g for g in pickle.load(open(AN + path, 'rb')) if g['opp'][:4] == opp]
    st = collections.defaultdict(lambda: collections.Counter())
    for g in G:
        ours = [d for d in g['D'] if d['ours'] and d['r'] <= E and not d['camp']]
        seen = set(); dead = collections.Counter()
        for d in sorted(ours, key=lambda d: d['r']):
            k = (nm(d['typ']), d['r'])
            if k in seen: continue      # the pair dies together: one death
            seen.add(k); dead[nm(d['typ'])] += 1
        first = nm(min(ours, key=lambda d: d['r'])['typ']) if ours else None
        for c in g['our_picks']:
            s = st[c]; s['n'] += 1; s['win'] += g['win']; s['deaths'] += dead[c]; s['first'] += first == c
            s['any'] += dead[c] > 0; s['win_any'] += g['win'] and dead[c] > 0; s['win_none'] += g['win'] and dead[c] == 0
            s['team_deaths'] += sum(dead.values())
    return G, st
print(f'early = rounds up to {E}; champion kills only (camp deaths left out); the pair counts once\n')
print('| our champion | games | early deaths a game: live Fish / Flp4 body | our first death: live Fish / body | win% with / without an early death of it, live Fish | live Mite: deaths a game (body) | first death (body) | win% with / without |')
print('|---|---:|---|---|---|---|---|---|')
LF, lf = read('deaths.pkl', 'Inte'); LM, lm = read('deaths.pkl', 'Mite')
try: BF, bf = read('deaths_local.pkl', 'Inte'); BM, bm = read('deaths_local.pkl', 'Mite')
except Exception as e: print(e); bf = bm = collections.defaultdict(collections.Counter)
if not bf:
    X = pickle.load(open(AN + 'deaths_local.pkl', 'rb')); print('local opp tags:', collections.Counter(g['opp'] for g in X))
for c in sorted(lf, key=lambda c: -lf[c]['deaths'] / lf[c]['n']):
    a, b, m, bb = lf[c], bf[c], lm[c], bm[c]
    r = lambda s, k: f'{s[k] / s["n"]:.2f}' if s['n'] else '-'
    p = lambda s, k: f'{100 * s[k] / s["n"]:.0f}%' if s['n'] else '-'
    w = lambda s: f'{100 * s["win_any"] / max(1, s["any"]):.0f}% of {s["any"]} / {100 * s["win_none"] / max(1, s["n"] - s["any"]):.0f}% of {s["n"] - s["any"]}'
    print(f'| {c} | {a["n"]} | {r(a, "deaths")} / {r(b, "deaths")} | {p(a, "first")} / {p(b, "first")} | {w(a)} | {r(m, "deaths")} ({r(bb, "deaths")}) | {p(m, "first")} ({p(bb, "first")}) | {w(m)} |')
for nmm, G in (('live Fish', LF), ('live Mite', LM)):
    h = [g for g in G if 'Cassi & Issac' in g['our_picks']]; n = [g for g in G if 'Cassi & Issac' not in g['our_picks']]
    ed = lambda gs: np.mean([len({(nm(d['typ']), d['r']) for d in g['D'] if d['ours'] and d['r'] <= E and not d['camp']}) for g in gs])
    print(f'\n{nmm}: with the pair {100 * np.mean([g["win"] for g in h]):.1f}% of {len(h)}, {ed(h):.2f} early deaths a game; without {100 * np.mean([g["win"] for g in n]):.1f}% of {len(n)}, {ed(n):.2f}')
