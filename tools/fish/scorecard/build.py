"""Decode games for the Fish fidelity scorecard: manifests, caches and row files of a dataset.

  py tools/fish/scorecard/build.py local NAME --batch replays/.../batch-DIR [--bot-index 0] [--jobs 8]
  py tools/fish/scorecard/build.py fish [seventh fifth sixth] [--jobs 8]

local: one side of each game of a run_batched.py batch plays "Fish's role": bot --bot-index (0 = the
batch's bot 1, the default) or the bot whose directory name is --bot. Writes
replays/fish-scorecard/NAME/{dataset.json, A/, B/}; each side part holds its manifest, the actor
perspectives (tools/fish/extract.mjs), observer caches (tools/fish/team_decode.mjs, obs.mjs) and the rows
the metrics read (tools/fish/engage_rows.py, combat_data.py, combat_tiles.py), exactly as the Fish
cohorts' were built. Steps whose output exists are skipped, so an interrupted build resumes.
fish: the observer cache (obs.mjs) for pinned Fish cohorts; their other caches already exist.
"""
import argparse
import gzip
import hashlib
import json
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from common import FISH_DEFAULT, ROOT, fish_part, local_part, parts

FISH = Path(__file__).resolve().parent.parent


def run(cmd):
    t = time.time()
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    return time.time() - t


def chunks(seq, k):
    k = max(1, min(k, len(seq)))
    return [seq[i::k] for i in range(k)]


def local_manifest(name, batch, bot_index, bot_name):
    res = json.loads((Path(batch) / 'results.json').read_text())
    bots = [Path(b).name for b in res['bots']]
    if bot_name is not None:
        if bot_name not in bots:
            raise SystemExit(f'--bot {bot_name} is not in the batch: {bots}')
        bot_index = bots.index(bot_name)
    by_side = {0: [], 1: []}
    for m in res['matches']:
        if m.get('winner') is None or not m.get('replay') or not Path(m['replay']).exists():
            continue
        side = m['order'].index(bot_index)  # order[team] = bot index playing that team
        f = Path(m['replay'])
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        mp_ = Path(m['map']).stem
        by_side[side].append(dict(sha256=digest, file=str(f.resolve().relative_to(Path.cwd().resolve())) if f.resolve().is_relative_to(Path.cwd().resolve()) else str(f),
                                  map=mp_, side=side, group=mp_, match=f.name, opponent=bots[1 - bot_index],
                                  bot=bots[bot_index], winner_side=m['order'].index(m['winner']), rounds=m.get('rounds'),
                                  split='all', kind='local'))
    out = ROOT / name
    out.mkdir(parents=True, exist_ok=True)
    names = []
    for side, label in ((0, 'A'), (1, 'B')):
        es = by_side[side]
        if not es:
            continue
        seen = set(); uniq = []
        for e in es:
            if e['sha256'] not in seen:
                seen.add(e['sha256']); uniq.append(e)
        (out / label).mkdir(exist_ok=True)
        (out / label / 'manifest.json').write_text(json.dumps(uniq, indent=1) + '\n')
        names.append(label)
    meta = dict(name=name, batch=str(batch), bot=bots[bot_index], opponent=bots[1 - bot_index], bots=bots,
                bot_index=bot_index, parts=names, games={l: len(json.loads((out / l / 'manifest.json').read_text())) for l in names})
    (out / 'dataset.json').write_text(json.dumps(meta, indent=1) + '\n')
    print(f'{name}: {meta["bot"]} in Fish\'s role against {meta["opponent"]}; games per side {meta["games"]}', flush=True)


def _extract(args):
    manifest, out = args
    subprocess.run(['node', str(FISH / 'extract.mjs'), manifest, out, 'all'], check=True, stdout=subprocess.DEVNULL)


def _engage(job):
    import engage_rows
    return json.dumps(engage_rows.one(job), separators=(',', ':'))


def _combat(args):
    kind, name, manifest, cache, out = args
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        if kind == 'combat':
            import combat_data
            combat_data.main(name, manifest, cache, out)
        else:
            import combat_tiles
            combat_tiles.main(name, manifest, cache, out)


def build_part(p, jobs):
    es = json.loads(Path(p['manifest']).read_text())
    tmp = Path(p['manifest']).parent / 'tmp'
    tmp.mkdir(exist_ok=True)
    label = p['part']
    t0 = time.time()
    # 1. Actor perspectives, one extract.mjs per chunk (it is single-threaded).
    todo = [e for e in es if not (Path(p['actor']) / f"{e['sha256'][:16]}.json.gz").exists()]
    if todo:
        Path(p['actor']).mkdir(parents=True, exist_ok=True)
        ms = []
        for i, c in enumerate(chunks(todo, jobs)):
            m = tmp / f'extract-{i}.json'; m.write_text(json.dumps(c)); ms.append((str(m), p['actor']))
        with mp.Pool(len(ms)) as pool:
            pool.map(_extract, ms)
    print(f'  {label}: actor perspectives {time.time() - t0:.0f}s', flush=True)
    # 2. Observer caches.
    for tool, out in ((FISH / 'team_decode.mjs', p['team']), (FISH / 'scorecard' / 'obs.mjs', p['obs'])):
        if any(not (Path(out) / f"{e['sha256'][:16]}.json.gz").exists() for e in es):
            run(['node', str(tool), out, '--jobs', str(jobs), p['manifest']])
    print(f'  {label}: observer caches {time.time() - t0:.0f}s', flush=True)
    # 3. Rows, with the Fish studies' own builders.
    if not Path(p['engage']).exists():
        jobs_ = [(label, p['actor'], e, p['team']) for e in es]
        t = Path(p['engage'] + '.tmp')
        with gzip.open(t, 'wt') as f, mp.Pool(jobs) as pool:
            for line in pool.imap(_engage, jobs_, chunksize=2):
                f.write(line + '\n')
        t.rename(p['engage'])
    for kind in ('combat', 'tiles'):
        dest = Path(p[kind])
        if dest.exists():
            continue
        cs = chunks(es, jobs); args = []
        for i, c in enumerate(cs):
            m = tmp / f'{kind}-{i}.json'; m.write_text(json.dumps(c))
            o = tmp / f'{kind}-{i}.jsonl.gz'
            o.unlink(missing_ok=True)
            args.append((kind, label, str(m), p['actor'], str(o)))
        with mp.Pool(len(args)) as pool:
            pool.map(_combat, args)
        with open(str(dest) + '.tmp', 'wb') as f:  # concatenated gzip members read as one stream
            for _, _, _, _, o in args:
                f.write(Path(o).read_bytes())
        os.replace(str(dest) + '.tmp', dest)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f'  {label}: rows {time.time() - t0:.0f}s ({len(es)} games)', flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    a1 = sub.add_parser('local'); a1.add_argument('name'); a1.add_argument('--batch', required=True)
    a1.add_argument('--bot-index', type=int, default=0); a1.add_argument('--bot'); a1.add_argument('--jobs', type=int, default=8)
    a2 = sub.add_parser('fish'); a2.add_argument('cohorts', nargs='*', default=FISH_DEFAULT); a2.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    if a.cmd == 'local':
        if not (ROOT / a.name / 'dataset.json').exists():
            local_manifest(a.name, a.batch, a.bot_index, a.bot)
        for p in parts(a.name):
            build_part(p, a.jobs)
    else:
        for c in a.cohorts:
            p = fish_part(c)
            t = time.time()
            run(['node', str(FISH / 'scorecard' / 'obs.mjs'), p['obs'], '--jobs', str(a.jobs), p['manifest']])
            print(f'fish-{c}: observer cache {time.time() - t:.0f}s', flush=True)


if __name__ == '__main__':
    main()
