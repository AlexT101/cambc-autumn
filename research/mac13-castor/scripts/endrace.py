# At game end: the loser's score and score+carried. And for the winner, how long its final tribute took.
import json,gzip,glob,collections,sys,os
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
idx={g['dir']:g for g in json.load(open(ROOT+'/index.json'))['games']}
def one(d):
    g=idx.get(os.path.basename(d)); 
    if not g: return None
    meta=json.load(open(d+'/meta.json'))
    R=json.load(gzip.open(d+'/rounds.json.gz'))
    w=g['winner']; l=1-w; i=len(R['round'])-1
    sc=[R['gems'][0][i],R['gems'][1][i]]
    bag=[0,0]
    for c in R['champions']:
        if c['alive'][i]: bag[c['team']]+=c['gems'][i] or 0
    prism={c['id'] for c in meta['champions'] if en[c['type']]=='Prism'}
    ts=[]
    for line in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(line)
        if e['k'] in('tribute_start','tribute_end','tribute_cancel'): ts.append(e)
    return (g['teams'][w], g['rounds'], sc, bag, w, ts[-3:] if ts else [])
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S=[s for s in ex.map(one,ds,chunksize=4) if s]
    print(S[0]); print(S[1])
    close=collections.Counter(); n=collections.Counter()
    for wn,r,sc,bag,w,ts in S:
        if sc is None: continue
        l=1-w; tot=sc[l]+bag[l]
        k='timeout' if r>=2000 else ('loser>=1000' if tot>=1000 else 'loser 800-999' if tot>=800 else 'loser 500-799' if tot>=500 else 'loser<500')
        close[(k,wn)]+=1; n[k]+=1
    for k in sorted(close): print(k,close[k])
