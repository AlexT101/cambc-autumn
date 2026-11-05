"""Pin unseen games in the ten newest available groups, then freeze code/model."""
import argparse
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from manifest import build


def main(raw):
    root=Path('research/fish-2026-11-05');out=root/'fourth-manifest.json'
    if out.exists():raise SystemExit('refusing to overwrite evidence')
    old=[e for n in ('manifest.json','confirmation-manifest.json','third-manifest.json')
         for e in json.loads((root/n).read_text())]
    used={k:{e[k] for e in old if e[k]} for k in ('sha256','match','group')}
    pending=root/'fourth-candidates-v2.json'
    if pending.exists():raise SystemExit('candidate manifest already exists')
    build(raw,pending)
    rows=[e for e in json.loads(pending.read_text()) if all(e[k] not in used[k] for k in used)]
    groups={}
    for e in rows:groups.setdefault(e['group'],[]).append(e)
    complete=sorted(groups.values(),key=lambda es:es[0]['date'],reverse=True)[:10]
    if len(complete)!=10:raise SystemExit('need ten unseen groups')
    rows=[dict(e,split='fourth_confirmation') for es in complete for e in es]
    out.write_text(json.dumps(rows,indent=2)+'\n')
    paths=[Path('tools/fish')/n for n in ('routes_data.py','routes_model.py','fit_routes.py','evaluate_routes.py',
        'decision_data.py','breadth.py','holder_model.py','fit_decisions.py','extract.mjs','pin_routes.py')]
    paths.append(root/'routes-trees.json')
    record=dict(created=datetime.now(timezone.utc).isoformat(),manifest=str(out),
        manifest_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),games=len(rows),groups=len(complete),
        files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        note='Ten newest available groups among downloaded metadata, excluding all three inspected cohorts by bytes, match ids and known group ids. Groups with duplicate replay bytes contribute fewer than five games. No fourth-cohort play decoded before freeze. Downloads outside these ten groups are not evaluated.')
    with (root/'routes-freeze.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
    print(len(rows),'games',min(e['date'] for e in rows),max(e['date'] for e in rows))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw');a=p.parse_args();main(a.raw)
