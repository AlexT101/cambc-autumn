# Per team: the first round its score + living bags reach 1000 (R1000), the Prism's share of that, and for the
# winner the lag from R1000 to the win; for the loser, how far behind it was at the winner's R1000.
import json,gzip,glob,collections,sys,os,statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
idx={g['dir']:g for g in json.load(open(ROOT+'/index.json'))['games']}
def one(d):
    g=idx.get(os.path.basename(d))
    if not g or g['rounds']>=2000: return None
    meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz'))
    prism={c['id'] for c in meta['champions'] if en[c['type']]=='Prism'}
    w=g['winner']; n=len(R['round']); out=[]
    for t in (0,1):
        r1=None
        for i in range(n):
            bag=sum((c['gems'][i] or 0) for c in R['champions'] if c['team']==t and c['alive'][i])
            pb=sum((c['gems'][i] or 0) for c in R['champions'] if c['team']==t and c['alive'][i] and c['id'] in prism)
            if R['gems'][t][i]+bag>=1000: r1=(R['round'][i],pb,bag,R['gems'][t][i]); break
        out.append(r1)
    return (g['teams'][w], w, g['rounds'], out, any(c['id'] in prism and c['team']==w for c in meta['champions']))
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S=[s for s in ex.map(one,ds,chunksize=4) if s]
    lag=collections.defaultdict(list); pb=collections.defaultdict(list); first=collections.Counter(); firstwin=collections.Counter()
    for wn,w,r,out,wp in S:
        ow=out[w]; ol=out[1-w]
        if ow: 
            lag[wp].append(r-ow[0]); pb[wp].append(ow[1])
        if ow and ol:
            f=w if ow[0]<ol[0] else (1-w if ol[0]<ow[0] else -1)
            first['both reach 1000']+=1; firstwin['first to 1000 total wins']+= (f==w)
            if f!=w and f!=-1: firstwin['lost after reaching first']+=1
    for k in lag: print('winner has Prism',k,'games',len(lag[k]),'lag median',st.median(lag[k]),'mean %.1f'%st.mean(lag[k]),'Prism bag at R1000 median',st.median(pb[k]))
    print(first,firstwin)
