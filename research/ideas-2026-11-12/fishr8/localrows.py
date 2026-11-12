"""Rows for ab.py replays decoded by extract.mjs (NNN-map-12 = our bot on side a), so the live-mode scripts
(vesper.py, fishx.py, traj.py, mitefit mstats/fstats live) read local runs.   py localrows.py EXT OUT.json"""
import json, os, sys
idx = json.load(open(sys.argv[1] + '/index.json'))['games']; rows = {}
for g in idx:
    base = os.path.basename(g['source'])[:-8]; num, rest = base.split('-', 1); m, o = rest.rsplit('-', 1)
    rows[base] = {'version': 0, 'map': m, 'side': 'a' if o == '12' else 'b'}
json.dump(rows, open(sys.argv[2], 'w')); print(len(rows))
