"""Opening farm efficiency tables from open2.jsonl.gz: Mite against its opponents (r7 live = against us; v1/v2 ranked)."""
import gzip, json, os, collections, sys
import fl
P = os.path.expanduser('~/tmp-offload/mitere/open2.jsonl.gz')
GR = sys.argv[1:] or ['r7', 'v2']
def vg(g):
    if g['src'] == 'live': return 'r7'
    e = int(g['ver'][1:]); return 'v0' if e == 0 else ('v1' if e <= 7 else 'v2')
G = [g for g in (json.loads(l) for l in gzip.open(P, 'rt')) if vg(g) in GR]
for g in G:
    g['vg'] = vg(g); g['name'] = {c[0]: c[2] for c in g['champs']}; g['team'] = {c[0]: c[1] for c in g['champs']}
def guard(types): return 'monster' if any(t in ('Wolf', 'Elk', 'Golem', 'Monolith') for t in types) else 'cluster'
for v in GR:
    gs = [g for g in G if g['vg'] == v]
    print(f'==== {v}: {len(gs)} games')
    for who in ('M', 'O'):
        T = lambda g: g['mite'] if who == 'M' else 1 - g['mite']
        E = {r: fl.mean(g['earned'][str(r)][T(g)] for g in gs) for r in (50, 100, 150, 200)}
        capg = collections.defaultdict(list); capn = collections.defaultdict(list); base = collections.defaultdict(list); vesp = [0, 0]
        for g in gs:
            t = T(g)
            for lim in (100, 200):
                cs = [x for x in g['eps'] if x['cap'] and x['cap'][1] == t and x['cap'][0] <= lim]
                capn[lim].append(len(cs)); capg[lim].append(sum(s[2] for x in cs for s in x['cap'][2])); base[lim].append(sum(x['gold'] for x in cs))
            for x in g['eps']:
                if x['cap'] and x['cap'][1] == t and x['cap'][0] <= 200 and x['gold'] > 0:
                    vesp[0] += 1; vesp[1] += any(g['name'][s[0]] == 'Vesper Vale' for s in x['cap'][2])
        print(f' {who}: earned r50/100/150/200 ' + '/'.join(f'{E[r]:.0f}' for r in (50, 100, 150, 200)) +
              f' | captures by r100 {fl.mean(capn[100]):.1f} (capture gold {fl.mean(capg[100]):.0f}, base {fl.mean(base[100]):.0f}), by r200 {fl.mean(capn[200]):.1f} '
              f'(gold {fl.mean(capg[200]):.0f}, base {fl.mean(base[200]):.0f}, x{fl.mean(capg[200])/max(1,fl.mean(base[200])):.2f}) | gold captures by Vesper {vesp[1]/max(1,vesp[0]):.0%}')
        # clear episodes by this team (team hit it and the clear's last hit is its own)
        eps = [(g, x) for g in gs for x in g['eps'] if x['t'] == T(g) and x['by'] == T(g) and x['hit0'] <= 200]
        print(f'   clears by r200 {len(eps)/len(gs):.1f}/game; stolen by the enemy after our hits {sum(1 for g in gs for x in g["eps"] if x["t"]==T(g) and x["by"] is not None and x["by"]!=T(g) and x["hit0"]<=200)/len(gs):.2f}/game')
        by = collections.defaultdict(list)
        for g, x in eps: by[fl.gtype(x['types'])].append((g, x))
        for ty, lst in sorted(by.items(), key=lambda kv: -len(kv[1])):
            if len(lst) < 40: continue
            dur = [x['clear'] - x['hit0'] + 1 for g, x in lst]; na = [len(x['att']) for g, x in lst]
            spread = [max(a[0] for a in x['att'].values()) - min(a[0] for a in x['att'].values()) for g, x in lst if len(x['att']) >= 2]
            hpr = [x['hp'] / (x['clear'] - x['hit0'] + 1) for g, x in lst]
            caplat = [x['cap'][0] - x['clear'] for g, x in lst if x['cap'] and x['cap'][1] == T(g)]
            lost = sum(1 for g, x in lst if x['cap'] and x['cap'][1] != T(g)) / len(lst)
            bodyrounds = [len(x['att']) * (x['clear'] - x['hit0'] + 1) for g, x in lst]
            print(f'   {ty:8s} n/game {len(lst)/len(gs):.2f} gold {fl.mean(x["gold"] for g,x in lst):.0f} gems {fl.mean(x["gems"] for g,x in lst):.0f} dist {fl.med([x["dist"] for g,x in lst])} rank {fl.med([x["rank"] for g,x in lst])} | '
                  f'rounds hit->clear median {fl.med(dur)} mean {fl.mean(dur):.1f}; attackers {fl.mean(na):.2f}; arrival spread median {fl.med(spread)}; hp/round {fl.mean(hpr):.0f}; body-rounds {fl.mean(bodyrounds):.1f} | '
                  f'clear->capture {fl.med(caplat)}; enemy captured {lost:.0%}')
        # order: first 6 clears per game, distance rank and type
        firsts = collections.defaultdict(collections.Counter); fr = collections.defaultdict(list)
        for g in gs:
            xs = sorted([x for x in g['eps'] if x['t'] == T(g) and x['by'] == T(g)], key=lambda x: x['clear'])[:6]
            for i, x in enumerate(xs):
                firsts[i][fl.gtype(x['types'])] += 1; fr[i].append((x['rank'], x['clear'], len(x['att']), x['gold'], x['gems']))
        print('   clear #: round median, distance rank median, attackers mean, gold/gems mean, top types')
        for i in range(6):
            if not fr[i]: continue
            n = len(fr[i])
            print(f'     #{i+1}: r{fl.med([f[1] for f in fr[i]])} rank {fl.med([f[0] for f in fr[i]])} att {fl.mean(f[2] for f in fr[i]):.2f} gold {fl.mean(f[3] for f in fr[i]):.0f} gems {fl.mean(f[4] for f in fr[i]):.0f} | ' +
                  ', '.join(f'{k} {c/n:.0%}' for k, c in firsts[i].most_common(4)))
        # what clear attackers do between the clear and the capture: hit another group first?
        mv = [0, 0, 0]
        for g in gs:
            t = T(g); xs = [x for x in g['eps'] if x['t'] == t]
            for x in xs:
                if x['by'] != t or not x['cap'] or x['cap'][1] != t or x['clear'] > 200: continue
                capturers = {str(s[0]) for s in x['cap'][2]}
                for a in x['att']:
                    if a in capturers: continue
                    mv[0] += 1
                    nxt = [y['att'][a][0] for y in xs if y is not x and a in y['att'] and y['att'][a][0] >= x['clear']]
                    if nxt and min(nxt) <= x['cap'][0]: mv[1] += 1
                    if nxt and min(nxt) <= x['clear'] + 10: mv[2] += 1
        print(f'   non-capturing clearers: hit the next group before the capture lands {mv[1]/max(1,mv[0]):.0%}, within 10 rounds of the clear {mv[2]/max(1,mv[0]):.0%} (n {mv[0]})')
        # gap from a team clear to the team's next first hit
        gaps = []
        for g in gs:
            t = T(g); xs = sorted([x for x in g['eps'] if x['t'] == t], key=lambda x: x['hit0'])
            cl = sorted(x['clear'] for x in xs if x['by'] == t and x['clear'] <= 200)
            h0 = [x['hit0'] for x in xs]
            for c in cl:
                nx = [h for h in h0 if h > c]
                if nx: gaps.append(min(nx) - c)
        print(f'   team gap clear -> next first hit: median {fl.med(gaps)} p75 {fl.q(gaps,.75)}; overlapping (next hit before clear) share n/a')
        # activity
        A = collections.Counter(); n = 0
        for g in gs:
            for cid, a in g['act'].items():
                if g['team'][int(cid)] != T(g): continue
                A.update(a)
        tot = sum(A.values())
        print('   body-rounds r2-200: ' + ', '.join(f'{k} {A[k]/tot:.0%}' for k in ('camp', 'hold', 'move', 'idle', 'chan', 'champ', 'dead')))
        cl = [sum(g['clump'][str(T(g))][i] for g in gs if len(g['clump'][str(T(g))]) > i) / max(1, sum(1 for g in gs if len(g['clump'][str(T(g))]) > i)) for i in range(0, 40, 4)]
        print('   largest clump share every 20 rounds: ' + ' '.join(f'{c:.2f}' for c in cl))
