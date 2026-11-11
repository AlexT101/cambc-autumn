"""Compact identity and per-turn fuel evidence for the local experiment matrix."""
import csv
import json
from pathlib import Path

root = Path('replays/fuel/fuelC')
rows = []
for mode in ('own', 'td'):
    base = json.loads((root / f'base-wide-{mode}.json').read_text())
    a = {(g['map'],g['side']):g for g in base['games']}
    for path in sorted(root.glob(f'*-wide-{mode}.json')):
        b = json.loads(path.read_text())
        bg = {(g['map'],g['side']):g for g in b['games'] if 'error' not in g}
        same = [k for k in a if k in bg and a[k]['replay'] == bg[k]['replay']]
        total = saving = heavy = heavy_saving = old_over = new_over = 0
        for key in same:
            g, h = a[key], bg[key]
            assert len(g['play']) == len(h['play'])
            for x,y in zip(g['play'][g['bodies']:], h['play'][h['bodies']:]):
                total += 1; saving += x-y
                old_over += x>100000; new_over += y>100000
                if x>=95000: heavy += 1; heavy_saving += x-y
        rows.append(dict(variant=path.stem.removesuffix(f'-wide-{mode}'), draft=mode, identical=len(same), games=len(a),
                         mean=b['all']['mean'], p99=b['all']['p99'], saving_on_matching_turns=round(saving/max(1,total),2),
                         saving_on_base_95k_turns=round(heavy_saving/max(1,heavy),2),
                         matching_turns_over100k_base=old_over, matching_turns_over100k_candidate=new_over))
out = Path('research/charybdis-fuelC/results/identity.csv')
with out.open('w') as f:
    w=csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n");w.writeheader();w.writerows(rows)
print(out)
