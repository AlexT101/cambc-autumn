"""Pin the third cohort and model/code hashes before any third-cohort decisions are decoded."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from manifest import build


def main(raw, out):
    root=Path('research/fish-2026-11-05')
    old=[e for name in ('manifest.json','confirmation-manifest.json') for e in json.loads((root/name).read_text())]
    used={e['sha256'] for e in old}; oldgroups={e['group'] for e in old if e['group']}
    out=Path(out)
    if out.exists():raise SystemExit('refusing to replace pinned evidence')
    temp=out.with_suffix('.pending.json')
    build(raw,temp)
    rows=[dict(e,split='third_confirmation') for e in json.loads(temp.read_text()) if e['sha256'] not in used and e['group'] not in oldgroups]
    out.write_text(json.dumps(rows,indent=2)+'\n')
    temp.unlink()
    paths=[Path('tools/fish')/n for n in ('decision_model.py','decision_data.py','evaluate_decisions.py','fit_decisions.py',
                                         'extract.mjs','breadth.py','holder_model.py')]
    paths.append(root/'decision-trees.json')
    freeze=dict(created=datetime.now(timezone.utc).isoformat(),manifest=str(out),
                manifest_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),games=len(rows),
                groups=len({e['group'] for e in rows}),
                files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                note='Only raw bytes and match metadata inspected for the third cohort. Both older cohorts are used data. No third-cohort play decoded before this freeze.')
    out.with_name('decision-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    print(len(rows),'games',freeze['groups'],'groups')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw');p.add_argument('out')
    a=p.parse_args();main(a.raw,a.out)
