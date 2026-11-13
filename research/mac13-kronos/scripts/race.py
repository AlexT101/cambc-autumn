import json,gzip,glob,collections,statistics
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz'))
    w=m['result']['winner']; T=len(o['round']); L=1-w
    sc=o['gems']  # per team per round tributed?
    def bags(team,r,prism_only=False,excl_prism=False):
        s=0
        for c in o['champions']:
            if c['team']!=team or not c['alive'][r]: continue
            isp=names[c['id']]=='Prism'
            if prism_only and not isp: continue
            if excl_prism and isp: continue
            s+=c['gems'][r]
        return s
    first=None
    for r in range(T):
        if sc[L][r]+bags(L,r)>=1000: first=r; break
    if first is None: return ('no',)
    return ('yes', T-first, bags(L,first,prism_only=True)/max(1,bags(L,first)), sc[L][first], bags(L,first), sc[w][first], bags(w,first), sc[w][first]+bags(w,first)>=1000)
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=8) if x]
    ys=[x for x in R if x[0]=='yes']; print('games',len(R),'loser had score+bags>=1000 at some round:',len(ys))
    lead=sorted(x[1] for x in ys); n=len(ys); print('rounds from that point to game end',[lead[int(n*q)] for q in (.1,.25,.5,.75,.9)])
    print('prism share of loser bags at that point median',statistics.median(x[2] for x in ys))
    print('loser score at that point median',statistics.median(x[3] for x in ys),'bags',statistics.median(x[4] for x in ys))
    print('winner score',statistics.median(x[5] for x in ys),'winner bags',statistics.median(x[6] for x in ys),'winner also >=1000:',sum(x[7] for x in ys))
