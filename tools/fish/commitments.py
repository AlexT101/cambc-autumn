"""Sample the next-turn choice to keep a prepared recall, plus altar histories."""
import argparse, collections, gzip, json
from pathlib import Path
from breadth import dist, xy, spawn, static_groups


def main(manifest,cache,out):
    rows=[]; banks=[]
    for i,entry in enumerate(json.loads(Path(manifest).read_text())):
        key=entry['sha256'][:16]
        with gzip.open(Path(cache)/f'{key}.json.gz') as f:g=json.load(f)
        homes=spawn(g['map'],g['side']); groups,at=static_groups(g['map'])
        previous={}
        for t in g['turns']:
            s=t['start'];m=s['me'];prev=previous.get(t['id']);previous[t['id']]=t
            if not m['alive'] or any(b['type']==1 for b in m['buffs']):continue
            ref=dict(game=key,round=t['round'],actor=t['id'],step=t['step'],type=m['type'])
            if m['channelType']==1 and prev and any(a['kind']=='Recall' for a in prev['actions']) and t.get('finish')=='End turn':
                group=at.get(xy(m)); gs=next((q for q in s['groups'] if q[0]==next((c['group'] for c in s['camps'] if xy(c)==xy(m)),None)),None)
                # A dead camp may be omitted, so match visible live ids to the static graph.
                if group is not None and gs is None:
                    liveids={c['group'] for c in s['camps'] if at[xy(c)]==group}
                    gs=next((q for q in s['groups'] if q[0] in liveids),None)
                rows.append(dict(ref,me=m,continued=not any(a['kind']=='Cancel channel' for a in t['actions']),
                    home_distance=min(dist(xy(m),p) for p in homes),
                    altar_distance=min((dist(xy(m),p) for p in g['map']['altars']),default=999),
                    enemies=s['enemies'],allies=s['allies'],
                    camp_tile=group is not None,group_state=gs,
                    awake=[c for c in s['camps'] if c['awake'] and c['hp']>0],
                    previous_actions=[a['kind'] for a in prev['actions']]))
        if (i+1)%20==0:print(i+1,len(rows),flush=True)
    with gzip.open(out,'wt') as f:json.dump(dict(schema=1,manifest=manifest,rows=rows),f,separators=(',',':'))
    print(len(rows),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest');p.add_argument('cache');p.add_argument('out')
    a=p.parse_args();main(a.manifest,a.cache,a.out)
