"""Per group kind and side (relative to team that 'owns' side): share of rounds the group is up and asleep at full
hp (available, unworked), and captures per 100 rounds by each team, gems/capture. Rounds 1..min(600,end)."""
import json, gzip, glob, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; END=600
def kind(G,camps):
    ts=[camps[c]['type'] for c in G['camps']]
    for k in ('Monolith','Golem','Elk','Wolf'):
        if k in ts: return k
    return 'gem' if all(t=='Gem cluster' for t in ts) else 'gold' if all(t=='Gold cluster' for t in ts) else 'cluster-mix'
def one(d):
    meta=json.load(open(d+'/meta.json'))
    mp=json.load(open(os.path.join(d,meta['mapFile']))); camps={c['id']:c for c in mp['camps']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); rounds=R['round']; n=min(len(rounds),END)
    full={}
    for G in mp['groups']: full[G['id']]=sum(camps[c]['hp'] for c in G['camps'])
    rows=collections.defaultdict(list)
    for row in R['groups']: rows[row[1]].append(row)
    out=collections.Counter()
    for G in mp['groups']:
        k=kind(G,camps); side=G['side']
        rs=rows[G['id']]; j=0; cur=None; avail=0
        for i in range(n):
            r=rounds[i]
            while j<len(rs) and rs[j][0]<=r: cur=rs[j]; j+=1
            if cur and cur[2]==1 and cur[6]==0 and cur[7]>=full[G['id']]-1: avail+=1
        lab='mid' if side==-1 else 'side'
        out[(k,lab,'avail')]+=avail; out[(k,lab,'rounds')]+=n; out[(k,lab,'groups')]+=1; out[(k,lab,'gems')]+=G['gems']
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['r']>END: break
        if e['k']=='capture':
            G=next((g for g in mp['groups'] if g['id']==e['g']),None)
            if G: out[(kind(G,camps),'mid' if G['side']==-1 else 'side','caps')]+=1
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    tot=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one,ds,chunksize=8): tot.update(o)
    N=len(ds)
    for k in sorted(set((a,b) for a,b,c in tot)):
        g=tot[k+('groups',)]
        print('%-12s %-4s groups/game %5.1f gems/group %5.1f avail %4.0f%%  caps/group/100r %.2f'%(k[0],k[1],g/N,tot[k+('gems',)]/g,100*tot[k+('avail',)]/tot[k+('rounds',)],100*tot[k+('caps',)]/tot[k+('rounds',)]))
