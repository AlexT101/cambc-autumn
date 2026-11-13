import json,gzip,glob,collections,sys,os,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; TYPE=sys.argv[2]
en=json.load(open(ROOT+'/enums.json'))['champions']
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    meta=json.load(open(d+'/meta.json'))
    mp=json.load(open(os.path.normpath(os.path.join(d,meta['mapFile']))))
    R=json.load(gzip.open(d+'/rounds.json.gz'))
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    camp_pos={c['id']:(c['x'],c['y']) for c in mp['camps']}
    rid={r:i for i,r in enumerate(R['round'])}
    res=[]
    for ci,c in enumerate(R['champions']):
        if en[meta['champions'][ci]['type']]!=TYPE: continue
        cid=c['id']; my=[e for e in ev if e.get('a')==cid]
        starts={}
        for j,e in enumerate(my):
            if e['k']=='recall_start': starts=e
            if e['k']=='recall_end' and starts:
                r0=starts['r']; i0=rid.get(r0-1,0)
                hpf=c['hp'][i0]/max(1,c['maxHp'][i0]); gold=c['gold'][i0]; gems=c['gems'][i0]
                frm=tuple(e['f'])
                # after arrival: shop within 2 rounds, next camp hit position
                shop=any(x['k']=='shop' and e['r']<=x['r']<=e['r']+1 for x in my[j:j+8])
                nxt=next((x for x in my[j:] if x['k'] in('attack','cast') and x.get('cdmg')),None)
                trib=next((x for x in my[j:] if x['k']=='tribute_start'),None)
                tribsoon = trib is not None and (nxt is None or trib['s']<nxt['s'])
                if nxt:
                    tp=camp_pos.get(nxt['cdmg'][0][0]) or tuple(nxt['to'])
                    d_home=cheb(tuple(e['to']),tp); d_from=cheb(frm,tp); dt=nxt['r']-e['r']
                else: d_home=d_from=dt=-1
                res.append((hpf,gold,gems,shop,d_home,d_from,dt,cheb(frm,tuple(e['to'])),tribsoon,e['r']))
                starts={}
    return res
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    S=[]
    with ProcessPoolExecutor(48) as ex:
        for s in ex.map(one,ds,chunksize=4): S+=s
    S=[x for x in S if x[9]<=600]
    n=len(S); print(TYPE,'completed recalls r<=600 per game', n/len(ds))
    print('hp<50%',sum(x[0]<0.5 for x in S)/n,'hp>=90%',sum(x[0]>=0.9 for x in S)/n,'shop on arrival',sum(x[3] for x in S)/n,'tribute before next hit',sum(x[8] for x in S)/n)
    print('mean gold at start',statistics.mean(x[1] for x in S),'mean gems',statistics.mean(x[2] for x in S),'mean dist from spawn',statistics.mean(x[7] for x in S))
    H=[x for x in S if x[4]>=0]
    print('next hit: dist from spawn',statistics.mean(x[4] for x in H),'dist from recall origin',statistics.mean(x[5] for x in H),'rounds until',statistics.mean(x[6] for x in H))
    back=[x for x in H if x[5]<=x[4]-5]
    print('next hit nearer origin than spawn by 5+ (went home and came back):',len(back)/len(H),'mean rounds until hit',statistics.mean(x[6] for x in back) if back else 0)
    hb=[x for x in back if x[0]>=0.9 and not x[3]]
    print('  of those at >=90% hp and no shop:',len(hb)/len(H))
