# Enemy tributes that win alone (score before + bag >= 1000): outcome, seen by CAND or not, CAND deaths within the channel.
import json,gzip,sys,collections
from multiprocessing import Pool
def game(a):
    A,r,cand=a; d=r['dir']; ct=r['teams'].index(cand)
    R=json.load(gzip.open(A+d+'/rounds.json.gz')); ri={x:i for i,x in enumerate(R['round'])}
    ch={int(c['id']):c for c in R['champions']}
    ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    score=[0,0]; op={}; o=collections.Counter()
    for e in ev:
        if e['k']=='tribute_start': op[e['a']]=(e,score[ch[e['a']]['team']])
        elif e['k'] in('tribute_end','tribute_cancel') and e['a'] in op:
            s,sc=op.pop(e['a']); t=ch[s['a']]['team']
            if e['k']=='tribute_end': score[t]=e.get('total',score[t])
            if t==ct or sc+s.get('gems',0)<1000: continue
            i0,i1=ri.get(s['r']),ri.get(e['r'])
            if i0 is None or i1 is None: continue
            seen=any(s['a'] in ch[x]['sees'][i] for i in range(i0,i1+1) for x in ch if ch[x]['team']==ct)
            out='final' if e['k']=='tribute_end' else e.get('cause')
            o['n']+=1; o['seen' if seen else 'unseen']+=1; o[('seen ' if seen else 'unseen ')+str(out)]+=1
            o['deaths_in']+=sum(1 for x in ev if x['k']=='death' and ch[x['v']]['team']==ct and s['r']<=x['r']<=e['r'])
    return o
if __name__=='__main__':
    A,cand=sys.argv[1].rstrip('/')+'/',sys.argv[2]
    idx=json.load(open(A+'index.json'))['games']
    T=collections.Counter()
    with Pool(8) as p:
        for o in p.map(game,[(A,r,cand) for r in idx]): T.update(o)
    for k in sorted(T): print('%-22s %d'%(k,T[k]))
