"""The fresh-map gate in large batches (the default mode of tools/fgate.py).

    py tools/fgate.py CAND REF [--batch-maps 2560] [--max-batches N] [--fuel N] [--screen] [--zone-stop] [--ci 0.25]

CAND and REF (bot dirs under bots/, test_draft off) each play the synthetic Fish and Mite bodies on the same fresh
ladder-v2 maps, both sides. A batch is --batch-maps maps the gate has not played yet plus the 128 ladder maps:
(2560 + 128) x 2 sides x 2 bodies x 2 bots = 21,504 games in four ab.py runs (each nine suites side by side). REF's runs are cached by name and
serve every candidate, so a changed bot needs a new dir.

- Opponents: one compiled body per version (variants/rt-Flp4, rt-Mt3q: the spar-dvnK body with its noise seed and
  draft salt read at run time), so no batch compiles an opponent. Every fresh map has its own noise seed (pool
  index i plays noise i + 1); batch j's ladder maps play noise j + 1. The bodies run unmetered; CAND and REF keep
  the exact fuel budget (--fuel N, default 100k a turn). Only a body carrying the run-time import can be unmetered.
- A unit is a map: 0.5 + CAND's mean minus REF's over its four paired games. Decisions read the fresh units only,
  after each batch: REJECT (low SPRT 0.4975/0.50 at H0), ACCEPT (high SPRT 0.505/0.5075 at H1; the gate plays on to
  the LIVE BAR, ln 99, on maps the screen never saw, unless --screen), ZONE (low H1 and high H0: judgement),
  NARROWED (95% CI half-width <= --ci points). The ladder maps are a side read.
- Size: a unit's standard deviation is about 27 points, so a batch narrows the fresh read to about +-1.05 points,
  4 batches to +-0.52, 16 to +-0.26. A +2 point change reaches ACCEPT in about 3 batches, +1.5 in 4, +1 in 9; a
  1 point loss reaches REJECT in about 4; a change within a quarter point of zero runs to NARROWED, about 18.
  --max-batches caps the gate, --batch-maps sets the step, and `--max-batches N --ci 0` is a fixed read of at most
  N batches. The pool (FGATE_HOME/pool, 97,535 maps) holds 38 default batches; every gate walks it from batch 0
  unless --first-batch J starts later, on maps earlier gates have not played (a held-out confirmation).
- Ladder side read: the 128 ladder maps pinned in tools/ladder128.txt, whatever else maps/ holds (it has 170 from
  2026-11-12). --ladder all plays every map under maps/ instead, under its own opponent configs and run names
  (suffix -Lall), so REF's cached 128 runs are never reused for it or mixed with it.
- Results: gate-logs/fgate-<cand>--<ref><bodies><fuel>[-Lall]-batch.json, and a "Results against <ref>" table.
"""
import argparse, fcntl, hashlib, importlib.util, json, math, os, random, re, subprocess, sys, time
from pathlib import Path
import numpy as np
import ladder_set

ROOT = Path(__file__).resolve().parents[1]
HOME = Path(os.environ.get('FGATE_HOME', os.path.expanduser('~/tmp-offload/gatebatch')))
# The runner library with run-time opponent configuration, built beside the shared one so jobs on that are untouched:
# cd tools/fastengine/runner && CARGO_TARGET_DIR=target-rt cargo build --release
LIB = Path(os.environ.get('FGATE_RUNNER_LIB', ROOT / 'tools/fastengine/runner/target-rt/release/libfastrunner.so'))
NOISE0 = 1310000  # dgate's noise member k is seed NOISE0 + k with draft salt k
PART = 320       # maps a suite (see suite())
# The ladder side read: the pinned 128 maps (default; every run before 2026-11-12) or all maps under maps/ (--ladder all).
# A set other than the 128 has its own opponent config and run names, so its REF runs never mix with the 128's.
LADDER = '128'
TIMEOUT = 600     # seconds a game; an unmetered body cannot run out of fuel, so only this stops a hung one
LO, SCREEN, LIVE = math.log(0.05 / 0.95), math.log(0.95 / 0.05), math.log(99)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def bot_dir(bot):
    """A bot argument as ab.py resolves it: a name under bots/, or a path."""
    return next((p for p in (ROOT / 'bots' / bot, Path(bot)) if (p / 'src').is_dir()), Path(bot))


def read_summary(n):
    try: return json.loads((ROOT / f'replays/ab/{n}/summary.json').read_text())
    except (OSError, ValueError): return None


# run_batched.py prints "Bot 1: DIR" and "  as .../replays/frozen/<hash>/<name>" into each suite's log.
PLAYED = re.compile(r'^Bot 1: .*\n\s+as \S*/replays/frozen/([0-9a-f]{12})/', re.M)
_played, _now, _unrecorded = {}, {}, set()


def source_now(bot):
    import run_batched
    if bot not in _now: _now[bot] = run_batched.source_hash(bot_dir(bot))
    return _now[bot]


def played(n, x):
    """The frozen copies (hashes) of bot 1 that run n played: its summary's record, or for a run from before ab.py
    kept one, the copies its suite logs name, which are what it played."""
    if x['cand'].get('frozen'): return set(x['cand']['frozen'])
    key = (n, x.get('started'))
    if key not in _played:
        found = set()
        for su in x.get('suites', []):
            try: m = PLAYED.search((ROOT / su['log']).read_text(errors='replace'))
            except OSError: continue
            if m: found.add(m.group(1))
        _played[key] = found
    return _played[key]


def check_source(n, x, bot):
    """Stop the gate on a cached run of `bot` (bot 1 of run n, summary x) that played other source than bot's now."""
    p = played(n, x)
    if not p:
        if n not in _unrecorded:
            _unrecorded.add(n); print(f'note: {n} records no source and its logs are gone; reused unchecked', flush=True)
        return
    if p != {source_now(bot)}:
        raise SystemExit(f'{n} played {bot} as replays/frozen/{"+".join(sorted(p))}, but its source (or sdk/cpp) now hashes '
                         f'to {source_now(bot)}: give the changed bot a new dir, or delete replays/ab/{n} to replay it')


def adopt(fg, rel):
    """bots/REL here, copied from the checkout the gate's bodies are built in (dgate's R, the primary one) when only
    that has it: the build markers are shared by every tree, so a worktree never builds a body itself."""
    import run_batched, shutil
    dst, src = ROOT / 'bots' / rel, Path(fg.dgate.R) / 'bots' / rel
    if dst.is_dir() or not src.is_dir() or src.resolve() == dst.resolve(): return
    staging = dst.parent / f'.{dst.name}-{os.getpid()}'
    shutil.copytree(src, staging, ignore=lambda d, names: run_batched.BUILD_OUTPUT & set(names) if Path(d) == src else ())
    try: staging.rename(dst)
    except OSError: shutil.rmtree(staging, ignore_errors=True)  # another gate adopted it first


def pool():
    return json.loads((HOME / 'pool/index.json').read_text())['maps']


def ladder():
    return ladder_set.names(LADDER)


def ladder_tag():
    return '' if LADDER == '128' else f'-L{LADDER}'


def grow(dirs, seeds):
    """Append the maps under dirs to the pool, after the ones it has (so batches already played keep their maps):
    byte-new against the pool and the ladder, one per layout key, in a seeded order."""
    import shutil, tempfile
    path = HOME / 'pool/index.json'; idx = json.loads(path.read_text())
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    seen = {sha(p) for p in [*(HOME / 'pool/maps').iterdir(), *(ROOT / 'maps').glob('*.map26a')]}
    names, keys = {n for n, _ in idx['maps']}, set(idx['keys'])
    with tempfile.TemporaryDirectory(dir=HOME) as td:
        subprocess.run(['node', str(ROOT / 'tools/draftlab/features.mjs'), *dirs, '--out', f'{td}/f.jsonl'], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        rows = [json.loads(line) for line in open(f'{td}/f.jsonl')]
    new = []
    for r in sorted(rows, key=lambda r: r['name']):
        src = ROOT / r['path'] if not os.path.isabs(r['path']) else Path(r['path'])
        h = sha(src)
        if r['name'] in names or r['key'] in keys or h in seen: continue
        names.add(r['name']); keys.add(r['key']); seen.add(h)
        shutil.copyfile(src, HOME / f'pool/maps/{r["name"]}.map26a')
        f = r['f']
        new.append(([r['name'], int(f['altars'] == 1 or (f['altars'] == 2 and (f.get('altar_centre') or 0) < 0.06))], r['key']))
    random.Random(len(idx['maps'])).shuffle(new)
    idx['maps'] += [m for m, _ in new]; idx['keys'] += [k for _, k in new]
    idx['tranches'].append({'maps': len(new), 'seeds': seeds, 'added': time.strftime('%Y-%m-%d')})
    tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(idx)); tmp.rename(path)
    print(f'{len(new)} of {len(rows)} maps added; the pool holds {len(idx["maps"])}')


def suite(maps, n, j):
    """Batch j of n maps: its suite dir (links into the pool) and its opponent config. None past the pool's last
    whole batch, so a batch never changes when the pool grows."""
    rows = maps[j * n:(j + 1) * n]
    if len(rows) < n: return None
    base = HOME / f'suites/m{n}'; d = base / f'b{j:03d}'; cfg = base / f'b{j:03d}{ladder_tag()}.json'
    if not cfg.exists():
        base.mkdir(parents=True, exist_ok=True)
        with open(base / 'lock', 'w') as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            if not cfg.exists():
                d.mkdir(exist_ok=True)
                for name, _ in rows:
                    if not (d / f'{name}.map26a').exists(): os.symlink(HOME / f'pool/maps/{name}.map26a', d / f'{name}.map26a')
                noise = {name: j * n + i + 1 for i, (name, _) in enumerate(rows)}
                noise.update({name: j + 1 for name in ladder()})
                tmp = base / f'b{j:03d}{ladder_tag()}.json.tmp'
                tmp.write_text(json.dumps({'schema': 1, 'opponent_index': 1, 'maps': {
                    name: {'seed': NOISE0 + k, 'salt': k, 'unmetered': True} for name, k in noise.items()}}))
                tmp.rename(cfg)
    # run_batched.py handles finished games one at a time (it saves each pruned replay's fuel counts with an fsync):
    # about 30 games a second a suite, so one suite a run leaves most of the machine idle. A run plays the batch as
    # PART-map suites side by side.
    parts = [base / f'b{j:03d}.parts/p{k}' for k in range(-(-len(rows) // PART))]
    if not parts[-1].is_dir():
        with open(base / 'lock', 'w') as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            for k, part in enumerate(parts):
                part.mkdir(parents=True, exist_ok=True)
                for name, _ in rows[k * PART:(k + 1) * PART]:
                    if not (part / f'{name}.map26a').exists(): os.symlink(HOME / f'pool/maps/{name}.map26a', part / f'{name}.map26a')
    return {'suites': ','.join(map(str, parts)) + (',ladder' if LADDER == '128' else f',ladder-{LADDER}'), 'config': cfg, 'sha': hashlib.sha256(cfg.read_bytes()).hexdigest(),
            'maps': dict(rows), 'games': 2 * (len(rows) + len(ladder()))}


def body(fg, version):
    """variants/rt-<version>: noise body 1 of that version with its seed and salt read at run time. Built once."""
    name = f'variants/rt-{version}'; dst = ROOT / 'bots' / name; mark = Path(fg.LOCKS) / f'built-rt-{version}'
    adopt(fg, name)
    if mark.exists() and dst.is_dir(): return name
    os.makedirs(fg.LOCKS, exist_ok=True)
    with open(Path(fg.LOCKS) / f'build-rt-{version}', 'w') as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        if not (mark.exists() and dst.is_dir()):
            fg.build_seed(1); fg.build_body(1, version)  # in fg.R, where the shared markers say they are
            rb = load('fgate_runtime_body', ROOT / 'research/ideas-2026-11-11/conditional-batch506/runtime_body.py')
            if dst.exists(): raise SystemExit(f'{dst} exists without its marker {mark}: remove it and rerun')
            rb.prepare(Path(fg.R) / f'bots/variants/spar-dvn1-{version}', dst)
            mark.touch()
    return name


def est(u):
    u = np.array(u) - 0.5
    return [round(100 * u.mean(), 3), round(196 * u.std() / math.sqrt(len(u)), 3)] if len(u) > 1 else None


class Sequential:
    """The three-way decision over the fresh units, read once a batch."""
    def __init__(self, llr, sprt=(0.505, 0.5075), low=(0.4975, 0.50), ci=0.25, min_batches=1, zone_stop=False, screen=False):
        self.llr, self.sprt, self.low, self.ci, self.min_batches = llr, sprt, low, ci, min_batches
        self.zone_stop, self.screen = zone_stop, screen
        self.units, self.batches = [], 0
        self.screen_at = self.low_at = self.high_h0_at = self.zone_at = None
        self.notes = []

    def add(self, units, flips=None):
        """Add a batch's units; the outcome that ends the gate, or None to play on."""
        self.units += units; self.batches += 1; n = len(self.units)
        hl, ll = self.llr(self.units, *self.sprt), self.llr(self.units, *self.low)
        d = np.array(self.units) - 0.5; se = d.std() / math.sqrt(n)
        self.hl, self.ll, self.mean, self.half = hl, ll, 100 * d.mean(), 196 * se
        # No paired game differs: the bots play alike here, and more maps of nothing decide nothing.
        if flips == 0 and not d.any(): return 'IDENTICAL (no paired game differs)'
        if self.screen_at is None and ll <= LO: return 'REJECT'
        if self.low_at is None and ll >= SCREEN: self.low_at = n
        if self.high_h0_at is None and self.screen_at is None and hl <= LO: self.high_h0_at = n
        if self.zone_at is None and self.low_at is not None and self.high_h0_at is not None:
            self.zone_at = n; self.notes.append(f'ZONE at batch {self.batches}')
            if self.zone_stop: return 'ZONE'
        if self.ci > 0 and self.screen_at is None and self.batches >= self.min_batches and 196 * se <= self.ci:
            return 'NARROWED' + (' (ZONE crossed)' if self.zone_at else '')
        if self.screen_at is None and self.high_h0_at is None and hl >= SCREEN:
            self.screen_at = n; self.notes.append(f'ACCEPT (screen H1) at batch {self.batches}')
            return 'ACCEPT (screen H1)' if self.screen else None
        # The live bar is read on maps the screen never saw, so never in the screen's own batch.
        if self.screen_at is not None and n > self.screen_at and hl >= LIVE:
            return 'LIVE BAR H1' if d[self.screen_at:].mean() >= 0 else 'H1 but the post-screen batches read negative: not live'
        return None

    def final(self):
        return 'ACCEPT (screen), live bar undecided' if self.screen_at is not None else 'undecided'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog='The 256-game noise blocks this replaced: py tools/fgate.py --blocks CAND REF [its options].')
    ap.add_argument('cand'); ap.add_argument('ref')
    ap.add_argument('--batch-maps', type=int, default=2560, help='fresh maps a batch (default 2560: 21,504 games with the ladder maps, half of them REF\'s)')
    ap.add_argument('--max-batches', type=int, default=10**6, help='stop after this many batches (default: the whole pool)')
    ap.add_argument('--first-batch', type=int, default=0, help='start at this pool batch (from 0): a later one is maps no gate from the start has played')
    ap.add_argument('--fuel', type=int, help='fuel a turn for CAND and REF (default 100k); the bodies are unmetered either way')
    ap.add_argument('--screen', action='store_true', help='stop at ACCEPT instead of playing on to the live bar')
    ap.add_argument('--zone-stop', action='store_true', help='stop at a ZONE crossing')
    ap.add_argument('--ci', type=float, default=0.25, help='NARROWED once the fresh 95%% CI half-width is this many points; 0 disables')
    ap.add_argument('--min-batches', type=int, default=1, help='batches before NARROWED can stop')
    ap.add_argument('--sprt', default='0.505,0.5075'); ap.add_argument('--low', default='0.4975,0.50')
    ap.add_argument('--seed', type=int, default=0, help='orders the units within a batch')
    ap.add_argument('--jobs', type=int, default=4, help='ab.py runs at once (a batch is four)')
    ap.add_argument('--ahead', type=int, default=0, help='batches started before the one being read has decided')
    ap.add_argument('--no-run', action='store_true', help='decide from finished runs only')
    ap.add_argument('--fish-body', default='Flp4'); ap.add_argument('--mite-body', default='Mt3q')
    ap.add_argument('--ladder', choices=('128', 'all'), default='128',
                    help='the ladder side read: the pinned 128 maps (default, comparable with every earlier gate) or all maps '
                    'under maps/ (its own opponent configs and run names, so REF plays it afresh)')
    a = ap.parse_args(argv)
    global LADDER
    LADDER = a.ladder
    if a.fuel is not None and a.fuel <= 0: ap.error('--fuel must be positive')
    if a.batch_maps <= 0 or a.first_batch < 0: ap.error('--batch-maps must be positive and --first-batch not negative')
    if not a.no_run and not LIB.is_file():
        ap.error(f'{LIB} is not built: cd tools/fastengine/runner && CARGO_TARGET_DIR=target-rt cargo build --release')
    os.environ.setdefault('CAMBC_BIN', str(ROOT / 'tools/fastengine/runner/fastrunner'))
    os.environ.setdefault('FASTRUNNER_MODE', 'native')
    fg = load('fgate_blocks', ROOT / 'research/ideas-2026-11-09/freshgate-tools/fgate.py')
    # local.R names the primary checkout; in a worktree, read the cells from the summaries this tree's ab.py writes.
    fg.local.R = f'{ROOT}/'
    import ab
    td = [ab.test_draft_of(bot_dir(b)) for b in (a.cand, a.ref)]
    if td[0] != td[1]:
        ap.error(f'test_draft differs (CAND {td[0]}, REF {td[1]}): a paired gate needs both bots on the same draft')
    for v, known in ((a.fish_body, ['Flp'] + fg.FISH_PATCHES), (a.mite_body, ['Mt3p'] + fg.MITE_PATCHES)):
        if v not in known: ap.error(f'unknown body {v}: one of {", ".join(known)}')
    bodies = {'F': a.fish_body, 'M': a.mite_body}
    fuel = ('' if a.fuel is None else f'-fuel{a.fuel}') + ladder_tag()
    maps, lad = pool(), set(ladder())
    opp = {o: f'variants/rt-{v}' for o, v in bodies.items()} if a.no_run else {o: body(fg, v) for o, v in bodies.items()}

    def rname(bot, o, j):
        return f'fb{fg.ENG}-{os.path.basename(bot.rstrip("/")).removeprefix("oc-")}-{bodies[o]}-m{a.batch_maps}b{j:03d}{fuel}'

    summary = read_summary

    def done(n, s, bot):
        x = summary(n)
        if not (x is not None and x['games'] + x['errors'] >= s['games'] and x.get('release') is True and x.get('cambc') == fg.CAMBC
                and x.get('fuel') == a.fuel and (x.get('experiment_config') or {}).get('sha256') == s['sha']): return False
        # Runs are cached by name, which a bot dir edited in place keeps.
        check_source(n, x, bot)
        return True

    class Runner(fg.dgate.Runner):
        def want(self, bot, o, j, s):
            n = rname(bot, o, j)
            if done(n, s, bot): return True
            self.poll()
            if n in self.procs or len(self.procs) >= self.jobs or fg.dgate.running_elsewhere(n): return False
            # A run that ends without a complete summary is retried once, not forever.
            if self.tries.get(n, 0) >= 2: raise SystemExit(f'{n} failed twice (log {fg.LOGS}/{n}.log)')
            import run_batched
            if run_batched.source_hash(bot_dir(bot)) != source_now(bot):
                raise SystemExit(f'{bot} changed during the gate: its runs so far played other source')
            lock = f'{fg.LOCKS}/{n}'
            try: os.close(os.open(lock, os.O_CREAT | os.O_EXCL))
            except FileExistsError:
                # Nothing runs it (checked above): a lock older than a launch takes is a killed gate's.
                if time.time() - os.path.getmtime(lock) < 60: return False
                os.unlink(lock); os.close(os.open(lock, os.O_CREAT | os.O_EXCL))
            cmd = [sys.executable, str(ROOT / 'tools/ab.py'), bot, opp[o], '--no-test-draft', '--suites', s['suites'],
                   '--name', n, '--keep-replays', '1', '--experiment-config', str(s['config']), '--game-timeout', str(TIMEOUT)]
            if a.fuel is not None: cmd += ['--fuel', str(a.fuel)]
            self.procs[n] = (subprocess.Popen(cmd, cwd=ROOT, env=self.env, stdout=open(f'{fg.LOGS}/{n}.log', 'w'),
                                              stderr=subprocess.STDOUT), lock)
            self.started += s['games']; self.tries[n] = self.tries.get(n, 0) + 1
            return False

    run = Runner(a.jobs); run.started = 0; run.tries = {}
    run.env = dict(run.env, FASTRUNNER_LIB=str(LIB))
    seq = Sequential(fg.ab.llr, tuple(map(float, a.sprt.split(','))), tuple(map(float, a.low.split(','))), a.ci,
                     a.min_batches, a.zone_stop, a.screen)
    U = {'fresh': {g: [] for g in ('all', 'F', 'M', 'one', 'multi')}, 'L': {g: [] for g in ('all', 'F', 'M')}}
    wins = {'cand': [], 'ref': []}; errors = early = games = 0
    outcome = None; j = a.first_batch; last = a.first_batch + a.max_batches - 1; began = time.time()
    while j <= last and (s := suite(maps, a.batch_maps, j)):
        if not a.no_run:
            for jj in range(j, min(j + a.ahead, last) + 1):
                if ss := suite(maps, a.batch_maps, jj):
                    for o in 'FM':
                        for bot in (a.ref, a.cand): run.want(bot, o, jj, ss)
        names = [rname(bot, o, j) for o in 'FM' for bot in (a.cand, a.ref)]
        if not all(done(rname(bot, o, j), s, bot) for o in 'FM' for bot in (a.cand, a.ref)):
            if a.no_run: break
            time.sleep(2); continue
        diff, flips = {'fresh': {}, 'L': {}}, 0
        for o in 'FM':
            x, y = fg.local.cells(rname(a.cand, o, j)), fg.local.cells(rname(a.ref, o, j))
            for c in x.keys() & y.keys():
                key = 'L' if c[0] in lad else 'fresh'
                diff[key].setdefault(c[0], {}).setdefault(o, []).append(x[c] - y[c]); flips += x[c] != y[c]
                if key == 'fresh': wins['cand'].append(x[c]); wins['ref'].append(y[c])
        for n in names:
            x = summary(n); errors += x['errors']; games += x['games']
            early += sum(x.get('early_losses', {}).values())
        rng = random.Random(a.seed * 1000 + j + 1)
        for key in ('fresh', 'L'):
            order = sorted(diff[key]); rng.shuffle(order)
            for m in order:
                v = [d for o in diff[key][m] for d in diff[key][m][o]]
                U[key]['all'].append(0.5 + float(np.mean(v)))
                for o in diff[key][m]: U[key][o].append(0.5 + float(np.mean(diff[key][m][o])))
                cls = s['maps'].get(m) if key == 'fresh' else None
                if cls is not None: U[key]['one' if cls else 'multi'].append(0.5 + float(np.mean(v)))
        before = len(seq.notes)
        outcome = seq.add(U['fresh']['all'][len(seq.units):], flips)
        rd = lambda u: f'{100 * (np.mean(u) - 0.5):+.2f}' if u else 'n/a'
        print(f'batch {j + 1:2d}: fresh {len(seq.units)} maps {seq.mean:+.2f} ±{seq.half:.2f} LLR high {seq.hl:+.2f} low {seq.ll:+.2f} '
              f'[{LO:.2f} | {SCREEN:.2f} | live {LIVE:.2f}] | ladder {rd(U["L"]["all"])} | fresh F {rd(U["fresh"]["F"])} '
              f'M {rd(U["fresh"]["M"])} one {rd(U["fresh"]["one"])} multi {rd(U["fresh"]["multi"])} | {flips} games differ', flush=True)
        for note in seq.notes[before:]: print(note, flush=True)
        j += 1
        if outcome: break
    while run.procs: run.poll(); time.sleep(5)
    if outcome is None: outcome = seq.final()
    wall = time.time() - began
    res = {'cand': a.cand, 'ref': a.ref, 'outcome': outcome, 'mode': 'batch', 'batches': seq.batches, 'batch_maps': a.batch_maps, 'first_batch': a.first_batch,
           'cambc': fg.CAMBC, 'fuel': a.fuel, 'bodies': f'run-time, unmetered ({bodies["F"]}/{bodies["M"]})',
           'fresh': est(U['fresh']['all']), 'ladder': est(U['L']['all']), 'fresh_fish': est(U['fresh']['F']), 'fresh_mite': est(U['fresh']['M']),
           'fresh_one_site': est(U['fresh']['one']), 'fresh_multi_site': est(U['fresh']['multi']),
           'ladder_fish': est(U['L']['F']), 'ladder_mite': est(U['L']['M']), 'fresh_units': len(seq.units),
           'llr_high': round(seq.hl, 3) if seq.units else None, 'llr_low': round(seq.ll, 3) if seq.units else None,
           'zone_at_units': seq.zone_at, 'screen_at_units': seq.screen_at, 'low_h1_at_units': seq.low_at, 'high_h0_at_units': seq.high_h0_at,
           'cand_win_pct': round(100 * float(np.mean(wins['cand'])), 2) if wins['cand'] else None,
           'ref_win_pct': round(100 * float(np.mean(wins['ref'])), 2) if wins['ref'] else None,
           'games': games, 'errors': errors, 'early_losses': early, 'wall_seconds': round(wall, 1), 'games_started': run.started}
    ef, el = est(U['fresh']['all']), est(U['L']['all'])
    # The ladder and fresh units are different maps: an unpaired difference.
    res['ladder_minus_fresh'] = [round(el[0] - ef[0], 3), round(math.hypot(el[1], ef[1]), 3)] if ef and el else None
    print(json.dumps(res))
    base = os.path.basename(a.ref.rstrip('/'))
    print(f'\nResults against {base} ({os.path.basename(a.cand.rstrip("/"))}; bodies {bodies["F"]}/{bodies["M"]} unmetered, '
          f'our fuel {a.fuel or 100000}, {seq.batches} batch{"es" if seq.batches != 1 else ""}):')
    print('| read | win% (95% CI) | maps | games |\n|---|---|---|---|')
    for label, u, per in (('fresh (decides)', U['fresh']['all'], 8), ('fresh, Fish', U['fresh']['F'], 4), ('fresh, Mite', U['fresh']['M'], 4),
                          ('fresh, one-site', U['fresh']['one'], 8), ('fresh, multi-site', U['fresh']['multi'], 8),
                          ('ladder (side read)', U['L']['all'], 8)):
        e = est(u)
        if e: print(f'| {label} | {50 + e[0]:.2f}% ({50 + e[0] - e[1]:.2f}-{50 + e[0] + e[1]:.2f}) | {len(u):,} | {per * len(u):,} |')
    if res['ladder_minus_fresh']: print('Ladder minus fresh: {:+.2f} ±{:.2f} points.'.format(*res['ladder_minus_fresh']))
    if seq.units:
        print(f'{outcome}. LLR high {seq.hl:+.2f}, low {seq.ll:+.2f} [{LO:.2f} | {SCREEN:.2f} | live {LIVE:.2f}]. Against the bodies: CAND '
              f'{res["cand_win_pct"]}%, REF {res["ref_win_pct"]}%. Failed games {errors}, lost by round 5 {early}.')
    if run.started: print(f'{run.started:,} games started here in {wall / 60:.1f} min ({3600 * run.started / wall:,.0f} games/h).')
    if not a.no_run and seq.units:
        tag = ''.join(v.removeprefix('Fl').removeprefix('Mt3') for v in bodies.values() if v not in ('Flp', 'Mt3p'))
        size = ('' if a.batch_maps == 2560 else f'-m{a.batch_maps}') + (f'-b{a.first_batch}' if a.first_batch else '')
        json.dump(res, open(f'{fg.LOGS}/fgate-{os.path.basename(a.cand.rstrip("/"))}--{base}{tag}{fuel}{size}-batch.json', 'w'))


if __name__ == '__main__':
    if sys.argv[1:2] == ['grow']:  # py tools/fgate_batch.py grow SEEDS DIR...: add generated maps to the pool
        grow(sys.argv[3:], sys.argv[2])
    else:
        main()
