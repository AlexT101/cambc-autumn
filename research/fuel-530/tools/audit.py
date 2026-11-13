"""Audit benchmark handoff, draft and stdout censoring before deleting bundles."""
import json,sys,zipfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

def audit(name):
 file=Path(name);data=json.loads(file.read_text());root=file.with_name(file.stem+'-games')
 if (root/root).is_dir(): root=root/root
 def check(g):
  key=f"{g['map']}-{g['side']}"
  bundles=list((root/key).glob('*.repl26a'))
  if not bundles: return {'key':key,'missing_bundle':True}
  with zipfile.ZipFile(bundles[0]) as z:
   size=z.getinfo(f"team-{g['side']}.stdout").file_size
   text_size=len(z.read(f"team-{g['side']}.stdout").replace(b"\0",b"")) if size>=1048576 else size
  return {'key':key,'size':size,'text_size':text_size}
 with ThreadPoolExecutor(8) as ex: rows=list(ex.map(check,data['games']))
 return dict(file=name,games=len(data['games']),errors=[g for g in data['games'] if 'error' in g],
  handoff=sum(bool(g.get('handoff')) for g in data['games']),capped=sum(bool(g.get('capped')) for g in data['games']),
  max_stdout=max(x.get('size',0) for x in rows),
  censored=[x for x in rows if x.get('text_size',0)>=1048576],missing=[x for x in rows if x.get('missing_bundle')])
print(json.dumps([audit(f) for f in sys.argv[1:]],indent=2))
