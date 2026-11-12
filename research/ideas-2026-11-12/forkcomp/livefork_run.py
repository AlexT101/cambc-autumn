"""Drive `fastrunner livefork` (a runner copy built with research/ideas-2026-11-12/forkcomp/livefork.rs) over live Mite games.

    python3 livefork_run.py OUT_DIR --exp live|local [--versions v111,v112] [--forks 100,300,600] [--shards 16]
        [--limit N] [--runner DIR]

live:  the live game (our release build vs the opponent puppet, tools/replay/harness), forked; arms: the puppet (the
       live continuation), the Mite body (two noise seeds), our own side cold-started, and two frozen charybdis
       versions swapped in for our side (calibration pair chy-life vs chy-519, +1.23 on 122,880 fresh-map gate games).
local: the same maps and sides, our release build vs the body from round 1 (body warm), forked; arms: the warm body
       going on, a fresh body with the same configuration, a fresh body with another noise seed.
Each shard runs under tools/pooled.py 1 (one CPU slot of the shared pool).
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path('/home/ubuntu/cambc-autumn')
NOISE0 = 1310000
BODY = 'variants/rt-Mt3q'


def body(k):
    return {'bot': BODY, 'seed': NOISE0 + k, 'salt': k, 'unmetered': True}


def lines(exp, versions, forks, limit):
    out = []
    for v in versions:
        val = {x['key']: x for x in json.load(open(ROOT / f'replays/{v}/runs/batch/validation.json'))}
        ws = f'replays/{v}/ws'
        for key, g in sorted(val.items()):
            if g['opponent'] != 'Mite' or not g['release']['exact']:
                continue
            ours = 0 if g['our_side'] == 'a' else 1
            opp = 1 - ours
            fk = [r for r in forks if r <= g['rounds'] - 30]
            if not fk:
                continue
            mp = f'{ws}/maps/{g["map"].replace("_", "-")}.map26a'
            rel = f'{ws}/bots/{v}-release'
            bots = [None, None]
            if exp == 'live':
                bots[ours], bots[opp] = rel, f'{ws}/bots/p-{key}'
                pup = [False, False]; pup[opp] = True
                arms = [{'label': 'puppet'},
                        {'label': 'body1', f't{opp}': body(1)},
                        {'label': 'body2', f't{opp}': body(2)},
                        {'label': 'cold+body1', f't{ours}': {'bot': rel}, f't{opp}': body(1)},
                        {'label': 'life+body1', f't{ours}': {'bot': 'variants/chy-life'}, f't{opp}': body(1)},
                        {'label': '519+body1', f't{ours}': {'bot': 'variants/chy-519'}, f't{opp}': body(1)},
                        {'label': 'life+body2', f't{ours}': {'bot': 'variants/chy-life'}, f't{opp}': body(2)},
                        {'label': '519+body2', f't{ours}': {'bot': 'variants/chy-519'}, f't{opp}': body(2)}]
            else:
                bots[ours], bots[opp] = rel, body(1)
                pup = [False, False]
                arms = [{'label': 'warm'},
                        {'label': 'cold-same', f't{opp}': body(1)},
                        {'label': 'cold-other', f't{opp}': body(2)}]
            out.append({'id': f'{v}:{key}', 'map': mp, 'bots': bots, 'puppet': pup, 'forks': fk, 'arms': arms, 'ours': ours,
                        'live': {'result': g.get('score'), 'rounds': g['rounds'], 'our_side': g['our_side']}})
    return out[:limit] if limit else out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--exp', default='live', choices=['live', 'local'])
    ap.add_argument('--versions', default='v111,v112')
    ap.add_argument('--forks', default='100,300,600')
    ap.add_argument('--shards', type=int, default=16)
    ap.add_argument('--limit', type=int)
    ap.add_argument('--runner', default=str(ROOT / 'replays/forkcomp/runner'))
    ap.add_argument('--arms', help='keep only these arm labels (comma list)')
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    gl = lines(a.exp, a.versions.split(','), [int(x) for x in a.forks.split(',')], a.limit)
    if a.arms:
        keep = set(a.arms.split(','))
        for g in gl:
            g['arms'] = [x for x in g['arms'] if x['label'] in keep]
    env = dict(os.environ, FASTRUNNER_LIB=f'{a.runner}/target/release/libfastrunner.so', FASTRUNNER_ENGINE='wasm',
               FASTRUNNER_MODE='native', FASTRUNNER_BUILT='1')
    exe = f'{a.runner}/fastrunner'
    # Warm the compile cache: one game per version first, alone.
    seen, warm, rest = set(), [], []
    for g in gl:
        v = g['id'].split(':')[0]
        (warm if v not in seen else rest).append(g); seen.add(v)
    shards = [warm] + [rest[i::a.shards] for i in range(a.shards)]
    t0 = time.time()
    procs = []
    for i, sh in enumerate(shards):
        if not sh:
            continue
        gf = out / f'games-{i:02d}.jsonl'
        gf.write_text(''.join(json.dumps(g) + '\n' for g in sh))
        cmd = ['python3', str(ROOT / 'tools/pooled.py'), '1', '--', exe, 'livefork', '--games', str(gf), '--out', str(out / f'out-{i:02d}.jsonl')]
        log = open(out / f'log-{i:02d}.txt', 'w')
        p = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
        if i == 0:
            p.wait()
            print(f'warm-up done {time.time() - t0:.0f}s', flush=True)
        else:
            procs.append(p)
    for p in procs:
        p.wait()
    with open(out / 'out.jsonl', 'w') as f:
        for i in range(len(shards)):
            p = out / f'out-{i:02d}.jsonl'
            if p.exists():
                f.write(p.read_text())
    (out / 'DONE').write_text(f'{len(gl)} games {time.time() - t0:.0f}s\n')
    print(f'{len(gl)} games in {time.time() - t0:.0f}s -> {out}/out.jsonl')


if __name__ == '__main__':
    main()
