"""Audit v138's book-enabled ladder sweep, reusing its qualification cells."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import ladder_scrims as ls

PINS = {'fish': ('r10', '01a1d732-2d11-7f85-85fa-f4953aad836c'),
        'mite': ('r15', '01a1d706-59a1-78b3-9db5-8109569b1865')}


def audit():
    tasks, created, finished, dropped, _ = ls.state()
    suspect = ls.suspect_groups()
    ladder = json.loads((ls.DATA / 'set-full170.json').read_text())['all']
    expected = {(m['name'], side) for m in ladder for side in ('a', 'b')}
    assert len(expected) == 340
    rows = ls.read_jsonl(ls.DATA / 'games.jsonl')
    results = {}
    for opp, (refset, pin) in PINS.items():
        parts = {f'chy532-book40-{opp}-{refset}', f'chy532-v138-full-{opp}-{refset}'}
        mine = {t['id']: t for t in tasks if t['version'] == 138 and t.get('part') in parts}
        assert not set(mine).intersection(dropped)
        planned = {(g['map'], g['side']) for t in mine.values() for g in t['games'] if not g.get('filler')}
        assert planned <= expected
        groups = set()
        for tid, task in mine.items():
            assert task['opp_id'] == ls.TEAMS[opp][0]
            assert task['refset'] == refset and task['pin'] == 'ref'
            if tid in created:
                event = created[tid]
                assert event['live'] == event['selected'] == 138
                assert event['source_group'] == pin and event['group'] not in suspect
                groups.add(event['group'])
        cells = {}
        for row in rows:
            if row.get('task') not in mine or row.get('filler'):
                continue
            task = mine[row['task']]
            event = created[row['task']]
            game = task['games'][row['position'] - 1]
            cell = row['map'], row['side']
            assert cell == (game['map'], game['side']) and not game.get('filler')
            assert row['version'] == 138 and row['opp_id'] == task['opp_id']
            assert row['refset'] == refset and row['pin'] == 'ref'
            assert row['source_group'] == pin and row['group'] == event['group']
            assert row['status'] == 'finished' and row['result'] in ('win', 'loss')
            if cell in cells:
                assert cells[cell]['result'] == row['result']
            cells[cell] = row
        wins = sum(r['result'] == 'win' for r in cells.values())
        complete = set(cells) == expected and groups <= set(finished)
        results[opp] = dict(refset=refset, source_group=pin, complete=complete,
                            expected_cells=340, planned_cells=len(planned), cells=len(cells),
                            wins=wins, losses=len(cells)-wins,
                            win_rate=wins/len(cells) if cells else None,
                            created_groups=len(groups), collected_groups=len(groups.intersection(finished)),
                            interpretation='full ladder' if complete else 'partial; qualification cells are loss-weighted',
                            results=[dict(map=m, side=s, result=r['result'], match=r['match'])
                                     for (m, s), r in sorted(cells.items())])
    return dict(at=ls.now(), version=138, code='532 9ad13ba', book_enabled=True,
                complete=all(r['complete'] for r in results.values()), provenance='clean', opponents=results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--watch', action='store_true')
    args = parser.parse_args()
    while True:
        result = audit()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.out.with_suffix('.tmp')
        tmp.write_text(json.dumps(result, indent=2) + '\n')
        tmp.replace(args.out)
        print(json.dumps({**{k: v for k, v in result.items() if k != 'opponents'},
                          'opponents': {o: {k: v for k, v in r.items() if k != 'results'}
                                        for o, r in result['opponents'].items()}}), flush=True)
        if result['complete'] or not args.watch:
            break
        time.sleep(60)
