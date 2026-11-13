# When is the mirror decided: P(leader wins) by round for several leads.
import json,gzip,glob,collections
from multiprocessing import Pool
RS=(50,100,150,200,300,400,500,600)
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]; w=m['result']['winner']
    o=json.load(gzip.open(d+'/rounds.json.gz')); T=len(o['round'])
    out={}
    for r in RS:
        if r>=T: continue
        tot=[0,0]; pr=[0,0]; foc=[0,0]; kills=[0,0]; earned=[0,0]; alive=[0,0]
        for c in o['champions']:
            t=c['team']; g=c['gems'][r] or 0
            tot[t]+=g if c['alive'][r] else 0
            earned[t]+=c['earned'][r] or 0; kills[t]+=c['kills'][r] or 0
            if c['foc'][r] is not None and c['name']=='Prism' if 'name' in c else False: pass
        for t in (0,1): tot[t]+=o['gems'][t][r]
        out[r]=(w,tot,earned,kills)
    return out
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=4) if x]
    for r in RS:
        S=[x[r] for x in R if r in x]
        for i,nm in ((1,'gems tributed+carried'),(2,'gold earned'),(3,'kills')):
            dec=[s for s in S if s[i][0]!=s[i][1]]
            ok=sum((s[i][1]>s[i][0])==(s[0]==1) for s in dec)
            big=[s for s in dec if max(s[i])>=1.5*max(1,min(s[i]))]
            okb=sum((s[i][1]>s[i][0])==(s[0]==1) for s in big)
            print(r,nm,'leader wins',round(ok/max(1,len(dec)),3),'n',len(dec),'| 1.5x lead share',round(len(big)/max(1,len(S)),3),'wins',round(okb/max(1,len(big)),3))
