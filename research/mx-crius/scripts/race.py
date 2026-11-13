"""Endgame race in lost games: first round the loser could win with one tribute (tributed + one champion's bag >= 1000),
or with its whole team's bags; how long before the loss; did that carrier start a tribute after, why it failed."""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
CH=json.load(open(A+'/enums.json'))['champions']
def one(d):
    m=json.load(open(d+'/meta.json')); w=m['result']['winner']; L=1-w; end=m['result']['rounds']
    typ={c['id']:CH[c['type']] for c in m['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); rr=R['round']
    one_r=None; who=None; team_r=None; bag=None
    for i,r in enumerate(rr):
        T=R['gems'][L][i]
        bags=[(c['gems'][i] or 0,c['id']) for c in R['champions'] if c['team']==L]
        if team_r is None and T+sum(b for b,_ in bags)>=1000: team_r=r
        b,cid=max(bags)
        if one_r is None and T+b>=1000: one_r=r; who=cid; bag=b; Tat=T
    if one_r is None: return ('none',team_r is not None,end-(team_r or end))
    # tribute starts by who after one_r
    starts=0; ends=0; cancels=0; died=False; startr=None
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['r']<one_r: continue
        if e['k']=='tribute_start' and e.get('a',e.get('c'))==who: starts+=1; startr=startr or e['r']
        if e['k']=='tribute_cancel' and e.get('a',e.get('c'))==who: cancels+=1
        if e['k']=='death' and e['v']==who: died=True
    return ('one',typ[who],end-one_r,bag,starts,cancels,died,startr and startr-one_r, 1000-Tat)
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(A+'/*/meta.json')]
    with ProcessPoolExecutor(48) as ex: S=list(ex.map(one,ds,chunksize=8))
    n=len(S); print('games',n)
    O=[s for s in S if s[0]=='one']; print('loser could win with one tribute at some point: %d (%.1f%%)'%(len(O),100*len(O)/n))
    print('  carrier types',collections.Counter(s[1] for s in O).most_common())
    import statistics as st
    print('  rounds from then to loss: quartiles',sorted(s[2] for s in O)[len(O)//4],sorted(s[2] for s in O)[len(O)//2],sorted(s[2] for s in O)[3*len(O)//4])
    print('  bag quartiles',sorted(s[3] for s in O)[len(O)//4],sorted(s[3] for s in O)[len(O)//2],sorted(s[3] for s in O)[3*len(O)//4])
    print('  needed (1000-T) quartiles',sorted(s[8] for s in O)[len(O)//4],sorted(s[8] for s in O)[len(O)//2],sorted(s[8] for s in O)[3*len(O)//4])
    print('  started a tribute after: %.1f%%, of those delay quartiles %s'%(100*sum(1 for s in O if s[4])/len(O), sorted(s[7] for s in O if s[7] is not None)[::max(1,sum(1 for s in O if s[7] is not None)//4)][:5]))
    print('  carrier died after: %.1f%%, cancelled: %.1f%%'%(100*sum(s[6] for s in O)/len(O),100*sum(1 for s in O if s[5])/len(O)))
    Z=[s for s in S if s[0]=='none']; print('team-total only (no single carrier):',sum(1 for s in Z if s[1]))
