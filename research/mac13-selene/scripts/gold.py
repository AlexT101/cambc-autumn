import json,gzip,sys,os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json'))); R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    win=meta['result']['winner']; n=len(R['round']); rows=[]
    for c in R['champions']:
        g=c['gold']; e=c['earned']
        # time-weighted unspent gold, rounds holding >=30 gold (a shard affordable), >=150
        avg=sum(g)/n; h30=sum(1 for x in g if x>=30)/n; h150=sum(1 for x in g if x>=150)/n
        spent=e[-1]-g[-1]
        # gold at r300
        i3=min(299,n-1)
        rows.append((names[c['id']], int(team[c['id']]==win), avg, h30, h150, e[-1], spent, g[i3], e[i3]))
    return rows
def main():
  dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x))]
  rows=[]
  with ProcessPoolExecutor(32) as ex:
      for r in ex.map(game,dirs,chunksize=8):
          if r: rows+=r
  by=defaultdict(list)
  for r in rows: by[(r[0],r[1])].append(r)
  print('name win n avgUnspent frac>=30 frac>=150 earned spent gold@300 earned@300')
  for k in sorted(by):
      v=by[k]; m=lambda i: sum(x[i] for x in v)/len(v)
      print(k[0][:10],k[1],len(v),*('%.1f'%m(i) for i in (2,)),*('%.2f'%m(i) for i in (3,4)),*('%.0f'%m(i) for i in (5,6,7,8)))
  
if __name__=='__main__': main()