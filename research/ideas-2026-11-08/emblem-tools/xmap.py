import sys; sys.path.insert(0,'/home/ubuntu/tmp-offload/emblem/tools'); from arch import *
import collections
S,U,m=day(sys.argv[1]); ty=sys.argv[2]
def modal(team):
    s=(U['team']==team)&(U['type']==ty)
    per=collections.defaultdict(collections.Counter)
    for a,c in zip(S['map'][U['row'][s]],U['e'][s][:,0]): per[a][fam(c).split('-')[0]]+=1
    return {k:v.most_common(1)[0][0] for k,v in per.items() if sum(v.values())>=5}
F=modal('Intercontinental Fish'); O=modal('stellar best girl'); M=modal('Mite')
c=collections.Counter((F[k],O[k]) for k in F if k in O); print('Fish x ours',c.most_common())
c=collections.Counter((M[k],O[k]) for k in M if k in O); print('Mite x ours',c.most_common())
