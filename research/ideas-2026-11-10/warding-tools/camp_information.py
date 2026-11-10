"""Potential first-hand camp-state information supplied only by the owner's ward, not team-shared knowledge."""
import collections,gzip,json,os,sys
from pathlib import Path
from multiprocessing import Pool
sys.path.insert(0,'/home/ubuntu/cambc-autumn/tools/replay/narrative');from vision import Vision
H=Path('/home/ubuntu/tmp-offload/warding-2026-11-10')
from audit import clusters

def run(job):
 p=Path(job['path']);m=json.loads((p/'meta.json').read_text());mp=json.loads((p/m['mapFile']).resolve().read_text());cs={c['id']:c for c in m['champions']};own={cid for cid,c in cs.items() if c['team']==job['side']};bush={tuple(t) for t in mp['bushes']};camps={(c['x'],c['y']):c['group'] for c in mp['camps']};gtiles={g['id']:{tuple(t) for t in g['tiles']} for g in mp['groups']};V=Vision(mp['width'],mp['height'],{tuple(t) for t in mp['walls']},clusters(bush));cache={}
 def view(pos,r):
  key=(pos,r)
  if key not in cache:cache[key]=V.fov(pos,r)
  return cache[key]
 sp=mp['spawn'][0];tiles=[(x,y) for y in range(sp['minY'],sp['maxY']+1) for x in range(sp['minX'],sp['maxX']+1)]
 def mirror(t):
  x,y=t;W=mp['width'];HH=mp['height'];s=mp['symmetry'];return (W-1-x,y) if s=='horizontal' else (x,HH-1-y) if s=='vertical' else (W-1-x,HH-1-y)
 positions={};alive={cid:True for cid in cs}
 for team in (0,1):
  for i,c in enumerate(sorted([c for c in cs.values() if c['team']==team],key=lambda c:c['id'])):positions[c['id']]=tiles[i] if team==0 else mirror(tiles[i])
 wards={};records=[];counts=collections.Counter()
 with gzip.open(p/'events.jsonl.gz','rt') as f:
  for line in f:
   e=json.loads(line);kind=e['k'];cid=e.get('a')
   if cid is not None and e.get('f') and kind!='teleport_start':positions[cid]=tuple(e['f'])
   if kind=='ward' and cid in own:
    pos=tuple(e['to']);vs=view(pos,6);gs={camps[t] for t in vs if t in camps};rec=dict(cid=cid,r=e['r'],to=e['to'],bush=pos in bush,camp=pos in camps,events=[],seen_groups=len(gs));records.append(rec);wards[cid]=(rec,gs)
   elif kind in ('group_clear','capture','group_respawn'):
    g=e['g'];counts['transitions']+=1
    for owner,(rec,gs) in wards.items():
     if g not in gs:continue
     if alive[owner] and view(positions[owner],8)&gtiles[g]:continue
     rec['events'].append(dict(r=e['r'],g=g,kind=kind,dead=not alive[owner]));counts['owner_ward_only_'+kind]+=1
   if kind=='move':positions[cid]=tuple(e['to'])
   elif kind=='cast' and e.get('moved'):positions[cid]=tuple(e['moved'])
   elif kind in ('recall_end','teleport_end'):positions[cid]=tuple(e['to'])
   elif kind=='respawn':positions[cid]=tuple(e['at']);alive[cid]=True
   elif kind=='death':alive[e['v']]=False
 return dict(job=job,counts=dict(counts),wards=records)
if __name__=='__main__':
 with Pool(int(os.environ.get('OMP_NUM_THREADS','2'))) as pool:out=list(pool.imap(run,json.loads((H/'jobs.json').read_text())))
 (H/'camp-information.json').write_text(json.dumps(out))
 for co in ['Mite-r5','Ad-Astra','Ocean-v105']:
  rows=[v for x in out if x['job']['cohort']==co for v in x['wards']];c=collections.Counter()
  for x in out:
   if x['job']['cohort']==co:c.update(x['counts'])
  print(co,dict(c),flush=True)
  for kind in ['all','camp','bush']:
   rs=[r for r in rows if kind=='all' or r[kind]];events=[e for r in rs for e in r['events']]
   print(kind,'wards',len(rs),'used',sum(bool(r['events']) for r in rs),'events',len(events),'events_while_dead',sum(e['dead'] for e in events),flush=True)
