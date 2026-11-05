"""Discovery observations for recall, camp attacks, unit spells and opening destinations.

Uses only the pinned actor perspectives; previous predictors/caches are unchanged.
Opening destinations are future outcome labels, never predictor features.
"""
import argparse
import collections
import gzip
import json
from pathlib import Path

RANGED = {1, 3, 5, 6, 8, 11}
NAMES = ['Ryth','Vesper Vale','Vendetta','Cassi','Issac','Stellar','Prism','Marcella','Willow','Ren','Varg','Tavi','Heart of Ruin']
HP = [1350,2400,120,120,20000,5000]
GOLD = [40,90,0,20,300,160]
GEMS = [4,15,7,0,200,36]


def xy(c):
    return c['x'], c['y']


def dist(a, b):
    return max(abs(a[0]-b[0]), abs(a[1]-b[1]))


def mirror(m, p):
    x,y = p
    return (m['width']-1-x if m['symmetry']!='vertical' else x,
            m['height']-1-y if m['symmetry']!='horizontal' else y)


def spawn(m, side):
    s=m['spawnA']
    tiles={(x,y) for y in range(s['minY'],s['maxY']) for x in range(s['minX'],s['maxX'])}
    return tiles if side==0 else {mirror(m,p) for p in tiles}


def static_groups(m):
    # Coordinates, not canonical list indices, identify the live camp graph.
    camps={}
    for c in m['camps']:
        for p in (xy(c), mirror(m,xy(c))):
            assert p not in camps or camps[p]==c['type']
            camps[p]=c['type']
    remaining=set(camps)
    groups=[]
    while remaining:
        p=min(remaining); remaining.remove(p)
        stack=[p]; tiles=[]
        while stack:
            q=stack.pop(); tiles.append(q)
            for n in [(q[0]+1,q[1]),(q[0]-1,q[1]),(q[0],q[1]+1),(q[0],q[1]-1)]:
                if n in remaining: remaining.remove(n); stack.append(n)
        types=[camps[q] for q in tiles]
        groups.append(dict(id=len(groups),tiles=sorted(tiles),types=types,hp=sum(HP[t] for t in types),
                           gold=sum(GOLD[t] for t in types),gems=sum(GEMS[t] for t in types)))
    return groups, {tuple(p):g['id'] for g in groups for p in g['tiles']}


def field(m, start, blocked):
    seen={start:0}; queue=collections.deque([start])
    while queue:
        x,y=queue.popleft(); d=seen[x,y]+1
        for dx,dy in [(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)]:
            p=x+dx,y+dy
            if 0<=p[0]<m['width'] and 0<=p[1]<m['height'] and p not in blocked and p not in seen:
                seen[p]=d; queue.append(p)
    return seen


def opening_candidates(game, me, groups, camp_at):
    m=game['map']
    blocked=set(map(tuple,m['walls']+m['holes']+m['altars'])) | spawn(m,1-game['side']) | set(camp_at)
    f=field(m,xy(me),blocked)
    candidates=[]
    for gr in groups:
        adj={ (x+dx,y+dy) for x,y in gr['tiles'] for dx in [-1,0,1] for dy in [-1,0,1] }
        d=min((f.get(p,999) for p in adj),default=999)
        ch=min(dist(xy(me),p) for p in gr['tiles'])
        candidates.append(dict(gr,walk=d,cheb=ch))
    return candidates


def main(manifest, cache, out):
    rows=collections.defaultdict(list)
    counts=collections.Counter()
    entries=json.loads(Path(manifest).read_text())
    for idx,entry in enumerate(entries):
        key=entry['sha256'][:16]
        with gzip.open(Path(cache)/f'{key}.json.gz') as f: game=json.load(f)
        homes=spawn(game['map'],game['side'])
        groups,camp_at=static_groups(game['map'])
        initial={}; opening_seen=set(); opening_threat=collections.defaultdict(bool)
        last_camp={}
        next_turn={}; previous={}
        for t in reversed(game['turns']):
            next_turn[t['step']]=previous.get(t['id'])
            previous[t['id']]=t
        for t in game['turns']:
            counts['turns']+=1
            start=t['start']; sm=start['me']; acts=t['actions']; end=t.get('end')
            ref=dict(game=key,round=t['round'],actor=t['id'],type=sm['type'])
            initial.setdefault(t['id'],t)
            opening_threat[t['id']] |= bool(start['enemies']) or not sm['alive'] or any(a.get('before',{}).get('enemies') for a in acts)
            for a in acts:
                if 'before' not in a: continue
                s=a['before']; me=s['me']
                if not me['alive']: continue
                p=xy(me)
                cs=[c for c in s['camps'] if c['hp']>0]
                for c in cs:
                    assert xy(c) in camp_at, (key,c)
                hit_groups=set()
                if a['kind']=='Attack' or a['kind']=='Cast ability' and a['ability'] in [2,4]:
                    hit_groups={camp_at[xy(c)] for c in cs if list(xy(c))==a['to']}
                elif a['kind']=='Cast ability' and (a['ability']==3 or a['ability']==6 and me['type']==12):
                    hit_groups={camp_at[xy(c)] for c in cs if dist(xy(c),a['to'])<=1}
                if hit_groups and t['id'] not in opening_seen:
                    opening_seen.add(t['id'])
                    first=initial[t['id']]
                    rows['opening'].append(dict(ref,step=a['step'],decision_round=first['round'],
                        start=first['start']['me'],enemies_before_hit=opening_threat[t['id']],targets=sorted(hit_groups),
                        candidates=opening_candidates(game,first['start']['me'],groups,camp_at)))
                if a['kind']=='Attack':
                    if a['to'] in game['map']['altars']: counts['basic_attack_at_altar']+=1
                    radius=3 if me['type'] in RANGED else 1
                    possible=[dict(c,distance=dist(p,xy(c)),static_group=camp_at[xy(c)]) for c in cs if dist(p,xy(c))<=radius]
                    enemies=[c for c in s['enemies'] if dist(p,xy(c))<=radius]
                    target=next((c for c in possible if list(xy(c))==a['to']),None)
                    if possible and not enemies:
                        rows['camp_attack'].append(dict(ref,step=a['step'],me=me,candidates=possible,
                            previous_group=last_camp.get(t['id']),target=target['id'] if target else None))
                    if target: last_camp[t['id']]=target['group']
                if a['kind']=='Cast ability' and a['ability'] in [2,4]:
                    enemies=[c for c in s['enemies'] if dist(p,xy(c))<=4]
                    target=next((c for c in enemies if list(xy(c))==a['to']),None)
                    if enemies:
                        rows['unit_spell'].append(dict(ref,step=a['step'],slot=a['slot'],ability=a['ability'],me=me,
                            target=target['id'] if target else None,candidates=enemies))
            if not end or t.get('finish')!='End turn': continue
            recalls=[a for a in acts if a['kind']=='Recall']
            # The decision is sampled immediately before terminal recall, or at turn end.
            s=recalls[-1]['before'] if recalls else end
            me=s['me']
            eligible=(me['alive'] and not me['channelType'] and xy(me) not in homes and
                      not any(b['type']==1 for b in me['buffs']) and not me['roundFlags']&64)
            if eligible:
                nxt=next_turn[t['step']]
                rows['recall'].append(dict(ref,step=recalls[-1]['step'] if recalls else t['step'],
                    started=bool(recalls),me=me,enemies=len(s['enemies']),
                    last_action=acts[-1]['kind'] if acts else None,
                    next_cancel=bool(nxt and nxt['start']['me']['channelType']==1 and any(a['kind']=='Cancel channel' for a in nxt['actions'])),
                    next_channel=nxt['start']['me']['channelType'] if nxt else None))
            # An end-of-turn attempt classifier, not a departure-for-altar classifier.
            attempts=[a for a in acts if a['kind']=='Submit gems']
            bs=attempts[0]['before'] if attempts else s
            bm=bs['me']
            if (bm['alive'] and bm.get('gems',0)>0 and not bm['channelType'] and not bm['roundFlags']&128
                and not any(b['type']==1 for b in bm['buffs'])
                and min((dist(xy(bm),p) for p in game['map']['altars']),default=999)<=1):
                rows['bank'].append(dict(ref,step=attempts[0]['step'] if attempts else t['step'],me=bm,
                    attempted=bool(attempts),end_channel=end['me']['channelType'],enemies=len(bs['enemies']),
                    nearest_enemy=min((dist(xy(bm),xy(c)) for c in bs['enemies']),default=999),score=bs['score'][game['side']],
                    allies=bs['allies'],actions=[a['kind'] for a in acts]))
        if (idx+1)%20==0: print(idx+1,dict((k,len(v)) for k,v in rows.items()),flush=True)
    result=dict(schema=1,manifest=manifest,games=len(entries),counts=counts,rows=rows)
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(out,'wt') as f: json.dump(result,f,separators=(',',':'))
    print(dict((k,len(v)) for k,v in rows.items()),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest'); p.add_argument('cache'); p.add_argument('out')
    a=p.parse_args(); main(a.manifest,a.cache,a.out)
