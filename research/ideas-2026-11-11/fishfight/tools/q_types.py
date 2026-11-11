import sys,pickle,collections
sys.path.insert(0,'/home/ubuntu/cambc-autumn/research/ideas-2026-11-11/fishfight/tools')
from summ import mean
P='/home/ubuntu/tmp-offload/fishfight/'
def run(name,path,opp,by_us,rel='A+'):
    rows=[r for r in pickle.load(open(path,'rb'))['rows'] if r['opp']==opp and r['by_us']==by_us and ((r['nA']>r['nD']) if rel=='A+' else (r['nA']<r['nD']))]
    n=len(rows); T=collections.defaultdict(collections.Counter)
    for r in rows:
        for b in r['B']:
            t=T[b['typ']]; t['n']+=1; t['hit']+=b['first_hit_off'] is not None; t['dmg']+=b['dmg']; t['w4']+=b['d'][0]<=4; t['camp']+=any('C' in x for x in b['post'][:3])
    print(name,'n',n)
    print('   '+' | '.join('%s present %.2f hits %.0f%% dmg/eng %.0f within4 %.0f%% camp %.0f%%'%(k[:6],t['n']/n,100*t['hit']/t['n'],t['dmg']/n,100*t['w4']/t['n'],100*t['camp']/t['n']) for k,t in sorted(T.items(),key=lambda kv:-kv[1]['n'])[:8]))
    for lab,f in (('Willow within 8',lambda r:any(b['typ']=='Willow' for b in r['B'])),('no Willow within 8',lambda r:not any(b['typ']=='Willow' for b in r['B'])),('Willow hit',lambda r:any(b['typ']=='Willow' and b['first_hit_off'] is not None for b in r['B']))):
        x=[r for r in rows if f(r)]
        if x: print('   %-20s n %3d died %2.0f%% net for attacker %+.2f kA %.2f kD %.2f attackers %.2f dmg on t0 %.0f heal on their side? nA %.2f nD %.2f'%(lab,len(x),100*mean([r['died'] for r in x]),mean([r['kA']-r['kD'] for r in x]),mean([r['kA'] for r in x]),mean([r['kD'] for r in x]),mean([r['att_total'] for r in x]),mean([r['dmg_on_t0'] for r in x]),mean([r['nA'] for r in x]),mean([r['nD'] for r in x])))
run('liveFish T1',P+'live.pkl','Inte',False); run('Flp4-lad T1',P+'local.pkl','Inte',False); run('Flp4-gen T1',P+'rows-base-gen.pkl','Inte',False)
run('liveMite T1',P+'live.pkl','Mite',False); run('Mt3q T1',P+'local.pkl','Mite',False)
run('ocean v Fish (we start, numbers)',P+'live.pkl','Inte',True)
