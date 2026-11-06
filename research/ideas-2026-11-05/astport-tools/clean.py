"""clean.py NAME...: delete an A/B's replays (replays/batch-*-ab-NAME-*/), keeping results.json and logs."""
import sys
from pathlib import Path
root = Path('/home/ubuntu/cambc-autumn/replays')
for name in sys.argv[1:]:
    if not (root / 'ab' / name / 'summary.md').exists():
        print(f'{name}: no summary, left alone'); continue
    freed = 0
    for d in root.glob(f'batch-*-ab-{name}-*'):
        for p in d.iterdir():
            if p.is_file() and p.suffix in ('.repl26a', '.camstat', '.zip'):
                freed += p.stat().st_size; p.unlink()
    print(f'{name}: freed {freed/1e9:.2f} GB')
