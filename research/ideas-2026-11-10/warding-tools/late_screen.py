"""Read-only evaluation of the bounded200k late-ward screen; never admits or launches100k."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics

T = Path(__file__).resolve().parent
R = T.parents[2]
H = Path('/home/ubuntu/tmp-offload/warding-2026-11-10')
STATE = Path('/home/ubuntu/tmp-offload/localq/state/ward-oc-wlate-498-200000')
RESULT = Path('/home/ubuntu/tmp-offload/diverse/gate-logs/fgate-oc-wlate-498--oc-campsh-498p4q-fuel200000.json')
ARMS = ('oc-wlate-498', 'oc-campsh-498')

def estimate(values):
    mean = statistics.mean(values)
    half = 1.96 * statistics.pstdev(values) / math.sqrt(len(values))
    return mean * 100, half * 100, (mean - half) * 100

def valid_stop(blocks, outcome):
    return 1 <= blocks <= 8 and (blocks == 8 or outcome in (
        'REJECT', 'LIVE BAR H1', 'H1 but the post-screen blocks read negative: not live'))

def evaluate():
    if not (STATE / 'done').exists():
        return {'decision': 'pending', 'reason': 'screen still running; no interim strength read'}
    if (STATE / 'done').read_text().strip() != '0' or not RESULT.exists():
        return {'decision': 'hold', 'reason': 'interrupted/failed screen; no inference or extension'}
    result_raw = RESULT.read_bytes()
    result = json.loads(result_raw)
    blocks = result['blocks']
    if not valid_stop(blocks, result['outcome']):
        return {'decision': 'hold', 'reason': 'not a valid prespecified terminal stop', 'terminal_result': result}
    assert result['cand'] == 'variants/' + ARMS[0] and result['ref'] == 'variants/' + ARMS[1]
    assert result['fuel'] == 200000 and result['cambc'] == '5.0.1'
    assert result['bodies'] == 'pick-model (Flp4/Mt3q)'
    expected_sources = json.loads((T / 'sources.json').read_text())
    sources = {}
    for arm in ARMS:
        root = R / 'bots/variants' / arm / 'src'
        rows = [(str(p.relative_to(root)), hashlib.sha256(p.read_bytes()).hexdigest())
                for p in sorted(root.rglob('*')) if p.is_file()]
        sources[arm] = hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()
        assert sources[arm] == expected_sources[arm], arm
    values, records, seen_maps = [], [], set()
    for k in range(1, blocks + 1):
        fresh = {}
        for tag in ('L', f'f{(k - 1) % 8}'):
            suite = R / 'maps' if tag == 'L' else Path('/home/ubuntu/tmp-offload/diverse/fresh/pool') / tag
            cells = {(p.stem, side) for p in suite.glob('*.map26a') for side in 'ab'}
            assert len(cells) == 256
            for code, body in (('Fp4', 'Flp4'), ('Mq', 'Mt3q')):
                for arm in ARMS:
                    name = f'fge501-{arm.removeprefix("oc-")}-dvn{k}{code}-{tag}-fuel200000'
                    sp = R / 'replays/ab' / name / 'summary.json'
                    raw = sp.read_bytes()
                    summary = json.loads(raw)
                    assert summary['release'] is True and summary['cambc'] == '5.0.1'
                    assert summary.get('fuel') == 200000 and summary['games'] == 256 and summary['errors'] == 0
                    assert summary['cand']['spec'] == 'variants/' + arm
                    assert summary['ref']['spec'] == f'variants/spar-dvn{k}-{body}'
                    matches, result_hashes = [], {}
                    for su in summary['suites']:
                        rp = R / su['batch'] / 'results.json'
                        data = rp.read_bytes()
                        result_hashes[str(rp)] = hashlib.sha256(data).hexdigest()
                        matches.extend(json.loads(data)['matches'])
                    actual = [(Path(m['map']).stem, 'a' if m['order'][0] == 0 else 'b') for m in matches]
                    assert len(matches) == 256 and len(set(actual)) == 256 and set(actual) == cells
                    assert all(m.get('winner') in (0, 1) for m in matches)
                    if tag != 'L':
                        fresh[code, arm] = {cell: float(m['winner'] == 0) for cell, m in zip(actual, matches)}
                    records.append({'name': name, 'summary_sha256': hashlib.sha256(raw).hexdigest(),
                                    'results_sha256': result_hashes, 'early_losses': summary.get('early_losses'),
                                    'handoff_failures': summary.get('handoff_failures'),
                                    'capped_drafts': summary.get('capped_drafts')})
        maps = {m for m, side in fresh['Fp4', ARMS[0]]}
        assert not seen_maps & maps
        seen_maps.update(maps)
        for m in sorted(maps):
            values.append(statistics.mean(fresh[o, ARMS[0]][m, s] - fresh[o, ARMS[1]][m, s]
                                          for o in ('Fp4', 'Mq') for s in 'ab'))
    assert len(values) == blocks * 128 == result['fresh_units']
    delta, half, lower = estimate(values)
    assert abs(delta - result['fresh'][0]) <= .00051 and abs(half - result['fresh'][1]) <= .00051
    return {'decision': 'positive' if lower > 0 else 'hold', 'fuel': 200000,
            'complete_blocks': blocks, 'valid_terminal_stop': True, 'validated_cells': True,
            'fresh_units': len(values), 'fresh_delta_pp': delta, 'fresh_ci95_halfwidth_pp': half,
            'fresh_lower_pp': lower, 'sources': sources, 'terminal_result': result,
            'terminal_result_sha256': hashlib.sha256(result_raw).hexdigest(), 'records': records,
            'policy': 'Positive makes100k eligible only for explicit coordinator admission; hold is not rejection. No extension.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=H / 'late-screen-proof.json')
    args = parser.parse_args()
    try:
        proof = evaluate()
    except (AssertionError, OSError, ValueError, KeyError) as error:
        proof = {'decision': 'hold', 'reason': 'validation failed; no inference or extension', 'error': repr(error)}
    args.out.write_text(json.dumps(proof, indent=1) + '\n')
    print(json.dumps({k: v for k, v in proof.items() if k != 'records'}))
