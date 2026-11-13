import json,gzip,glob,collections,statistics
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    team={c['id']:c['team'] for c in m['champions']}
    w=m['result']['winner']
    mp=json.load(open('/home/ubuntu/wt/mac13-kronos/replays/.analysis/maps/'+m['mapFile'].split('/')[-1]))
    starts={}; win=None
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['k']=='tribute_start': starts[e['a']]=e
        elif e['k']=='tribute_end':
            s=starts.pop(e['a'],None)
            if team[e['a']]==w and e['total']>=1000 and s and s['gems']>=200: win=s
        elif e['k']=='tribute_cancel': starts.pop(e['a'],None)
    if not win: return None
    alt=win['altar']; sp=mp['spawn']
    return (len(mp['altars']), alt, sp, w)
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=8) if x]
    print(len(R)); print(R[0])
    import collections
    c=collections.Counter(); fr=[]
    for na,alt,sp,w in R:
        def dd(s): 
            cx=(s['minX']+s['maxX'])/2; cy=(s['minY']+s['maxY'])/2
            return max(abs(alt[0]-cx),abs(alt[1]-cy))
        dw=dd(sp[w]); dl=dd(sp[1-w]); f=dw/(dw+dl); fr.append(f)
        c['winner_side' if f<0.4 else 'mid' if f<=0.6 else 'loser_side']+=1
    print(c)
