"""Camp tanking and attack resets (REPORT.md 10 and 11.3; definitions as subreports/replay.md, whole game).

Tanking: a group's engagement opens at the first champion damage to one of its monsters and closes when it is
cleared (dropped if it respawns first); camp damage taken by any champion while it is open counts. Kept: groups
cleared by one team, with >= 2 participants (champions that damaged it), melee and ranged among them. Per clear:
share of camp damage taken by melee champions and by the participant with the highest max health (clears with
any damage taken), melee share of damage dealt, champions hit.
Reset: turns on which a champion with an attack reset acted with the reset ready, and attacked or cast the reset;
'camp' turns attacked no champion. Share of those turns that cast the reset.

  py campshare.py                                             # ladder games of the top six and us since 10-16
  py campshare.py --src replays/batch-20261017-091937-928141 --team nemesis rival
Selection options: gamesel.py.
"""
import json, gzip, os, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
import gamesel
ROOT = gamesel.ROOT
MELEE = {'Ryth', 'Vendetta', 'Marcella', 'Ren', 'Varg', 'Issac'}
RESET_SLOT = {'Ryth': 1, 'Vesper Vale': 0, 'Vendetta': 0, 'Marcella': 0, 'Tavi': 0, 'Willow': 1, 'Varg': 0, 'Issac': 0}


def game(args):
    d, names = args
    m = json.load(open(os.path.join(ROOT, d, 'meta.json'), encoding='utf-8'))
    R = json.load(gzip.open(os.path.join(ROOT, d, 'rounds.json.gz')))
    mp = json.load(open(os.path.join(ROOT, 'maps', m['map']['hash'] + '.json')))
    ev = sorted((json.loads(l) for l in gzip.open(os.path.join(ROOT, d, 'events.jsonl.gz'), 'rt')), key=lambda e: e['s'])
    name = {c['id']: c['name'] for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    ch = {c['id']: c for c in R['champions']}
    camp_group = {c['id']: c['group'] for c in mp['camps']}
    nR = len(R['round'])
    clears, reset = [], collections.Counter()
    eng = {}
    acts = collections.defaultdict(list)
    for e in ev:
        k = e['k']
        if e['r'] < 2:
            continue
        if k in ('attack', 'cast') and e.get('a') in team:
            acts[(e['r'], e['a'])].append(e)
        if k in ('attack', 'cast'):
            for cid, amt in e.get('cdmg') or []:
                g = camp_group.get(cid)
                if g is None:
                    continue
                x = eng.setdefault(g, {'dealt': collections.Counter(), 'taken': collections.Counter()})
                x['dealt'][e['a']] += amt
        elif k == 'camp_attack' and e['g'] in eng:
            x = eng[e['g']]
            if e.get('tgt') in team:
                x['taken'][e['tgt']] += e.get('dmg', 0) or 0
            for v, amt in e.get('xdmg') or []:
                if v in team:
                    x['taken'][v] += amt
        elif k == 'group_respawn':
            eng.pop(e['g'], None)
        elif k == 'group_clear':
            x = eng.pop(e['g'], None)
            if x is None or e.get('by') not in team:
                continue
            i0 = min(max(0, e['r'] - 2), nR - 1)
            clears.append((names[team[e['by']]], {c: (name[c], team[c], v) for c, v in x['dealt'].items()},
                           {c: (name[c], v) for c, v in x['taken'].items()}, {c: ch[c]['maxHp'][i0] for c in x['dealt']}))
    for i in range(1, nR):
        r = R['round'][i]
        if r < 2:
            continue
        for c in R['champions']:
            nm = name[c['id']]
            rs = RESET_SLOT.get(nm)
            if rs is None or c['turn'][i] != 1 or c['cd%d' % rs][i - 1] != 0:
                continue
            tev = acts.get((r, c['id']), [])
            used = any(e['k'] == 'cast' and e.get('slot') == rs for e in tev)
            att_ch = any(e['k'] == 'attack' and e.get('tgt') in team for e in tev)
            att_cp = any(e['k'] == 'attack' and 'camp' in e for e in tev)
            if att_ch or att_cp or used:
                kind = 'champ' if att_ch else 'camp'
                t = names[c['team']]
                for key in ((t, kind), (t, kind, nm)):
                    reset[key + ('n',)] += 1
                    reset[key + ('used',)] += used
    return clears, reset


if __name__ == '__main__':
    p = gamesel.parser(__doc__, team=gamesel.TOPS)
    a = p.parse_args()
    games = gamesel.select(a)
    clears, reset = [], collections.Counter()
    with ProcessPoolExecutor(a.threads) as ex:
        for cl, rs in ex.map(game, games, chunksize=8):
            clears += cl; reset += rs
    print(f'{len(games)} games. Mixed melee+ranged single-team clears: n, camp damage taken by melee, dealt by melee, '
          'taken by the max-HP participant, participants hit')
    for t in a.team:
        mixed = [c for c in clears if c[0] == t and len({v[1] for v in c[1].values()}) == 1 and len(c[1]) >= 2
                 and {v[0] in MELEE for v in c[1].values()} == {True, False}]
        if not mixed:
            continue
        mel, top, hit = [], [], []
        for _, dealt, taken, maxhp in mixed:
            tot = sum(v for _, v in taken.values())
            if tot <= 0:
                continue
            mel.append(sum(v for nm, v in taken.values() if nm in MELEE) / tot)
            mx = max(dealt, key=lambda x: maxhp.get(x, 0))
            top.append(taken.get(mx, (None, 0))[1] / tot)
            hit.append(sum(1 for _, v in taken.values() if v > 0))
        dmg_mel = [sum(v for nm, _, v in dealt.values() if nm in MELEE) / max(1, sum(v for _, _, v in dealt.values())) for _, dealt, _, _ in mixed]
        print(f'  {t[:22]:22s} {len(mixed):6d}  taken by melee {st.mean(mel):.2f}  dealt by melee {st.mean(dmg_mel):.2f}  '
              f'taken by max-HP {st.mean(top):.2f}  hit {st.mean(hit):.2f}')
    print('Attack reset used on ready turns: camp-attack turns, champion-attack turns; then camp turns by champion')
    for t in a.team:
        n1, n2 = reset[(t, 'camp', 'n')], reset[(t, 'champ', 'n')]
        if not n1 + n2:
            continue
        print(f"  {t[:22]:22s} camp {n1:7d} used {reset[(t, 'camp', 'used')] / max(1, n1):.2f}   champ {n2:6d} used {reset[(t, 'champ', 'used')] / max(1, n2):.2f}   "
              + '  '.join(f"{nm} {reset[(t, 'camp', nm, 'used')] / reset[(t, 'camp', nm, 'n')]:.2f} ({reset[(t, 'camp', nm, 'n')]})"
                          for nm in sorted(RESET_SLOT) if reset[(t, 'camp', nm, 'n')]))
