"""Damage spells left uncast while farming: spell ready at the start of the champion's turn, attacking a camp this
round or last, a live monster within 4 at the end of the previous round (unit range; ground reach 5 ignored), and
no cast that round; first 300 rounds. Cast rate by champion and slot.

  py spellwaste3.py procless                                  # the report: PTN Hyperion vs procless head to head
  py spellwaste3.py --team procless "Intercontinental Fish"   # any team's ladder games
  py spellwaste3.py --src replays/batch-20261017-091937-928141 --team nemesis
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
    farming = set()
    for e in ev:
        if e['k'] == 'attack' and 'camp' in e:
            farming.add((e['a'], e['r']))
        if e['k'] == 'cast':
            casts.add((e['a'], e['r'], e['slot']))
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
                    out[(tn, 'near')] += 1
                    out[(tn, 'near_cast')] += cast
                    out[(tn, nm, s, 'n')] += 1
                    out[(tn, nm, s, 'c')] += cast
    return out


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
    print(f'{len(games)} games')
    for t in teams:
        print(f"{t:14s} ready-turns {tot[(t, 'ready')]:7d} cast {tot[(t, 'ready_cast')] / max(1, tot[(t, 'ready')]):.2f} | "
              f"farming with a live camp within 4: {tot[(t, 'near')]:7d} cast {tot[(t, 'near_cast')] / max(1, tot[(t, 'near')]):.2f}")
    print('by champion/slot (actively farming, spell ready): cast rate')
    keys = sorted({k[:3] for k in tot if len(k) == 4}, key=lambda k: (k[1], k[2], k[0]))
    for k in keys:
        n = tot[k + ('n',)]; c = tot[k + ('c',)]
        print(f'   {k[0][:14]:14s} {k[1]:8s} s{k[2]}  n {n:5d} cast {c / max(1, n):.2f}')
