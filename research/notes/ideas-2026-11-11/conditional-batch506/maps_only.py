"""Authorized outcome-free preparation, separate from runtime validation and gate admission."""
import fcntl
import json
import os
from run import D, sha, prepare_maps, write


def main():
    proof = json.loads((D / 'map-preparation-seal.json').read_text())
    for path, digest in proof['files'].items():
        assert sha(path) == digest, path
    assert os.environ.get('CAMBC_SLOTS') == '86' and not os.environ.get('CAMBC_SLOT_DIR')
    os.environ['CAMBC_SLOT_GROUP'] = 'cond-runtime-map-preparation'
    os.environ['CAMBC_SLOT_WEIGHT'] = '1'
    os.environ['OMP_NUM_THREADS'] = os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['NODE_OPTIONS'] = '--max-old-space-size=16384'
    with (D / 'chanM/run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        rows = prepare_maps('chanM')
    # mapgen inputs and reservation stay immutable; wrapper integration may evolve separately.
    for path, digest in proof['inputs'].items():
        assert sha(path) == digest, path
    write(D / 'map-preparation-complete.json', {'maps': len(rows), 'map_manifest_sha256': sha(D / 'chanM/maps.json'),
          'preparation_seal_sha256': sha(D / 'map-preparation-seal.json'), 'outcomes_observed': False})


if __name__ == '__main__':
    main()
