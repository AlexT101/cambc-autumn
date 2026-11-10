"""Count diagnostic camp-initiation guards; debug behavior evidence, not a strength gate."""
import argparse
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('results', type=Path)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
d = json.loads(a.results.read_text())
waits, heals = [], []
for match in d['matches']:
    if not match.get('replay'):
        continue
    replay = Path(match['replay'])
    team = 'ab'[match['order'].index(0)]
    with zipfile.ZipFile(replay) as z:
        stdout = z.read(f'team-{team}.stdout').decode(errors='replace')
    for x in re.finditer(r'CREW WAKE WAIT (\d+) (\d+) g(\d+) ally(\d+) damage([\d.]+) hp([\d.]+)', stdout):
        r, champ, group, ally, damage, hp = x.groups()
        waits.append(dict(replay=str(replay), team=team, round=int(r), champ=int(champ), group=int(group),
                          ally=int(ally), damage=float(damage), hp=float(hp)))
    for x in re.finditer(r'CREW PREHEAL (\d+) (\d+) g(\d+) escape ([\d.]+) hp ([\d.]+)', stdout):
        r, champ, group, damage, hp = x.groups()
        heals.append(dict(replay=str(replay), team=team, round=int(r), champ=int(champ), group=int(group),
                          escape=float(damage), hp=float(hp)))
by = defaultdict(set)
for x in waits:
    by[x['replay'], x['champ'], x['group']].add(x['round'])
episodes = []
for key, rounds in by.items():
    sequence = []
    for r in sorted(rounds):
        if sequence and r != sequence[-1] + 1:
            episodes.append(dict(key=key, start=sequence[0], end=sequence[-1], turns=len(sequence)))
            sequence = []
        sequence.append(r)
    if sequence:
        episodes.append(dict(key=key, start=sequence[0], end=sequence[-1], turns=len(sequence)))
episodes.sort(key=lambda x: x['turns'], reverse=True)
out = dict(games=d['completed'], errors=d['errors'], wait_calls=len(waits),
           wait_champ_rounds=len({(x['replay'], x['champ'], x['round']) for x in waits}),
           wait_games=len({x['replay'] for x in waits}), preheal_calls=len(heals),
           preheal_games=len({x['replay'] for x in heals}), episodes=episodes, waits=waits, preheals=heals)
a.out.write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({k: v for k, v in out.items() if k not in ('episodes', 'waits', 'preheals')}))
