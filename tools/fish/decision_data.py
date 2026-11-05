"""Causal turn-start action/holder features and post-payout/spawn destination episodes.

Future actor frames supply labels only. Remembered camps are updated only from this
actor's prior perspectives. JSONL keeps the large observation tables streamable.
"""
import argparse
import collections
import gzip
import json
from pathlib import Path

from breadth import RANGED, dist, field, spawn, static_groups, xy
from holder_model import RANK


def stunned(m):
    return any(b['type'] == 1 for b in m['buffs'])


def eligible(t):
    m = t['start']['me']
    return (m['alive'] and not stunned(m) and m['channelType'] in (0, 1)
            and t.get('finish') == 'End turn' and 'end' in t)


def contexts(t):
    return [t['start']] + [a['before'] for a in t['actions'] if 'before' in a] + ([t['end']] if 'end' in t else [])


def hit_groups(t, at):
    for a in t['actions']:
        s = a.get('before')
        if not s:
            continue
        cs = [c for c in s['camps'] if c['hp'] > 0]
        hit = set()
        if a['kind'] == 'Attack' or a['kind'] == 'Cast ability' and a['ability'] in (2, 4):
            hit = {at[xy(c)] for c in cs if list(xy(c)) == a['to']}
        elif a['kind'] == 'Cast ability' and (a['ability'] == 3 or a['ability'] == 6 and s['me']['type'] == 12):
            hit = {at[xy(c)] for c in cs if dist(xy(c), a['to']) <= 1}
        if hit:
            return sorted(hit)
    return []


def main(manifest, cache, out, limit=None):
    counts = collections.Counter()
    entries = json.loads(Path(manifest).read_text())[:limit]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, 'wt') as output:
        def emit(kind, ref, features, label):
            output.write(json.dumps(dict(kind=kind, **ref, x=features, y=label), separators=(',', ':')) + '\n')
            counts[kind] += 1

        for n, entry in enumerate(entries):
            key = entry['sha256'][:16]
            with gzip.open(Path(cache) / f'{key}.json.gz') as f:
                g = json.load(f)
            groups, at = static_groups(g['map'])
            home = spawn(g['map'], g['side'])
            terrain = set(map(tuple, g['map']['walls'] + g['map']['holes'] + g['map']['altars'])) | spawn(g['map'], 1-g['side'])
            live = {}
            for t in g['turns']:
                for s in contexts(t):
                    for c in s['camps']:
                        sg = at[xy(c)]
                        assert sg not in live or live[sg] == c['group']
                        live[sg] = c['group']
            reverse = {v: k for k, v in live.items()}
            actors = collections.defaultdict(list)
            for t in g['turns']:
                actors[t['id']].append(t)
            for actor, turns in actors.items():
                memory = {}
                previous = None
                prior_home = True
                last_arrival = None
                for index, t in enumerate(turns):
                    s = t['start']; m = s['me']
                    if not m['alive']:
                        for state in contexts(t):
                            for q in state['groups']:
                                if q[0] in reverse:
                                    memory[reverse[q[0]]] = (t['round'], q)
                        previous=t; prior_home=False
                        continue
                    pos = xy(m)
                    ref = dict(game=key, round=t['round'], actor=actor, step=t['step'])
                    for q in s['groups']:
                        if q[0] in reverse:
                            memory[reverse[q[0]]] = (t['round'], q)
                    gs = {reverse[q[0]]: q for q in s['groups'] if q[0] in reverse}
                    own = at.get(pos); ownstate = gs.get(own)
                    in_home = pos in home
                    arrived = in_home and not prior_home and m['alive']
                    if arrived:
                        last_arrival = t['round']
                    common = dict(type=m['type'], hp=m['hp'], maxhp=m['maxHp'], gold=m.get('gold', 0),
                                  gems=m.get('gems', 0), focus=m['focus'], strength=m['strength'],
                                  shield=sum(b['mag'] for b in m['buffs'] if b['type']==0),
                                  channel=m['channelType'], timer=m['channelTimer'], cd=m['cd'],
                                  home_distance=min(dist(pos, p) for p in home),
                                  enemies=len(s['enemies']), enemy_distance=min((dist(pos, xy(c)) for c in s['enemies']), default=999),
                                  own_group=own, own_state=ownstate)
                    if eligible(t):
                        acts = t['actions']
                        casts = [a['slot'] for a in acts if a['kind'] == 'Cast ability']
                        cancels = any(a['kind'] == 'Cancel channel' for a in acts)
                        if m['channelType'] == 1 and m['channelTimer'] == 1:
                            nxt = turns[index+1] if index+1 < len(turns) else None
                            outcome = ('cancel' if cancels else 'censored' if not nxt else
                                       'arrive' if nxt['start']['me']['alive'] and xy(nxt['start']['me']) in home else 'interrupted')
                            emit('recall_final', ref, common | dict(groups=[dict(group=k, age=t['round']-r, state=q) for k,(r,q) in memory.items()]),
                                 dict(keep=not cancels, outcome=outcome))
                        if ownstate and ownstate[1] == 2 and not s['enemies']:
                            holders = [c for c in s['allies'] if at.get(xy(c)) == own]
                            occupied = {xy(c) for c in s['allies'] + s['enemies'] + s['camps'] if c['hp'] > 0}
                            escapes = [(pos[0]+dx, pos[1]+dy) for dx in (-1,0,1) for dy in (-1,0,1)
                                       if (dx or dy) and 0 <= pos[0]+dx < g['map']['width'] and 0 <= pos[1]+dy < g['map']['height']]
                            exits = [p for p in escapes if p not in terrain | occupied and at.get(p) != own]
                            alternatives = [dict(group=k, distance=min(dist(pos,p) for p in groups[k]['tiles']), state=q,
                                                 age=t['round']-r, gold=groups[k]['gold'], gems=groups[k]['gems'])
                                            for k,(r,q) in memory.items() if k != own]
                            emit('holder', ref, common | dict(holders=holders, exits=len(exits), group=groups[own], alternatives=alternatives),
                                 dict(left=at.get(xy(t['end']['me'])) != own, actions=[a['kind'] for a in acts]))
                        can_cast = bool(m['roundFlags'] & 1024)
                        if can_cast:
                            near = [c for c in s['allies'] if dist(pos, xy(c)) <= 4]
                            targets = [c for c in s['enemies'] + s['camps'] if c['hp'] > 0 and dist(pos, xy(c)) <= 4]
                            spell = {3:0, 7:1, 6:0, 11:1, 5:0}.get(m['type'])
                            if m['type'] == 8 and m['cd'][0] == 0 and near:
                                emit('heal', ref, common | dict(allies=near), dict(cast=0 in casts, other_cast=1 in casts))
                            if spell is not None and m['cd'][spell] == 0 and targets:
                                emit('damage_spell', ref, common | dict(slot=spell, targets=targets), dict(cast=spell in casts))
                        radius = 3 if m['type'] in RANGED else 1
                        in_range = [c for c in s['enemies'] if dist(pos,xy(c)) <= radius]
                        if in_range and (m['roundFlags'] & 2 or m['channelType']==1):
                            choices = [a for a in acts if a['kind'] in ('Attack','Move','Cast ability','Submit gems')]
                            emit('enemy_attack', ref, common | dict(targets=in_range, allies=s['allies'], visible_enemies=s['enemies']),
                                 dict(attack=any(a['kind']=='Attack' for a in acts),
                                      first=choices[0]['kind'] if choices else 'none',
                                      move=any(a['kind']=='Move' for a in acts), cast=bool(casts)))

                        prevstate = None
                        if previous and previous.get('end',{}).get('me',{}).get('alive') and own is not None:
                            prevstate = next((q for q in previous['end']['groups'] if q[0] == live.get(own)), None) if 'end' in previous else None
                        payout = bool(ownstate and ownstate[1] == 3 and prevstate and prevstate[1] == 2 and xy(previous['end']['me'])==pos)
                        spawn_exit = in_home and (last_arrival is not None or t['round'] == 1) and bool(m['roundFlags'] & 1)
                        if spawn_exit:
                            last_arrival = None
                        if (payout or spawn_exit) and not s['enemies']:
                            blocked = terrain | {xy(c) for c in s['camps'] if c['hp']>0}
                            walk = field(g['map'], pos, blocked)
                            candidates = []
                            for gr in groups:
                                k = gr['id']; r,q = memory.get(k, (0, None))
                                # Unknown groups have public initial stats, not inferred live HP.
                                state = q[1] if q else 0
                                dead = state in (2,3)
                                approach = set(map(tuple, gr['tiles'])) if dead else {
                                    (x+dx,y+dy) for x,y in gr['tiles'] for dx in (-1,0,1) for dy in (-1,0,1)
                                    if dx or dy}
                                candidates.append(dict(gr, state=state, age=t['round']-r if q else None,
                                    respawn=max(0,q[4]-(t['round']-r)) if q and state==3 else 0,
                                    walk=min((walk.get(p,999) for p in approach), default=999),
                                    cheb=min(dist(pos,p) for p in gr['tiles']),
                                    allies=sum(min(dist(xy(c),p) for p in gr['tiles']) <= 3 for c in s['allies'])))
                            label = dict(status='timeout', targets=[])
                            departed = pos not in home
                            for future in turns[index:]:
                                if future['round'] > t['round']+40:
                                    break
                                fs = future['start']; fm = fs['me']
                                if not fm['alive']:
                                    label['status']='dead'; break
                                if any(z['enemies'] for z in contexts(future)):
                                    label['status']='enemy'; break
                                if departed and xy(fm) in home:
                                    label['status']='home'; break
                                departed |= xy(fm) not in home
                                if any(a['kind']=='Submit gems' for a in future['actions']):
                                    label['status']='tribute'; break
                                hit = hit_groups(future, at)
                                held = at.get(xy(fm))
                                hq = next((q for q in fs['groups'] if q[0]==live.get(held)),None)
                                if not hit and held != own and hq and hq[1]==2:
                                    hit=[held]
                                if hit:
                                    label=dict(status='hit' if len(hit)==1 else 'ambiguous', targets=hit,
                                               round=future['round'], same_group=hit==[own]); break
                            emit('destination', ref, common | dict(reason='payout' if payout else 'opening' if t['round']==1 else 'spawn', candidates=candidates), label)
                    for state in contexts(t):
                        for q in state['groups']:
                            if q[0] in reverse:
                                memory[reverse[q[0]]] = (t['round'], q)
                    previous=t; prior_home=in_home
            if (n+1)%10 == 0:
                print(n+1, dict(counts), flush=True)
    print(dict(counts), flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest'); p.add_argument('cache'); p.add_argument('out'); p.add_argument('--limit', type=int)
    a=p.parse_args(); main(a.manifest,a.cache,a.out,a.limit)
