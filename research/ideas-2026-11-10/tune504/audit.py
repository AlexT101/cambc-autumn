"""Audit exact paired cells before the draft gate reads a block."""
import json
from pathlib import Path
from run import R, sha, source


def validate_block(fg, cand, ref, k, fuel):
    records = []
    for o in 'FM':
        for tag, suite, games in fg.suites(k):
            directory = R / 'maps' if suite == 'ladder' else Path(suite)
            expected = {(p.stem, side) for p in directory.glob('*.map26a') for side in 'ab'}
            assert len(expected) == games
            for bot in (ref, cand):
                name = fg.rname(bot, k, o, tag)
                sp = R / 'replays/ab' / name / 'summary.json'
                s = json.loads(sp.read_text())
                assert s['games'] == games and s['errors'] == 0, name
                assert s['release'] is True and s['cambc'] == '5.0.1' and s['fuel'] == fuel, name
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

