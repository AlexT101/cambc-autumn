"""Pin every downloaded Fish game outside all existing manifests as cohort NAME, and hash
the given frozen files, before any of its play is decoded.

Reads only group metadata and replay bytes (hash, engine version).
"""
import argparse
import collections
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from manifest import build

ROOT = Path('research/fish-2026-11-05')


def main(name, raws, frozen):
    out, record_path = ROOT / f'{name}-manifest.json', ROOT / f'{name}-freeze.json'
    if out.exists() or record_path.exists():
        raise SystemExit('refusing to overwrite evidence')
    old = [e for p in sorted(ROOT.glob('*manifest.json')) for e in json.loads(p.read_text())]
    used = {k: {e[k] for e in old if e.get(k)} for k in ('sha256', 'match', 'group')}
    rows, seen = [], set()
    for raw in raws:
        tmp = ROOT / f'.{name}-candidates-{Path(raw).name}.json'
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
        e['split'] = f'{name}_confirmation'
    rows.sort(key=lambda e: (e['date'], e['file']))
    out.write_text(json.dumps(rows, indent=2) + '\n')
    paths = [Path(p) for p in frozen] + [Path(__file__)]
    record = dict(created=datetime.now(timezone.utc).isoformat(), manifest=str(out),
                  manifest_sha256=hashlib.sha256(out.read_bytes()).hexdigest(), games=len(rows),
                  groups=len({e['group'] for e in rows}),
                  excluded_manifests=sorted(str(p) for p in ROOT.glob('*manifest.json') if p != out),
                  files={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                  note='Every downloaded Fish game outside all earlier manifests by bytes, match or group id. '
                       'No play of this cohort decoded before this freeze.')
    with record_path.open('x') as f:
        json.dump(record, f, indent=2); f.write('\n')
    print(len(rows), 'games', record['groups'], 'groups', collections.Counter(e['engine'] for e in rows),
          collections.Counter(e['kind'] for e in rows), min(e['date'] for e in rows), max(e['date'] for e in rows))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('name'); p.add_argument('--raw', nargs='+', required=True); p.add_argument('--freeze', nargs='+', required=True)
    a = p.parse_args(); main(a.name, a.raw, a.freeze)
