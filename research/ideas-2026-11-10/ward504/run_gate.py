"""Sealed504 camp ward gates: full200k, standard three-way decisions, no width stop."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

R = Path('/home/ubuntu/cambc-autumn')
D = Path('/home/ubuntu/tmp-offload/ward504-full')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def source(bot):
    root = R / 'bots' / bot
    return {str(p.relative_to(root)): sha(p) for p in sorted((root / 'src').rglob('*')) if p.is_file()}


def verify():
    m = json.loads((D / 'manifest.json').read_text())
    assert sha(Path(__file__)) == m['launcher_sha256']
    assert sha(D / 'protocol.json') == m['protocol_sha256']
    for p, h in m['tools'].items():
        assert sha(R / p) == h, p
    for bot, files in m['sources'].items():
        assert source(bot) == files, bot
    for p, h in m['maps'].items():
        assert sha(Path(p)) == h, p
    return m, json.loads((D / 'protocol.json').read_text())


def validate_block(fg, cand, ref, k):
    records = []
    for o in 'FM':
        for tag, suite, games in fg.suites(k):
            directory = R / 'maps' if suite == 'ladder' else Path(suite)
            expected = {(p.stem, side) for p in directory.glob('*.map26a') for side in 'ab'}
            assert len(expected) == games == 256
            for bot in (ref, cand):
                name = fg.rname(bot, k, o, tag)
                sp = R / 'replays/ab' / name / 'summary.json'
                s = json.loads(sp.read_text())
                assert s['games'] == games and s['errors'] == 0, name
                assert s['release'] is True and s['cambc'] == '5.0.1' and s['fuel'] == 200000, name
                assert s['cand']['spec'] == bot and s['ref']['spec'] == fg.mdir(k, o), name
                cells = []
                batches = {}
                for sub in s['suites']:
                    bp = R / sub['batch'] / 'results.json'
                    b = json.loads(bp.read_text())
                    assert b['errors'] == 0 and b['completed'] == b['scheduled'] == games
                    for x in b['matches']:
                        assert x.get('winner') in (0, 1) and x['order'] in ([0, 1], [1, 0]), name
                        cells.append((Path(x['map']).stem, 'a' if x['order'][0] == 0 else 'b'))
                    batches[str(bp)] = sha(bp)
                assert len(cells) == len(set(cells)) == games and set(cells) == expected, name
                records.append({'name': name, 'summary_sha256': sha(sp), 'batch_hashes': batches,
                                'counts': {key: s.get(key) for key in ('early_losses', 'handoff_failures', 'capped_drafts')}})
    return {'block': k, 'validated_summaries': len(records), 'records': records,
            'bodies': {fg.mdir(k, o): source(fg.mdir(k, o)) for o in 'FM'}}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('arm', choices=['camp', 'campall'])
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    m, protocol = verify()
    argv = protocol['argv'][a.arm]
    if a.check:
        print(json.dumps({'argv': argv, 'manifest_sha256': sha(D / 'manifest.json')}))
        return
    with (D / (a.arm + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = D / (a.arm + '-started.json')
        assert not state.exists(), 'Existing run: no automatic repeat or restart'
        state.write_text(json.dumps({'pid': os.getpid(), 'argv': argv, 'manifest_sha256': sha(D / 'manifest.json')}))
        spec = importlib.util.spec_from_file_location('ward504_fgate', R / argv[1])
        fg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fg)
        original = fg.block_units
        blocks = D / (a.arm + '-blocks')
        blocks.mkdir(exist_ok=True)

        def audited(cand, ref, k, rng):
            record = validate_block(fg, cand, ref, k)
            (blocks / f'{k:04d}.json').write_text(json.dumps(record, indent=1) + '\n')
            return original(cand, ref, k, rng)

        fg.block_units = audited
        sys.argv = argv[1:]
        os.chdir(R)
        fg.main()
        verify()
        result_path = Path(fg.LOGS) / f'fgate-{Path(argv[2]).name}--{Path(argv[3]).name}p4q-fuel200000.json'
        result = json.loads(result_path.read_text())
        result['validated_blocks'] = len(list(blocks.glob('*.json')))
        assert result['validated_blocks'] == result['blocks']
        result['decision_note'] = ('Judgement review; not automatic rejection or CI proof of positive gain.'
                                   if result['outcome'] == 'ZONE' else
                                   'UNRESOLVED at ordinary1000-block cap; no repeat.' if result['blocks'] >= 1000 and
                                   result['outcome'] in ('undecided', 'ACCEPT (screen), live bar undecided') else
                                   'Standard sequential outcome; coordinator review required before100k or promotion.')
        result['manifest_sha256'] = sha(D / 'manifest.json')
        (D / (a.arm + '-result.json')).write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
