# Enemy tributes (by defenders' view): seen by some defender (body or ward, at its turn start) during the channel,
# and whether a defender that does not see it could reach it (walk to within 4 of the tributer) before the end.
import json,gzip,collections,sys,os
from multiprocessing import Pool
A=sys.argv[1] if len(sys.argv)>1 else '/home/ubuntu/wt/mx-iapetus/replays/.an-mirror/'
STUN={'Ryth','Prism','Cassi & Issac','Tavi','Ren','Heart of Ruin','Marcella'}
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def game(d):
    out=collections.Counter()
    try:
        m=json.load(open(A+d+'/meta.json')); w=m['result']['winner']
        R=json.load(gzip.open(A+d+'/rounds.json.gz'))
    except Exception: return out
    names={c['id']:c['name'] for c in m['champions']}
    rounds=R['round']; ri={x:i for i,x in enumerate(rounds)}
    ch={int(c['id']):c for c in R['champions']}
    ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    open_={}
    for e in ev:
        if e['k']=='tribute_start':
            open_[e['a']]=e
        elif e['k'] in ('tribute_end','tribute_cancel') and e['a'] in open_:
            s=open_.pop(e['a']); g=s.get('gems',0)
            if g<100: continue
            a=s['a']; t=ch[a]['team']; p=tuple(s['at'])
            i0=ri.get(s['r']); i1=ri.get(e['r'])
            if i0 is None or i1 is None: continue
            done=e['k']=='tribute_end'
            fin=done and e.get('total',0)>=1000
            defs=[o for o,c in ch.items() if c['team']!=t]
            seen_r=None; seers=set()
            for i in range(i0,i1+1):
                for o in defs:
                    if a in ch[o]['sees'][i]:
                        seers.add(o)
                        if seen_r is None: seen_r=i
            key=('W' if t==w else 'L')+('F' if fin else '')
            out[key,'n']+=1; out[key,'done']+=done
            if seen_r is None: out[key,'unseen']+=1; out[key,'unseen_done']+=done; continue
            out[key,'seen']+=1; out[key,'seen_done']+=done
            left=i1-seen_r
            # a non-seer that could reach within 4 (stun) before the end
            reach=False
            for o in defs:
                if o in seers: continue
                c=ch[o]
                if not c['alive'][seen_r] or c['x'][seen_r] is None: continue
                if names.get(o) not in STUN and not (c['cons'][seen_r] and c['cons'][seen_r][1]>0): continue
                if cheb((c['x'][seen_r],c['y'][seen_r]),p)-4<=left-1: reach=True
            if reach: out[key,'seen_reach']+=1; out[key,'seen_reach_done']+=done
            # seen only by wards/far bodies: no seer body within 8
            near=any(cheb((ch[o]['x'][seen_r],ch[o]['y'][seen_r]),p)<=8 for o in seers if ch[o]['alive'][seen_r] and ch[o]['x'][seen_r] is not None)
            if not near: out[key,'seen_far']+=1; out[key,'seen_far_done']+=done
            out[key,'gems_done']+=g*done; out[key,'gems_seen_reach_done']+=g*done*reach
    return out
if __name__=='__main__':
    idx=json.load(open(A+'index.json'))['games']
    dirs=sorted({r['dir'] for r in idx})
    tot=collections.Counter()
    with Pool(32) as p:
        for c in p.imap_unordered(game,dirs): tot.update(c)
    G=len(dirs)
    for k in sorted(tot): print(k, tot[k], '%.2f/game'%(tot[k]/G))
