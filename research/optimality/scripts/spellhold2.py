"""Damage spells held while farming: spell ready at the start of the champion's turn, attacking a camp this round
or last, a live monster within 4 at the end of the previous round; first 300 rounds. Split by an enemy within 6
(seen at turn start) or not, and walked / stood still. Excludes-walking spells cannot be cast after a walk.

  py spellhold2.py procless                                   # the report: PTN Hyperion vs procless head to head
  py spellhold2.py --team procless "Intercontinental Fish"    # any team's ladder games
  py spellhold2.py --src replays/batch-20261017-091937-928141 --team nemesis
Selection options: gamesel.py.
"""
import json, gzip, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
import gamesel
ROOT = gamesel.ROOT
SPELL = {'Stellar': [0, 1], 'Ryth': [0], 'Cassi': [0], 'Ren': [0], 'Prism': [0, 1], 'Tavi': [1], 'Marcella': [1]}
W = 300


def game(args):
    d, names, teams = args
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
    state = {}
    j = 0
    out = collections.Counter()
    nR = min(W, len(R['round']))
    cix = {x['id']: k for k, x in enumerate(R['champions'])}
    for i in range(1, nR):
        r = R['round'][i]
        while j < len(rows) and rows[j][0] <= R['round'][i - 1]:
            row = rows[j]; state[row[gi['group']]] = (row[gi['state']], row[gi['hp']]); j += 1
        alive_groups = [g for g, (s, hp) in state.items() if s == 1 and hp and hp > 0]
        for c in R['champions']:
            tn = names[c['team']]
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
                    enemy6 = any(R['champions'][cix[e]]['alive'][i - 1] and
                                 max(abs(p[0] - R['champions'][cix[e]]['x'][i - 1]), abs(p[1] - R['champions'][cix[e]]['y'][i - 1])) <= 6
                                 for e in seen)
                    fight = any(rr in fought[c['id']] for rr in range(r, r + 8))
                    key = ('enemy6' if enemy6 else 'noenemy') + '|' + nm + '|' + str(s) + '|' + ('walked' if (c['id'], r) in walked else 'still')
                    out[(tn, key)] += 1
                    out[(tn, key + '_cast')] += cast
                    out[(tn, key + '_fight')] += fight
    return out


def summary(tot, teams):
    """Per team, champion and slot: ready farming turns, walk share, cast share, cast share when still, fight share."""
    rows = []
    for t in teams:
        for env in ('noenemy', 'enemy6'):
            slots = sorted({tuple(k[1].split('|')[1:3]) for k in tot if k[0] == t and isinstance(k[1], str) and k[1].startswith(env + '|')})
            for nm, s in slots:
                still, walk = f'{env}|{nm}|{s}|still', f'{env}|{nm}|{s}|walked'
                n = tot[(t, still)] + tot[(t, walk)]
                if n:
                    cast = tot[(t, still + '_cast')] + tot[(t, walk + '_cast')]
                    fight = tot[(t, still + '_fight')] + tot[(t, walk + '_fight')]
                    rows.append((t, env, nm, int(s), n, tot[(t, walk)] / n, cast / n, tot[(t, still + '_cast')] / max(1, tot[(t, still)]), fight / n))
    return rows


if __name__ == '__main__':
    p = gamesel.parser(__doc__)
    p.add_argument('opp', nargs='?', help="PTN Hyperion's head-to-head games against OPP, every source copy (the report)")
    a = p.parse_args()
    if a.opp:
        a.team, a.together, a.copies = ['PTN Hyperion', a.opp], True, True
    teams = list(a.team or [])
    games = gamesel.select(a)
    tot = collections.Counter()
    with ProcessPoolExecutor(a.threads) as ex:
        for r in ex.map(game, [(d, names, set(teams)) for d, names in games]):
            tot += r
    for t in teams:
        for key in sorted({k[1] for k in tot if isinstance(k[1], str) and k[1].startswith('noenemy|') and not k[1].endswith(('_cast', '_fight'))}):
            n = tot[(t, key)]
            print(f"  {t[:14]:14s} farming+spell ready, {key:8s}: n {n:6d} cast {tot[(t, key + '_cast')] / max(1, n):.2f}  champion fight within 8 rounds {tot[(t, key + '_fight')] / max(1, n):.2f}")
        print(f"{t:14s} ready-turns {tot[(t, 'ready')]:7d} cast {tot[(t, 'ready_cast')] / max(1, tot[(t, 'ready')]):.2f}")
    print(f'\n{len(games)} games. Farming turns with the spell ready: n, walk share, cast share, cast share when still, champion fight within 8 rounds')
    for t, env, nm, s, n, walk, cast, still, fight in summary(tot, teams):
        print(f'  {t[:22]:22s} {env:8s} {nm:8s} s{s}  n {n:6d}  walk {walk:.2f}  cast {cast:.2f}  cast|still {still:.2f}  fight {fight:.2f}')
