#!/usr/bin/env python3
"""Validate physical roles, map pins, source pins, and output absence for the pending screen."""
from pathlib import Path
import hashlib, json
HERE=Path(__file__).resolve().parent
ROOT=Path('/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development')
rows=json.loads((HERE/'ORDERED-ROWS.pending.json').read_text())['rows']
assert len(rows)==84
assert sum(r['arm']=='equal-ray-vs-v33' for r in rows)==80
assert sum(r['arm']=='equal-ray-vs-execution-parent' for r in rows)==4
for r in rows:
    assert Path(r['map_path']).is_file()
    assert hashlib.sha256(Path(r['map_path']).read_bytes()).hexdigest()==r['map_sha256']
    assert not Path(r['output']).exists() and not Path(r['statistics']).exists()
    if r['arm']=='equal-ray-vs-v33':
        assert r['candidate_side'] in ('A','B')
        assert (r['A_source']=='equal-ray') == (r['candidate_side']=='A')
        assert (r['B_source']=='equal-ray') == (r['candidate_side']=='B')
    else:
        assert r['candidate_side']=='A' and r['A_source']=='equal-ray' and r['B_source']=='execution-parent'
print('84 ordered rows validated: map/source roles match candidate side; all outputs absent')
