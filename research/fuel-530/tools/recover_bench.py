"""Recover the original fast-runner bench after the initial relative --games path.

No games are rerun. Use bench.py's read_game and summary on saved bundles/camstats.
"""
import json, sys, subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(Path('tools/fuel').resolve()))
import bench
root=Path('replays/fuel/f530/base-dev-games')
raw=root/root
maps=Path('research/fuel-530/maps-dev.txt').read_text().splitlines()
def read(job):
    m,s=job
    p=raw/(Path(m).stem+'-'+s)
    d=json.loads(subprocess.check_output(['cambc','summary',str(p/'game.camstat'),'-o','-']))
    draft=[x['champion'] for x in d['roster']['draft'] if x['team']=='team'+s.upper()]
    win=d['match']['outcome']
    return bench.read_game(m,s,next(p.glob('*.repl26a')),draft,win[-1] if win in ('teamA','teamB') else None)
with ThreadPoolExecutor(8) as ex: games=list(ex.map(read, [(m,s) for m in maps for s in 'ab']))
data=json.loads(Path('replays/fuel/f530/base-id.json').read_text())
data.update(fuel=0, games=games, all=bench.summary([t for g in games for t in bench.after_round1(g)]),round1=bench.summary([t for g in games for t in g['round1']]))
Path('replays/fuel/f530/base-dev.json').write_text(json.dumps(data,indent=1))
print(len(games), data['all'])
