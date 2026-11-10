import collections,json,os,sys
from pathlib import Path
from multiprocessing import Pool
H=Path('/home/ubuntu/tmp-offload/warding-2026-11-10')
from timing import run

def one(job):
 row=run(job);p=Path(job['path']);m=json.loads((p/'meta.json').read_text());mp=json.loads((p/m['mapFile']).resolve().read_text());bush={tuple(t) for t in mp['bushes']};c=collections.Counter(row['counts'])
 for w in row['wards']:
  kind='bush' if tuple(w['to']) in bush else 'nonbush';c[kind]+=1
  if any(k in w['after'] for k in ['move','attack','cast']):c['early']+=1;c['early_'+kind]+=1
 row['counts']=dict(c);return row
if __name__=='__main__':
 jobs=[]
 for p in (H/'smoke-analysis').glob('*/meta.json'):
  m=json.loads(p.read_text());assert m['validation']['ok'],p;side=next(i for i,t in enumerate(m['teams']) if t['bot']==0);bot=m['teams'][side]['name']
  if bot not in ['oc-campsh-498','oc-wlate-498']:continue
  fuel=200000 if '-200000-' in m['source'] else 100000;jobs.append(dict(cohort=bot,side=side,path=str(p.parent),fuel=fuel,map=m['map']['name'],source=m['source']))
 assert len(jobs)==32
 with Pool(int(os.environ.get('OMP_NUM_THREADS','2'))) as pool:out=list(pool.imap(one,jobs))
 (H/'late-timing.json').write_text(json.dumps(out))
 for bot in ['oc-campsh-498','oc-wlate-498']:
  for fuel in [100000,200000]:
   c=collections.Counter()
   for row in out:
    if row['job']['cohort']==bot and row['job']['fuel']==fuel:c.update(row['counts'])
   if bot=='oc-wlate-498':assert c['early_nonbush']==0 and c['nonbush']>0,(bot,fuel,c)
   print(bot,fuel,dict(c),flush=True)
