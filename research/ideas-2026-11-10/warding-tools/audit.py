import collections,gzip,json,os,sys
from pathlib import Path
from multiprocessing import Pool
sys.path.insert(0,'/home/ubuntu/cambc-autumn/tools/replay/narrative');from vision import Vision
H=Path('/home/ubuntu/tmp-offload/warding-2026-11-10')
def dist(a,b):return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def clusters(tiles):
 bc={};unseen=set(tiles);n=0
 while unseen:
  first=unseen.pop();stack=[first];bc[first]=n
  while stack:
   x,y=stack.pop()
   for t in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    if t in unseen:unseen.remove(t);bc[t]=n;stack.append(t)
  n+=1
 return bc

def audit(job):
 p=Path(job['path']);meta=json.loads((p/'meta.json').read_text());mp=json.loads((p/meta['mapFile']).resolve().read_text());rd=json.load(gzip.open(p/'rounds.json.gz','rt'));side=job['side'];cs={c['id']:c for c in meta['champions']}
 W,HH=mp['width'],mp['height'];walls={tuple(t) for t in mp['walls']};holes={tuple(t) for t in mp['holes']};bushes={tuple(t) for t in mp['bushes']};bc=clusters(bushes);altars={tuple(t) for t in mp['altars']};camps={(c['x'],c['y']) for c in mp['camps']};vision=Vision(W,HH,walls,bc)
 a=mp['spawn'][0];tiles=[(x,y) for y in range(a['minY'],a['maxY']+1) for x in range(a['minX'],a['maxX']+1)]
 def mirror(t):
  x,y=t;s=mp['symmetry'];return (W-1-x,y) if s=='horizontal' else (x,HH-1-y) if s=='vertical' else (W-1-x,HH-1-y)
 positions={};alive={cid:True for cid in cs}
 for team in (0,1):
  for i,c in enumerate(sorted([c for c in cs.values() if c['team']==team],key=lambda c:c['id'])):positions[c['id']]=tiles[i] if team==0 else mirror(tiles[i])
 sp=mp['spawn'][1-side];enemyspawn={(x,y) for y in range(sp['minY'],sp['maxY']+1) for x in range(sp['minX'],sp['maxX']+1)}
 wards={};records=[];cnt=collections.Counter();last_turn={}
 for c in rd['champions']:
  if c['team']==side:
   cnt['alive_rounds']+=sum(c['alive']);cnt['ready_rounds']+=sum(bool(a) and bool(w and w[0]) for a,w in zip(c['alive'],c['ward']))
 def legal(t):return 0<=t[0]<W and 0<=t[1]<HH and t not in walls and t not in holes and t not in altars and t not in enemyspawn
 with gzip.open(p/'events.jsonl.gz','rt') as f:
  for line in f:
   e=json.loads(line);kind=e['k'];cid=e.get('a');r=e['r']
   if cid is not None and e.get('f') and kind != 'teleport_start':
    if tuple(e['f'])!=positions[cid]:cnt['position_corrections']+=1
    positions[cid]=tuple(e['f'])
   if cid is not None and cs[cid]['team']==side:
    pos=positions[cid];old=wards.get(cid)
    if kind=='ward':
     tile=tuple(e['to']);cnt['wards']+=1;cnt['ward_range_invalid']+=dist(pos,tile)>2
     own=vision.fov(pos);previous=vision.fov(old['to'],6) if old else frozenset();view=vision.fov(tile,6);new=view-own-previous
     foes=[positions[q] for q,c in cs.items() if c['team']!=side and alive[q]]
     seen=[q for q in foes if q in own or q in previous]
     bestb=bestall=-1;nbestb=[];nbestall=[]
     for x in range(pos[0]-2,pos[0]+3):
      for y in range(pos[1]-2,pos[1]+3):
       t=(x,y)
       if not legal(t):continue
       gain=vision.fov(t,6)-own-previous;b=len(gain&bushes);alln=len(gain)
       if b>bestb:bestb=b;nbestb=[t]
       elif b==bestb:nbestb.append(t)
       if alln>bestall:bestall=alln;nbestall=[t]
       elif alln==bestall:nbestall.append(t)
     row=dict(r=r,cid=cid,type=cs[cid]['name'],origin=pos,to=tile,bush=tile in bushes,camp=tile in camps,new_tiles=len(new),new_bush=len(new&bushes),new_camps=len(new&camps),old_dist=dist(pos,old['to']) if old else None,gap=r-old['r'] if old else None,enemy_seen=len(seen),contact=any(dist(pos,q)<=4 for q in seen),new_enemies=sum(q in new for q in foes),best_bush=tile in nbestb,best_all=tile in nbestall,used_hits=0,best_bush_gain=bestb)
     records.append(row);wards[cid]=row
    elif kind=='attack' and e.get('tgt') in cs and cs[e['tgt']]['team']!=side:
     cnt['champion_attacks']+=1;target=tuple(e['to']);own=vision.fov(pos)
     if target not in own:
      cnt['ward_only_attacks']+=1
      if old and target in vision.fov(old['to'],6):old['used_hits']+=1
      else:cnt['unexplained_attacks']+=1
   if kind=='move':positions[cid]=tuple(e['to'])
   elif kind=='cast' and e.get('moved'):positions[cid]=tuple(e['moved'])
   elif kind in ('recall_end','teleport_end'):positions[cid]=tuple(e['to'])
   elif kind=='respawn':positions[cid]=tuple(e['at']);alive[cid]=True
   elif kind=='death':alive[e['v']]=False
 return dict(job=job,counts=dict(cnt),wards=records,validation=meta['validation']['ok'])

if __name__=='__main__':
 jobs=json.loads((H/'jobs.json').read_text())
 with Pool(int(os.environ.get('OMP_NUM_THREADS','4'))) as p:
  out=[]
  for i,x in enumerate(p.imap(audit,jobs,chunksize=1),1):
   out.append(x)
   if i%10==0:print('done',i,'/',len(jobs),flush=True)
 (H/'audit.json').write_text(json.dumps(out));print('finished')
