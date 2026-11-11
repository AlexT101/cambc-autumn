import json,gzip,glob,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def cheb(a,b):
    if None in a or None in b: return 99
    return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    M=json.load(open(d+'/meta.json')); team={c['id']:c['team'] for c in M['champions']}
    mp=json.load(open(d+'/'+M['mapFile'])); tiles={g['id']:[tuple(t) for t in g['tiles']] for g in mp['groups']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}; C=R['champions']
    out=collections.Counter()
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='capture_reset' and e.get('contested'): out['contested_resets']+=1
        if e['k']!='capture': continue
        t=e['team']; gems=sum(s[1] for s in e['shares']); T=tiles.get(e['g'],[])
        best=99; nearown=0
        for rr in range(e['r']-6,e['r']):
            i=ri.get(rr)
            if i is None: continue
            for c in C:
                if c['team']==t or not c['alive'][i]: continue
                dd=min([cheb((c['x'][i],c['y'][i]),p) for p in T] or [99]); best=min(best,dd)
        out['caps']+=1; out['gems']+=gems
        if best<=3: out['opp<=3']+=1; out['gems<=3']+=gems
        if best<=6: out['opp<=6']+=1; out['gems<=6']+=gems
    return out
def main():
    agg=collections.Counter(); n=0
    for o in ProcessPoolExecutor(32).map(one,[x[:-10] for x in glob.glob(A+'/*/meta.json')]): agg.update(o); n+=1
    print({k:round(v/n,1) for k,v in agg.items()})
if __name__=='__main__': main()
