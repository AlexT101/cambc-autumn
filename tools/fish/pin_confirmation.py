"""Pin the separate November 4/5 post-patch replay cohort, without decoding play."""
import hashlib,json
from pathlib import Path
from datetime import datetime,timezone

root=Path('research/fish-2026-11-05')
used={r['sha256'] for r in json.loads((root/'manifest.json').read_text())}
rows=[]
for line in Path('replays/bush-ladder/matches.tsv').read_text().splitlines():
    cols=line.split('\t')
    if 'Intercontinental Fish' not in cols[1:3]:continue
    match,a,b,_,_,mapname=cols[:6]
    p=Path('replays/bush-ladder/games')/(match+'.repl26a')
    sha=hashlib.sha256(p.read_bytes()).hexdigest()
    if sha in used:continue
    used.add(sha)
    # UUIDv7 encodes the match creation timestamp, not the match-group id.
    stamp=int(match.replace('-','')[:12],16)/1000
    rows.append(dict(sha256=sha,file=str(p),group=None,match=match,
        date=datetime.fromtimestamp(stamp,timezone.utc).isoformat(),map=mapname,
        side=0 if a=='Intercontinental Fish' else 1,opponent=b if a=='Intercontinental Fish' else a,
        version=None,split='confirmation'))
(root/'confirmation-manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
freeze=dict(models={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path('tools/fish/farm_model.py')]},
            games=len(rows),manifest_sha256=hashlib.sha256((root/'confirmation-manifest.json').read_bytes()).hexdigest(),
            note='No play from this cohort decoded during this continuation before these models were frozen. Match-group ids are unavailable.')
(root/'farm-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
print(len(rows),rows[0]['date'],rows[-1]['date'])
