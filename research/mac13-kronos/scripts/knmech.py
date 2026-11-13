# kn (team named kn-x) vs chy-ref on study512: gold spent by r200/400/600 per team, locks placed, lock cancels.
import json,gzip,glob,collections,statistics,sys
from multiprocessing import Pool
ROOT=sys.argv[1] if len(sys.argv)>1 else '/home/ubuntu/wt/mac13-kronos/replays/.kn-analysis'
def one(f):
    m=json.load(open(f)); d=f.rsplit('/',1)[0]
    kn=[i for i,t in enumerate(m['teams']) if t['name'].startswith('kn')]
    if not kn: return None
    k=kn[0]; team={c['id']:c['team'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz')); T=len(o['round'])
    out={'win':m['result']['winner']==k}
    for r in (200,400,600):
        if r<=T:
            sp=[0,0]
            for c in o['champions']:
                e=c['earned'][r-1]; g=c['gold'][r-1]
                if e is not None and g is not None: sp[c['team']]+=e-g
            out['spent%d'%r]=(sp[k],sp[1-k])
    lp=[0,0]; canc=[0,0]
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['k']=='lock_place': lp[e['team']]+=1
        if e['k']=='tribute_cancel' and e.get('cause')=='lock': canc[team[e['a']]]+=1
    out['locks']=(lp[k],lp[1-k]); out['cancelled_by_lock']=(canc[k],canc[1-k])
    return out
if __name__=='__main__':
    fs=glob.glob(ROOT+'/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=4) if x]
    print('games',len(R),'kn wins',sum(x['win'] for x in R))
    for key in ('spent200','spent400','spent600','locks','cancelled_by_lock'):
        S=[x[key] for x in R if key in x]
        print(key,'kn',round(statistics.mean(s[0] for s in S),1),'ref',round(statistics.mean(s[1] for s in S),1),'n',len(S))
