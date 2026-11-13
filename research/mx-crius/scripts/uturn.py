"""Walk legs (maximal runs of rounds in which the champion moved, alive, not channelling) with 8+ steps: share of
walking steps in legs whose Chebyshev displacement is under half the steps (back-and-forth), by champion type."""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
R=sys.argv[1]; END=int(sys.argv[2]) if len(sys.argv)>2 else 2000
CH=json.load(open(R+'/enums.json'))['champions']
def one(p):
    d=os.path.dirname(p); m=json.load(open(p)); typ={c['id']:CH[c['type']] for c in m['champions']}
    RR=json.load(gzip.open(d+'/rounds.json.gz')); n=min(len(RR['round']),END)
    out=collections.Counter()
    for c in RR['champions']:
        t=typ[c['id']]; i=1
        while i<n:
            if not (c['alive'][i] and c['alive'][i-1] and c['x'][i] is not None and c['x'][i-1] is not None and (c['x'][i],c['y'][i])!=(c['x'][i-1],c['y'][i-1]) and max(abs(c['x'][i]-c['x'][i-1]),abs(c['y'][i]-c['y'][i-1]))<=3):
                i+=1; continue
            j=i; steps=0
            while j<n and c['alive'][j] and c['x'][j] is not None and c['x'][j-1] is not None and (c['x'][j],c['y'][j])!=(c['x'][j-1],c['y'][j-1]) and max(abs(c['x'][j]-c['x'][j-1]),abs(c['y'][j]-c['y'][j-1]))<=3:
                steps+=1; j+=1
            disp=max(abs(c['x'][j-1]-c['x'][i-1]),abs(c['y'][j-1]-c['y'][i-1]))
            out[(t,'steps')]+=steps
            if steps>=8 and disp<0.5*steps: out[(t,'waste')]+=steps; out[(t,'legs')]+=1
            i=j
    return out
if __name__=='__main__':
    ps=glob.glob(R+'/*/meta.json'); tot=collections.Counter()
    with ProcessPoolExecutor(48) as ex:
        for o in ex.map(one,ps,chunksize=8): tot.update(o)
    for t in sorted(set(k[0] for k in tot), key=lambda t:-tot[(t,'steps')]):
        if tot[(t,'steps')]<20000: continue
        print('%-13s steps/game %6.0f  in back-and-forth legs %.1f%%  legs/game %.2f'%(t,tot[(t,'steps')]/len(ps),100*tot[(t,'waste')]/tot[(t,'steps')],tot[(t,'legs')]/len(ps)))
