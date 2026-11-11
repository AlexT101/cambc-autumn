import sys,pickle,collections
sys.path.insert(0,'/home/ubuntu/cambc-autumn/research/ideas-2026-11-11/fishfight/tools')
from summ import mean
P='/home/ubuntu/tmp-offload/fishfight/'
def run(name,path,opp,by_us):
    rows=[r for r in pickle.load(open(path,'rb'))['rows'] if r['opp']==opp and r['by_us']==by_us and r['nA']>r['nD']]
    B=[b for r in rows for b in r['B']]
    s=name.ljust(11)+' A bodies within 8 seen by t0 at r0-1: %.0f%%; within 4: %.0f%% (n %d); 5-8: %.0f%%'%(100*mean([b['seen_by_t'] for b in B]),100*mean([b['seen_by_t'] for b in B if b['d'][0]<=4]),sum(1 for b in B if b['d'][0]<=4),100*mean([b['seen_by_t'] for b in B if b['d'][0]>4]))
    s+=' | unseen within 4 per eng %.2f, seen within 4 %.2f'%(mean([sum(1 for b in r['B'] if b['d'][0]<=4 and not b['seen_by_t']) for r in rows]),mean([sum(1 for b in r['B'] if b['d'][0]<=4 and b['seen_by_t']) for r in rows]))
    for lab,f in (('0 unseen<=5',lambda r: sum(1 for b in r['B'] if b['d'][0]<=5 and not b['seen_by_t'])==0),('1+ unseen<=5',lambda r: sum(1 for b in r['B'] if b['d'][0]<=5 and not b['seen_by_t'])>=1)):
        x=[r for r in rows if f(r)]
        s+=' | %s: n %d died %.0f%% net %+.2f'%(lab,len(x),100*mean([r['died'] for r in x]),mean([r['kA']-r['kD'] for r in x]))
    print(s)
run('liveFish',P+'live.pkl','Inte',False); run('Flp4-lad',P+'local.pkl','Inte',False); run('Flp4-gen',P+'rows-base-gen.pkl','Inte',False)
run('liveMite',P+'live.pkl','Mite',False); run('Mt3q',P+'local.pkl','Mite',False); run('us v Fish',P+'live.pkl','Inte',True); run('us v Flp4',P+'local.pkl','Inte',True)
