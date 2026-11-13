"""What happens in the rounds just after the loser's last level round: source deltas over [swing, swing+W],
the biggest bag lost, the victim, and the local numbers (allies/enemies within 8 of the victim the round before)."""
import json, gzip, glob, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; W=int(sys.argv[2]) if len(sys.argv)>2 else 25
CH=json.load(open(ROOT+'/enums.json'))['champions']
IDX={g['dir']:g for g in json.load(open(ROOT+'/index.json'))['games']}
def one(d):
    meta=json.load(open(d+'/meta.json')); w=meta['result']['winner']; L=1-w
    team={c['id']:c['team'] for c in meta['champions']}; typ={c['id']:CH[c['type']] for c in meta['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); rounds=R['round']; n=len(rounds)
    val=[[R['gems'][t][i] for i in range(n)] for t in (0,1)]
    cidx={c['id']:j for j,c in enumerate(R['champions'])}
    for c in R['champions']:
        for i in range(n): val[c['team']][i]+=c['gems'][i] or 0
    gap=[val[L][i]-val[w][i] for i in range(n)]
    sw=0
    for i in range(n):
        if gap[i]>=0: sw=i
    sr=rounds[sw]
    d_cap=0; d_kill=0; d_camp=0; big=None; ldeaths=0; wdeaths=0
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l); r=e['r']
        if r<=sr: continue
        if r>sr+W: break
        if e['k']=='capture':
            for cid,gm,gd in e['shares']: d_cap+= gm if team[cid]==L else -gm
        elif e['k']=='death':
            v=e['v']; tv=team[v]; g=e.get('gems',0)
            if tv==L: ldeaths+=1
            else: wdeaths+=1
            if e.get('by') is not None:
                d_kill+= -2*g if tv==L else 2*g
            else:
                d_camp+= -g if tv==L else g
            if tv==L and (big is None or g>big[1]):
                # local count the round before
                i=max(0,rounds.index(r)-1) if r in rounds else 0
                cv=R['champions'][cidx[v]]; vx,vy=cv['x'][i],cv['y'][i]
                al=en=0
                if vx is not None:
                    for c in R['champions']:
                        if c['id']==v or not c['alive'][i] or c['x'][i] is None: continue
                        if max(abs(c['x'][i]-vx),abs(c['y'][i]-vy))<=8:
                            if c['team']==L: al+=1
                            else: en+=1
                big=(typ[v],g,al,en,'camp' if e.get('by') is None else typ.get(e['by'],'?'))
    return dict(sr=sr,gap_after=gap[min(n-1,sw+W)] if n else 0,d_cap=d_cap,d_kill=d_kill,d_camp=d_camp,big=big,ld=ldeaths,wd=wdeaths,rounds=meta['result']['rounds'])
if __name__=='__main__':
  ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
  with ProcessPoolExecutor(32) as ex: S=list(ex.map(one,ds,chunksize=8))
  N=len(S); print('games',N,'window',W)
  print('gap after window mean %.0f, d_cap %.1f d_kill %.1f d_camp %.1f; loser deaths %.2f winner deaths %.2f'%(st.mean(s['gap_after'] for s in S),st.mean(s['d_cap'] for s in S),st.mean(s['d_kill'] for s in S),st.mean(s['d_camp'] for s in S),st.mean(s['ld'] for s in S),st.mean(s['wd'] for s in S)))
  c=collections.Counter()
  for s in S:
      if s['ld']==0: c['no loser death in window']+=1
      else: c['loser death, biggest %s'%('Prism' if s['big'][0]=='Prism' else 'other')]+=1
  for k,v in c.most_common(): print('  %-40s %d %.1f%%'%(k,v,100*v/N))
  dd=[s for s in S if s['big']]
  print('biggest-victim outnumbered (en>al+1):',sum(1 for s in dd if s['big'][3]>s['big'][2]+1)/len(dd), 'allies within 8 = 0:',sum(1 for s in dd if s['big'][2]==0)/len(dd))
  print('killer types',collections.Counter(s['big'][4] for s in dd).most_common(6))
  print('victim types',collections.Counter(s['big'][0] for s in dd).most_common(8))
  nod=[s for s in S if s['ld']==0]
  print('no-death swings: d_cap %.1f, d_kill %.1f, sr median %d'%(st.mean(s['d_cap'] for s in nod),st.mean(s['d_kill'] for s in nod),sorted(s['sr'] for s in nod)[len(nod)//2]))
