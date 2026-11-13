"""joinrate.py EXTRACT_DIR: joins.py split by team name. Who joins a fight: at the first champion hit of an engagement, every other alive champion within 8 of the target,
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
        row = dict(ateam=[t['name'] for t in meta['teams']][ta], r=r, att={'champ': 0, 'camp': 0, 'none': 0, 'n4': 0}, dfn={'champ': 0, 'camp': 0, 'none': 0, 'n4': 0}, att_names=[], dfn_names=[])
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
        out.append(row)
    return out

if __name__ == '__main__':
    dirs = [d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: E = [x for r in ex.map(g, dirs, chunksize=8) for x in r]
    names = sorted(set(e['ateam'] for e in E))
    print('games', len(dirs), 'engagements (r<=900)', len(E))
    for nm in names:
        A = [e for e in E if e['ateam'] == nm]; D = [e for e in E if e['ateam'] != nm]
        at = collections.Counter(); df = collections.Counter()
        for e in A:
            for k in ('champ', 'camp', 'none'): at[k] += e['att'][k]
        for e in D:
            for k in ('champ', 'camp', 'none'): df[k] += e['dfn'][k]
        ta, td = sum(at.values()), sum(df.values())
        print(f"{nm:14s} starts {len(A)/len(dirs):.2f}/game; as attacker: bystanders {ta/max(1,len(A)):.2f} join {at['champ']/max(1,ta):.3f} camp {at['camp']/max(1,ta):.3f}"
              f" target dies {sum(e['target_dead'] for e in A)/max(1,len(A)):.3f} own deaths {sum(e['att_dead'] for e in A)/max(1,len(A)):.3f} their deaths {sum(e['dfn_dead'] for e in A)/max(1,len(A)):.3f}")
        print(f"{'':14s} as defender: bystanders {td/max(1,len(D)):.2f} join {df['champ']/max(1,td):.3f} camp {df['camp']/max(1,td):.3f}"
              f" own deaths {sum(e['dfn_dead'] for e in D)/max(1,len(D)):.3f} their deaths {sum(e['att_dead'] for e in D)/max(1,len(D)):.3f}")
