"""Clears by group kind and number of strikers: rounds first hit -> clear, camp damage taken, by team result."""
import json, gzip, glob, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def kind(G,camps):
    ts=[camps[c]['type'] for c in G['camps']]
    for k in ('Monolith','Golem','Elk','Wolf'):
        if k in ts: return '%s x%d'%(k,len(ts))
    return 'cluster x%d'%len(ts)
def one(d):
    meta=json.load(open(d+'/meta.json'))
    mp=json.load(open(os.path.join(d,meta['mapFile']))); camps={c['id']:c for c in mp['camps']}; groups={g['id']:g for g in mp['groups']}
    team={c['id']:c['team'] for c in meta['champions']}
    cg={c['id']:c['group'] for c in mp['camps']}
    open_={}; out=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l); k=e['k']
        if k in('attack','cast') and e.get('cdmg'):
            for cid,amt in e['cdmg']:
                g=cg.get(cid)
                if g is None: continue
                o=open_.setdefault(g,{'r0':e['r'],'dmg':collections.Counter(),'taken':collections.Counter()})
                o['dmg'][e['a']]+=amt
        elif k=='camp_attack':
            g=e.get('g')
            if g in open_:
                tgt=e['tgt']; open_[g]['taken'][team[tgt]]+=e['dmg']
                for x in e.get('xdmg',[]) or []:
                    pass
        elif k=='group_clear':
            g=e['g']; o=open_.pop(g,None)
            if not o: continue
            tot=sum(o['dmg'].values())
            st_=[a for a,v in o['dmg'].items() if v>=0.1*tot]
            t=team[max(o['dmg'],key=o['dmg'].get)]
            G=groups.get(g)
            if not G: continue
            out.append((kind(G,camps),len(st_),e['r']-o['r0'],o['taken'][t],t==meta['result']['winner']))
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S=[x for o in ex.map(one,ds,chunksize=8) for x in o]
    tab=collections.defaultdict(list)
    for k,n,dur,tk,win in S: tab[(k,min(n,3))].append((dur,tk))
    for key in sorted(tab):
        xs=tab[key]
        if len(xs)<200: continue
        print('%-14s n=%d clears %6d dur %.1f taken %.0f'%(key[0],key[1],len(xs),st.mean(x[0] for x in xs),st.mean(x[1] for x in xs)))
