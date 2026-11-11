import sys,pickle,json,gzip,collections
sys.path.insert(0,'/home/ubuntu/cambc-autumn/research/ideas-2026-11-11/fishfight/tools')
from summ import mean
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def run(name,path,opp,by_us):
    rows=[r for r in pickle.load(open(path,'rb'))['rows'] if r['opp']==opp and r['by_us']==by_us and r['nA']>r['nD']]
    rows.sort(key=lambda r:r['dir']); cur=None; out=collections.defaultdict(list)
    for r in rows:
        if cur!=r['dir']:
            cur=r['dir']; meta=json.load(open(cur+'/meta.json')); R=json.load(gzip.open(cur+'/rounds.json.gz')); ch=R['champions']
        A=[c for c in ch if (c['team']==r['us'])==r['by_us']]
        t0=[c for c in ch if c not in A and meta['champions'][c['id']]['name']==r['tgt']][0]
        for q in (1,3,6,10):
            i=r['r0']-1-q
            if i<0 or not t0['alive'][i]: continue
            tp=(t0['x'][i],t0['y'][i])
            near=[c for c in A if c['alive'][i] and cheb((c['x'][i],c['y'][i]),tp)<=10]
            if len(near)<2: continue
            pts=[(c['x'][i],c['y'][i]) for c in near]
            pair=[cheb(a,b) for k,a in enumerate(pts) for b in pts[k+1:]]
            out['pair%d'%q].append(sum(pair)/len(pair)); out['n10_%d'%q].append(len(near))
            # largest clump: most bodies within 3 of some body
            out['clump3_%d'%q].append(max(sum(1 for b in pts if cheb(a,b)<=3) for a in pts))
            out['dmin%d'%q].append(min(cheb(p,tp) for p in pts))
            # of A alive anywhere: share within 10
            out['share10_%d'%q].append(len(near)/max(1,sum(1 for c in A if c['alive'][i])))
    print(name.ljust(12),'n',len(rows),' | '.join('r0-%d: A within 10 of t0 %.2f (%.0f%% of alive), mean pairwise %.2f, largest clump(3) %.2f, nearest %.1f'%(q,mean(out['n10_%d'%q]),100*mean(out['share10_%d'%q]),mean(out['pair%d'%q]),mean(out['clump3_%d'%q]),mean(out['dmin%d'%q])) for q in (1,3,6,10)))
P='/home/ubuntu/tmp-offload/fishfight/'
run('liveFish',P+'live.pkl','Inte',False); run('Flp4-lad',P+'local.pkl','Inte',False); run('Flp4-gen',P+'rows-base-gen.pkl','Inte',False); run('Flp4f-gen',P+'rows-Flp4f-gen.pkl','Inte',False)
run('liveMite',P+'live.pkl','Mite',False); run('Mt3q',P+'local.pkl','Mite',False); run('us v Fish',P+'live.pkl','Inte',True); run('us v Flp4',P+'local.pkl','Inte',True)
