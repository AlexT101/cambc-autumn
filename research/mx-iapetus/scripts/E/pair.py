# Per-game tribute/death metrics for CAND (team named CAND) in extracted A/B batches; with two dirs, paired by source file name.
# Usage: pair.py EXTRACT_DIR CAND_NAME [EXTRACT_DIR2 CAND_NAME2]
import json,gzip,sys,os,collections
from multiprocessing import Pool
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def game(args):
    A,d,row,cand=args
    try:
        m=json.load(open(A+d+'/meta.json')); R=json.load(gzip.open(A+d+'/rounds.json.gz'))
        ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    except Exception: return None
    teams=row['teams']; ct=teams.index(cand) if cand in teams else None
    if ct is None: return None
    w=m['result']['winner']
    ch={int(c['id']):c for c in R['champions']}; ri={x:i for i,x in enumerate(R['round'])}
    o=collections.Counter(); o['win']=int(w==ct); o['rounds']=R['round'][-1]
    open_={}
    for e in ev:
        if e['k']=='death':
            o['deaths_c' if ch[e['a']]['team']==ct else 'deaths_r']+=1
        if e['k']=='tribute_start': open_[e['a']]=e
        elif e['k'] in ('tribute_end','tribute_cancel') and e['a'] in open_:
            s=open_.pop(e['a']); g=s.get('gems',0)
            if g<100: continue
            side='c' if ch[s['a']]['team']==ct else 'r'
            done=e['k']=='tribute_end'
            o['big_'+side]+=1; o['done_'+side]+=done
            if done and e.get('total',0)>=1000: o['final_'+side]+=1
            if not done: o['cancel_%s_%s'%(side,e.get('cause'))]+=1
            i0=ri.get(s['r']); i1=ri.get(e['r'])
            if side=='r' and i0 is not None and i1 is not None:
                seen=any(s['a'] in ch[x]['sees'][i] for i in range(i0,i1+1) for x in ch if ch[x]['team']==ct)
                o['seen_r']+=seen; o['seen_done_r']+=seen and done
    return row['file'],dict(o)
def load(A,cand):
    A=A.rstrip('/')+'/'
    idx=json.load(open(A+'index.json'))['games']
    jobs=[(A,r['dir'],dict(r,file=os.path.basename(r.get('source',r.get('file','')))),cand) for r in idx]
    with Pool(32) as p: res=[x for x in p.map(game,jobs) if x]
    return dict(res)
def tot(D):
    t=collections.Counter()
    for v in D.values(): t.update(v)
    n=len(D); return {k:round(t[k]/n,3) for k in sorted(t)},n
if __name__=='__main__':
    a=load(sys.argv[1],sys.argv[2])
    if len(sys.argv)>3:
        b=load(sys.argv[3],sys.argv[4]); keys=set(a)&set(b)
        a={k:a[k] for k in keys}; b={k:b[k] for k in keys}
        ta,n=tot(a); tb,_=tot(b); print('paired games',n)
        for k in sorted(set(ta)|set(tb)): print('%-22s %8.3f %8.3f %+8.3f'%(k,ta.get(k,0),tb.get(k,0),tb.get(k,0)-ta.get(k,0)))
        flips=collections.Counter((a[k].get('win',0),b[k].get('win',0)) for k in keys); print('win A->B',dict(flips))
    else:
        t,n=tot(a); print(n); [print(k,v) for k,v in t.items()]
