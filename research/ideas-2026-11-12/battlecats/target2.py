"""Target rule detail: nearest vs lowest health when they disagree; attacks vs spells; kill-securing."""
import sys, collections, fl
vers = sys.argv[1].split(',') if len(sys.argv) > 1 else ['cur']
G = fl.load(lambda g: g['ver'] in vers)
for who in ('bc', 'opp'):
    st = collections.defaultdict(collections.Counter)
    for g in G:
        t = g['bc'] if who == 'bc' else 1 - g['bc']
        for r, a, kind, tg, cands in g['targ']:
            if g['team'][a] != t or len(cands) < 2: continue
            ids = [c[0] for c in cands]
            if tg not in ids: continue
            ch = cands[ids.index(tg)]
            kk = 'attack' if kind == 'attack' else 'spell'
            dmin = min(c[4] for c in cands); hmin = min(c[2] for c in cands)
            near = [c for c in cands if c[4] == dmin]; low = [c for c in cands if c[2] == hmin]
            s = st[kk]; s['n'] += 1
            if len(near) == 1 and low[0][0] != near[0][0]:
                s['conflict'] += 1; s['conf_near'] += ch[0] == near[0][0]; s['conf_low'] += ch[2] == hmin
            if len(near) > 1:
                s['tie_near'] += 1; s['tie_low'] += ch[2] == min(c[2] for c in near)
                s['tie_lowfrac'] += ch[1] == min(c[1] for c in near)
                if max(c[3] for c in near) > 0: s['tie_gemsany'] += 1; s['tie_gems'] += ch[3] == max(c[3] for c in near)
            # same distance band: chosen among those within the attacker's range? already; frac vs abs
            fr = min(c[1] for c in cands)
            if [c for c in cands if c[1] == fr][0][0] != low[0][0]:
                s['fa_conf'] += 1; s['fa_abs'] += ch[2] == hmin; s['fa_frac'] += ch[1] == fr
    for kk, s in st.items():
        print(f'{who} {kk}: n={s["n"]}; nearest-vs-lowest-hp conflicts {s["conflict"]}: picks nearest {fl.pct(s["conf_near"], s["conflict"])}, lowest hp {fl.pct(s["conf_low"], s["conflict"])}; '
              f'ties on nearest {s["tie_near"]}: lowest hp {fl.pct(s["tie_low"], s["tie_near"])}, lowest frac {fl.pct(s["tie_lowfrac"], s["tie_near"])}, most gems {fl.pct(s["tie_gems"], s["tie_gemsany"])}; '
              f'abs-vs-frac conflicts {s["fa_conf"]}: abs {fl.pct(s["fa_abs"], s["fa_conf"])} frac {fl.pct(s["fa_frac"], s["fa_conf"])}')
# spells: what BC casts on (champion vs camp) and when
cc = collections.Counter()
for g in G:
    for r, a, ab, tgc, camp, hits in g['casts']:
        if g['team'][a] != g['bc']: continue
        cc[(g['name'][a], ab, 'champ' if tgc is not None else 'camp' if camp else 'hits' if hits else 'none')] += 1
n = len(G)
print('\nBC casts per game by champion/ability/target:')
for k, v in sorted(cc.items(), key=lambda x: -x[1])[:30]: print(' ', k, f'{v / n:.1f}')
