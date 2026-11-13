import json, collections, math
G='/home/ubuntu/cambc-autumn/research/ladder-scrims-2026-11-06/data/games.jsonl'
gs=[json.loads(l) for l in open(G)]
gs=[g for g in gs if g.get('status')=='finished' and g.get('our_picks') and g.get('result') in ('win','loss')]
def tab(filt, label):
    by=collections.defaultdict(lambda:[0,0])
    for g in gs:
        if not filt(g): continue
        k=('ourV' if 'Vesper Vale' in g['our_picks'] else 'noV', 'oppV' if 'Vesper Vale' in g['opp_picks'] else 'oppNoV')
        by[k][0]+=g['result']=='win'; by[k][1]+=1
    print(label)
    for k in sorted(by):
        w,n=by[k]; p=w/n; se=math.sqrt(p*(1-p)/n)
        print(f'   {k}: {w}/{n} = {100*p:.1f} +-{100*se:.1f}')
vers=collections.Counter((g['version'],g['opp_name'],g.get('refset')) for g in gs if g['opp_name']=='Intercontinental Fish' and g.get('refset')=='r8')
print(sorted(vers.items()))
tab(lambda g:g['opp_name']=='Intercontinental Fish' and g.get('refset')=='r8','Fish r8 all versions')
tab(lambda g:g['opp_name']=='Intercontinental Fish' and g.get('refset')=='r2' and g['version']>=110,'Fish r2 v110+')
tab(lambda g:g['opp_name']=='Mite' and g['version']>=113,'Mite v113+')
tab(lambda g:g['opp_name'] not in ('Mite','Intercontinental Fish') and g['version']>=113,'others v113+')
# our Vesper fraction per slot
sl=collections.Counter(); n=0
for g in gs:
    if g['version']>=117 and g['opp_name']=='Intercontinental Fish' and g.get('refset')=='r8':
        n+=1
        if 'Vesper Vale' in g['our_picks']: sl[g['our_picks'].index('Vesper Vale')]+=1
print('our vesper slot (v117+ vs r8):',sl,'of',n)
