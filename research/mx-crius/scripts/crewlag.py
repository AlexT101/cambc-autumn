"""Elk/Golem clears with 2+ strikers (>=10% dmg): lag from first hit to the second striker's first hit, share of
clear rounds with 2+ strikers hitting, damage taken before the second striker arrives."""
import json, gzip, glob, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def one(d):
    meta=json.load(open(d+'/meta.json'))
    mp=json.load(open(os.path.join(d,meta['mapFile']))); camps={c['id']:c for c in mp['camps']}
    team={c['id']:c['team'] for c in meta['champions']}; cg={c['id']:c['group'] for c in mp['camps']}
    big={g['id'] for g in mp['groups'] if any(camps[c]['type'] in ('Elk','Golem') for c in g['camps'])}
    open_={}; out=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l); k=e['k']
        if k in('attack','cast') and e.get('cdmg'):
            for cid,amt in e['cdmg']:
                g=cg.get(cid)
                if g not in big: continue
                o=open_.setdefault(g,{'first':{},'dmg':collections.Counter(),'rounds':collections.defaultdict(set),'taken':[]})
                o['first'].setdefault(e['a'],e['r']); o['dmg'][e['a']]+=amt; o['rounds'][e['r']].add(e['a'])
        elif k=='camp_attack' and e.get('g') in open_:
            open_[e['g']]['taken'].append((e['r'],e['dmg']))
        elif k=='group_clear' and e['g'] in open_:
            o=open_.pop(e['g']); tot=sum(o['dmg'].values()); st_=[a for a,v in o['dmg'].items() if v>=0.1*tot]
            if len(st_)<2: continue
            fs=sorted(o['first'][a] for a in st_); r0=fs[0]; r1=fs[1]
            multi=sum(1 for r,s in o['rounds'].items() if len(s & set(st_))>=2); allr=len(o['rounds'])
            before=sum(dm for r,dm in o['taken'] if r<r1); tk=sum(dm for r,dm in o['taken'])
            out.append((r1-r0,multi/allr,before/max(1,tk),e['r']-r0))
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S=[x for o in ex.map(one,ds,chunksize=8) for x in o]
    L=sorted(s[0] for s in S); n=len(S)
    print('crew clears',n,'lag to 2nd striker quartiles',L[n//4],L[n//2],L[3*n//4],'p90',L[9*n//10])
    print('share of hit-rounds with 2+ strikers %.2f; share of damage taken before 2nd arrives %.2f'%(st.mean(s[1] for s in S),st.mean(s[2] for s in S)))
    for lo,hi in ((0,0),(1,3),(4,10),(11,999)):
        xs=[s for s in S if lo<=s[0]<=hi]
        print(' lag %d-%d: %d clears, dur %.1f'%(lo,hi,len(xs),st.mean(s[3] for s in xs)))
