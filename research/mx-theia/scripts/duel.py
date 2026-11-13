# Prism-on-Prism kills: killer vs victim state K rounds before the death (focus, gems, hp, max hp, items,
# allies/enemies within 8 of the victim), and when the two first came within 8 of each other.
import json,gzip,sys,os,collections,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    d=os.path.join(ROOT,d)
    try:
        meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz'))
        ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    except Exception: return []
    names={c['id']:c['name'] for c in meta['champions']}
    CH={c['id']:c for c in R['champions']}; rd={r:i for i,r in enumerate(R['round'])}
    out=[]; seen_first=False
    for e in ev:
        if e['k']=='death' and names.get(e['v'])=='Prism':
            first= not seen_first; seen_first=True
        else: first=False
        if e['k']!='death' or names.get(e['v'])!='Prism' or names.get(e.get('by'))!='Prism': continue
        v,k=CH[e['v']],CH[e['by']]; r=e['r']
        # first round of the approach: walk back while both alive and within 8
        i=rd.get(r-1)
        if i is None: continue
        j=i
        while j>0 and v['alive'][j-1] and k['alive'][j-1] and cheb((v['x'][j-1],v['y'][j-1]),(k['x'][j-1],k['y'][j-1]))<=8: j-=1
        s=j  # contact start
        def st(c,t): return dict(foc=c['foc'][t],gems=c['gems'][t],hp=c['hp'][t],mhp=c['maxHp'][t],items=len(c['items'][t]),str=c['str'][t])
        vp=(v['x'][s],v['y'][s])
        def near(team,t,p):
            return sum(1 for c in R['champions'] if c['team']==team and c['alive'][t] and c['id'] not in (v['id'],k['id']) and cheb((c['x'][t],c['y'][t]),p)<=8)
        out.append(dict(first=first,r=r,dur=i-s+1,V=st(v,s),K=st(k,s),v_allies=near(v['team'],s,vp),k_allies=near(k['team'],s,vp)))
    return out
def main():
    idx=json.load(open(ROOT+'/index.json')); dirs=[g['dir'] for g in idx['games']]
    with ProcessPoolExecutor(32) as ex: rows=[x for l in ex.map(one,dirs,chunksize=8) for x in l]
    if len(sys.argv)>2: rows=[r for r in rows if r['first']]
    print('prism-on-prism kills',len(rows),'(first Prism death of the game only)' if len(sys.argv)>2 else '')
    print('round buckets',sorted(collections.Counter(min(r['r'],900)//150*150 for r in rows).items()))
    for f in ('foc','gems','hp','mhp','items','str'):
        kb=sum(1 for r in rows if r['K'][f]>r['V'][f]); vb=sum(1 for r in rows if r['K'][f]<r['V'][f])
        print('%-5s killer higher %4d victim higher %4d equal %4d | mean K %.0f V %.0f'%(f,kb,vb,len(rows)-kb-vb,statistics.mean(r['K'][f] for r in rows),statistics.mean(r['V'][f] for r in rows)))
    hpf=lambda c:c['hp']/c['mhp']
    print('hp frac at contact: killer %.2f victim %.2f'%(statistics.mean(hpf(r['K']) for r in rows),statistics.mean(hpf(r['V']) for r in rows)))
    print('allies of victim / killer within 8 of victim at contact: %.2f / %.2f'%(statistics.mean(r['v_allies'] for r in rows),statistics.mean(r['k_allies'] for r in rows)))
    print('outnumbered victim (k_allies>v_allies) %d, even %d, victim more %d'%(sum(r['k_allies']>r['v_allies'] for r in rows),sum(r['k_allies']==r['v_allies'] for r in rows),sum(r['k_allies']<r['v_allies'] for r in rows)))
    print('contact duration median',statistics.median(r['dur'] for r in rows), collections.Counter(min(r['dur'],30)//5*5 for r in rows))
    print('victim hp frac at contact buckets',sorted(collections.Counter(round(hpf(r['V']),1) for r in rows).items()))
    fd=[r['K']['foc']-r['V']['foc'] for r in rows]
    print('focus diff K-V buckets',sorted(collections.Counter(max(-100,min(100,x//25*25)) for x in fd).items()))
if __name__=='__main__': main()
