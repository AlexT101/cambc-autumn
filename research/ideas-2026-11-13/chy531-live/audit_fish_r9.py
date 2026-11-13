"""Audit the outcome-only 531 baseline on Fish r9, excluding batch fillers."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import ladder_scrims as ls

PIN = '01a1d67e-e307-7f33-9412-90716c3b4ad9'


def audit():
    tasks, created, finished, dropped, _ = ls.state()
    tasks = [t for t in tasks if t['version'] == 132 and t.get('refset') == 'r9'
             and t.get('purpose') == 'set' and t['opp_id'] == ls.TEAMS['fish'][0]]
    assert len(tasks) == 69
    by_id = {t['id']: t for t in tasks}
    expected = {(g['map'], g['side']) for t in tasks for g in t['games'] if not g.get('filler')}
    ladder = json.loads((ls.DATA / 'set-full170.json').read_text())['all']
    assert expected == {(m['name'], side) for m in ladder for side in ('a', 'b')}
    assert len(expected) == 340
    assert not set(by_id).intersection(dropped)
    suspect = ls.suspect_groups()
    groups = set()
    for t in tasks:
        if t['id'] not in created:
            continue
        e = created[t['id']]
        assert e['live'] == e['selected'] == 132
        assert e['group'] not in suspect
        assert (e['group'] == PIN and e['source_group'] is None) or e['source_group'] == PIN
        groups.add(e['group'])
    positions, cells = {}, {}
    for r in ls.read_jsonl(ls.DATA / 'games.jsonl'):
        if r.get('task') not in by_id:
            continue
        t = by_id[r['task']]
        e = created[r['task']]
        g = t['games'][r['position'] - 1]
        assert r['version'] == 132 and r['refset'] == 'r9' and r['pin'] == 'ref'
        assert r['opp_id'] == t['opp_id'] and r['group'] == e['group']
        assert r['source_group'] == e['source_group']
        assert r['status'] == 'finished' and r['result'] in ('win', 'loss')
        assert (r['map'], r['side']) == (g['map'], g['side'])
        assert bool(r.get('filler')) == bool(g.get('filler'))
        key = r['task'], r['position']
        if key in positions:
            assert positions[key]['match'] == r['match'] and positions[key]['result'] == r['result']
        positions[key] = r
        if not r.get('filler'):
            cell = r['map'], r['side']
            if cell in cells:
                assert cells[cell]['result'] == r['result']
            cells[cell] = r
    complete = len(groups) == 69 and groups <= set(finished) and len(positions) == 345 and set(cells) == expected
    wins = sum(r['result'] == 'win' for r in cells.values())
    return dict(at=ls.now(), version=132, code='531 c451e3387', opponent='Fish', refset='r9',
                pin_source_group=PIN, complete=complete, planned_groups=69, created_groups=len(groups),
                collected_groups=len(groups.intersection(finished)), expected_unique_cells=340,
                unique_cells=len(cells), wins=wins, losses=len(cells)-wins,
                filler_records=sum(bool(r.get('filler')) for r in positions.values()),
                provenance='clean', collection='outcome_only; no replay archive claim',
                cells=[dict(map=m, side=s, result=r['result'], match=r['match'], group=r['group'])
                       for (m, s), r in sorted(cells.items())])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    result = audit()
    if args.require_complete:
        assert result['complete'], 'Campaign is not complete'
    Path(__file__).with_name('fish-r9-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'cells'}))
