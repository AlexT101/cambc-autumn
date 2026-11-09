#!/usr/bin/env python3
"""polyak.py RUN OUT_JSON [--from-frac 0.5]: the mean of a tune run's iterates from that fraction on, as name -> value
(tune.py apply --values). s87b's 26 knobs random-walked (net/path <= 0.12), so the last iterate carries walk noise that
the mean of the second half averages out."""
import json, sys
from pathlib import Path
run = Path('/home/ubuntu/cambc-autumn/replays/tune') / sys.argv[1]
frac = float(sys.argv[sys.argv.index('--from-frac') + 1]) if '--from-frac' in sys.argv else 0.5
cfg = json.loads((run / 'config.json').read_text())
H = [json.loads(l) for l in open(run / 'history.jsonl')]
H = H[int(len(H) * frac):]
out = {}
for n, (lo, hi, kind) in cfg['params'].items():
    x = sum(min(1.0, max(0.0, h['x'][n])) for h in H) / len(H)
    v = lo + x * (hi - lo)
    out[n] = int(round(v)) if kind == 'int' else v
Path(sys.argv[2]).write_text(json.dumps(out, indent=1))
print(f'{len(H)} iterates averaged -> {sys.argv[2]}')
