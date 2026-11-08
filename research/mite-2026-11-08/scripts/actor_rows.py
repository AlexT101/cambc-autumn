import json,gzip,sys,os,pickle,collections
R='replays/fish-scorecard/mite-1107/'
rows=[]
for part in ('A','B'):
    d0=R+part+'/actor/'
    if not os.path.isdir(d0): continue
    for f in sorted(os.listdir(d0)):
        d=json.load(gzip.open(d0+f))
        names={c['id']:c['name'] for c in d['roster']}
        nb=sum(1 for c in d['roster'] if c['team']==d['side'])
        for t in d['turns']:
            for i,a in enumerate(t['actions']):
                if a['kind']!='Set priority': continue
                b=a['before']; me=b['me']
                en=[e for e in b['enemies'] if e.get('alive',True) and e.get('x') is not None]
                ds=sorted(max(abs(e['x']-me['x']),abs(e['y']-me['y'])) for e in en) if me.get('x') is not None else []
                rows.append(dict(g=f,round=t['round'],id=t['id'],name=names[t['id']],v=a['value'],old=me['priority'],alive=me['alive'],
                    hp=me['hp'],mx=me['maxHp'],gems=me['gems'],gold=me['gold'],ch=me['channelType'],cht=me['channelTimer'],
                    nen=len(en),ds=ds,etypes=[names[e['id']] for e in en],ehp=[e['hp']/e['maxHp'] for e in en],
                    nal=len([x for x in b['allies'] if x.get('alive',True)]),prev=[x['kind'] for x in t['actions'][:i]],
                    after=[x['kind'] for x in t['actions'][i+1:]],side=d['side'],nb=nb,cd=me['cd'],
                    allies=[(x['id'],x.get('x'),x.get('y'),x.get('hp'),x.get('maxHp'),x.get('gems')) for x in b['allies']],me=me,en=en))
pickle.dump(rows,open('actor_rows.pkl','wb')); print(len(rows))
print(collections.Counter(r['v'] for r in rows).most_common(25))
