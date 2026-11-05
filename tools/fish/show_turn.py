"""Print one Fish turn and its pre-input perspectives, identified in the report."""
import argparse
import gzip
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('game', help='16-character replay SHA prefix')
p.add_argument('round', type=int)
p.add_argument('actor', type=int)
p.add_argument('--cache', default='replays/fish-model')
a = p.parse_args()
with gzip.open(Path(a.cache)/f'{a.game}.json.gz') as f:
    game = json.load(f)
turns = [t for t in game['turns'] if t['round'] == a.round and t['id'] == a.actor]
if len(turns) != 1:
    raise SystemExit(f'expected one turn, found {len(turns)}')
print(json.dumps(dict(file=game['file'], match=game['match'], engine=game['engine'], turn=turns[0]), indent=2))
