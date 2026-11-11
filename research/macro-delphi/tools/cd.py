import json,gzip,glob,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def cheb(a,b):
    if None in a or None in b: return 99
    return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    M=json.load(open(d+'/meta.json'))
    names={c['id']:c['name'] for c in M['champions']}; team={c['id']:c['team'] for c in M['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}; C={c['id']:c for c in R['champions']}
    evs=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    out=collections.Counter()
    for e in evs:
        if e['k']!='death' or names[e['v']]!='Prism' or names.get(e.get('by'))!='Prism': continue
        v=e['v'];k=e['by'];r=e['r']
        # first damaging cast by k on v within 10 rounds before death
        hits=[x for x in evs if r-10<=x['r']<=r and x['k']=='cast' and x.get('a')==k and any(t==v for t,_ in x.get('dmg',[]))]
        if not hits: continue
        h=hits[0]; i=ri.get(h['r']-1)
        if i is None: continue
        vst=C[v]['cd0'][i]; kst=C[k]['cd0'][i]
        out['n']+=1
        out['victim stun ready']+= vst==0
        out['killer stun ready']+= kst==0
        out['first hit is stun']+= h['slot']==0
        # did victim cast slot0 on a camp in prior 8 rounds while killer seen within 8
        wasted=False
        for x in evs:
            if h['r']-8<=x['r']<h['r'] and x['k']=='cast' and x.get('a')==v and x['slot']==0 and 'camp' in x:
                j=ri.get(x['r'])
                if j is not None and k in C[v]['sees'][j]: wasted=True
        out['victim stunned a camp w/ killer in sight in prior 8']+=wasted
        anywaste=any(h['r']-8<=x['r']<h['r'] and x['k']=='cast' and x.get('a')==v and x['slot']==0 and 'camp' in x for x in evs)
        out['victim stunned a camp prior 8']+=anywaste
        rat=C[v]['foc'][i]/max(1,C[k]['foc'][i]); out['ratio>=0.8']+= rat>=0.8
        out['ratio>=0.8 & victim stun down']+= rat>=0.8 and vst>0
    return out
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    agg=collections.Counter()
    for o in ProcessPoolExecutor(32).map(one,dirs): agg.update(o)
    print(agg)
if __name__=='__main__': main()
