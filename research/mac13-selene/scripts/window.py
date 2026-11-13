import json, gzip, sys, os
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json'))); mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    G={g['id']:g for g in mp['groups']}
    n=len(R['round']); rix={r:i for i,r in enumerate(R['round'])}
    team={c['id']:c['team'] for c in R['champions']}
    dead=[[0]*n,[0]*n]  # bodies dead per team per round
    for c in R['champions']:
        for i,a in enumerate(c['alive']):
            if not a: dead[c['team']][i]+=1
    # group state per round (delta encoded)
    st={}; avail=[[0.0]*n for _ in range(2)]  # gems of side-s groups in state 1 (alive) per round
    rows=R['groups']; j=0; cur={}
    for i,r in enumerate(R['round']):
        while j<len(rows) and rows[j][0]<=r:
            cur[rows[j][1]]=rows[j][2]; j+=1
        for g,s in cur.items():
            if s==1 and G[g]['side'] in (0,1): avail[G[g]['side']][i]+=G[g]['gems']
    res=Counter(); stc=Counter(x[2] for x in rows)
    for t in (0,1):
        o=1-t
        for i in range(n):
            k=min(3,dead[o][i]); res[(k,'rounds')]+=1; res[(k,'avail_enemyhalf')]+=avail[o][i]; res[(k,'avail_ownhalf')]+=avail[t][i]
            res[(k,'ourdead')]+=dead[t][i]
    for e in ev:
        if e['k']!='capture': continue
        t=e['team']; o=1-t; i=rix.get(e['r']);
        if i is None: continue
        k=min(3,dead[o][i]); sd=G[e['g']]['side']; gems=sum(s[1] for s in e['shares'])
        res[(k,'cap_enemyhalf' if sd==o else 'cap_ownhalf' if sd==t else 'cap_mid')]+=gems
    return res,stc
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    tot=Counter(); stc=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: tot.update(r[0]); stc.update(r[1])
    print('state codes',stc)
    print('k enemy bodies dead | share of team-rounds | our capture gems /100 rounds: own, mid, enemy half | alive gems standing: enemy half, own half | our dead bodies')
    T=sum(tot[(k,'rounds')] for k in range(4))
    for k in range(4):
        r=tot[(k,'rounds')] or 1
        print(k, '%.1f%%'%(100*r/T), *('%.1f'%(100*tot[(k,x)]/r) for x in ('cap_ownhalf','cap_mid','cap_enemyhalf')), *('%.1f'%(tot[(k,x)]/r) for x in ('avail_enemyhalf','avail_ownhalf','ourdead')))
if __name__=='__main__': main()
