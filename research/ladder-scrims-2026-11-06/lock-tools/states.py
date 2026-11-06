#!/usr/bin/env python3
"""states.py ANALYSIS_DIR OUT.jsonl CAND [--both] [--every N]: game states on one-site maps for the win and hold models.

Every N rounds (default 25), from CAND's side (and the opponent's too with --both, for self-play of two equal bots):
round, tributed lead, carried gems (ours, theirs, their biggest bag), gold, earned gold, alive, hp, strength, locks
carried, distances to the site, whose lock is on it, enemy channels there, and the outcome: won, and whether the enemy
landed any gems at the site from this round on (hold_ok)."""
import glob, gzip, json, os, sys

root, out, cand = sys.argv[1], sys.argv[2], sys.argv[3]
both = '--both' in sys.argv
every = int(sys.argv[sys.argv.index('--every') + 1]) if '--every' in sys.argv else 25
f = open(out, 'w')
ng = 0
for meta_p in sorted(glob.glob(f'{root}/*/meta.json')):
    d = os.path.dirname(meta_p)
    m = json.load(open(meta_p))
    names = [t['name'] for t in m['teams']]
    if cand not in names: continue
    mp = json.load(open(f'{root}/maps/{m["map"]["hash"]}.json'))
    alts = [tuple(a) for a in mp['altars']]
    if not alts or len(alts) > 2 or max(max(abs(a[0] - b[0]), abs(a[1] - b[1])) for a in alts for b in alts) > 3: continue
    R = json.load(gzip.open(f'{d}/rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(f'{d}/events.jsonl.gz', 'rt')]
    gems = R['gems']; n = len(R['round']); ch = R['champions']; champs = m['champions']
    cid_team = {c['id']: c['team'] for c in champs}
    land = [[] for _ in range(2)]  # (round, gems) of each team's landed tributes
    for e in ev:
        if e['k'] == 'tribute_end' and e['gems'] > 0: land[cid_team[e['a']]].append((e['r'], e['gems']))
    ng += 1
    sides = [names.index(cand)] + ([1 - names.index(cand)] if both else [])
    for us in sides:
        them = 1 - us
        ours = [k for k, c in enumerate(champs) if c['team'] == us]
        theirs = [k for k, c in enumerate(champs) if c['team'] == them]
        won = m['result']['winner'] == us
        comp = sorted(c['name'] for c in champs if c['team'] == them)
        for i in range(every - 1, n, every):
            r = R['round'][i]
            def dist(k):
                c = ch[k]
                if not c['alive'][i] or c['x'][i] is None: return 60
                return min(max(abs(c['x'][i] - a[0]), abs(c['y'][i] - a[1])) for a in alts)
            def s(ks, key): return sum(ch[k][key][i] or 0 for k in ks)
            def alive(ks): return [k for k in ks if ch[k]['alive'][i]]
            lk = R['locks'][i]
            row = dict(game=os.path.basename(d), map=m['map']['name'], us=us, R=r, L=gems[us][i] - gems[them][i],
                       gu=gems[us][i], gt=gems[them][i],
                       cu=sum(ch[k]['gems'][i] for k in alive(ours)), ct=sum(ch[k]['gems'][i] for k in alive(theirs)),
                       bt=max([ch[k]['gems'][i] for k in alive(theirs)] or [0]),
                       gold_u=s(ours, 'gold'), gold_t=s(theirs, 'gold'), earn_u=s(ours, 'earned'), earn_t=s(theirs, 'earned'),
                       au=len(alive(ours)), at=len(alive(theirs)), n=len(ours),
                       hp_u=sum(ch[k]['hp'][i] for k in alive(ours)), hp_t=sum(ch[k]['hp'][i] for k in alive(theirs)),
                       mhp_u=sum(ch[k]['maxHp'][i] for k in ours), mhp_t=sum(ch[k]['maxHp'][i] for k in theirs),
                       str_u=sum(ch[k]['str'][i] for k in alive(ours)), str_t=sum(ch[k]['str'][i] for k in alive(theirs)),
                       locks_u=sum(ch[k]['cons'][i][2] for k in alive(ours)), locks_t=sum(ch[k]['cons'][i][2] for k in alive(theirs)),
                       du=sorted(dist(k) for k in ours), dt=sorted(dist(k) for k in theirs),
                       lock_u=any(l[0] == us and (l[1], l[2]) in alts for l in lk), lock_t=any(l[0] == them and (l[1], l[2]) in alts for l in lk),
                       kills_u=s(ours, 'kills'), kills_t=s(theirs, 'kills'),
                       won=won, end=m['result']['rounds'],
                       land_t=sum(g for rr, g in land[them] if rr > r), land_u=sum(g for rr, g in land[us] if rr > r),
                       comp=comp)
            row['hold_ok'] = row['land_t'] == 0
            f.write(json.dumps(row) + '\n')
print(f'{ng} games -> {out}')
