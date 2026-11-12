"""Target convergence per team, from extract.mjs output: when several of a team's units strike enemy champions in
one round, do they hit the same one?

A strike is a unit's damage on enemy champions in a round (attacks and casts; a linked pair counts as one target);
its target is the enemy it dealt most to. A unit's options are the enemies it saw at its turn start within OPT
(Chebyshev) of its tile at the previous round's end. A "choice round" has 2+ strikers and 2+ enemies that are an
option of at least two of them.

Per team label: strikes in multi-striker rounds; modal share (strikes on the round's most-hit target) and all-agree
rate, overall and in choice rounds, with the chance level (each striker picking uniformly among its options);
outcomes after choice rounds (an enemy death and an own death within W rounds), all-agree against split.

py conv.py live            # Fish r8 live games (~/tmp-offload/fishr8/live): labels us / fish
py conv.py EXTRACT_DIR...  # local batches: labels are the team names
"""
import gzip, json, os, random, sys
from collections import Counter, defaultdict
from multiprocessing import Pool

OPT = 4
W = 3
H = os.path.expanduser('~/tmp-offload/fishr8/live/')


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(job):
    d, labels = job
    try:
        meta = json.load(open(d + '/meta.json'))
        R = json.load(gzip.open(d + '/rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    except Exception:
        return None
    team = {c['id']: c['team'] for c in meta['champions']}
    # One target id per pick: a linked pair's bodies share their lower id.
    pick = {c['id']: c['id'] for c in meta['champions']}
    names = {c['id']: c['name'] for c in meta['champions']}
    for t in (0, 1):
        ids = [c for c in team if team[c] == t]
        cass = [c for c in ids if names[c] in ('Cassi', 'Issac')]
        if len(cass) == 2: pick[max(cass)] = min(cass)
    idx = {r: i for i, r in enumerate(R['round'])}
    ch = {c['id']: c for c in R['champions']}
    hits = defaultdict(lambda: defaultdict(Counter))  # round -> actor -> target pick -> dmg
    deaths = defaultdict(list)  # round -> [(team of victim, pick)]
    for e in ev:
        k = e['k']
        if k in ('attack', 'cast') and e.get('dmg'):
            a = e['a']
            for v, amt in e['dmg']:
                if v in team and team[v] != team[a] and amt > 0: hits[e['r']][a][pick[v]] += amt
        elif k == 'death' and e.get('linked') is None:
            deaths[e['r']].append((team[e['v']], pick[e['v']]))
    winner = meta['result'].get('winner')
    out = {}
    rng = random.Random(1)
    for t in (0, 1):
        lab = labels[t]
        if lab is None: continue
        S = Counter()
        rows = []  # choice rounds: (all_agree, enemy_death_W, own_death_W, modal_target_death_W, nstrikers)
        for r, by in hits.items():
            st = {a: tg for a, tg in by.items() if team[a] == t}
            if len(st) < 2: continue
            prim = {a: max(tg, key=tg.get) for a, tg in st.items()}
            cnt = Counter(prim.values())
            modal, m = cnt.most_common(1)[0]
            n = len(prim)
            S['mr'] += 1; S['ms'] += n; S['mm'] += m; S['ma'] += (m == n)
            i = idx.get(r - 1)
            if i is None: continue
            opts = {}
            for a in prim:
                c = ch[a]
                if c['x'][i] is None or c['x'][i] < 0: continue
                p = (c['x'][i], c['y'][i])
                ri = idx.get(r)
                seen = set(c['sees'][ri]) if ri is not None and c['sees'][ri] is not None else set()
                o = set()
                for v in seen:
                    cv = ch.get(v)
                    if cv is None or not cv['alive'][i] or cv['x'][i] is None: continue
                    if cheb(p, (cv['x'][i], cv['y'][i])) <= OPT: o.add(pick[v])
                o.add(prim[a])
                opts[a] = o
            if len(opts) < 2: continue
            shared = Counter(v for o in opts.values() for v in o)
            if sum(1 for v, k in shared.items() if k >= 2) < 2: continue
            # Chance: each striker uniform over its options.
            sim_m = sim_a = 0
            for _ in range(200):
                c2 = Counter(rng.choice(sorted(o)) for o in opts.values())
                mm = c2.most_common(1)[0][1]
                sim_m += mm; sim_a += (mm == len(opts))
            S['cr'] += 1; S['cs'] += n; S['cm'] += m; S['ca'] += (m == n)
            S['chm'] += sim_m / 200; S['cha'] += sim_a / 200
            ed = od = md = 0
            dead = set()
            for rr in range(r, r + W + 1):
                for vt, vp in deaths.get(rr, ()):
                    if vt != t: ed = 1; md |= (vp == modal); dead.add(vp)
                    else: od = 1
            tot_d = sum(sum(tg.values()) for tg in st.values())
            use_d = sum(v for tg in st.values() for k, v in tg.items() if k in dead)
            nsh = sum(1 for v, k in shared.items() if k >= 2)
            # our and their bodies alive within 8 of the strikers' centre
            cx = sum(ch[a]['x'][i] for a in opts) / len(opts); cy = sum(ch[a]['y'][i] for a in opts) / len(opts)
            near = [0, 0]
            for c, cv in ch.items():
                if cv['alive'][i] and cv['x'][i] is not None and cv['x'][i] >= 0 and max(abs(cv['x'][i] - cx), abs(cv['y'][i] - cy)) <= 8:
                    near[0 if team[c] == t else 1] += 1
            rows.append((int(m == n), ed, od, md, n, min(nsh, 3), min(near[0], 5), min(near[1], 5), use_d, tot_d))
            S['cud'] += use_d; S['ctd'] += tot_d
        S['games'] = 1
        S['win'] = int(winner == t)
        out[lab] = (S, rows)
    return out


def live_jobs():
    rows = json.load(open(H + 'rows-r8-all.json'))
    jobs = []
    for g in json.load(open(H + 'ext/index.json'))['games']:
        mid = os.path.basename(g['source'])[:-8]
        if mid in rows and g.get('ok'):
            us = 0 if rows[mid]['side'] == 'a' else 1
            labels = [None, None]; labels[us] = 'us-live'; labels[1 - us] = 'fish-r8-live'
            jobs.append((H + 'ext/' + g['dir'], labels))
    return jobs


def batch_jobs(ex):
    jobs = []
    for g in json.load(open(ex + '/index.json'))['games']:
        if g.get('ok'): jobs.append((ex + '/' + g['dir'], list(g['teams'])))
    return jobs


def pct(a, b): return f'{100 * a / b:5.1f}' if b else '  -  '


def main():
    jobs = live_jobs() if sys.argv[1:] == ['live'] else [j for ex in sys.argv[1:] for j in batch_jobs(ex)]
    with Pool(int(os.environ.get('NPROC', 8))) as p: res = [x for x in p.map(one, jobs, chunksize=4) if x]
    tot = defaultdict(Counter); allrows = defaultdict(list)
    for o in res:
        for lab, (S, rows) in o.items(): tot[lab].update(S); allrows[lab].extend(rows)
    print(f'OPT={OPT} W={W}')
    print('team               games  multi-rounds modal%  agree% | choice-rounds modal% (chance) agree% (chance) | '
          'after choice, all-agree vs split: enemy death%  own death%  modal-target death%')
    for lab, S in sorted(tot.items()):
        rows = allrows[lab]
        A = [x for x in rows if x[0]]; B = [x for x in rows if not x[0]]
        f = lambda L, j: pct(sum(x[j] for x in L), len(L))
        print(f'{lab:18s} {S["games"]:5d} {S["mr"]:8d} {pct(S["mm"], S["ms"])} {pct(S["ma"], S["mr"])} | '
              f'{S["cr"]:7d} {pct(S["cm"], S["cs"])} ({pct(S["chm"], S["cs"])}) {pct(S["ca"], S["cr"])} ({pct(S["cha"], S["cr"])}) | '
              f'{f(A, 1)} vs {f(B, 1)}   {f(A, 2)} vs {f(B, 2)}   {f(A, 3)} vs {f(B, 3)}  (n {len(A)}/{len(B)})')
        print(f'{"":18s} multi-striker rounds a game {S["mr"] / S["games"]:.1f}, choice rounds a game {S["cr"] / S["games"]:.1f}; '
              f'choice-round damage on enemies dying within W: {pct(S["cud"], S["ctd"])}%')
        # Stratified (strikers, shared options, ours near, theirs near): agree - split, weighted by min count
        st = defaultdict(lambda: [[], []])
        for x in rows: st[(x[4], x[5], x[6], x[7])][x[0]].append(x)
        for j, nm in ((1, 'enemy death'), (2, 'own death'), (8, 'useful dmg share')):
            num = den = 0
            for k, (B2, A2) in st.items():
                if not A2 or not B2: continue
                w = len(A2) * len(B2) / (len(A2) + len(B2))
                if j == 8:
                    a = sum(x[8] for x in A2) / max(1, sum(x[9] for x in A2)); b = sum(x[8] for x in B2) / max(1, sum(x[9] for x in B2))
                else:
                    a = sum(x[j] for x in A2) / len(A2); b = sum(x[j] for x in B2) / len(B2)
                num += w * (a - b); den += w
            print(f'{"":18s} stratified agree - split, {nm}: {100 * num / den if den else 0:+.1f} pts (weight {den:.0f})')


if __name__ == '__main__':
    main()
