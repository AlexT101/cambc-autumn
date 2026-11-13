import json, gzip, sys, os
from collections import defaultdict, deque
from concurrent.futures import ProcessPoolExecutor
ROOT = sys.argv[1]
def bfs(mp, srcs):
    W,H = mp['width'], mp['height']
    block = set(map(tuple, mp['walls'])) | set(map(tuple, mp['holes'])) | set(map(tuple, mp['altars']))
    INF=10**9; D=[[INF]*H for _ in range(W)]
    q=deque()
    for s in srcs: D[s[0]][s[1]]=0; q.append(s)
    while q:
        x,y=q.popleft()
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                nx,ny=x+dx,y+dy
                if 0<=nx<W and 0<=ny<H and (nx,ny) not in block and D[nx][ny]==INF:
                    D[nx][ny]=D[x][y]+1; q.append((nx,ny))
    return D
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        mp=json.load(open(os.path.join(d,meta['mapFile'])))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception as e:
        return None
    sp=mp['spawn']
    srcs=[[(x,y) for x in range(s['minX'],s['maxX']+1) for y in range(s['minY'],s['maxY']+1)] for s in sp]
    DA=bfs(mp,srcs[0]); DB=bfs(mp,srcs[1])
    side={}
    for g in mp['groups']:
        a=min(DA[t[0]][t[1]] for t in g['tiles']); b=min(DB[t[0]][t[1]] for t in g['tiles'])
        side[g['id']] = a/(a+b) if a+b>0 and a<10**8 and b<10**8 else 0.5  # share toward B: 0 = at A
    win=meta['result']['winner']; rounds=meta['result']['rounds']
    team_of={c['id']:c['team'] for c in meta['champions']}
    out=[]
    cap=defaultdict(float)
    for e in ev:
        if e['k']=='capture':
            t=e['team']; s=side[e['g']]; s = s if t==0 else 1-s  # share toward enemy
            z='own' if s<0.4 else ('mid' if s<=0.6 else 'enemy')
            gems=sum(x[1] for x in e['shares']); gold=sum(x[2] for x in e['shares'])
            w = 'early' if e['r']<=150 else ('midg' if e['r']<=400 else 'late')
            cap[(t,z,w,'gems')]+=gems; cap[(t,z,w,'n')]+=1; cap[(t,z,'all','gems')]+=gems
        if e['k']=='death' and 'by' in e and e.get('by') is not None:
            pass
    for t in (0,1):
        row={'win':int(win==t),'rounds':rounds}
        for z in ('own','mid','enemy'):
            for w in ('early','midg','late','all'):
                row[f'{z}_{w}']=cap[(t,z,w,'gems')]
        # mid supply: total gems of mid groups
        row['n_mid_groups']=sum(1 for g in mp['groups'] if 0.4<=side[g['id']]<=0.6)
        row['n_groups']=len(mp['groups'])
        for z in ('own','mid','enemy'):
            sup=0
            for g in mp['groups']:
                sg=side[g['id']]; sg = sg if t==0 else 1-sg
                zz='own' if sg<0.4 else ('mid' if sg<=0.6 else 'enemy')
                if zz==z: sup+=g['gems']*(1+rounds//(g['respawn']+8))
            row['sup_'+z]=sup
        out.append(row)
    return out
def main():
  dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
  rows=[]
  with ProcessPoolExecutor(24) as ex:
    for r in ex.map(game, dirs, chunksize=8):
        if r: rows+=r
  import statistics as st
  W=[r for r in rows if r['win']]; L=[r for r in rows if not r['win']]
  print('team-games',len(rows))
  for k in [k for k in rows[0] if k not in ('win',)]:
    print(f"{k:14s} win {st.mean(r[k] for r in W):8.1f}  lose {st.mean(r[k] for r in L):8.1f}")

if __name__=='__main__': main()