import collections,gzip,json,os
from pathlib import Path
from multiprocessing import Pool
H=Path('/home/ubuntu/tmp-offload/warding-2026-11-10')
def run(job):
 p=Path(job['path']);m=json.loads((p/'meta.json').read_text());mp=json.loads((p/m['mapFile']).resolve().read_text());cs={c['id']:c for c in m['champions']};camp={tuple((c['x'],c['y'])):c['group'] for c in mp['camps']};states={g['id']:'alive' for g in mp['groups']};old={};c=collections.Counter()
 with gzip.open(p/'events.jsonl.gz','rt') as f:
  for line in f:
   e=json.loads(line);k=e['k']
   if k=='group_clear':states[e['g']]='cleared'
   elif k=='capture':states[e['g']]='respawning'
   elif k=='group_respawn':states[e['g']]='alive'
   elif k=='ward' and cs[e['a']]['team']==job['side']:
    cid=e['a'];g=camp.get(tuple(e['to']))
    if g is not None:
     c['camp_wards']+=1;c[states[g]]+=1;c['same_group_replacement']+=old.get(cid)==g
    old[cid]=g
 return dict(job=job,counts=dict(c))
if __name__=='__main__':
 with Pool(int(os.environ.get('OMP_NUM_THREADS','2'))) as pool:out=list(pool.imap(run,json.loads((H/'jobs.json').read_text())))
 (H/'camp-timing.json').write_text(json.dumps(out))
 for co in ['Mite-r5','Ad-Astra','Ocean-v105']:
  c=collections.Counter()
  for x in out:
   if x['job']['cohort']==co:c.update(x['counts'])
  print(co,dict(c),flush=True)
