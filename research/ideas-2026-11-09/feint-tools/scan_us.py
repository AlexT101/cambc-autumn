# Our side (oc-base25) in local of-c25 runs: round ends within 1 of an altar with gems, no tribute channel.
import json,gzip,re,sys,collections
from multiprocessing import Pool
sys.path.insert(0,'/home/ubuntu/cambc-autumn/research/ideas-2026-11-09/oppfidelity-tools'); import episodes as E
D='/home/ubuntu/tmp-offload/oppfidelity/ana/'
def scan(job):
    dd,T,opp=job; out=collections.Counter()
    meta=json.load(open(D+dd+'/meta.json')); mp=json.load(open(D+dd+'/'+meta['mapFile'])); alt=[tuple(a) for a in mp['altars']]
    name={c['id']:c['name'] for c in meta['champions']}
    rd=json.load(gzip.open(D+dd+'/rounds.json.gz')); R=rd['round']
    for c in rd['champions']:
        if c['team']!=T: continue
        for i,r in enumerate(R):
            if r>=600: break
            if not c['alive'][i] or not c['gems'][i] or c['x'][i] is None: continue
            x,y=c['x'][i],c['y'][i]
            if min(max(abs(ax-x),abs(ay-y)) for ax,ay in alt)>1: continue
            g=c['gems'][i]; bag='<=10' if g<=10 else '11-20' if g<=20 else '>20'
            dn=E.near(rd,i,T,x,y); b='<=3' if dn<=3 else '4-6' if dn<=6 else '7+'
            ch=c['chan'][i]
            nxt=None
            if i+1<len(R): nxt='stay' if (c['x'][i+1],c['y'][i+1])==(x,y) else 'move'
            out[('all',)] += 1
            out[('chan',ch)] += 1
            if ch!=2: out[('notrib',bag,b,ch,nxt)] += 1; out[('notrib',)] += 1; out[('who',name[c['id']])]+=1
    return opp, out
if __name__=='__main__':
  jobs=[]
  for g in json.load(open(D+'index.json'))['games']:
      m=re.search(r'of-c25-spar-dvn(\d+)-(Fl|Mt3)-ladder/\d+-(.+)-(12|21)\.repl26a$',g['source'])
      if m and int(m.group(1))<=8:
          cls=E.MC.get(m.group(3).replace('-','_')); jobs.append((g['dir'],0 if m.group(4)=='12' else 1,(m.group(2),cls)))
  with Pool(32) as P: res=P.map(scan,jobs,chunksize=8)
  S=collections.defaultdict(collections.Counter); n=collections.Counter()
  for o,c in res: S[o].update(c); n[o]+=1
  for o in sorted(S):
      print(o,n[o],'games; per game:')
      for k,v in sorted(S[o].items(), key=lambda kv:(-kv[1])):
          if v/n[o]>=0.3: print('  ',k,round(v/n[o],2))
  