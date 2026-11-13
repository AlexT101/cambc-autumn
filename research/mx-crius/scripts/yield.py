"""Gems (and gold) per champion-round invested, by group kind: each round of a champion is attributed to the next group
it damages (walk, recall and spawn time included); its share of that group's next capture is the return.
Rounds <= END. Per champion type too (--type)."""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
R=sys.argv[1]; END=int(sys.argv[2]) if len(sys.argv)>2 else 600
CH=json.load(open(R+'/enums.json'))['champions']
def kind(G,camps):
    ts=[camps[c]['type'] for c in G['camps']]
    for k in ('Monolith','Golem','Elk','Wolf'):
        if k in ts: return k
    return 'gem' if all(t=='Gem cluster' for t in ts) else 'gold' if all(t=='Gold cluster' for t in ts) else 'mix'
def one(p):
    d=os.path.dirname(p); m=json.load(open(p)); typ={c['id']:CH[c['type']] for c in m['champions']}
    mp=json.load(open(os.path.join(d,m['mapFile']))); camps={c['id']:c for c in mp['camps']}; cg={c['id']:c['group'] for c in mp['camps']}
    gk={g['id']:kind(g,camps) for g in mp['groups']}
    hits=collections.defaultdict(list); shares=collections.defaultdict(list)
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['r']>END: break
        if e['k'] in ('attack','cast') and e.get('cdmg'):
            g=cg.get(e['cdmg'][0][0])
            if g is not None: hits[e['a']].append((e['r'],g))
        elif e['k']=='capture':
            for cid,gm,gd in e['shares']: shares[cid].append((e['r'],e['g'],gm,gd))
    out=collections.Counter()
    for a,hs in hits.items():
        # jobs: consecutive hits on the same group form one job; its rounds run from the previous job's end
        jobs=[]; prev_end=0
        i=0
        while i<len(hs):
            g=hs[i][1]; j=i
            while j+1<len(hs) and hs[j+1][1]==g: j+=1
            jobs.append([g,prev_end,hs[j][0]]); prev_end=hs[j][0]; i=j+1
        sh=list(shares[a])
        for idx,(g,start,end) in enumerate(jobs):
            nxt=jobs[idx+1][1] if idx+1<len(jobs) else END
            gems=gold=0; cap_r=end
            for s in sh:
                if s[1]==g and end-1<=s[0]<=end+12: gems+=s[2]; gold+=s[3]; cap_r=s[0]; sh.remove(s); break
            k=gk.get(g,'?'); rounds=max(cap_r,end)-start
            out[(k,'rounds')]+=rounds; out[(k,'gems')]+=gems; out[(k,'gold')]+=gold; out[(k,'jobs')]+=1
            out[(typ[a],k,'rounds')]+=rounds; out[(typ[a],k,'gems')]+=gems
    return out
if __name__=='__main__':
    ps=glob.glob(R+'/*/meta.json'); tot=collections.Counter()
    with ProcessPoolExecutor(48) as ex:
        for o in ex.map(one,ps,chunksize=8): tot.update(o)
    T=sum(v for k,v in tot.items() if len(k)==2 and k[1]=='rounds')
    for k in ('gem','gold','mix','Wolf','Elk','Golem','Monolith'):
        r=tot[(k,'rounds')]
        if r: print('%-9s time %.1f%%  jobs/game %.1f  gems/round %.3f gold/round %.2f  rounds/job %.1f'%(k,100*r/T,tot[(k,'jobs')]/len(ps),tot[(k,'gems')]/r,tot[(k,'gold')]/r,r/tot[(k,'jobs')]))
    print('per type gems/round on Elk vs Wolf vs gem:')
    for t in ('Prism','Vesper Vale','Cassi','Issac','Willow','Ryth','Vendetta'):
        print('  %-12s'%t,' '.join('%s %.2f (%.0f%%)'%(k,tot[(t,k,'gems')]/max(1,tot[(t,k,'rounds')]),100*tot[(t,k,'rounds')]/max(1,sum(tot[(t,kk,'rounds')] for kk in ('gem','gold','mix','Wolf','Elk','Golem','Monolith')))) for k in ('gem','Wolf','Elk','Golem')))
