"""Combat-micro observations for Fish (MICRO.md): one row per Fish turn in contact.

A row is an alive Fish turn whose start perspective shows a living enemy champion within 6.
Inputs come from the actor's own perspectives (turn start and each action's before-state, the
existing caches in combat_common.COHORTS). Two observer-derived inputs are kept apart under
`ctx` and are causal but not necessarily readable by Fish: what earlier actors did this round
(they precede the actor, and an ally could post its target in the 8 shared bytes) and the
actor's own previous turn. Labels (`y`) come from the observer decode (micro_decode.mjs): every
champion and camp effect of every action, with kills and stuns.

    python3 tools/fish/micro_rows.py COHORT [--jobs N]   # -> replays/fish-micro/<cohort>-micro-v1.jsonl.gz
"""
import argparse
import gzip
import json
import multiprocessing as mp
from pathlib import Path

from breadth import RANGED, dist, xy
from combat_common import COHORTS, ehp, load, one_turn_damage, shield, stun_timer, stunned_next
from misc_rows import spawn_tiles

OBS = Path('replays/fish-micro/obs')
CAMP_RANGE = {0: 3, 1: 4, 4: 5, 5: 4}   # Wolf, Elk, Monolith, Golem; clusters never attack
NB = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]


def effects(acts, team, side):
    """Per action: champion effects split into enemy/ally, camps damaged; from observer diffs."""
    out = []
    for a in acts:
        if a[0] not in ('Attack', 'Cast ability'):
            continue
        dm = []
        for cid, e0, e1, alive, s0, s1, k in a[6]:
            dm.append(dict(id=cid, foe=team[cid] != side, dmg=round(e0 - e1, 1), dead=int(not alive and e0 > 0),
                           stun=int(s1 > s0 and s1 > 0), kills=k))
        out.append(dict(kind=a[0], to=[a[1], a[2]], slot=a[3], ab=a[4], step=a[5], champs=dm,
                        camps=[[c, h0, h1] for c, h0, h1 in a[7]]))
    return out


def erow(e, pos, me, bush):
    d = dist(pos, xy(e))
    return dict(id=e['id'], type=e['type'], x=e['x'], y=e['y'], d=d, hp=e['hp'], maxhp=e['maxHp'], sh=shield(e),
                str=e['strength'], focus=e['focus'], gems=e.get('gems', 0), cd=e['cd'], ch=e.get('channelType', 0),
                ct=e.get('channelTimer', 0), stun=stun_timer(e), bush=int(xy(e) in bush),
                threat=0.0 if stunned_next(e) else one_turn_damage(e, d), mine=one_turn_damage(me, d))


def game_rows(args):
    name, cache, entry = args
    g = load(cache, entry)
    key = entry['sha256'][:16]
    with gzip.open(OBS / f'{key}.json.gz') as f:
        o = json.load(f)
    side = g['side']
    team = {c['id']: c['team'] for c in o['roster']}
    m = g['map']
    walls, holes = set(map(tuple, m['walls'])), set(map(tuple, m['holes']))
    altars, bush = set(map(tuple, m['altars'])), set(map(tuple, m['bushes']))
    home, ehome = spawn_tiles(m, side), spawn_tiles(m, 1 - side)
    static = walls | holes | altars | ehome
    W, H = m['width'], m['height']
    rounds = {R['r']: R for R in o['rounds']}
    # Every action's effects, by round, in turn order.
    eff = {r: [(t['id'], effects(t['acts'], team, side)) for t in R['turns']] for r, R in rounds.items()}
    rows = []
    for t in g['turns']:
        s = t['start']; me = s['me']
        if not me['alive'] or 'x' not in me:
            continue
        pos = xy(me)
        enemies = [e for e in s['enemies'] if 'x' in e and e.get('alive', True)]
        if not enemies or min(dist(pos, xy(e)) for e in enemies) > 6:
            continue
        R = rounds.get(t['round'])
        if R is None:
            continue
        order = [x['id'] for x in R['turns']]
        if t['id'] not in order:
            continue
        k = order.index(t['id'])
        # Earlier actors this round (allies and enemies) and their effects on champions.
        before = []
        for aid, acts in eff[t['round']][:k]:
            for a in acts:
                for c in a['champs']:
                    if c['dmg'] > 0 or c['stun'] or c['dead']:
                        before.append(dict(by=aid, ally=team[aid] == side, ab=a['ab'], kind=a['kind'], **c))
        mine_now = eff[t['round']][k][1]
        prev = []
        for aid, acts in eff.get(t['round'] - 1, []):
            if aid == t['id']:
                prev = [c['id'] for a in acts for c in a['champs'] if c['foe'] and (c['dmg'] > 0 or c['stun'])]
        prev_enemy = []   # enemy effects on Fish since this actor's previous turn (last round after it, this round before it)
        last = eff.get(t['round'] - 1, [])
        j = next((i for i, (aid, _) in enumerate(last) if aid == t['id']), len(last))
        for aid, acts in last[j + 1:] + eff[t['round']][:k]:
            if team[aid] != side:
                for a in acts:
                    for c in a['champs']:
                        if not c['foe'] and c['dmg'] > 0:
                            prev_enemy.append(dict(by=aid, on=c['id'], dmg=c['dmg']))
        es = [erow(e, pos, me, bush) for e in enemies]
        allies = [dict(id=a['id'], type=a['type'], x=a['x'], y=a['y'], hp=a['hp'], maxhp=a['maxHp'], sh=shield(a),
                       gems=a.get('gems', 0), cd=a['cd'], str=a['strength'], focus=a['focus'], ch=a.get('channelType', 0))
                  for a in s['allies'] if 'x' in a and a.get('alive', True)]
        camps = [dict(id=c['id'], group=c['group'], type=c['type'], x=c['x'], y=c['y'], hp=c['hp'], awake=c['awake'])
                 for c in s['camps'] if c['hp'] > 0]
        blocked = static | {xy(c) for c in enemies} | {(a['x'], a['y']) for a in allies} | {(c['x'], c['y']) for c in camps}
        tiles = [list(pos)] + [[pos[0] + dx, pos[1] + dy] for dx, dy in NB
                               if 0 <= pos[0] + dx < W and 0 <= pos[1] + dy < H and (pos[0] + dx, pos[1] + dy) not in blocked]
        tf = []
        for p in tiles:
            pt = tuple(p)
            cfire = sum(c['awake'] and c['type'] in CAMP_RANGE and dist(pt, (c['x'], c['y'])) <= CAMP_RANGE[c['type']] for c in camps)
            wall8 = sum((pt[0] + dx, pt[1] + dy) in walls for dx, dy in NB)
            tf.append([p[0], p[1], int(pt in bush), cfire, wall8, int(pt in home)])
        acts = []
        for a in t['actions']:
            if a['kind'] in ('Set priority',):
                continue
            acts.append([a['kind'], a['to'], a.get('slot'), a.get('ability'), a['step']])
        # Each attack/cast's before-state candidates (visible enemies, their health at that moment).
        bstates = []
        for a in t['actions']:
            if a['kind'] in ('Attack', 'Cast ability') and 'before' in a:
                b = a['before']; bm = b['me']
                bstates.append(dict(step=a['step'], pos=[bm['x'], bm['y']], cd=bm['cd'], hp=bm['hp'],
                                    en=[[e['id'], e['x'], e['y'], e['hp'], shield(e), stun_timer(e), e.get('gems', 0), e['type'],
                                         e['strength'], e['maxHp'], e['focus']]
                                        for e in b['enemies'] if 'x' in e and e.get('alive', True)]))
        end = t.get('end', {}).get('me', {})
        rows.append(dict(
            cohort=name, game=key, group=entry.get('group'), map=entry.get('map'), round=t['round'], actor=t['id'],
            step=t['step'], side=side, k=k, n_order=len(order), order=order, fish_starts=int(t['round'] % 2 == (1 if side == 0 else 0)),
            type=me['type'], pos=list(pos), hp=me['hp'], maxhp=me['maxHp'], sh=shield(me), gems=me.get('gems', 0),
            str=me['strength'], focus=me['focus'], cd=me['cd'], ch=me['channelType'], ct=me['channelTimer'],
            stunned=stun_timer(me) >= 0 and any(b['type'] == 1 for b in me['buffs']), at_home=pos in home,
            in_bush=int(pos in bush), done=t.get('finish') == 'End turn' and 'x' in end,
            enemies=es, allies=allies, camps=camps, tiles=tf,
            ctx=dict(before=before, prev=prev, hurt_by=prev_enemy),
            y=dict(acts=acts, b=bstates, eff=mine_now, end=[end['x'], end['y']] if 'x' in end else None,
                   end_alive=bool(end.get('alive')))))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('cohort', choices=[c[0] for c in COHORTS])
    p.add_argument('--jobs', type=int, default=6)
    p.add_argument('--out', default='replays/fish-micro')
    a = p.parse_args()
    name, manifest, cache = next(c for c in COHORTS if c[0] == a.cohort)
    out = Path(a.out) / f'{name}-micro-v1.jsonl.gz'
    if out.exists():
        raise SystemExit(f'refusing to overwrite {out}')
    entries = json.loads(Path(manifest).read_text())
    tmp = out.with_suffix('.tmp')
    n = 0
    with mp.Pool(min(a.jobs, 6)) as pool, gzip.open(tmp, 'wt') as f:
        for rows in pool.imap_unordered(game_rows, [(name, cache, e) for e in entries]):
            for r in rows:
                f.write(json.dumps(r, separators=(',', ':')) + '\n')
            n += len(rows)
    tmp.rename(out)
    print(name, len(entries), 'games', n, 'rows')


if __name__ == '__main__':
    main()
