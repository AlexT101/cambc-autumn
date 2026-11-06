"""Count crew decisions in matched benchmark logs; these are descriptive, not independent A/Bs."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
TAGS = ['CREW PROPOSE', 'CREW JOIN', 'CREW BAIL', 'MONO STAGE', 'MONO ENGAGE']


def one(m):
    with zipfile.ZipFile(m['replay']) as z:
        text = z.read('team-' + 'ab'[m['order'].index(0)] + '.stdout')
    return {**{t: text.count(t.encode()) for t in TAGS}, 'logged_turns': text.count(b'\nD '), 'capped': int(len(text) >= 1048576)}


out = {}
for name in ['crew-index-fix', 'crew-index-confirm']:
    p = ROOT / f'replays/ab/astraeus-teacher-{name}-10k/summary.json'
    if not p.exists():
        continue
    s = json.loads(p.read_text())
    games = json.loads((ROOT / s['suites'][0]['batch'] / 'results.json').read_text())['matches']
    counts = {t: 0 for t in [*TAGS, 'logged_turns', 'capped']}
    with ThreadPoolExecutor(4) as pool:
        for row in pool.map(one, games):
            for k, v in row.items():
                counts[k] += v
    out[name] = counts
    print(name, counts, flush=True)
Path(__file__).with_name('fixed-crew-metrics.json').write_text(json.dumps(out, indent=2) + '\n')
