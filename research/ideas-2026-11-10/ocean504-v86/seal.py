"""Seal the explicitly selected benchmark before any heavy work."""
from pathlib import Path
import json
from run import R, D, CAND, REF, source, committed, sha, write

assert not (D / 'first-heavy-start.json').exists()
p = json.loads((D / 'protocol.json').read_text())
assert source(CAND) == committed(p['candidate_commit'])
assert source(REF) == committed(p['reference_commit'])
paths = list(Path(__file__).parent.glob('*.py')) + [D / 'protocol.json']
paths += [R / x for x in ('tools/ab.py', 'tools/run_batched.py', 'tools/pooled.py', 'tools/cpu_slots.py', 'tools/cambc_env.py', 'tools/fuel/oof.py')]
paths += list((R / 'tools/mapgen').glob('*.mjs')) + list((R / 'sdk/cpp').glob('*.h')) + list((R / 'maps').glob('*.map26a'))
paths += [Path('/home/ubuntu/tmp-offload/localq/reservations/ocean504-v86/seeds.json')]
write(D / 'manifest.json', {'files': {str(x.resolve()): sha(x) for x in paths},
      'sources': {b: source(b) for b in (CAND, REF)},
      'source_provenance': {'candidate_commit': p['candidate_commit'], 'reference_commit': p['reference_commit']}})
print(json.dumps({'manifest_sha256': sha(D / 'manifest.json'), 'launcher_sha256': sha(Path(__file__).parent / 'run.py')}))
