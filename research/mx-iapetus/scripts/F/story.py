# Events around one death: story.py EXTRACT_DIR SRC ROUND VICTIM [BEFORE]
import json,gzip,sys
A,src,rd,v=sys.argv[1].rstrip('/')+'/',sys.argv[2],int(sys.argv[3]),int(sys.argv[4]); before=int(sys.argv[5]) if len(sys.argv)>5 else 8
idx=json.load(open(A+'index.json'))['games']; r=next(x for x in idx if x['source'].endswith(src)); d=r['dir']
m=json.load(open(A+d+'/meta.json')); nm={c['id']:c['name'][:4]+str(c['id']) for c in m['champions']}
R=json.load(gzip.open(A+d+'/rounds.json.gz')); ri={x:i for i,x in enumerate(R['round'])}; ch={c['id']:c for c in R['champions']}
for e in gzip.open(A+d+'/events.jsonl.gz','rt'):
    e=json.loads(e)
    if e['r']<rd-before or e['r']>rd: continue
    if e['k'] in ('move','camp_attack','group_wake','group_sleep','capture_hold','capture_reset','camp_death','ward','shop'): 
        if e['k']!='move' or e['a']!=v: continue
    who=nm.get(e.get('a'),'')
    x={k:e[k] for k in e if k not in ('s','r','t','k','a')}
    if 'dmg' in x: x['dmg']=[[nm.get(i,i),round(a)] for i,a in x['dmg']]
    for k in ('tgt','v','by'):
        if k in x and x[k] in nm: x[k]=nm[x[k]]
    print(e['r'],e['t'],who,e['k'],x)
i=ri[rd-1]
for c in ch.values():
    if c['alive'][i]: print('  @',rd-1,nm[c['id']],'T'+str(c['team']),(c['x'][i],c['y'][i]),'hp%.0f/%.0f'%(c['hp'][i],c['maxHp'][i]),'g',c['gems'][i],'foc%.0f'%c['foc'][i],'chan',c['chan'][i],c['chanT'][i],'cd',c['cd0'][i],c['cd1'][i])
