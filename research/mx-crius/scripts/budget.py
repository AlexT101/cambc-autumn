"""Time budget by champion type over rounds <= END: dead, recall channel, tribute channel, on spawn, moving, still
(near an awake/any camp or not is not split). usage: py budget.py EXTRACT [END] [TEAM]  (TEAM: bot name filter)"""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]; END=int(sys.argv[2]) if len(sys.argv)>2 else 600; TEAM=sys.argv[3] if len(sys.argv)>3 else None
CH=json.load(open(A+'/enums.json'))['champions']
def one(d):
    m=json.load(open(d+'/meta.json')); typ={c['id']:CH[c['type']] for c in m['champions']}
    names=[t['name'] for t in m['teams']]
    R=json.load(gzip.open(d+'/rounds.json.gz')); rr=R['round']
    cen={}
    for t in (0,1):
        xs=[(c['x'][0],c['y'][0]) for c in R['champions'] if c['team']==t and c['x'][0] is not None]
        cen[t]=(sum(a for a,b in xs)/len(xs),sum(b for a,b in xs)/len(xs)) if xs else (0,0)
    out=collections.Counter()
    for c in R['champions']:
        if TEAM and names[c['team']]!=TEAM: continue
        if all((c['gems'][i] or 0)==0 for i in range(len(rr))) and all(not c['x'][i] or c['x'][i]==c['x'][0] for i in range(len(rr))): continue  # idle side
        ty=typ[c['id']]
        for i,r in enumerate(rr):
            if r>END: break
            if not c['alive'][i]: k='dead'
            elif c['chan'][i]==2: k='tribute'
            elif c['x'][i] is not None and max(abs(c['x'][i]-cen[c['team']][0]),abs(c['y'][i]-cen[c['team']][1]))<=1.5: k='spawn'
            elif i>0 and c['x'][i-1] is not None and (c['x'][i],c['y'][i])!=(c['x'][i-1],c['y'][i-1]): k='move'
            else: k='still'
            out[(ty,k)]+=1; out[('all',k)]+=1
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(A+'/*/meta.json')]
    tot=collections.Counter()
    with ProcessPoolExecutor(48) as ex:
        for o in ex.map(one,ds,chunksize=8): tot.update(o)
    K=('move','still','recall','tribute','spawn','dead')
    for ty in ['all','Prism','Vesper Vale','Cassi','Issac','Willow','Ryth','Vendetta','Marcella']:
        s=sum(tot[(ty,k)] for k in K)
        if s: print('%-12s'%ty,' '.join('%s %.1f%%'%(k,100*tot[(ty,k)]/s) for k in K))
