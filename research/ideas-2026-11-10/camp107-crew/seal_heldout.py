"""Seal the unused suite before candidate selection or any confirmation games."""
import hashlib
import json
from pathlib import Path
import random
import time

R = Path('/home/ubuntu/cambc-autumn')
D = Path('/home/ubuntu/tmp-offload/camp107-mechanism/heldout')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
protocol = json.loads((D / 'protocol.json').read_text())
assert not (D / 'manifest.json').exists()
original = sorted(p for seed in protocol['map_seeds']
                  for p in (D / 'generated' / f'seed-{seed}').glob('*.map26a'))
assert len(original) == 4096
known = list(Path('/home/ubuntu/tmp-offload/diverse/fresh/pool').glob('*/*.map26a'))
known += list((R / 'maps').glob('*.map26a'))
known += list((R / 'maps/gen').glob('*.map26a'))
known += list((R / 'maps/gen-s1').glob('*.map26a'))
old = {sha(p): str(p) for p in known}
audit = json.loads((D / 'novelty-audit.json').read_text())
assert not audit['missing'], 'Resolve missing inventory maps before sealing'
old.update({digest: paths[0] for digest, paths in audit['collisions'].items()})
excluded = [{'path': str(p), 'prior': old[sha(p)]} for p in original if sha(p) in old]
files = [p for p in original if sha(p) not in old]
replacement_seed = 63671816
extra = sorted((D / 'generated' / f'seed-{replacement_seed}').glob('*.map26a'))
random.Random(2061111).shuffle(extra)
used = set(old) | {sha(p) for p in files}
replacements = []
for p in extra:
    if len(files) == 4096:
        break
    digest = sha(p)
    if digest not in used:
        files.append(p)
        replacements.append(str(p))
        used.add(digest)
assert len(files) == len({sha(p) for p in files}) == 4096
random.Random(2061110).shuffle(files)
sources = {}
for f in ('wakeheal2-source.json', 'wakecrew3-source.json'):
    for bot, record in json.loads((D.parent / f).read_text()).items():
        assert bot not in sources or sources[bot] == record
        sources[bot] = record
for k in range(1, 9):
    for body in ('Flp4', 'Mt3q'):
        bot = f'variants/spar-dvn{k}-{body}'
        root = R / 'bots' / bot
        fs = {str(p.relative_to(root)): sha(p) for p in sorted((root / 'src').rglob('*')) if p.is_file()}
        assert fs
        sources[bot] = {'files': fs}
for bot, record in sources.items():
    root = R / 'bots' / bot
    for rel, digest in record['files'].items():
        assert sha(root / rel) == digest, (bot, rel)
    assert 'constexpr bool test_draft = false;' in (root / 'src/params.h').read_text()
base_src = R / 'bots/variants/oc-campsh-498/src'
for p in base_src.rglob('*'):
    if p.is_file():
        assert p.read_bytes() == (R / 'bots/ocean/src' / p.relative_to(base_src)).read_bytes()
blocks, maps = [], []
for i in range(8):
    suite = D / 'blocks-audited' / f'b{i + 1}'
    suite.mkdir(parents=True, exist_ok=False)
    group = files[i * 512:(i + 1) * 512]
    for p in group:
        link = suite / p.name
        link.symlink_to(p)
        maps.append({'path': str(link), 'sha256': sha(p), 'noise': i + 1})
    blocks.append({'noise': i + 1, 'suite': str(suite), 'names': [p.stem for p in group]})
manifest = {'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'base': protocol['base'], 'map_count': 4096, 'protocol_sha256': sha(D / 'protocol.json'),
            'launcher_sha256': sha(Path(__file__).with_name('heldout.py')),
            'novelty_audit_sha256': sha(D / 'novelty-audit.json'),
            'map_seeds': protocol['map_seeds'], 'replacement_seed': replacement_seed,
            'collision_check': {'prior_maps_checked': audit['unique_inodes'], 'excluded': excluded,
                                'replacements': replacements, 'final_hash_overlap': 0},
            'sources': sources, 'blocks': blocks, 'maps': maps}
(D / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
print(json.dumps({'maps': len(files), 'manifest_sha256': sha(D / 'manifest.json'),
                  'prior_maps_checked': audit['unique_inodes'], 'source_count': len(sources)}))
