"""Count fuel shortcuts and map-group buckets from the completed accuracy-port A/B."""
import collections
import json
from multiprocessing import get_context
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import re
import sys
import zipfile


def read_match(match):
    counts = [collections.Counter(), collections.Counter()]
    with zipfile.ZipFile(match['replay']) as replay:
        for side, team in enumerate('ab'):
            bot = match['order'][side]
            data = replay.read(f'team-{team}.stdout').replace(b'\0', b'')
            counts[bot].update(x.decode() for x in re.findall(rb'SHORTCUT \d+ \d+ ([\w-]+)', data))
            counts[bot]['oof_lines'] = sum(not x.startswith(b'draft') for x in re.findall(rb'^OOF \d+ (.+)$', data, re.M))
            counts[bot]['stdout_at_limit'] = int(len(data) >= 1024 * 1024)
    return counts


def main():
    batch, suite, target = map(Path, sys.argv[1:])
    report = json.loads((batch / 'results.json').read_text())
    assert report['completed'] == report['scheduled'] and report['errors'] == 0
    rows = {r['file']: r for r in json.loads((suite / 'index.json').read_text())['maps']}
    matches = report['matches']
    buckets = {}
    totals = [collections.Counter(), collections.Counter()]
    with ProcessPoolExecutor(8, mp_context=get_context('fork')) as pool:
        for match, counts in zip(matches, pool.map(read_match, matches, chunksize=32)):
            metrics = rows[Path(match['map']).name]['metrics']
            groups = 2 * metrics['groups_side'] + metrics['shared_groups']
            label = '<12' if groups < 12 else '12-23' if groups < 24 else '24-47' if groups < 48 else '48+'
            b = buckets.setdefault(label, {'games': 0, 'cand_wins': 0, 'oof': [0, 0], 'farm_partial': [0, 0]})
            b['games'] += 1
            b['cand_wins'] += match['winner'] == 0
            for bot in range(2):
                totals[bot].update(counts[bot])
                b['oof'][bot] += counts[bot]['oof_lines']
                b['farm_partial'][bot] += counts[bot]['farm-partial-evaluation']
    for b in buckets.values():
        b['cand_win_pct'] = round(100 * b['cand_wins'] / b['games'], 3)
    result = {'games': len(matches), 'bots': report['bots'], 'shortcuts': [dict(c.most_common()) for c in totals], 'group_buckets': buckets}
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
