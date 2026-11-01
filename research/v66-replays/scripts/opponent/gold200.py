# Earned gold at r200 by champion type, and gold from captures vs kills in r1-200, per team.
import sys, json
from collections import defaultdict, Counter
from multiprocessing import Pool
S='replays/v66-analysis'
sys.path.insert(0,S+'/an')
from common import *
def one(r):
    m=meta(r['dir']); R=rounds(r['dir']); us=r['us']
    if len(R['round'])<200: return None
    nm={c['id']:c['name'] for c in m['champions']}; tm={c['id']:c['team'] for c in m['champions']}
    out=Counter()
    for c in R['champions']:
        ro='us' if c['team']==us else 'them'
        out[f"{ro}|type|{nm[c['id']]}"]+=c['earned'][199]; out[f"{ro}|typen|{nm[c['id']]}"]+=1
    for e in events(r['dir']):
        if e['r']>200: break
        if e['k']=='capture':
            for cid,gm,gold in e['shares']: out[('us' if tm[cid]==us else 'them')+'|capgold']+=gold
        if e['k']=='death' and e.get('by') is not None: out[('us' if tm[e['by']]==us else 'them')+'|killgold']+=e.get('gold',0)
    return r['opp'],dict(out)
if __name__=='__main__':
    with Pool(40) as p: R=[x for x in p.map(one,games()) if x]
    for o in ['Fish','Mite','UoS','PBG']:
        c=Counter(); n=0
        for oo,x in R:
            if oo==o: c.update(x); n+=1
        print(o,n,'capgold us %.0f them %.0f | killgold us %.0f them %.0f'%(c['us|capgold']/n,c['them|capgold']/n,c['us|killgold']/n,c['them|killgold']/n))
        for ro in ('us','them'):
            print('   ',ro,', '.join(f"{k.split('|')[2]} {c[k]/c[k.replace('|type|','|typen|')]:.0f}" for k in sorted(c) if k.startswith(ro+'|type|') and c[k.replace('|type|','|typen|')]>=10))
