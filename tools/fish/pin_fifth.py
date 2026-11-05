"""Pin every unseen downloaded Fish game as the fifth cohort, then freeze code/models.

Reads only group metadata and replay bytes (hash, engine version), never play.
"""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from manifest import build

ROOT = Path('research/fish-2026-11-05')
FROZEN = ['choice_data.py', 'choice_model.py', 'fit_choice.py', 'evaluate_choice.py', 'routes_data.py', 'routes_model.py',
          'evaluate_routes.py', 'audit_incoming_payout.py', 'decision_data.py', 'evaluate_decisions.py', 'decision_model.py',
          'breadth.py', 'holder_model.py', 'extract.mjs', 'audit.mjs', 'pin_fifth.py']
MODELS = ['choice-fit.json', 'choice-fit-discovery.json', 'routes-trees.json', 'decision-trees.json']


def main(raws):
    out = ROOT / 'fifth-manifest.json'
    if out.exists() or (ROOT / 'choice-freeze.json').exists():
        raise SystemExit('refusing to overwrite evidence')
    old = [e for n in ('manifest.json', 'confirmation-manifest.json', 'third-manifest.json', 'fourth-manifest.json')
           for e in json.loads((ROOT / n).read_text())]
    used = {k: {e[k] for e in old if e.get(k)} for k in ('sha256', 'match', 'group')}
    rows, seen = [], set()
    for raw in raws:
        tmp = ROOT / f'.fifth-candidates-{Path(raw).name}.json'
        build(raw, tmp)
        for e in json.loads(tmp.read_text()):
            if all(e[k] not in used[k] for k in used) and e['sha256'] not in seen:
                seen.add(e['sha256']); rows.append(e)
        tmp.unlink()
    for e in rows:
        e['kind'] = json.loads((Path(e['file']).parent / 'group.json').read_text())['group']['kind']
        e['engine'] = subprocess.run(['node', '--input-type=module', '-e',
            "import fs from 'node:fs';import {replayEngine} from './tools/replay/engine.mjs';"
            f"console.log(replayEngine(fs.readFileSync({json.dumps(e['file'])})))"],
            capture_output=True, text=True, check=True).stdout.strip()
        e['split'] = 'fifth_confirmation'
    rows.sort(key=lambda e: (e['date'], e['file']))
    out.write_text(json.dumps(rows, indent=2) + '\n')
    paths = [Path('tools/fish') / n for n in FROZEN] + [ROOT / n for n in MODELS]
    record = dict(created=datetime.now(timezone.utc).isoformat(), manifest=str(out),
                  manifest_sha256=hashlib.sha256(out.read_bytes()).hexdigest(), games=len(rows),
                  groups=len({e['group'] for e in rows}), files={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                  note='Every downloaded Fish game not in the four inspected cohorts by bytes, match or group id, ranked and '
                       'unranked. No fifth-cohort play decoded before this freeze. choice-fit.json was fitted on all three '
                       'decoded current cohorts; choice-fit-discovery.json on the 124 discovery games only.')
    with (ROOT / 'choice-freeze.json').open('x') as f:
        json.dump(record, f, indent=2); f.write('\n')
    from collections import Counter
    print(len(rows), 'games', record['groups'], 'groups', Counter(e['engine'] for e in rows), Counter(e['kind'] for e in rows),
          min(e['date'] for e in rows), max(e['date'] for e in rows))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('raws', nargs='+'); a = p.parse_args(); main(a.raws)
