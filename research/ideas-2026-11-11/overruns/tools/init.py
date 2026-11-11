import pickle,collections
from engage import engagements
for pk,tag in(('deaths.pkl','live'),('deaths_local.pkl','local')):
    G=pickle.load(open(pk,'rb')); seen=set(); S=collections.defaultdict(collections.Counter)
    for g in G:
        if g['match'] in seen: continue
        seen.add(g['match'])
        for en in engagements(g,maxr=250):
            a,b=en['near']
            rel='even' if a==b else ('we+' if a>b else 'they+')
            who='we_init' if en['first_us'] else 'they_init'
            for k in ((tag,g['opp'],who,rel),(tag,g['opp'],who,'ALL')):
                s=S[k]; s['n']+=1; s['ourk']+=en['kills'][0]; s['theirk']+=en['kills'][1]; s['ourdmg']+=en['dmg'][0]; s['theirdmg']+=en['dmg'][1]
                s['small']+= sum(en['dmg'])<150
    for k in sorted(S):
        s=S[k]; print(k,'n %4d | our kills %.3f their kills %.3f | net/eng %+.3f | dmg us %.0f them %.0f | poke-only(<150 dmg) %.2f'%(s['n'],s['ourk']/s['n'],s['theirk']/s['n'],(s['ourk']-s['theirk'])/s['n'],s['ourdmg']/s['n'],s['theirdmg']/s['n'],s['small']/s['n']))
