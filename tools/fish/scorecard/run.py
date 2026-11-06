"""One command: play CANDIDATE in Fish's role on the ladder maps, decode, score against Fish.

  py tools/fish/scorecard/run.py fish                                  # bots/fish vs the frozen astraeus
  py tools/fish/scorecard/run.py fish --name fish-r2 --opponent variants/astraeus-37e1eb6 --control control-ast37
  py tools/fish/scorecard/run.py fish --batch replays/fish-scorecard/batches/fish-r2   # reuse played games

Steps: tools/run_batched.py CANDIDATE OPPONENT on the 128 ladder maps (maps/*.map26a), both sides, on
the fast runner (into replays/fish-scorecard/batches/NAME; skipped with --batch or if it exists);
build.py local NAME (CANDIDATE's side of each game); metrics.py NAME; compare.py against the Fish
cohorts and the control dataset (default control-ast37: frozen astraeus in Fish's role in a mirror),
written to replays/fish-scorecard/NAME/scorecard.{md,json} or --out PREFIX. NAME defaults to the
candidate's directory name; a rerun after changing the bot needs a new --name (or delete the dataset).
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('candidate'); ap.add_argument('--opponent', default='variants/astraeus-37e1eb6')
    ap.add_argument('--name'); ap.add_argument('--batch'); ap.add_argument('--maps-dir')
    ap.add_argument('--control', default='control-ast37'); ap.add_argument('--fish', default='fish')
    ap.add_argument('--out'); ap.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    name = a.name or Path(a.candidate).name
    py = sys.executable
    t0 = time.time()
    batch = Path(a.batch) if a.batch else Path('replays/fish-scorecard/batches') / name
    if not (batch / 'results.json').exists():
        env = dict(os.environ, CAMBC_BIN=str(REPO / 'tools/fastengine/runner/fastrunner'), FASTRUNNER_MODE='native',
                   PATH=f"{Path.home() / '.cargo/bin'}:{os.environ['PATH']}")
        env.setdefault('CAMBC_SLOTS', '86')
        cmd = [py, 'tools/run_batched.py', a.candidate, a.opponent, '--output', str(batch)]
        if a.maps_dir:
            cmd += ['--maps-dir', a.maps_dir]
        print('playing:', ' '.join(cmd), flush=True)
        subprocess.run(cmd, check=True, env=env)
    print(f'games: {time.time() - t0:.0f}s', flush=True)
    subprocess.run([py, str(HERE / 'build.py'), 'local', name, '--batch', str(batch), '--jobs', str(a.jobs)], check=True)
    print(f'decoded: {time.time() - t0:.0f}s', flush=True)
    subprocess.run([py, str(HERE / 'metrics.py'), name, '--jobs', str(a.jobs)], check=True)
    out = a.out or f'replays/fish-scorecard/{name}/scorecard'
    cmd = [py, str(HERE / 'compare.py'), '--fish', a.fish, '--candidate', name, '--out', out, '--jobs', str(a.jobs)]
    if a.control and a.control != name:
        cmd += ['--control', a.control]
    subprocess.run(cmd, check=True)
    print(f'done in {time.time() - t0:.0f}s: {out}.md', flush=True)


if __name__ == '__main__':
    main()
