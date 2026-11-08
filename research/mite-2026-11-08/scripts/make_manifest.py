"""Scorecard manifests for Mite's side of its 11-07 05-14 UTC ladder games (index.py's mite_index.json)."""
import json,datetime,hashlib,sys
from pathlib import Path
ix=json.load(open(sys.argv[1] if len(sys.argv)>1 else 'mite_index.json'))
H=lambda o: datetime.datetime.utcfromtimestamp(int(o['mid'].replace('-','')[:12],16)/1000).strftime('%m-%d %H')
S=[o for o in ix if '11-07 05'<=H(o)<='11-07 14']
out=Path('replays/fish-scorecard/mite-1107')
by={0:[],1:[]}; seen=set()
for o in S:
    f=Path(f"/home/ubuntu/tmp-offload/gaps/repl/{o['src']}/{o['mid']}.repl26a")
    if not f.exists(): continue
    d=hashlib.sha256(f.read_bytes()).hexdigest()
    if d in seen: continue
    seen.add(d)
    by[o['side']].append(dict(sha256=d,file=str(f),map=o['map'],side=o['side'],group=o['mid'],match=o['mid'],opponent=o['opp'],bot='Mite',split='all',kind='ladder'))
for s,l in ((0,'A'),(1,'B')):
    (out/l).mkdir(parents=True,exist_ok=True); (out/l/'manifest.json').write_text(json.dumps(by[s],indent=1))
(out/'dataset.json').write_text(json.dumps(dict(name='mite-1107',bot='Mite',opponent='ladder',parts=['A','B'],games={l:len(by[s]) for s,l in ((0,'A'),(1,'B'))}),indent=1))
