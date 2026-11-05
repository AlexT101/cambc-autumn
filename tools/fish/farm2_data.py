"""Causal extras for choice-v1 destination episodes (farm2 study).

For each clean episode of a cohort's choice-v1 file, rebuilds the actor's own memory from its
recorded perspectives up to the episode's turn start (never later) and writes, keyed by
(game, step): map size, static walks from both spawns and to altars per group, remembered live
camp health and awake state per group, visible allies' stats, and the actor's recent history
(recall start, death, last off-spawn position). Future frames are not read.

usage: farm2_data.py CHOICE_V1 CACHE_DIR OUT
"""
import argparse
import collections
import gzip
import json
from pathlib import Path

from breadth import HP, dist, field, spawn, static_groups, xy
from decision_data import contexts

RESPAWN = {0: 40, 1: 60, 2: 50, 3: 50, 4: 150, 5: 80}


def multi_field(m, sources, blocked):
    seen = {p: 0 for p in sources}; queue = collections.deque(sources)
    while queue:
        x, y = queue.popleft(); d = seen[x, y] + 1
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                p = x + dx, y + dy
                if (dx or dy) and 0 <= p[0] < m['width'] and 0 <= p[1] < m['height'] and p not in blocked and p not in seen:
                    seen[p] = d; queue.append(p)
    return seen


def approach(tiles):
    return {(x + dx, y + dy) for x, y in tiles for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy} - set(map(tuple, tiles))


def main(choice, cache, out):
    wanted = collections.defaultdict(set)
    with gzip.open(choice, 'rt') as f:
        for line in f:
            r = json.loads(line)
            if r['x']['reason'] != 'opening' and r['y']['status'] == 'hit':
                wanted[r['game']].add(r['step'])
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(out, 'xt') as output:
        for gi, (key, steps) in enumerate(sorted(wanted.items())):
            with gzip.open(Path(cache) / f'{key}.json.gz') as f:
                g = json.load(f)
            m = g['map']
            groups, at = static_groups(m)
            home = spawn(m, g['side']); away = spawn(m, 1 - g['side'])
            static = set(map(tuple, m['walls'] + m['holes'] + m['altars']))
            camp_tiles = set(at)
            f_us = multi_field(m, list(home), static | away | camp_tiles)
            f_them = multi_field(m, list(away), static | home | camp_tiles)
            altar_adj = [p for a in m['altars'] for p in approach([a]) if p not in static | camp_tiles | away
                         and 0 <= p[0] < m['width'] and 0 <= p[1] < m['height']]
            f_altar = multi_field(m, altar_adj, static | away | camp_tiles) if altar_adj else {}
            gstatic = {}
            for q in groups:
                ap = approach(q['tiles'])
                gstatic[q['id']] = dict(
                    from_us=min((f_us.get(p, 999) for p in ap), default=999),
                    from_them=min((f_them.get(p, 999) for p in ap), default=999),
                    to_altar=min((f_altar.get(p, 999) for p in ap), default=999),
                    respawn_time=max(RESPAWN[t] for t in q['types']), size=len(q['tiles']))
            live = {}
            for t in g['turns']:
                for s in contexts(t):
                    for c in s['camps']:
                        live[at[xy(c)]] = c['group']
            reverse = {v: k for k, v in live.items()}
            actors = collections.defaultdict(list)
            for t in g['turns']:
                actors[t['id']].append(t)
            for actor, turns in actors.items():
                gmem = {}  # static group -> (round, q)
                cmem = {}  # tile -> (round, hp, awake)
                last_recall = None; last_death = None; last_off = None; last_off_round = None
                ally_seen = {}  # ally id -> (round, x, y, type, strength); this actor's own sightings
                ally_prev = {}  # ally id -> its sighting before the latest round's
                recall_allies = None
                damaged = {}  # static group -> last round its remembered hp fell
                dead = {}  # static group -> last round it was seen empty or respawning

                def remember(s, rnd):
                    me = s['me']
                    seen_tiles = {}
                    for c in s['camps']:
                        p = xy(c)
                        old = cmem.get(p)
                        if old and c['hp'] < old[1] - 1e-6:
                            damaged[at[p]] = rnd
                        cmem[p] = (rnd, c['hp'], c['awake'])
                        seen_tiles[p] = c
                    for c in s['allies']:
                        old = ally_seen.get(c['id'])
                        if old and old[0] < rnd:
                            ally_prev[c['id']] = old
                        ally_seen[c['id']] = (rnd, c['x'], c['y'], c['type'], c['strength'])
                    for q in s['groups']:
                        if q[0] not in reverse:
                            continue
                        k = reverse[q[0]]
                        gmem[k] = (rnd, q)
                        if q[1] == 1 and me['alive']:
                            # Members of a visible living group missing from the camp list near us are dead.
                            for p in groups[k]['tiles']:
                                p = tuple(p)
                                if p not in seen_tiles and dist(xy(me), p) <= 6:
                                    cmem[p] = (rnd, 0.0, False)
                        elif q[1] in (2, 3):
                            dead[k] = rnd

                for i, t in enumerate(turns):
                    s = t['start']; me = s['me']; rnd = t['round']
                    remember(s, rnd)
                    if t['step'] in steps:
                        pos = xy(me)
                        cands = {}
                        for q in groups:
                            k = q['id']
                            r, gq = gmem.get(k, (None, None))
                            hp_left = 0.0; awake = 0; members_alive = 0; hp_age = None
                            state = gq[1] if gq else 0
                            for p, tp in zip(q['tiles'], q['types']):
                                cm = cmem.get(tuple(p))
                                if state in (2, 3):
                                    h = 0.0
                                elif cm is not None and cm[0] > dead.get(k, -1):
                                    h = cm[1]; awake += bool(cm[2])
                                    hp_age = rnd - cm[0] if hp_age is None else min(hp_age, rnd - cm[0])
                                else:
                                    h = HP[tp]
                                hp_left += h; members_alive += h > 0
                            cands[k] = gstatic[k] | dict(hp_left=hp_left, awake=awake, members_alive=members_alive,
                                                         capture=gq[2] if gq else None, capture_timer=gq[3] if gq else None,
                                                         respawn_raw=gq[4] if gq else None, hp_age=hp_age,
                                                         damaged_age=rnd - damaged[k] if k in damaged else None)
                        allies = [dict(id=c['id'], type=c['type'], x=c['x'], y=c['y'], hp=c['hp'], maxhp=c['maxHp'],
                                       strength=c['strength'], focus=c['focus'], gems=c.get('gems', 0),
                                       channel=c['channelType'], timer=c['channelTimer'], home=xy(c) in home)
                                  for c in s['allies']]
                        x = dict(width=m['width'], height=m['height'], n_groups=len(groups),
                                 me=dict(type=me['type'], hp=me['hp'], maxhp=me['maxHp'], strength=me['strength'],
                                         focus=me['focus'], gems=me.get('gems', 0), gold=me.get('gold', 0), cd=me['cd']),
                                 allies=allies,
                                 recall_age=rnd - last_recall[0] if last_recall else None,
                                 recall_xy=last_recall[1] if last_recall else None,
                                 death_age=rnd - last_death if last_death is not None else None,
                                 off_xy=last_off, off_age=rnd - last_off_round if last_off_round is not None else None,
                                 ally_memory=[dict(id=i, age=rnd - v[0], x=v[1], y=v[2], type=v[3], strength=v[4])
                                              for i, v in sorted(ally_seen.items())],
                                 recall_allies=recall_allies,
                                 ally_prev={str(c['id']): dict(age=rnd - ally_prev[c['id']][0], x=ally_prev[c['id']][1], y=ally_prev[c['id']][2])
                                            for c in s['allies'] if c['id'] in ally_prev},
                                 candidates=cands)
                        output.write(json.dumps(dict(game=key, round=rnd, actor=actor, step=t['step'], x=x),
                                                separators=(',', ':')) + '\n')
                        n += 1
                    # History after the episode features: this turn's later perspectives.
                    for a in t['actions']:
                        if a['kind'] == 'Recall' and 'before' in a:
                            last_recall = (rnd, list(xy(a['before']['me'])))
                            recall_allies = [dict(id=c['id'], type=c['type'], x=c['x'], y=c['y'], strength=c['strength'])
                                             for c in a['before']['allies']]
                    for z in contexts(t)[1:]:
                        remember(z, rnd)
                    if not me['alive']:
                        if i == 0 or turns[i - 1]['start']['me']['alive']:
                            last_death = rnd; recall_allies = None
                    elif xy(me) not in home:
                        last_off = list(xy(me)); last_off_round = rnd
            if (gi + 1) % 20 == 0:
                print(gi + 1, n, flush=True)
    print(n, 'rows', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for a in ('choice', 'cache', 'out'):
        p.add_argument(a)
    a = p.parse_args()
    main(a.choice, a.cache, a.out)
