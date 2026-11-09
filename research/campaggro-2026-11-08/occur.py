"""How often a sleeping high-Strength camp could be woken onto an enemy champion, and whether teams do it.

Usage: python3 occur.py ANA_DIR [games.json] [--ours NAME]
  Live: ANA_DIR = ~/tmp-offload/bigl/ana, games.json gives our side per match id.
  Local: ANA_DIR = an extract.mjs --out dir of an ab.py batch; --ours picks the team name from meta.sources.

Opportunity for team T at the end of round r (the positions the next camp phase uses):
  group monsters up and all asleep; a monster of type M has an enemy-of-T champion within its range,
  strictly nearer than every T champion ('tie' when equal); some T champion is within WAKE of a member.
'persist' = the same holds at the end of r+1 (wake in r+1, the attack at camp phase r+2 uses r+1's positions).
Aggro wake = group_wake by a champion whose group's camp attacks in the next 6 rounds hit only the waker's enemies.
"""
import json, gzip, os, sys, collections
from multiprocessing import Pool

RANGE = {'Monolith': 5, 'Golem': 4, 'Elk': 4, 'Wolf': 3}
STR = {'Monolith': 200, 'Golem': 120, 'Elk': 60, 'Wolf': 20}
WAKE = 4  # ranged attack 3 (+0), ground spell 4 (+1 area), melee 1 + walk 1
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))

def game(args):
    d, our = args
    meta = json.load(open(d + '/meta.json'))
    mp = json.load(open(os.path.join(d, meta['mapFile'])))
    R = json.load(gzip.open(d + '/rounds.json.gz'))
    ch = R['champions']; team = {c['id']: c['team'] for c in ch}
    camps = {c['id']: c for c in mp['camps']}
    groups = {g['id']: g for g in mp['groups']}
    big = {g: [camps[c] for c in G['camps'] if camps[c]['type'] in RANGE] for g, G in groups.items()}
    # forward-filled group rows by round index
    gstate = {}; rows = collections.defaultdict(list)
    for row in R['groups']: rows[row[0]].append(row)
    out = collections.Counter(); ep = collections.Counter(); last = {}
    nr = len(R['round'])
    cond = []  # per round index: set of (T, g, type, kind)
    for i in range(nr):
        for row in rows.get(R['round'][i], []): gstate[row[1]] = row
        pos = {}
        for c in ch:
            if c['alive'][i] and c['x'][i] is not None: pos[c['id']] = (c['x'][i], c['y'][i])
        s = set()
        for g, mons in big.items():
            st = gstate.get(g)
            if not mons or st is None or st[2] != 1 or st[6] != 0: continue
            for T in (0, 1):
                mine = [p for k, p in pos.items() if team[k] == T]; theirs = [p for k, p in pos.items() if team[k] != T]
                if not mine or not theirs: continue
                wake = min(cheb(p, (m['x'], m['y'])) for p in mine for m in [camps[c] for c in groups[g]['camps']])
                if wake > WAKE: continue
                # waker safe: no member would hit T (nearest within its range is not T, ties counted unsafe)
                safe = True
                for m in mons:
                    mm = (m['x'], m['y']); dT = min(cheb(p, mm) for p in mine); dE = min(cheb(p, mm) for p in theirs)
                    if dT <= RANGE[m['type']] and dT <= dE: safe = False
                for m in mons:
                    mm = (m['x'], m['y']); dT = min(cheb(p, mm) for p in mine); dE = min(cheb(p, mm) for p in theirs)
                    if dE > RANGE[m['type']]: continue
                    kind = 'strict' if dE < dT else ('tie' if dE == dT else None)
                    if kind: s.add((T, g, m['type'], kind, safe))
        cond.append(s)
    res = collections.Counter()
    for i in range(nr - 1):
        for (T, g, ty, kind, safe) in cond[i]:
            side = 'us' if T == our else 'opp'
            res[(side, ty, kind, safe, 'round')] += 1
            if any(x[:4] == (T, g, ty, kind) for x in cond[i + 1]):
                res[(side, ty, kind, safe, 'persist')] += 1
                key = (T, g, ty, kind)
                if last.get(key) != i - 1: res[(side, ty, kind, safe, 'episode')] += 1
                last[key] = i
    # observed aggro wakes
    ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    gtypes = {g: set(G['types']) for g, G in groups.items()}
    wakes = [(e['r'], e['g'], e.get('by')) for e in ev if e['k'] == 'group_wake']
    atk = collections.defaultdict(list)
    for e in ev:
        if e['k'] == 'camp_attack': atk[e['g']].append((e['r'], e['tgt'], e['dmg'], camps[e['camp']]['type']))
    for r, g, by in wakes:
        if by is None or by not in team: continue
        hits = [(rr, t, dm, ty) for rr, t, dm, ty in atk[g] if r < rr <= r + 6]
        if not hits: continue
        en = sum(dm for _, t, dm, _ in hits if team.get(t) != team[by]); ow = sum(dm for _, t, dm, _ in hits if team.get(t) == team[by])
        side = 'us' if team[by] == our else 'opp'
        topty = max((t for t in gtypes[g] if t in STR), key=lambda t: STR[t], default='-')
        if en > 0 and ow == 0: res[(side, topty, 'aggro_wake', en)] += 1
        elif en > 0: res[(side, topty, 'mixed_wake', en, ow)] += 1
    return d, res

if __name__ == '__main__':
    ana = sys.argv[1]
    idx = json.load(open(ana + '/index.json'))['games']
    jobs = []
    if len(sys.argv) > 2 and sys.argv[2].endswith('.json'):
        G = json.load(open(sys.argv[2]))
        for g in idx:
            mid = os.path.basename(g['source']).split('.')[0]
            if mid in G and G[mid]['version'] in (86, 87, 88, 89):
                jobs.append((ana + '/' + g['dir'], 0 if G[mid]['side'] == 'a' else 1))
    else:
        name = sys.argv[sys.argv.index('--ours') + 1]
        for g in idx:
            if name in g['teams']: jobs.append((ana + '/' + g['dir'], g['teams'].index(name)))
    tot = collections.Counter(); per = []
    with Pool(32) as p:
        for d, r in p.imap_unordered(game, jobs, chunksize=4):
            tot.update(r); per.append((d, r))
    print('games', len(jobs))
    for k, v in sorted(tot.items(), key=lambda kv: str(kv[0])):
        if k[2] in ('aggro_wake', 'mixed_wake'): continue
        print(k, v)
    agg = collections.Counter(); dmg = collections.Counter()
    for k, v in tot.items():
        if k[2] in ('aggro_wake', 'mixed_wake'): agg[(k[0], k[1], k[2])] += v; dmg[(k[0], k[1], k[2])] += v * k[3]
    for k in sorted(agg): print('WAKE', k, agg[k], 'enemy dmg', dmg[k])
    json.dump([(d, [[list(map(str, k)), v] for k, v in r.items()]) for d, r in per], open(sys.argv[-1] + '.per.json' if sys.argv[-1].endswith('out') else os.path.expanduser('~/tmp-offload/campaggro/occur-per.json'), 'w'))
