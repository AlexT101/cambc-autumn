"""Per extract: wins, big Prism tributes (hoards) by outcome, how far in they were cancelled, completions by class, our deaths."""
import json, gzip, os, sys, collections, statistics as st
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def run(ext):
    idx = json.load(open(ext + '/index.json'))['games']
    A = collections.Counter(); frac = collections.defaultdict(list); games = 0; wins = 0; pg = 0; pw = 0
    deaths = 0; pdeaths = 0; pbag = 0; vdeaths = 0; rounds = 0; lost_with_done = 0; near_deaths = 0
    for g in idx:
        mid = os.path.basename(g['source'])[:-8]; cand = 0 if mid.endswith('-12') else 1
        p = f"{ext}/{g['dir']}"; meta = json.load(open(p + '/meta.json')); R = json.load(gzip.open(p + '/rounds.json.gz'))
        typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
        ch = R['champions']; n = len(R['round']); games += 1; win = g['winner'] == cand; wins += win; rounds += n
        ev = [json.loads(l) for l in gzip.open(p + '/events.jsonl.gz', 'rt')]
        for e in ev:
            if e['k'] == 'death' and 'linked' not in e:
                if team[e['v']] == cand: deaths += 1; vdeaths += typ[e['v']] == 'Vesper Vale'
        P = [c for c in ch if c['team'] != cand and typ[c['id']] == 'Prism']
        if not P: continue
        P = P[0]; pid = P['id']; pg += 1; pw += win; oid = {c['id'] for c in ch if c['team'] == cand}
        s = None; done_any = False
        for e in ev:
            if e['k'] == 'death' and e['v'] == pid and e.get('by') in oid: pdeaths += 1; pbag += e.get('gems', 0)
            if e['k'] == 'tribute_start' and e['a'] == pid: s = e
            elif e['k'] in ('tribute_end', 'tribute_cancel') and e['a'] == pid and s:
                if s['gems'] >= 100:
                    i0 = s['r'] - 1; i1 = min(e['r'], n) - 1
                    seen = any(any(x in oid for x in P['seenBy'][i]) for i in range(i0, i1 + 1))
                    if e['k'] == 'tribute_end':
                        A['done'] += 1; A['done_seen' if seen else 'done_unseen'] += 1; done_any = True
                        if R['gems'][1 - cand][i0] + s['gems'] >= 1000: A['done_win'] += 1
                    else:
                        A['cancel_' + str(e.get('cause'))] += 1; frac[e.get('cause')].append((e['r'] - s['r']) / max(1, s['dur']))
                    A['big'] += 1
                    near_deaths += sum(1 for d in ev if d['k'] == 'death' and 'linked' not in d and team[d['v']] == cand and s['r'] <= d['r'] <= e['r'] + 3 and cheb(d['at'], s['at']) <= 8)
                s = None
        if not win and done_any: lost_with_done += 1
    print(f"{os.path.basename(ext)}: games {games} win {wins / games:.3f} ({wins}) | vs Prism {pg}: {pw / max(1, pg):.3f} | rounds {rounds / games:.0f} | our deaths {deaths / games:.2f} (Vesper {vdeaths / games:.2f}) | Prism deaths to us {pdeaths / max(1, pg):.2f}, gems taken {pbag / max(1, pg):.0f}")
    print(f"   hoard tributes {A['big'] / max(1, pg):.2f}/game: completed {A['done'] / max(1, pg):.3f}/game ({A['done']}; seen {A['done_seen']}, unseen {A['done_unseen']}, winning {A['done_win']}); losses with one {lost_with_done}; cancels manual {A['cancel_manual']} stun {A['cancel_stun']} lock {A['cancel_lock']} death {A['cancel_death']}; channel share run before a cancel: " + ', '.join(f"{k} {st.mean(v):.2f}" for k, v in frac.items() if v) + f"; our deaths within 8 of it during one {near_deaths / max(1, pg):.2f}/game")
for x in sys.argv[1:]: run(x)
