# Who placed the lock that cancelled each tribute: same team (self-inflicted) or enemy. Distinct games.
import json,gzip,os,collections
ana=os.path.expanduser('~/tmp-offload/bigl/ana'); games=json.load(open(os.path.expanduser('~/tmp-offload/bigl/games.json')))
idx=json.load(open(ana+'/index.json'))['games']; done=set()
cnt=collections.Counter(); gems=collections.Counter(); ex=[]
for g in idx:
    m=os.path.basename(g['source']).split('.')[0]; gm=games.get(m)
    if not gm or g['dir'] in done: continue
    done.add(g['dir']); d=ana+'/'+g['dir']
    meta=json.load(open(d+'/meta.json')); team={c['id']:c['team'] for c in meta['champions']}; us=0 if gm['side']=='a' else 1
    last=None
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='lock_place': last=e
        elif e['k']=='tribute_cancel' and e.get('cause')=='lock':
            if last and last['s']==e['s']:
                who='self' if team[last['a']]==team[e['a']] else 'enemy'
            else: who='unknown'
            side='ours' if team[e['a']]==us else 'opp'
            cnt[(side,who)]+=1; gems[(side,who)]+=e.get('gems',0)
            if who=='self' and side=='ours' and len(ex)<5: ex.append((g['dir'],e['r'],e.get('gems')))
print({k:(cnt[k],gems[k]) for k in cnt}); print(ex)
