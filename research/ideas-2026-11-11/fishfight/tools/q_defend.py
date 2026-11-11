import sys,pickle,collections
sys.path.insert(0,'/home/ubuntu/cambc-autumn/research/ideas-2026-11-11/fishfight/tools')
from summ import *
L,M=cells()
for rel in ('A-','A=','A+'):
    cols=[('us v Fish',sel(L,'Inte',True,rel)),('us v Flp4',sel(M,'Inte',True,rel)),('us v Mite',sel(L,'Mite',True,rel)),('us v Mt3q',sel(M,'Mite',True,rel))]
    print('we started,',rel)
    for name,rows in cols:
        n=len(rows)
        tg=collections.Counter(r['tgt'] for r in rows); dd=collections.Counter(r['tgt'] for r in rows if r['died'])
        print(' ',name.ljust(10),'n %3d kA %.3f kD %.3f | t0 died by off '%(n,mean([r['kA'] for r in rows]),mean([r['kD'] for r in rows]))+' '.join('%d:%.3f'%(o,mean([r['died'] and r['die_off']<=o for r in rows])) for o in (2,5,8,12,20,40)),
          '| t0 hp +1..+6 '+' '.join('%.2f'%mean([r['t_hp'][q] for r in rows]) for q in range(6)),
          '| t0 dist from start +1..+4 '+' '.join('%.1f'%mean([r['t_move'][q] for r in rows]) for q in range(4)))
        print('    targets (died/n):',' '.join('%s %d/%d'%(k[:5],dd[k],v) for k,v in tg.most_common(8)))
        # defenders' reaction: share of D bodies within 8 that hit back by off1; D bodies within 3 of t0 at +2
        Dd=[x for r in rows for x in r['Dd'] if x['d']>0]
        print('    D allies: hit back %.2f, hit camp r0..+2 %.2f, dist to t0 r0-1 %.2f -> +2 %.2f -> +4 %.2f | our attackers dist to t0 +2 %.2f +4 %.2f | dmg by us %.0f by them %.0f, our hitters %.2f, their hitters %.2f, dur %.1f'%(
            mean([x['dmg']>0 for x in Dd]),mean([any('C' in y for y in x['post'][:3]) for x in Dd]),mean([x['d'] for x in Dd]),mean([x['dafter'][1] for x in Dd]),mean([x['dafter'][3] for x in Dd]),
            mean([b['dafter'][1] for r in rows for b in r['B']]),mean([b['dafter'][3] for r in rows for b in r['B']]),mean([r['dmg_A'] for r in rows]),mean([r['dmg_D'] for r in rows]),mean([r['att_total'] for r in rows]),mean([r['def_hitters'] for r in rows]),mean([r['r1']-r['r0']+1 for r in rows])))
