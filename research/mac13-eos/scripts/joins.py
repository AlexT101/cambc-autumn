"""Who joins a fight: at the first champion hit of an engagement, every other alive champion within 8 of the target,
by side (attacker's team / target's team): in the next 3 rounds did it hit a champion, hit a camp, or neither.
Engagement start: a cross-team champion hit with no cross-team champion hit within 10 tiles in the previous 6 rounds.
Outcome: champion deaths within 15 rounds, within 10 of the target."""
import gzip, json, sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))

def g(d):
    meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
    names = {int(c['id']): c['name'] for c in meta['champions']}; team = {int(c['id']): int(c['team']) for c in meta['champions']}
    ch = {int(c['id']): c for c in R['champions']}
    import zipfile
    br = {}
    try:
        z = zipfile.ZipFile(meta['source'])
        for f in ('team-a.stdout', 'team-b.stdout'):
            for line in z.read(f).decode(errors='replace').splitlines():
                if line.startswith('D '):
                    p = line.split(); br[(int(p[1]), int(p[2]))] = p[3]
    except Exception: pass
    n = len(next(iter(ch.values()))['x'])
    def pos(c, r):
        i = min(max(0, r-1), n-1)
        x = ch[c]['x'][i]
        return None if x is None or not ch[c]['alive'][i] else (x, ch[c]['y'][i])
    hits = collections.defaultdict(set)   # (round, attacker) -> 'champ'/'camp'
    chits = []                            # (round, attacker, victim)
    deaths = []
    for l in gzip.open(d/'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        k = e['k']
        if k in ('attack', 'cast'):
            a = e.get('a')
            if a is None: continue
            if e.get('dmg'):
                for v, dm in e['dmg']:
                    if v in team and team[v] != team[a] and dm > 0:
                        hits[(e['r'], a)].add('champ'); chits.append((e['r'], a, v))
            if e.get('stun'):
                for v in e['stun']:
                    if v in team and team[v] != team[a]: hits[(e['r'], a)].add('champ'); chits.append((e['r'], a, v))
            if e.get('cdmg') or e.get('camp') is not None: hits[(e['r'], a)].add('camp')
        elif k == 'death':
            deaths.append((e['r'], e['v'], e['at']))
    out = []
    last = []
    for (r, a, v) in chits:
        pv = pos(v, r)
        if pv is None: continue
        if any(r - rr <= 6 and rr < r and cheb(pp, pv) <= 10 for rr, pp in last):
            last.append((r, pv)); continue
        last.append((r, pv))
        if r > 900: continue
        ta = team[a]
        row = dict(r=r, att={'champ': 0, 'camp': 0, 'none': 0, 'n4': 0}, dfn={'champ': 0, 'camp': 0, 'none': 0, 'n4': 0}, att_names=[], dfn_names=[])
        for c in ch:
            if c in (a, v): continue
            pc = pos(c, r)
            if pc is None or cheb(pc, pv) > 8: continue
            did = set()
            for rr in range(r, r+3): did |= hits.get((rr, c), set())
            kind = 'champ' if 'champ' in did else 'camp' if 'camp' in did else 'none'
            side = row['att'] if team[c] == ta else row['dfn']
            side[kind] += 1
            if cheb(pc, pv) <= 4: side['n4'] += 1
            (row['att_names'] if team[c] == ta else row['dfn_names']).append((names[c], kind))
            row.setdefault('br', []).append(('att' if team[c] == ta else 'dfn', kind, br.get((r, c), '?'), cheb(pc, pv)))
        dd = [(rr, vv) for rr, vv, at in deaths if r <= rr <= r+15 and cheb(at, pv) <= 10]
        row['att_dead'] = sum(1 for _, vv in dd if team[vv] == ta)
        row['dfn_dead'] = sum(1 for _, vv in dd if team[vv] != ta)
        row['target_dead'] = any(vv == v for _, vv in dd)
        row['attacker_dead'] = any(vv == a for _, vv in dd)
        row['aname'] = names[a]; row['vname'] = names[v]; row['abr'] = br.get((r, a), '?')
        out.append(row)
    return out

if __name__ == '__main__':
    dirs = [d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: E = [x for r in ex.map(g, dirs, chunksize=8) for x in r]
    print('engagements (r<=900)', len(E), 'per game', round(len(E)/len(dirs), 2))
    for s in ('att', 'dfn'):
        t = collections.Counter()
        for e in E:
            for k in ('champ', 'camp', 'none'): t[k] += e[s][k]
        tot = sum(t.values())
        print(f' {s} bystanders within 8: {tot/len(E):.2f} a fight; join {t["champ"]/tot:.2f} camp {t["camp"]/tot:.2f} neither {t["none"]/tot:.2f}')
    by = collections.defaultdict(collections.Counter)
    for e in E:
        for s in ('att', 'dfn'):
            for nm, kind in e[s + '_names']: by[(s, nm)][kind] += 1
    print(' by champion (side, name): n join camp neither')
    for (s, nm), c in sorted(by.items(), key=lambda x: -sum(x[1].values()))[:24]:
        t = sum(c.values()); print(f'   {s} {nm:14s} {t:6d} {c["champ"]/t:.2f} {c["camp"]/t:.2f} {c["none"]/t:.2f}')
    # outcome by joined counts
    tab = collections.defaultdict(lambda: [0, 0, 0, 0])
    for e in E:
        k = (min(e['att']['champ'], 3), min(e['dfn']['champ'], 3))
        tab[k][0] += 1; tab[k][1] += e['target_dead']; tab[k][2] += e['att_dead']; tab[k][3] += e['dfn_dead']
    print(' (attackers joining, defenders joining): n, target died, attacker-side deaths, defender-side deaths (per fight)')
    for k in sorted(tab):
        n, td, ad, dd = tab[k]
        if n >= 30: print(f'   {k} {n:6d} {td/n:.3f} {ad/n:.3f} {dd/n:.3f}')
    # camp-hitters: what if they had joined? compare fights with >=1 attacker bystander on camp vs none
    for s in ('att', 'dfn'):
        a = [e for e in E if e[s]['camp'] > 0]; b = [e for e in E if e[s]['camp'] == 0 and (e[s]['champ'] + e[s]['none']) > 0]
        f = lambda S: (round(sum(x['att_dead'] for x in S)/len(S), 3), round(sum(x['dfn_dead'] for x in S)/len(S), 3))
        print(f' {s}: fights with a bystander on a camp n {len(a)} (att, dfn deaths) {f(a)}; without, with bystanders, n {len(b)} {f(b)}')

    for s in ('att','dfn'):
        for kind in ('none','camp','champ'):
            c = collections.Counter(b for e in E for (ss, kk, b, dd) in e.get('br', []) if ss == s and kk == kind)
            t = sum(c.values()); print(f' {s} {kind} branches:', [(k, round(v/t, 3)) for k, v in c.most_common(9)])
        c = collections.Counter(dd for e in E for (ss, kk, b, dd) in e.get('br', []) if ss == s and kk == 'none')
        print(f' {s} none: distance to target', sorted(c.items()))
    print(' by attacker bystanders within 4 of target at the first hit (n4), defenders within 4: target died / attacker-side deaths')
    tab = collections.defaultdict(lambda: [0, 0, 0])
    for e in E:
        k = (min(e['att']['n4'], 3), min(e['dfn']['n4'], 3))
        tab[k][0] += 1; tab[k][1] += e['target_dead']; tab[k][2] += e['att_dead']
    for k in sorted(tab):
        n, td, ad = tab[k]
        if n >= 50: print(f'   {k} {n:6d} {td/n:.3f} {ad/n:.3f}')

    print(' lone attacker (n4 att 0) into 2+ defenders within 4: by attacker, branch')
    S = [e for e in E if e['att']['n4'] == 0 and e['dfn']['n4'] >= 2]
    print('   n', len(S), 'attacker dies', round(sum(e['attacker_dead'] for e in S)/len(S), 3), 'target dies', round(sum(e['target_dead'] for e in S)/len(S), 3))
    for k, v in collections.Counter(e['aname'] for e in S).most_common(8):
        SS = [e for e in S if e['aname'] == k]
        print('   ', k, v, 'att dies', round(sum(e['attacker_dead'] for e in SS)/v, 3), 'tgt dies', round(sum(e['target_dead'] for e in SS)/v, 3), collections.Counter(e['abr'] for e in SS).most_common(5))
    print('   victims', collections.Counter(e['vname'] for e in S).most_common(6))
