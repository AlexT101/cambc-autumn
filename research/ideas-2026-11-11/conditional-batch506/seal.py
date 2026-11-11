"""Seal reviewed runtime, source, prospective configurations and queue preparations."""
import argparse
import json
from pathlib import Path
import shutil
from run import R, D, OLD, T, BASE, CAND, BODY, sha, source, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--runtime-proof', type=Path, required=True)
    args = parser.parse_args()
    assert not any((D / arm / 'first-heavy-start.json').exists() for arm in CAND), 'Cannot reseal a started gate'
    lib = args.library.resolve()
    proof = args.runtime_proof.resolve()
    assert lib.is_file() and proof.is_file()
    wrapper = R / 'tools/fastengine/runner/fastrunner'
    cambc = Path(shutil.which('cambc')).resolve()
    files = [*sorted(T.glob('*.py')), T / 'README.md', *sorted((R / 'sdk/cpp').glob('*')),
             *sorted((R / 'tools/mapgen').rglob('*.mjs')),
             *sorted((R / 'tools/fastengine/runner/src').glob('*.rs')),
             R / 'tools/fastengine/runner/src/aot_rt.h',
             *[R / 'tools' / name for name in ('ab.py', 'run_batched.py', 'cambc_env.py', 'cpu_slots.py', 'pooled.py', 'experiment_config.py')],
             R / 'tools/draftlab/features.mjs', R / 'tools/replay/drafts.mjs',
             D / 'protocol.json', D / 'smoke-maps.json', D / 'smoke-config.json', D / 'ladder-maps.json', D / 'ladder-config.json',
             D / 'seeds-chanM.json', D / 'seeds-bagfF.json', D / 'body-F.json', D / 'body-M.json',
             D / 'map-preparation-seal.json', D / 'map-preparation-source/run.py', D / 'map-preparation-source/maps_only.py',
             D / 'chanM/maps.json', D / 'chanM/maps-seal.json', D / 'chanM/features.jsonl',
             *[D / 'chanM' / ('config-' + str(i) + '.json') for i in range(4)],
             D / 'map-preparation-complete.json', D / 'map-preparation-ops-proof.json',
             OLD / 'manifest.json', OLD / 'chanM/mirror-manual-admission.json',
             wrapper, cambc, lib, proof, proof.parent / 'independent-code-review.json', D / 'independent-review.json']
    files.extend(Path(row['path']) for row in json.loads((D / 'smoke-maps.json').read_text()))
    files.extend(Path(row['path']) for row in json.loads((D / 'ladder-maps.json').read_text()))
    environment = {'CAMBC_BIN': str(wrapper), 'FASTRUNNER_LIB': str(lib), 'FASTRUNNER_MODE': 'native',
                   'FASTRUNNER_ENGINE': None, 'FASTRUNNER_CAMBC': None, 'FASTRUNNER_PGO': None,
                   'FASTRUNNER_CC': None, 'FASTRUNNER_COPT': None, 'FASTRUNNER_CFLAGS': None,
                   'FASTRUNNER_UNITS': None, 'FASTRUNNER_TRACE_FUEL': None, 'FASTRUNNER_TUNE': None}
    runtime = {'library': str(lib), 'library_sha256': sha(lib), 'wrapper_sha256': sha(wrapper),
               'cambc_path': str(cambc), 'cambc_sha256': sha(cambc), 'engine_version': '5.0.1',
               'validation_proof': str(proof), 'validation_proof_sha256': sha(proof),
               'environment': environment, 'cache_modes': 'metered Ocean; separate unmetered-v1 replica codegen key',
               'our_turn_fuel': 200000, 'replica_fuel': 'unmetered explicitREF config only', 'mirror_fuel': 'bothteams200000'}
    assert all(p.exists() for p in files), [str(p) for p in files if not p.exists()]
    manifest = {'files': {str(p): sha(p) for p in files if p.is_file()},
                'sources': {bot: source(bot) for bot in (BASE, *CAND.values(), *BODY.values())}, 'runtime': runtime}
    write(D / 'manifest.json', manifest)
    print(sha(D / 'manifest.json'))


if __name__ == '__main__':
    main()
