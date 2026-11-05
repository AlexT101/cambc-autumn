"""Discovery-only competing-holder observations on already empty camp groups.

Labels leaving the group on this turn, not who eventually receives the reward.
No future ally movement or payout enters the features.
"""
import argparse,collections,gzip,json
from pathlib import Path
from breadth import static_groups,xy


def main(manifest,cache,out):
    rows=[]
    for i,e in enumerate(json.loads(Path(manifest).read_text())):
        key=e['sha256'][:16]
        with gzip.open(Path(cache)/f'{key}.json.gz') as f:g=json.load(f)
        groups,at=static_groups(g['map']);live={}
        # Only immutable map-id correspondence is learned across snapshots.
        for t in g['turns']:
            for c in t['start']['camps']:
                k=at[xy(c)]
                if k in live:assert live[k]==c['group']
                live[k]=c['group']
        for t in g['turns']:
            s=t['start'];m=s['me'];end=t.get('end')
            if not m['alive'] or not end or t.get('finish')!='End turn' or m['channelType'] in [2,3] or any(b['type']==1 for b in m['buffs']):continue
            group=at.get(xy(m));gid=live.get(group)
            if group is None or gid is None:continue
            gs=next((q for q in s['groups'] if q[0]==gid),None)
            if gs is None or gs[1]!=2:continue
            allies=[c for c in s['allies'] if at.get(xy(c))==group]
            if not allies or s['enemies']:continue
            em=end['me']
            rows.append(dict(game=key,round=t['round'],actor=t['id'],step=t['step'],me=m,allies=allies,
                group=groups[group],state=gs,left=not em['alive'] or at.get(xy(em))!=group,
                actions=[a['kind'] for a in t['actions']]))
        if (i+1)%20==0:print(i+1,len(rows),flush=True)
    with gzip.open(out,'wt') as f:json.dump(dict(rows=rows),f,separators=(',',':'))
    pairs=collections.defaultdict(lambda:[0,0])
    for r in rows:
        if len(r['allies'])==1:
            pairs[r['me']['type'],r['allies'][0]['type']][r['left']]+=1
    print(sorted(pairs.items()))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest');p.add_argument('cache');p.add_argument('out')
    a=p.parse_args();main(a.manifest,a.cache,a.out)
