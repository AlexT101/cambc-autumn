import json,gzip,glob,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    M=json.load(open(d+'/meta.json'))
    w=M['result']['winner']
    names={c['id']:c['name'] for c in M['champions']}
    team={c['id']:c['team'] for c in M['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz'))
    ri={r:i for i,r in enumerate(R['round'])}
    ch={c['id']:c for c in R['champions']}
    out=[]
    first=None
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='death': continue
        v=e['v']; 
        if names.get(v)!='Prism': continue
        r=e['r']; i=ri.get(r)
        if i is None: continue
        vt=team[v]; at=e['at']
        def near(t,rad):
            n=0
            for c in R['champions']:
                if c['team']!=t or c['id']==v: continue
                if not c['alive'][i]: continue
                if cheb((c['x'][i],c['y'][i]),at)<=rad: n+=1
            return n
        efoc=[ch[c]['foc'][i] for c in ch if team[c]!=vt and names[c]=='Prism' and ch[c]['alive'][i]]
        row=dict(r=r,gems=e['gems'],killer=names.get(e.get('by'),'camp'),
                 vfoc=ch[v]['foc'][max(0,i-1)], efoc=max(efoc) if efoc else 0,
                 allies4=near(vt,4),allies8=near(vt,8),en4=near(1-vt,4),en8=near(1-vt,8),
                 lost=(w!=vt), first=(first is None))
        if first is None: first=vt
        out.append(row)
    return out
def main():
  dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
  rows=[]
  with ProcessPoolExecutor(32) as ex:
      for o in ex.map(one,dirs): rows+=o
  print(len(rows),'prism deaths in',len(dirs),'games')
  import statistics as st
  c=collections.Counter(r['killer'] for r in rows); print('killers',c.most_common())
  f=[r for r in rows if r['first']]
  print('first prism death: victim team lost %.1f%% of %d'%(100*sum(r['lost'] for r in f)/len(f),len(f)))
  for key in ['allies4','allies8','en4','en8']:
      print(key, collections.Counter(r[key] for r in rows).most_common())
  print('median bag',st.median(r['gems'] for r in rows),'mean',st.mean(r['gems'] for r in rows))
  rat=[r['vfoc']/r['efoc'] for r in rows if r['efoc']>0]
  bins=collections.Counter(('<0.5' if x<0.5 else '<0.8' if x<0.8 else '<1.25' if x<1.25 else '<2' if x<2 else '>2') for x in rat); print('victim/enemy focus ratio',bins)
  byr=collections.Counter((r['r']//200)*200 for r in rows); print('by round',sorted(byr.items()))
  # allies near vs enemies near
  cc=collections.Counter((min(r['allies8'],3),min(r['en8'],4)) for r in rows); print('allies8,en8',sorted(cc.items()))

if __name__=='__main__': main()