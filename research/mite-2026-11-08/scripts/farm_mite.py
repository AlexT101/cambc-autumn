"""Run tools/fish farm3_memory / farm3_evaluate on the Mite cohort 'mite1107' without adding a
manifest to research/fish-2026-11-05 (pin_cohort.py excludes every manifest there).
  python3 farm_mite.py memory
  python3 farm_mite.py evaluate FIT OUT [--also NAME=FIT]
"""
import sys
from pathlib import Path
sys.path.insert(0, 'tools/fish')
import farm3_lib
orig = farm3_lib.cohort_paths
def cohort_paths(c):
    if c != 'mite1107':
        return orig(c)
    d = Path('replays/fish-farm3/mite1107')
    return dict(choice=d / 'choice-v1.jsonl.gz', extras=d / 'farm2-v3.jsonl.gz', raw='replays/fish-scorecard/mite-1107/actor-all',
                manifest='replays/fish-scorecard/mite-1107/manifest-all.json')
farm3_lib.cohort_paths = cohort_paths
cmd = sys.argv[1]
if cmd == 'memory':
    import farm3_memory
    farm3_memory.cohort_paths = cohort_paths
    sys.argv = ['farm3_memory.py', 'mite1107']
    import runpy; runpy.run_module('farm3_memory', run_name='__main__')
else:
    sys.argv = ['farm3_evaluate.py'] + sys.argv[2:]
    import runpy; runpy.run_module('farm3_evaluate', run_name='__main__')
