import sys,pickle,collections
sys.path.insert(0,'/home/ubuntu/cambc-autumn/research/ideas-2026-11-11/fishfight/tools')
from summ import *
L,M=cells()
cols=[('live Fish',sel(L,'Inte',False,'A+')),('Flp4',sel(M,'Inte',False,'A+')),('live Mite',sel(L,'Mite',False,'A+')),('Mt3q',sel(M,'Mite',False,'A+')),('us v Fish',sel(L,'Inte',True,'A+')),('us v Flp4',sel(M,'Inte',True,'A+'))]
def w(r,k): return sum(1 for b in r['B'] if b['d'][0] is not None and b['d'][0]<=k)
print('by A bodies within 4 of t0 at r0-1: n, t0 died, net kills, att on t0, dmg on t0')
for name,rows in cols:
    s=name.ljust(12)
    for lo,hi in ((0,0),(1,1),(2,2),(3,9)):
        x=[r for r in rows if lo<=w(r,4)<=hi]
        s+=' | w4=%d%s n%3d died %.2f net %+.2f att %.2f dmg %4.0f'%(lo,'+' if hi>lo else ' ',len(x),mean([r['died'] for r in x]),mean([r['kA']-r['kD'] for r in x]),mean([r['att_on_t0'] for r in x]),mean([r['dmg_on_t0'] for r in x]))
    print(s)
print('kills by A, kills by D, and by nA-nD')
for name,rows in cols:
    s=name.ljust(12)+' kA %.3f kD %.3f'%(mean([r['kA'] for r in rows]),mean([r['kD'] for r in rows]))
    for dlt in (1,2,3):
        x=[r for r in rows if (r['nA']-r['nD']==dlt if dlt<3 else r['nA']-r['nD']>=3)]
        s+=' | +%d n%3d died %.2f net %+.2f'%(dlt,len(x),mean([r['died'] for r in x]),mean([r['kA']-r['kD'] for r in x]))
    print(s)
print('target type: share, died')
for name,rows in cols:
    c=collections.Counter(r['tgt'] for r in rows); dd=collections.Counter(r['tgt'] for r in rows if r['died'])
    print(name.ljust(12),' '.join('%s %d/%d'%(k[:5],dd[k],v) for k,v in c.most_common(9)))
print('initiator type')
for name,rows in cols:
    c=collections.Counter(r['init'] for r in rows); dd=collections.Counter(r['init'] for r in rows if r['died'])
    print(name.ljust(12),' '.join('%s %d/%d'%(k[:5],dd[k],v) for k,v in c.most_common(9)))
print('first ability')
for name,rows in cols:
    c=collections.Counter((r['first_kind'],r['first_ab']) for r in rows)
    print(name.ljust(12),dict(c.most_common(6)))
print('target rank among D within 8: lowest abs hp? nearest to A centroid?')
for name,rows in cols:
    lo=[];
    for r in rows:
        if len(r['Dd'])<2: continue
        # Dd includes t0 itself with d==0
        hps=sorted(x['hp'] for x in r['Dd']); lo.append(r['hp_t']<=hps[0]+1e-9)
    print(name.ljust(12),'multi-defender cases %d, target is lowest hp-frac %.2f'%(len(lo),mean(lo)))
print('timeline: cumulative dmg on t0 by offset; A bodies within 3 of t0 at +1..+4')
for name,rows in cols:
    print(name.ljust(12),'died by off: '+' '.join('%d:%.2f'%(o,mean([r['died'] and r['die_off']<=o for r in rows])) for o in (1,2,3,5,8,12,20)),
      '| A within3 at +1..+4 '+' '.join('%.2f'%mean([sum(1 for b in r['B'] if b['dafter'][q] is not None and b['dafter'][q]<=3) for r in rows]) for q in range(4)))
