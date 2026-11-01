import sys; sys.path.insert(0,sys.argv[1])
from tlib import *
from concurrent.futures import ProcessPoolExecutor
D=json.load(open(sys.argv[1]+'/deaths_tr_distinct.json'))
byk=defaultdict(list)
for x in D: byk[x['key']].append(x)
RANGED={'vesper','prism','cassi','willow','tavi','stellar'}
def one(key):
    T,TV=load(key); out=[]
    rev={}
    for (r,c),L in T.items():
        if L['TT']: rev.setdefault(c,{})[r]=L
    vic_by_name={TV[c]['t']:c for c in TV}
    for x in byk[key]:
        # find victim id: match the last TT round r0 with type
        cands=[c for c in rev if x['r0'] in rev[c] and float(rev[c][x['r0']]['TT'][0].get('hp',-1))==x['hp']]
        if not cands: continue
        c=cands[0]; R=rev[c]
        rs=sorted(r for r in R if r<=x['r0'])
        seq=[]
        for r in reversed(rs[-40:]):
            tt=R[r]['TT'][0]
            if tt.get('a')!='1': break
            hp=float(tt['hp']); mh=float(tt['mh'])
            home=[h for h in R[r]['TE'] if h.get('k')=='home']
            seq.append((r,tt.get('d'),hp,mh,float(tt.get('hq',hp)),float(tt.get('dmg') or 0),(home[-1].get('v'),home[-1].get('why')) if home else None,tt.get('fs'),tt.get('ls'),tt.get('p'),tt.get('q')))
            if hp>=0.8*mh: break
        seq.reverse()
        out.append(dict(x,seq=seq,type=TV[c]['t']))
    return out
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=[y for o in ex.map(one,list(byk)) for y in o]
    json.dump(res,open(sys.argv[1]+'/episodes.json','w'))
    # attribute damage taken (dmg of next turn) to the branch of the turn before
    agg=Counter(); first_branch=Counter(); start_home=Counter(); lens=[]
    for e in res:
        s=e['seq']
        if not s: continue
        lens.append(len(s))
        first_branch[s[0][1]]+=1
        start_home[s[0][6]]+=1
        for i in range(len(s)-1):
            agg[s[i][1]]+=s[i+1][5]
        agg[s[-1][1]]+=e['window_dmg']
    tot=sum(agg.values())
    print('episodes',len(res),'median len',sorted(lens)[len(lens)//2])
    print('damage taken after turns of branch (share):',[(k,'%.2f'%(v/tot)) for k,v in agg.most_common(8)])
    print('branch at the last >=80% turn:',first_branch.most_common(8))
    print('home answer at that turn:',start_home.most_common(10))
