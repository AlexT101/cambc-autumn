# Wasted spell opportunities: damage spell ready at the start of the champion's turn, a live monster of an
# alive group within 4 (unit range; ground reach 5 ignored) at the end of the previous round, and no cast that round.
import json, gzip, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
ROOT = r'C:\Users\alext\Github\cambc-autumn\replays\.analysis'
SPELL = {'Stellar': [0, 1], 'Ryth': [0], 'Cassi': [0], 'Ren': [0], 'Prism': [0, 1], 'Tavi': [1], 'Marcella': [1]}
W = 300


def game(args):
    d, teams = args
    m = json.load(open(os.path.join(ROOT, d, 'meta.json'), encoding='utf-8'))
    R = json.load(gzip.open(os.path.join(ROOT, d, 'rounds.json.gz')))
    ev = [json.loads(l) for l in gzip.open(os.path.join(ROOT, d, 'events.jsonl.gz'), 'rt')]
    mp = json.load(open(os.path.join(ROOT, 'maps', m['map']['hash'] + '.json')))
    name = {c['id']: c['name'] for c in m['champions']}
    casts = set()
    camp_casts = set()
    farming = set()
    walked = set()
    for e in ev:
        if e['k'] == 'move' or (e['k'] == 'cast' and e.get('moved')): walked.add((e['a'], e['r']))
    fought = collections.defaultdict(set)
    for e in ev:
        if e['k'] in ('attack', 'cast'):
            for v, amt in (e.get('dmg') or []):
                if amt > 0 and v in name and v != e['a']:
                    fought[e['a']].add(e['r']); fought[v].add(e['r'])
    enemy_near = set()
    for e in ev:
        if e['k'] == 'attack' and 'camp' in e:
            farming.add((e['a'], e['r']))
        if e['k'] == 'cast':
            casts.add((e['a'], e['r'], e['slot']))
            if e.get('cdmg'): camp_casts.add((e['a'], e['r'], e['slot']))
    # group alive state per round: forward fill groups rows [round, group, state, team, timer, respawn, awake, hp]
    cols = R['groupCols']
    gi = {c: i for i, c in enumerate(cols)}
    rows = sorted(R['groups'], key=lambda x: x[0])
    camp_pos = {}
    for c in mp['camps']:
        camp_pos.setdefault(c['group'], []).append((c['x'], c['y']))
    strengthful = {g['id']: any(t in ('Wolf', 'Elk', 'Monolith') for t in g['types']) for g in mp['groups']}
    state = {}
    j = 0
    out = collections.Counter()
    nR = min(W, len(R['round']))
    for i in range(1, nR):
        r = R['round'][i]
        while j < len(rows) and rows[j][0] <= R['round'][i - 1]:
            row = rows[j]; state[row[gi['group']]] = (row[gi['state']], row[gi['hp']]); j += 1
        alive_groups = [g for g, (s, hp) in state.items() if s == 1 and hp and hp > 0]
        for c in R['champions']:
            tn = m['teams'][c['team']]['name']
            if tn not in teams: continue
            nm = name[c['id']]
            if nm not in SPELL or not c['alive'][i - 1] or c['turn'][i] not in (1, 2): continue
            p = (c['x'][i - 1], c['y'][i - 1])
            near = ((c['id'], r) in farming or (c['id'], r - 1) in farming) and any(max(abs(p[0] - q[0]), abs(p[1] - q[1])) <= 4 for g in alive_groups for q in camp_pos.get(g, []))
            for s in SPELL[nm]:
                ready = c['cd%d' % s][i - 1] == 0
                if not ready: continue
                cast = (c['id'], r, s) in casts
                out[(tn, 'ready')] += 1
                out[(tn, 'ready_cast')] += cast
                if near:
                    seen = c['sees'][i]
                    enemy6 = any(R['champions'][[x['id'] for x in R['champions']].index(e)]['alive'][i - 1] and
                                 max(abs(p[0] - R['champions'][[x['id'] for x in R['champions']].index(e)]['x'][i - 1]),
                                     abs(p[1] - R['champions'][[x['id'] for x in R['champions']].index(e)]['y'][i - 1])) <= 6 for e in seen)
                    fight = any(rr in fought[c['id']] for rr in range(r, r + 8))
                    key = ('enemy6' if enemy6 else 'noenemy') + '|' + nm + '|' + str(s) + '|' + ('walked' if (c['id'], r) in walked else 'still')
                    out[(tn, key)] += 1
                    out[(tn, key + '_cast')] += cast
                    out[(tn, key + '_fight')] += fight
    return out


if __name__ == '__main__':
    opp = sys.argv[1]
    idxj = json.load(open(os.path.join(ROOT, 'index.json'), encoding='utf-8'))
    games = [g['dir'] for g in idxj['games'] if g['kind'] == 'ladder' and g['ok'] and 'PTN Hyperion' in g['teams'] and opp in g['teams'] and g['source'].split('/')[2][:8] >= '20261016']
    tot = collections.Counter()
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(game, [(d, {'PTN Hyperion', opp}) for d in games]):
            tot += r
    for t in ('PTN Hyperion', opp):
        for key in sorted({k[1] for k in tot if isinstance(k[1], str) and k[1].startswith('noenemy|') and not k[1].endswith(('_cast', '_fight'))}):
            n = tot[(t, key)]
            print(f"  {t[:14]:14s} farming+spell ready, {key:8s}: n {n:6d} cast {tot[(t, key + '_cast')] / max(1, n):.2f}  champion fight within 8 rounds {tot[(t, key + '_fight')] / max(1, n):.2f}")
        print(f"{t:14s} ready-turns {tot[(t, 'ready')]:7d} cast {tot[(t, 'ready_cast')] / max(1, tot[(t, 'ready')]):.2f} | "
              f"ready with a live camp within 4: {tot[(t, 'ready_near_camp')]:7d} cast {tot[(t, 'ready_near_camp_cast')] / max(1, tot[(t, 'ready_near_camp')]):.2f}")
