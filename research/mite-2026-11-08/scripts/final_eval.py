"""Score mite_prio.priority on every Mite turn of allturns.pkl (target: the written value, else the kept one)."""
import pickle,collections
from mite_prio import priority,cheb
games=pickle.load(open('allturns.pkl','rb'))
T=lambda e:dict(id=e[0],name=e[1],x=e[2],y=e[3],hp=e[4],maxHp=e[5],gems=e[6])
def mode(v):
    if v==1050: return 'dead'
    if v==18965: return 'channel'
    if v==0: return 'alert0'
    if 1000<=v<=1049: return 'quiet'
    if 90<=v%1000<=99 or 6000<v<12000: return 'contact'
    return 'other'
res=collections.defaultdict(collections.Counter)
for g in games:
    part=g['g'][:1]  # hash prefix: a coarse split for a stability check
    split='hex0-7' if part in '01234567' else 'hex8-f'
    prev={}
    for t in g['turns']:
        if t['e_me'] is None: continue
        w='v' in t
        me=t['w_me'] if w else t['e_me']; al=[T(a) for a in (t['w_al'] if w else t['e_al'])]
        sm=t['s_me']; S=[T(e) for e in t['s_en']]
        for e in S: e['d_start']=cheb(e,sm) if sm['x'] is not None else 99
        target=t['v'] if w else t['e_me']['priority']
        k=t['id']; r=t['round']
        if me['alive'] and me['x'] is None: p=q=target
        else:
            p=priority(t['name'],me,S,prev.get(k)==r-1,al); q=priority(t['name'],me,S,prev.get(k)==r-1,al,with_offset=False)
        tb= target%1000 if (90<=target%1000<=99 and 1000<target<12000) else target
        for s in (split,'all'):
            res[s]['n']+=1; res[s]['exact']+= p==target; res[s]['base']+= q==tb
            res[s+':'+mode(target)]['n']+=1; res[s+':'+mode(target)]['exact']+= p==target
        if sm['x'] is not None and any(e['d_start']<=8 for e in S): prev[k]=r
for s in sorted(res):
    c=res[s]; print(f"{s:16} n={c['n']:8} exact {c['exact']/c['n']:.4f}"+(f"  ignoring contact offsets {c['base']/c['n']:.4f}" if 'base' in c else ''))
