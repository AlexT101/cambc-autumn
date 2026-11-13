# Branch shares of champion turns (D lines), winner vs loser, in the 1,024 mirror games.
import json,glob,zipfile,collections
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    w=m['result']['winner']; z=zipfile.ZipFile('/home/ubuntu/wt/mac13-kronos/'+m['source'])
    out={}
    for side in (0,1):
        c=collections.Counter()
        for line in z.read('team-%s.stdout'%'ab'[side]).decode('latin1').splitlines():
            if line.startswith('D '): c[line.split()[3]]+=1
        out['W' if side==w else 'L']=c
    return out
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=4) if x]
    for k in 'WL':
        A=collections.Counter()
        for x in R: A.update(x[k])
        t=sum(A.values()); print(k,{b:round(v/t,3) for b,v in A.most_common(18)})
    print('games with any U: W',sum(1 for x in R if x['W']['U']),'L',sum(1 for x in R if x['L']['U']))
