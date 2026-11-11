import pickle,collections
import sys
G=pickle.load(open(sys.argv[1] if len(sys.argv)>1 else 'deaths.pkl','rb'))
seen=set(); G2=[]
for g in G:
    if g['match'] in seen: continue
    seen.add(g['match']); G2.append(g)
G=G2; print(len(G))
for opp in ('Inte','Mite'):
    gs=[g for g in G if g['opp']==opp]
    for lim in (150,300,2000):
        c=collections.Counter(); w=collections.Counter()
        for g in gs:
            D=[d for d in g['D'] if not d['camp'] and d['r']<=lim]
            k='none' if not D else ('us_first' if D[0]['ours'] else 'them_first')
            c[k]+=1; w[k]+=g['win']
        print(opp,'first champ kill by r',lim,{k:(c[k],round(w[k]/c[k],2)) for k in c})
    # net kills by r200 vs win
    c=collections.Counter(); w=collections.Counter()
    for g in gs:
        net=sum((1 if not d['ours'] else -1) for d in g['D'] if not d['camp'] and d['r']<=200 and d['typ']!='Issac')
        k=max(-3,min(3,net)); c[k]+=1; w[k]+=g['win']
    print(opp,'net kills by r200 -> (n, winrate)',{k:(c[k],round(w[k]/c[k],2)) for k in sorted(c)})
# which of our types die first / in early fights
c=collections.Counter(); t=collections.Counter()
for g in G:
    for d in g['D']:
        if d['camp'] or d['r']>200: continue
        (c if d['ours'] else t)[d['typ']]+=1
picks=collections.Counter(p for g in G for p in g['our_picks']); opicks=collections.Counter(p for g in G for p in g['opp_picks'])
print('our early deaths per pick-game',{k:round(v/max(1,picks.get(k if k not in('Cassi','Issac') else 'Cassi & Issac',1)),2) for k,v in c.items()})
print('their early deaths per pick-game',{k:round(v/max(1,opicks.get(k if k not in('Cassi','Issac') else 'Cassi & Issac',1)),2) for k,v in t.items()})
