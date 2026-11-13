"""Tribute starts per type: count a game, gems, rounds since the champion's last camp hit (the trip), completion."""
import json,gzip,glob,os,sys,collections,statistics as st
from concurrent.futures import ProcessPoolExecutor
R=sys.argv[1]; CH=json.load(open(R+'/enums.json'))['champions']
def one(p):
    d=os.path.dirname(p); m=json.load(open(p)); typ={c['id']:CH[c['type']] for c in m['champions']}
    last=collections.defaultdict(int); out=[]; pend={}
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l); k=e['k']
        if k in('attack','cast') and e.get('cdmg'): last[e['a']]=e['r']
        elif k=='tribute_start': pend[e['a']]=(e['r'],e['gems'],e['r']-last[e['a']])
        elif k=='tribute_end' and e['a'] in pend:
            r,g,trip=pend.pop(e['a']); out.append((typ[e['a']],g,trip,True,e['r']-r))
        elif k=='tribute_cancel' and e['a'] in pend:
            r,g,trip=pend.pop(e['a']); out.append((typ[e['a']],g,trip,False,e['r']-r))
    return out
if __name__=='__main__':
    ps=glob.glob(R+'/*/meta.json')
    with ProcessPoolExecutor(48) as ex: S=[x for o in ex.map(one,ps,chunksize=8) for x in o]
    tab=collections.defaultdict(list)
    for s in S: tab[s[0]].append(s)
    for t,xs in sorted(tab.items(),key=lambda kv:-len(kv[1])):
        done=[x for x in xs if x[3]]
        print('%-13s starts/game %.2f done %.0f%% gems(done) %.0f trip median %d'%(t,len(xs)/len(ps),100*len(done)/len(xs),st.mean(x[1] for x in done) if done else 0,st.median(x[2] for x in xs)))
