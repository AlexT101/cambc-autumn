# Summary of engagement rows: summ.py [min_ratio_filter]
import sys, pickle, collections, statistics as st
def mean(x):
    x=[v for v in x if v is not None]; return sum(x)/len(x) if x else float('nan')
def cells():
    L=pickle.load(open('/home/ubuntu/tmp-offload/fishfight/live.pkl','rb'))['rows']; M=pickle.load(open('/home/ubuntu/tmp-offload/fishfight/local.pkl','rb'))['rows']
    return L,M
def sel(rows,opp,by_us,rel):
    o=[]
    for r in rows:
        if r['opp']!=opp or r['by_us']!=by_us: continue
        if rel=='A+' and not r['nA']>r['nD']: continue
        if rel=='A=' and not r['nA']==r['nD']: continue
        if rel=='A-' and not r['nA']<r['nD']: continue
        o.append(r)
    return o
def desc(rows):
    n=len(rows)
    if not n: return {}
    B=[b for r in rows for b in r['B']]
    d=collections.OrderedDict()
    d['n']=n
    d['net kills for attacker']=mean([r['kA']-r['kD'] for r in rows])
    d['nA within 8']=mean([r['nA'] for r in rows]); d['nD within 8']=mean([r['nD'] for r in rows])
    d['first target died']=mean([r['died'] for r in rows])
    d['die offset (rounds)']=mean([r['die_off'] for r in rows])
    d['attackers on t0 total']=mean([r['att_on_t0'] for r in rows])
    for o in range(4): d['att cum on t0 by off %d'%o]=mean([r['att_cum'][o] for r in rows])
    for o in range(4): d['dmg on t0 at off %d'%o]=mean([r['dmg_by_off'][o] for r in rows])
    d['dmg on t0']=mean([r['dmg_on_t0'] for r in rows])
    d['dmg on t0 / its hp']=mean([r['dmg_on_t0']/max(1,r['hp_t']*r['maxhp_t']) for r in rows])
    d['t0 hp frac']=mean([r['hp_t'] for r in rows]); d['t0 maxhp']=mean([r['maxhp_t'] for r in rows])
    d['t0 hp abs']=mean([r['hp_t']*r['maxhp_t'] for r in rows])
    d['first hit cast']=mean([r['first_kind']=='cast' for r in rows]); d['first hit dist']=mean([r['first_dist'] for r in rows])
    d['stun t0 off0']=mean([r['stun_t0'][0]>0 for r in rows]); d['stun t0 off0-1']=mean([r['stun_t0'][0]+r['stun_t0'][1]>0 for r in rows])
    d['heal on t0']=mean([r['heal_t0'] for r in rows])
    d['t0 hit camp r0-1']=mean(['C' in r['t_act'][0] for r in rows]); d['t0 channelling']=mean([r['t_chan']>0 for r in rows])
    d['on defender half']=mean([r['home_D'] for r in rows])
    d['defender hitters']=mean([r['def_hitters'] for r in rows]); d['dmg by D']=mean([r['dmg_D'] for r in rows]); d['dmg by A']=mean([r['dmg_A'] for r in rows])
    d['late joiners']=mean([r['late_join'] for r in rows])
    # bodies
    for q,lab in ((0,'r0-1'),(2,'r0-3'),(4,'r0-6'),(5,'r0-9')): d['A body dist to t0 at %s'%lab]=mean([b['d'][q] for b in B])
    for k in (3,4,5): d['A bodies within %d at r0-1'%k]=mean([sum(1 for b in r['B'] if b['d'][0] is not None and b['d'][0]<=k) for r in rows])
    d['A bodies within 5 at r0-3']=mean([sum(1 for b in r['B'] if b['d'][2] is not None and b['d'][2]<=5) for r in rows])
    d['A body hit t0 share']=mean([b['first_hit_t0'] is not None for b in B]); d['A body hit any champ share']=mean([b['first_hit_off'] is not None for b in B])
    d['A body hit champ at off0']=mean([b['first_hit_off']==0 for b in B]); d['A body hit champ by off1']=mean([b['first_hit_off'] is not None and b['first_hit_off']<=1 for b in B])
    d['A body hit camp r0-1']=mean(['C' in b['pre'][0] for b in B]); d['A body hit camp r0-1..-3']=mean([any('C' in x for x in b['pre'][:3]) for b in B])
    d['A body hit camp r0..r0+2']=mean([any('C' in x for x in b['post'][:3]) for b in B])
    d['A body never hit: hit camp r0..+2']=mean([any('C' in x for x in b['post'][:3]) for b in B if b['first_hit_off'] is None])
    d['A body never hit: dist r0-1']=mean([b['d'][0] for b in B if b['first_hit_off'] is None])
    d['A body never hit: dist +3']=mean([b['dafter'][2] for b in B if b['first_hit_off'] is None])
    d['A body dash r0..r0+1']=mean([any('D' in x for x in b['post'][:2]) for b in B])
    d['A body hp frac']=mean([b['hp'] for b in B]); d['A body min hp frac']=mean([min(b['hp'] for b in r['B']) for r in rows if r['B']])
    d['A body items']=mean([b['nitems'] for b in B]); d['A body str']=mean([b['str'] for b in B])
    d['A body cd0 ready']=mean([b['cd0']==0 for b in B]); d['A body cd1 ready']=mean([b['cd1']==0 for b in B])
    d['A dmg per attacker']=mean([b['dmg'] for b in B if b['first_hit_off'] is not None])
    d['A body dist to t0 +2']=mean([b['dafter'][1] for b in B]); d['A body dist to t0 +4']=mean([b['dafter'][3] for b in B])
    d['t0 moved by +2']=mean([r['t_move'][1] for r in rows]); d['t0 moved by +4']=mean([r['t_move'][3] for r in rows])
    d['t0 hp frac after r0']=mean([r['t_hp'][0] for r in rows]); d['t0 hp frac after r0+1']=mean([r['t_hp'][1] for r in rows]); d['t0 hp frac after r0+2']=mean([r['t_hp'][2] for r in rows])
    Dd=[x for r in rows for x in r['Dd']]
    d['D body hit back share']=mean([x['dmg']>0 for x in Dd]); d['D body hit camp r0..+2']=mean([any('C' in y for y in x['post'][:3]) for x in Dd])
    d['D ally dist to t0 r0-1']=mean([x['d'] for x in Dd if x['d']>0]); d['D ally dist to t0 +3']=mean([x['dafter'][2] for x in Dd if x['d']>0])
    d['duration']=mean([r['r1']-r['r0']+1 for r in rows]); d['round']=mean([r['r0'] for r in rows])
    return d
if __name__=='__main__':
    L,M=cells()
    by_us=sys.argv[1]=='us'; rel=sys.argv[2]
    cols=[('live Fish',sel(L,'Inte',by_us,rel)),('Flp4',sel(M,'Inte',by_us,rel)),('live Mite',sel(L,'Mite',by_us,rel)),('Mt3q',sel(M,'Mite',by_us,rel))]
    if len(sys.argv)>3: cols+=[('ours v Fish (mirror)',sel(L,'Inte',not by_us,rel)),('ours v Flp4',sel(M,'Inte',not by_us,rel))]
    D=[desc(r) for _,r in cols]
    print('%-38s'%('attacker=%s, %s'%(sys.argv[1],rel))+''.join('%22s'%c for c,_ in cols))
    for k in D[0]:
        print('%-38s'%k+''.join('%22.3f'%d.get(k,float('nan')) for d in D))
