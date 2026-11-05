"""Actor-local route memory, adjacent capture entries, and completed economic trips.

Extends (never replaces) decision_data's episode rows. Future frames label outcomes
only; all history updates happen after emitting the current start-state features.
"""
import argparse
import collections
import gzip
import json
from pathlib import Path

from breadth import dist, spawn, static_groups, xy
from decision_data import contexts, eligible, hit_groups
from holder_model import RANK


def home_outcome(turns, index, home):
    for t in turns[index: index + 7]:
        m = t['start']['me']
        if not m['alive']:
            return 'dead'
        if t is not turns[index] and xy(m) in home:
            return 'arrive'
        if m['channelType'] != 1:
            return 'interrupted'
        if any(a['kind'] == 'Cancel channel' for a in t['actions']):
            return 'cancel'
    return 'censored'


def trip_outcome(turns, index, home, at, live, own):
    departed = xy(turns[index]['start']['me']) not in home
    for t in turns[index:]:
        if t['round'] > turns[index]['round'] + 40:
            return dict(status='timeout')
        s = t['start']; m = s['me']
        if not m['alive']:
            return dict(status='dead', round=t['round'])
        if departed and xy(m) in home:
            return dict(status='home', round=t['round'])
        departed |= xy(m) not in home
        if any(z['enemies'] for z in contexts(t)):
            return dict(status='enemy', round=t['round'])
        # A lock attack also says Submit gems, but cannot start a tribute channel.
        if any(a['kind'] == 'Submit gems' for a in t['actions']):
            success = any(z['me']['channelType'] == 2 for z in contexts(t))
            return dict(status='tribute' if success else 'lock_attempt', round=t['round'])
        hit = hit_groups(t, at)
        held = at.get(xy(m))
        q = next((q for q in s['groups'] if q[0] == live.get(held)), None)
        if not hit and held != own and q and q[1] == 2:
            hit = [held]
        if hit:
            return dict(status='farm' if len(hit) == 1 else 'ambiguous', targets=hit, round=t['round'])
    return dict(status='censored')


def main(manifest, cache, decisions, out):
    episodes = collections.defaultdict(dict)
    with gzip.open(decisions, 'rt') as f:
        for line in f:
            r = json.loads(line)
            if r['kind'] == 'destination':
                episodes[r['game']][r['step']] = r
    counts = collections.Counter()
    with gzip.open(out, 'xt') as output:
        def emit(kind, ref, x, y):
            output.write(json.dumps(dict(kind=kind, **ref, x=x, y=y), separators=(',', ':')) + '\n')
            counts[kind] += 1

        for n, entry in enumerate(json.loads(Path(manifest).read_text())):
            key = entry['sha256'][:16]
            with gzip.open(Path(cache) / f'{key}.json.gz') as f:
                g = json.load(f)
            groups, at = static_groups(g['map'])
            home = spawn(g['map'], g['side']); away = spawn(g['map'], 1-g['side'])
            terrain = set(map(tuple, g['map']['walls'] + g['map']['holes'] + g['map']['altars'])) | away
            live = {}
            for t in g['turns']:
                for s in contexts(t):
                    for c in s['camps']:
                        live[at[xy(c)]] = c['group']
            reverse = {v:k for k,v in live.items()}
            territories = {q['id']: min(dist(p,h) for p in q['tiles'] for h in home) -
                           min(dist(p,h) for p in q['tiles'] for h in away) for q in groups}
            actors = collections.defaultdict(list)
            for t in g['turns']:
                actors[t['id']].append(t)
            for actor, turns in actors.items():
                visits = collections.Counter(); transitions = collections.Counter()
                last_visit = {}; last_ally = {}; last_group = None; source = -1; was_home = True
                for i,t in enumerate(turns):
                    s = t['start']; m = s['me']; rnd = t['round']
                    if not m['alive']:
                        was_home=False
                        continue
                    pos = xy(m)
                    gs = {reverse[q[0]]:q for q in s['groups'] if q[0] in reverse}
                    own = at.get(pos); oq = gs.get(own)
                    if pos in home and not was_home:
                        source = -1
                    ref = dict(game=key, round=rnd, actor=actor, step=t['step'])
                    common = dict(type=m['type'], hp=m['hp'], maxhp=m['maxHp'], gems=m['gems'], gold=m['gold'],
                                  channel=m['channelType'], timer=m['channelTimer'],
                                  altar=min((dist(pos,p) for p in g['map']['altars']), default=999),
                                  home_distance=min(dist(pos,p) for p in home), score=s['score'][g['side']],
                                  ally_gems=sum(c['gems'] for c in s['allies']),
                                  enemies=len(s['enemies']), own_empty=bool(oq and oq[1]==2),
                                  capture_timer=oq[3] if oq and oq[1]==2 else 9,
                                  allies=len(s['allies']))
                    if eligible(t):
                        if m['channelType']==1 and m['channelTimer']==4 and pos not in home:
                            emit('early_home', ref, common, dict(outcome=home_outcome(turns,i,home)))
                        if not s['enemies']:
                            occupied={xy(c) for c in s['allies']+s['enemies']+s['camps'] if c['hp']>0}
                            for k,q in gs.items():
                                if q[1]!=2 or k==own:
                                    continue
                                free=[p for p in groups[k]['tiles'] if dist(pos,p)==1 and tuple(p) not in occupied | terrain]
                                if not free:
                                    continue
                                holders=[c for c in s['allies'] if at.get(xy(c))==k]
                                if not holders or m['type'] not in RANK or any(c['type'] not in RANK for c in holders):
                                    continue
                                best=min(holders,key=lambda c:RANK[c['type']])
                                x=common | dict(group=k, holders=holders, free=len(free),
                                                best_rank=RANK[best['type']], self_rank=RANK[m['type']],
                                                best_timer=best['channelTimer'] if best['channelType']==1 else 0,
                                                group_capture=q[3], capture_team=q[2], side=g['side'])
                                end=t['end']['me']
                                joined=end['alive'] and at.get(xy(end))==k
                                settled=False
                                if joined:
                                    nxt=turns[i+1] if i+1<len(turns) else None
                                    if not nxt or 'end' not in nxt:
                                        settled=None
                                    else:
                                        ns=nxt['start']; nm=ns['me']; ne=nxt['end']['me']
                                        paid=nm['alive'] and at.get(xy(nm))==k and any(
                                            q[0]==live[k] and q[1]==3 for q in ns['groups'])
                                        settled=bool(paid or ne['alive'] and at.get(xy(ne))==k)
                                emit('incoming',ref,x,dict(joined=joined,settled=settled,
                                                          actions=[a['kind'] for a in t['actions']]))
                        episode=episodes[key].get(t['step'])
                        if episode:
                            x=episode['x'] | common
                            origin=x['own_group'] if x['reason']=='payout' else -1
                            x['candidates']=[c | dict(visits=visits[c['id']],
                                visit_age=rnd-last_visit[c['id']] if c['id'] in last_visit else None,
                                route_count=transitions[origin,c['id']],
                                last_group=c['id']==last_group,
                                territory=territories[c['id']],
                                ally_age=rnd-last_ally[c['id']] if c['id'] in last_ally else None)
                                for c in episode['x']['candidates']]
                            emit('route',ref,x,episode['y'])
                            emit('trip',ref,x,trip_outcome(turns,i,home,at,live,own))
                    # The static id mapping above uses future positions only to name map
                    # groups; no future dynamic state is copied into this actor's memory.
                    for z in contexts(t):
                        for c in z['allies']:
                            k=at.get(xy(c))
                            if k is not None:
                                last_ally[k]=rnd
                    touched=hit_groups(t,at)
                    for z in contexts(t):
                        if not z['me']['alive']:continue
                        held=at.get(xy(z['me']))
                        if held is not None and any(q[0]==live.get(held) and q[1]==2 for q in z['groups']):
                            touched.append(held)
                    for k in dict.fromkeys(touched):
                        if k != source:
                            transitions[source,k]+=1; visits[k]+=1; source=k
                        last_group=k; last_visit[k]=rnd
                    was_home=pos in home
            if (n+1)%10==0:
                print(n+1,dict(counts),flush=True)
    print(dict(counts),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for a in ('manifest','cache','decisions','out'):p.add_argument(a)
    a=p.parse_args();main(a.manifest,a.cache,a.decisions,a.out)
