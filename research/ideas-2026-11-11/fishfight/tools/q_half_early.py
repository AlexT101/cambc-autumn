import sys,pickle,json,gzip,collections
sys.path.insert(0,'/home/ubuntu/cambc-autumn/research/ideas-2026-11-11/fishfight/tools')
from summ import mean
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
O='/home/ubuntu/tmp-offload/overruns/an/'; P='/home/ubuntu/tmp-offload/fishfight/'
def half(name,path,opp):
    seen=set(); S=collections.Counter()
    for g in pickle.load(open(path,'rb')):
        if g['opp']!=opp or g['match'] in seen: continue
        seen.add(g['match']); us=g['us']
        R=json.load(gzip.open(g['dir']+'/rounds.json.gz')); ch=R['champions']
        fd=min([d['r'] for d in g['D'] if not d['camp']],default=9999)
        sp=[None,None]
        for t in (0,1):
            xs=[(c['x'][0],c['y'][0]) for c in ch if c['team']==t]; sp[t]=(sum(p[0] for p in xs)/len(xs),sum(p[1] for p in xs)/len(xs))
        for i in range(29,min(100,len(R['round']),fd-1),2):
            for side,lab in ((1-us,'them'),(us,'us')):
                inv=0
                for c in ch:
                    if c['team']!=side or not c['alive'][i]: continue
                    p=(c['x'][i],c['y'][i]); S[lab+'_n']+=1
                    if cheb(p,sp[1-side])<cheb(p,sp[side]): S[lab+'_inv']+=1; inv+=1
                S[lab+'_r']+=1; S[lab+'_inv3']+=inv>=3
    print('%-10s rounds 30-100 before any champion kill: their body-rounds on our half %.1f%%, rounds with 3+ there %.1f%% | ours on theirs %.1f%%, 3+ %.1f%%'%(name,100*S['them_inv']/S['them_n'],100*S['them_inv3']/S['them_r'],100*S['us_inv']/S['us_n'],100*S['us_inv3']/S['us_r']))
half('liveFish',O+'deaths.pkl','Inte'); half('Flp4-lad',O+'deaths_local.pkl','Inte'); half('liveMite',O+'deaths.pkl','Mite'); half('Mt3q-lad',O+'deaths_local.pkl','Mite')
for name,path,opp in (('us v Fish',P+'live.pkl','Inte'),('us v Flp4',P+'local.pkl','Inte'),('us v Mite',P+'live.pkl','Mite'),('us v Mt3q',P+'local.pkl','Mite')):
    rows=[r for r in pickle.load(open(path,'rb'))['rows'] if r['opp']==opp and r['by_us'] and r['nA']<r['nD']]
    c=collections.defaultdict(list)
    for r in rows: c[r['init']].append(r)
    print(name,'T2 by our initiator: '+' | '.join('%s n%d net %+.2f (kA %.2f kD %.2f)'%(k[:6],len(v),mean([r['kA']-r['kD'] for r in v]),mean([r['kA'] for r in v]),mean([r['kD'] for r in v])) for k,v in sorted(c.items(),key=lambda kv:-len(kv[1]))[:8]))
    print('    by first ability: '+' | '.join('%s n%d net %+.2f'%(str(k),len(v),mean([r['kA']-r['kD'] for r in v])) for k,v in sorted(collections.Counter((r['first_kind'],r['first_ab']) for r in rows).items(),key=lambda kv:-kv[1]) for v in [[r for r in rows if (r['first_kind'],r['first_ab'])==k]])[:400])
