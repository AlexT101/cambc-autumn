import json,gzip,glob,sys,collections,statistics as st
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def one(d):
    M=json.load(open(d+'/meta.json')); w=M['result']['winner']
    names={c['id']:c['name'] for c in M['champions']}; team={c['id']:c['team'] for c in M['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}; C={c['id']:c for c in R['champions']}
    out=collections.Counter()
    # potential round per team
    pot={}
    for i,r in enumerate(R['round']):
        for t in (0,1):
            if t in pot: continue
            if R['gems'][t][i]+sum(c['gems'][i] for c in R['champions'] if c['team']==t and c['alive'][i])>=1000: pot[t]=r
    starts=collections.defaultdict(list); ends=collections.defaultdict(list)
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='tribute_start': starts[team[e['a']]].append((e['r'],e['gems'],e['a']))
        if e['k']=='tribute_end': ends[team[e['a']]].append((e['r'],e['gems']))
    for t in pot:
        big=[s for s in starts[t] if s[0]>=pot[t]-5 and s[1]>=150]
        out['teams']+=1
        out['big_starts_after_pot']+=len(big)
        out['won']+= (w==t)
        if big:
            out['first_big_delay']+=big[0][0]-pot[t]; out['nbig']+=1
    return out
def main():
    agg=collections.Counter()
    for o in ProcessPoolExecutor(32).map(one,[x[:-10] for x in glob.glob(A+'/*/meta.json')]): agg.update(o)
    print(dict(agg)); print('mean big tribute attempts after potential %.2f; delay to first %.1f'%(agg['big_starts_after_pot']/agg['teams'],agg['first_big_delay']/max(1,agg['nbig'])))
if __name__=='__main__': main()
