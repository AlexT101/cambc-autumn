"""Walk legs of 25+ steps (alive, moving every round): share of champion alive time, and the share whose end is
within 5 tiles of their start (wasted round trips), by type; rounds<=600."""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
R=sys.argv[1]; CH=json.load(open(R+'/enums.json'))['champions']
def one(p):
    d=os.path.dirname(p); m=json.load(open(p)); typ={c['id']:CH[c['type']] for c in m['champions']}
    RR=json.load(gzip.open(d+'/rounds.json.gz')); n=min(len(RR['round']),600); out=collections.Counter(); sp=json.load(open(os.path.join(d,m['mapFile'])))['spawn']
    for c in RR['champions']:
        t=typ[c['id']]; alive=sum(1 for i in range(n) if c['alive'][i]); out[(t,'alive')]+=alive
        i=1
        while i<n:
            ok=lambda j: c['alive'][j] and c['alive'][j-1] and c['x'][j] is not None and c['x'][j-1] is not None and (c['x'][j],c['y'][j])!=(c['x'][j-1],c['y'][j-1]) and max(abs(c['x'][j]-c['x'][j-1]),abs(c['y'][j]-c['y'][j-1]))<=3
            if not ok(i): i+=1; continue
            j=i
            # allow 2-round pauses inside a leg
            last=i
            while j<n:
                if ok(j): last=j; j+=1
                elif j+2<n and (ok(j+1) or ok(j+2)): j+=1
                else: break
            L=last-i+1
            if L>=25:
                disp=max(abs(c['x'][last]-c['x'][i-1]),abs(c['y'][last]-c['y'][i-1]))
                out[(t,'long')]+=L
                if disp<=5: out[(t,'trip')]+=L
                def zone(j):
                    x,y=c['x'][j],c['y'][j]
                    dd=[max(0,x-s_['maxX'],s_['minX']-x,y-s_['maxY'],s_['minY']-y) for s_ in sp]
                    if dd[c['team']]<=2: return 'spawn'
                    return 'own' if dd[c['team']]<dd[1-c['team']] else 'enemy'
                out[('ALL',zone(i-1)+'->'+zone(last))]+=L
                # was the walker hit by a champion in the 5 rounds before the leg? (retreat proxy): seen by enemy
                se=any(RR['champions'][k]['team']!=c['team'] and RR['champions'][k]['id'] in (c['seenBy'][j] if False else []) for k in [])

            i=last+1
    return out
if __name__=='__main__':
    ps=glob.glob(R+'/*/meta.json'); tot=collections.Counter()
    with ProcessPoolExecutor(48) as ex:
        for o in ex.map(one,ps,chunksize=8): tot.update(o)
    for t in sorted(set(k[0] for k in tot), key=lambda t:-tot[(t,'alive')]):
        a=tot[(t,'alive')]
        if a<200000: continue
        print('%-13s long legs (25+) %.1f%% of alive time; round trips ending within 5 of start %.1f%%'%(t,100*tot[(t,'long')]/a,100*tot[(t,'trip')]/a))
    T=sum(v for k,v in tot.items() if k[0]=='ALL')
    for k,v in sorted(((k,v) for k,v in tot.items() if k[0]=='ALL'),key=lambda kv:-kv[1]): print('  %-16s %.1f%%'%(k[1],100*v/T))
