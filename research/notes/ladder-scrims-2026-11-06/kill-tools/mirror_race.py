"""mirror_race.py EXTRACT_DIR OUT.pkl: race-model samples for both teams of every extracted self-play game, with the
race agent's fog replica (load_live.load_game), so chanforensics.py can read each side's margin."""
import json, pickle, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, '/tmp/claude-1000/-home-ubuntu-cambc-autumn/3650a530-f591-417e-a0c5-31524a1e3260/scratchpad/race')
import load_live


def one(args):
    g = load_live.load_game(args)
    if g:
        g['replay'] = Path(args[0]).name
    return g


if __name__ == '__main__':
    ext, out = Path(sys.argv[1]), sys.argv[2]
    jobs = []
    for gd in sorted(p for p in ext.iterdir() if (p / 'meta.json').exists()):
        meta = json.load(open(gd / 'meta.json'))
        for t in (0, 1):
            jobs.append((str(gd), t, meta['result']['winner'] == t, ''))
    with ProcessPoolExecutor(32) as ex:
        games = [g for g in ex.map(one, jobs, chunksize=4) if g]
    pickle.dump(games, open(out, 'wb'))
    print(len(games), 'game sides')
