import collections,gzip,json,os,sys
from pathlib import Path
from multiprocessing import Pool
sys.path.insert(0,'/home/ubuntu/cambc-autumn/tools/replay/narrative');from vision import Vision
H=Path('/home/ubuntu/tmp-offload/warding-2026-11-10')
from audit import clusters

def run(job):
 p=Path(job['path']);m=json.loads((p/'meta.json').read_text());mp=json.loads((p/m['mapFile']).resolve().read_text());side=job['side'];cs={c['id']:c for c in m['champions']}
 W,HH=mp['width'],mp['height'];vision=Vision(W,HH,{tuple(t) for t in mp['walls']},clusters({tuple(t) for t in mp['bushes']}));sp=mp['spawn'][0];tiles=[(x,y) for y in range(sp['minY'],sp['maxY']+1) for x in range(sp['minX'],sp['maxX']+1)]
 def mirror(t):
  x,y=t;s=mp['symmetry'];return (W-1-x,y) if s=='horizontal' else (x,HH-1-y) if s=='vertical' else (W-1-x,HH-1-y)
 positions={}
 for team in (0,1):
  for i,c in enumerate(sorted([c for c in cs.values() if c['team']==team],key=lambda c:c['id'])):positions[c['id']]=tiles[i] if team==0 else mirror(tiles[i])
 with gzip.open(p/'events.jsonl.gz','rt') as f:ev=[json.loads(line) for line in f]
 turns=collections.defaultdict(list);wards={};cnt=collections.Counter();records=[]
 for i,e in enumerate(ev):
  if e.get('a') in cs and cs[e['a']]['team']==side:turns[(e['r'],e['a'])].append((i,e))
 for i,e in enumerate(ev):
  kind=e['k'];cid=e.get('a');r=e['r']
  if cid is not None and e.get('f') and kind!='teleport_start':positions[cid]=tuple(e['f'])
  if cid in cs and cs[cid]['team']==side:
   if kind=='ward':
    before=[x['k'] for j,x in turns[(r,cid)] if j<i];after=[x['k'] for j,x in turns[(r,cid)] if j>i]
    row=dict(r=r,cid=cid,to=e['to'],before=before,after=after,same_turn_hits=0,later_hits=0)
    records.append(row);wards[cid]=row;cnt['wards']+=1
    for key,seq in [('before',before),('after',after)]:
     for action in ['move','attack','cast']:cnt[key+'_'+action]+=action in seq
    cnt['no_action_before']+=not any(k in before for k in ['move','attack','cast'])
   elif kind=='attack' and e.get('tgt') in cs and cs[e['tgt']]['team']!=side and cid in wards:
    row=wards[cid];target=tuple(e['to'])
    if target not in vision.fov(positions[cid]) and target in vision.fov(tuple(row['to']),6):
     when='same_turn_hits' if row['r']==r else 'later_hits';row[when]+=1;cnt[when]+=1
  if kind=='move':positions[cid]=tuple(e['to'])
  elif kind=='cast' and e.get('moved'):positions[cid]=tuple(e['moved'])
  elif kind in ('recall_end','teleport_end'):positions[cid]=tuple(e['to'])
  elif kind=='respawn':positions[cid]=tuple(e['at'])
 cnt['wards_same_turn_hit']=sum(row['same_turn_hits']>0 for row in records)
 return dict(job=job,counts=dict(cnt),wards=records)
if __name__=='__main__':
 with Pool(int(os.environ.get('OMP_NUM_THREADS','2'))) as pool:out=list(pool.imap(run,json.loads((H/'jobs.json').read_text())))
 (H/'timing.json').write_text(json.dumps(out))
 for co in ['Mite-r5','Ad-Astra','Ocean-v105']:
  c=collections.Counter()
  for x in out:
   if x['job']['cohort']==co:c.update(x['counts'])
  print(co,dict(c),flush=True)
