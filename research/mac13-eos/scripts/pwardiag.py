"""Prism-war diagnosis: rounds where our Prism (team CAND, its PW trace) and the enemy Prism are within 6 (truth)
with a Focus ratio >= 1.25 either way. Usage: pwardiag.py EXTRACTED_DIR CAND_NAME"""
import gzip, json, sys, collections, zipfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

RATIO = 1.25
NEAR = 6
import os
CAND = os.environ.get('PWCAND', 'pwar-dbg')
PWF = ['round', 'h', 'br', 'vis', 'stale', 'd0', 'd1', 'fu', 'fe', 'hp', 'mhp', 'ehp', 'emhp', 'al', 'en', 'leth0', 'leth1', 'flost',
       'falls', 'c0', 'c1', 'walked', 'cd0', 'erd0', 'erd1', 'gu', 'ge', 'eacted']


def cheb(c, d, i):
    if c['x'][i] is None or d['x'][i] is None: return 99
    return max(abs(c['x'][i] - d['x'][i]), abs(c['y'][i] - d['y'][i]))


def g(d):
    meta = json.loads((d / 'meta.json').read_text())
    tn = [t['name'] for t in meta['teams']]
    if CAND not in tn: return []
    us = tn.index(CAND)
    names = {int(c['id']): c['name'] for c in meta['champions']}
    team = {int(c['id']): int(c['team']) for c in meta['champions']}
    R = json.load(gzip.open(d / 'rounds.json.gz'))
    ch = {int(c['id']): c for c in R['champions']}
    pr = [i for i in ch if names[i] == 'Prism']
    if len(pr) != 2: return []
    pu = [i for i in pr if team[i] == us][0]
    pe = [i for i in pr if team[i] != us][0]
    z = zipfile.ZipFile(Path('/home/ubuntu/wt/mac13-eos') / meta['source'])
    pw, br = {}, {}
    for k, f in enumerate(('team-a.stdout', 'team-b.stdout')):
        txt = z.read(f).decode(errors='replace')
        for line in txt.splitlines():
            if line.startswith('D '):
                p = line.split()
                br[(int(p[1]), int(p[2]))] = p[3]
            elif k == us and line.startswith('PW '):
                p = line.split()[1:]
                rec = dict(zip(PWF, [p[0], p[1], p[2]] + [int(x) for x in p[3:]]))
                rec['round'] = int(p[0])
                pw[rec['round']] = rec
    deaths = collections.defaultdict(list)
    casts = collections.defaultdict(list)  # (round) -> casts by our prism / enemy prism with target
    for l in gzip.open(d / 'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] == 'death' and e['v'] in pr:
            by = e.get('by')
            deaths[e['v']].append((e['r'], names.get(by, 'camp') if by is not None else 'camp', by))
        elif e['k'] == 'cast' and e.get('a') in pr:
            casts[(e['a'], e['r'])].append(e)
    A, B = ch[pu], ch[pe]
    n = len(A['x'])
    out = []
    win = meta.get('winner')
    for i in range(1, n):
        if not (A['alive'][i] and B['alive'][i]): continue
        dd = cheb(A, B, i)
        if dd > NEAR: continue
        fu, fe = A['foc'][i] or 1, B['foc'][i] or 1
        ratio = fe / fu
        if ratio >= RATIO: role = 'small'
        elif ratio <= 1 / RATIO: role = 'big'
        else: continue
        die_u = [x for x in deaths[pu] if i <= x[0] <= i + 10]
        die_e = [x for x in deaths[pe] if i <= x[0] <= i + 10]
        p = pw.get(i)
        prevd = cheb(A, B, i - 1)
        # who moved: distance if we had stayed
        ds = max(abs(A['x'][i - 1] - B['x'][i]), abs(A['y'][i - 1] - B['y'][i])) if A['x'][i - 1] is not None and B['x'][i] is not None else dd
        ourcast = [c for c in casts.get((pu, i), []) if c.get('slot') in (0, 1)]
        ourhit = any(c.get('tgt') == pe or any(t[0] == pe for t in c.get('dmg', []) or []) for c in ourcast)
        encast = casts.get((pe, i), [])
        enhit = any(c.get('tgt') == pu or any(t[0] == pu for t in c.get('dmg', []) or []) for c in encast)
        al = sum(1 for c in ch if team[c] == us and c != pu and ch[c]['alive'][i] and cheb(ch[c], A, i) <= 8)
        en = sum(1 for c in ch if team[c] != us and c != pe and ch[c]['alive'][i] and cheb(ch[c], A, i) <= 8)
        seen = pe in (A['sees'][i] or [])
        out.append(dict(r=i, role=role, ratio=ratio, d=dd, prevd=prevd, closer_by_us=dd < ds, br=br.get((i, pu), '?'), ebr=br.get((i, pe), '?'),
                        pw=p, seen=seen, die_u=bool(die_u), die_e=bool(die_e), killer_u=die_u[0][1] if die_u else None,
                        killer_e=die_e[0][1] if die_e else None, ourhit=ourhit, enhit=enhit, al=al, en=en,
                        hpu=A['hp'][i] / A['maxHp'][i], hpe=B['hp'][i] / B['maxHp'][i], game=d.name, fu=fu, fe=fe))
    return out


def pct(x, n): return f'{100 * x / max(1, n):.0f}%'


def table(rows, label):
    n = len(rows)
    print(f'\n=== {label}: {n} rounds')
    if not n: return
    # encounter starts: rounds whose previous round was not in the set
    S = set((r['game'], r['r']) for r in rows)
    starts = [r for r in rows if (r['game'], r['r'] - 1) not in S]
    print(f'  encounters {len(starts)}; our Prism dies within 10 rounds: {pct(sum(r["die_u"] for r in rows), n)} of rounds,'
          f' {pct(sum(r["die_u"] for r in starts), len(starts))} of encounter starts; enemy dies {pct(sum(r["die_e"] for r in rows), n)} / {pct(sum(r["die_e"] for r in starts), len(starts))}')
    traced = [r for r in rows if r['pw']]
    print(f'  traced (belief within 10): {pct(len(traced), n)}; truth seen: {pct(sum(r["seen"] for r in rows), n)}')
    if traced:
        vis = sum(r['pw']['vis'] for r in traced)
        print(f'  belief visible {pct(vis, len(traced))}; stale>0 median {sorted(r["pw"]["stale"] for r in traced if not r["pw"]["vis"])[len([1 for r in traced if not r["pw"]["vis"]]) // 2] if len(traced) > vis else "-"}')
        bfu = [r['pw']['fe'] / max(1, r['pw']['fu']) for r in traced]
        print(f'  believed ratio enemy/ours median {sorted(bfu)[len(bfu) // 2]:.2f} vs true {sorted(r["ratio"] for r in traced)[len(traced) // 2]:.2f}')
        for k in ('leth0', 'leth1', 'walked', 'c0', 'c1'):
            print(f'  {k}: {pct(sum(r["pw"][k] > 0 for r in traced), len(traced))}', end='')
        fl = collections.Counter(r['pw']['flost'] for r in traced)
        print(f'\n  fight(here) verdict: lost {pct(fl[1], len(traced))} not-lost {pct(fl[0], len(traced))} no-fight {pct(fl[-1], len(traced))}; self_falls {pct(sum(r["pw"]["falls"] for r in traced), len(traced))}')
        print(f'  stale buckets (unseen belief): {collections.Counter(min(r["pw"]["stale"], 20) // 5 * 5 for r in traced if not r["pw"]["vis"]).most_common()}')
    print(f'  we closed the distance {pct(sum(r["closer_by_us"] for r in rows), n)}; we hit it {pct(sum(r["ourhit"] for r in rows), n)}; it hit us {pct(sum(r["enhit"] for r in rows), n)}')
    print(f'  allies within 8 mean {sum(r["al"] for r in rows) / n:.2f}; other enemies within 8 mean {sum(r["en"] for r in rows) / n:.2f}; hp ours {sum(r["hpu"] for r in rows) / n:.2f} theirs {sum(r["hpe"] for r in rows) / n:.2f}')
    bc = collections.Counter(r['br'] for r in rows)
    print('  our branch (rounds, our death%, enemy death%):', ', '.join(f'{b} {c} ({pct(sum(r["die_u"] for r in rows if r["br"] == b), c)}, {pct(sum(r["die_e"] for r in rows if r["br"] == b), c)})' for b, c in bc.most_common(12)))
    bc = collections.Counter(r['br'] for r in starts)
    print('  our branch at encounter start:', bc.most_common(10))
    bc = collections.Counter(r['ebr'] for r in rows)
    print('  enemy branch:', bc.most_common(10))
    for lab, f in (('visible-belief', lambda r: r['pw'] and r['pw']['vis']), ('unseen-belief', lambda r: r['pw'] and not r['pw']['vis']), ('untraced', lambda r: not r['pw'])):
        s = [r for r in rows if f(r)]
        print(f'  {lab}: {len(s)} rounds, our death {pct(sum(r["die_u"] for r in s), len(s))}, enemy death {pct(sum(r["die_e"] for r in s), len(s))}, closer by us {pct(sum(r["closer_by_us"] for r in s), len(s))}')
    for lab, f in (('lethal here', lambda r: r['pw'] and r['pw']['leth1']), ('fight lost here', lambda r: r['pw'] and r['pw']['flost'] == 1), ('fight not lost', lambda r: r['pw'] and r['pw']['flost'] == 0), ('no fight', lambda r: r['pw'] and r['pw']['flost'] == -1)):
        s = [r for r in rows if f(r)]
        print(f'  {lab}: {len(s)} rounds, our death {pct(sum(r["die_u"] for r in s), len(s))}, enemy death {pct(sum(r["die_e"] for r in s), len(s))}, we hit {pct(sum(r["ourhit"] for r in s), len(s))}, closer by us {pct(sum(r["closer_by_us"] for r in s), len(s))}')
    kb = collections.Counter(r['killer_u'] for r in starts if r['die_u'])
    print('  our killer (encounter starts):', kb.most_common(5))


if __name__ == '__main__':
    pass
    dirs = [d for d in Path(sys.argv[1]).iterdir() if (d / 'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: E = [x for r in ex.map(g, dirs, chunksize=4) for x in r]
    print('games', len(dirs), 'rows', len(E))
    early = [e for e in E if e['r'] < 600]
    table([e for e in early if e['role'] == 'small'], 'ours SMALLER (enemy Focus >= 1.25x ours), r<600')
    table([e for e in early if e['role'] == 'big'], 'ours BIGGER (ours >= 1.25x), r<600')
    table([e for e in E if e['r'] >= 600 and e['role'] == 'small'], 'ours SMALLER, r>=600')
    table([e for e in E if e['r'] >= 600 and e['role'] == 'big'], 'ours BIGGER, r>=600')
    import pickle
    pickle.dump(E, open('/tmp/pwardiag.pkl', 'wb'))
