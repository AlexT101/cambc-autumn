"""Builds a replay book into a bot copy from our live wins (games.jsonl), re-running each game locally to prove it
reproduces and to record the fingerprints the book checks.

    py rbuild.py --host variants/rbook-525 [--opp "Intercontinental Fish:r8" --opp Mite:r9] [--versions 117,118,119]
                 [--host-version 119] [--extra EXTRA.tsv] [--work ~/tmp-offload/rbook/fish] [--jobs 32] [--cells CELLS] [--cap N]
    py rbuild.py --host DIR --work WORK --verify-only     (another build of a book made in WORK, e.g. a masked copy)

--opp NAME:REFSET, repeatable: one book over several opponents; each is selected, recorded and verified against its
own puppet, and the bot holds them all (where two opponents pick alike on a cell, the first --opp's entry is kept).

Steps (each cached under --work by game key, so a rerun after new games only does the new ones):
  1. select: per (map, side), one winning game of ours (the shortest), from --versions against --opp/--refset;
     cells the host's own live version (--host-version) won are left out: the host plays them the same way unaided
     (with --host-repro, only those hostcheck.py found the host build replays exactly).
     --extra adds lines "REPLAY(.zip|.repl26a) OUR_SIDE KEY MAP" (e.g. other teams' wins).
  2. extract (extract.mjs): both teams' turns, picks, map id.
  3. record: build HOST-rec (our turns, record mode) and HOST-pup (the opponent's turns, puppet mode), play each game
     between them on the fast runner, keep the games whose every round state matches the live replay (cmp.mjs), and
     read the fingerprints from our stdout.
  4. book: write HOST/src/book/book_data.h (play mode) with the reproduced games (--cells/--cap: the strength dial, see
     build_book.py), build it, verify the shipped bot reproduces each kept game, and report the bundle size.
"""
import argparse, collections, concurrent.futures as cf, json, os, re, shutil, subprocess, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
GAMES = ROOT / 'research/ladder-scrims-2026-11-06/data/games.jsonl'
MAP_DIRS = [ROOT / 'maps', ROOT / 'replays/v118/ws/maps']
FAST = ROOT / 'tools/fastengine/runner/fastrunner'
sys.path.insert(0, str(ROOT / 'tools'))
import cpu_slots  # noqa: E402


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def map_path(name):
    for d in MAP_DIRS:
        for n in (name, name.replace('_', '-')):
            if (d / f'{n}.map26a').exists():
                return d / f'{n}.map26a'
    raise FileNotFoundError(name)


def opponents(a):
    """[(name prefix, refset, tag)] from --opp NAME:REFSET (NAME alone takes --refset)."""
    out = []
    for o in a.opp or ['Intercontinental Fish']:
        name, _, ref = o.partition(':')
        out.append((name, ref or a.refset, name.split()[-1].lower()))
    return out


def select(a, opp, refset, tag):
    versions = {int(v) for v in a.versions.split(',')}
    cells = collections.defaultdict(list)
    host_won = set()
    for line in open(GAMES):
        g = json.loads(line)
        if g.get('status') != 'finished' or not g['opp_name'].startswith(opp) or g.get('refset') != refset:
            continue
        cell = (g['map'], g['side'])
        if a.host_version and g['version'] == a.host_version and g['result'] == 'win':
            host_won.add(cell)
        if g['version'] in versions and g['result'] == 'win' and g.get('replay') and (ROOT / g['replay']).exists():
            cells[cell].append(g)
    repro = None
    if getattr(a, 'host_repro', None):
        repro = set()
        for f in a.host_repro.split(','):
            for l in Path(f).expanduser().read_text().splitlines():
                p = l.split()
                if len(p) >= 2 and (len(p) < 3 or p[2] == tag):
                    repro.add((p[0], p[1]))
    chosen = []
    for cell, gs in sorted(cells.items()):
        if cell in host_won and (repro is None or cell in repro):
            continue
        g = min(gs, key=lambda x: (x['rounds'], -x['version']))
        chosen.append(dict(key=f"{g['map']}-{g['side']}-v{g['version']}-{g['match'][-12:]}", replay=str(ROOT / g['replay']), side=g['side'],
                           map=g['map'], version=g['version'], rounds=g['rounds'], opp=tag))
    if a.extra and tag == opponents(a)[0][2]:
        for line in open(a.extra):
            if line.strip() and not line.startswith('#'):
                rep, side, key, mp = line.split()[:4]
                if (mp, side) not in {(c['map'], c['side']) for c in chosen} and (mp, side) not in host_won:
                    v = re.match(r'^.+-[ab]-v(\d+)-', key)
                    chosen.append(dict(key=key, replay=rep, side=side, map=mp, version=int(v.group(1)) if v else None, rounds=None, opp=tag))
    left = host_won if repro is None else host_won & repro
    log(f'select {tag} {refset}: {len(chosen)} cells ({len(left)} of its {len(host_won)} live wins left to the host)')
    return chosen


def raw_replay(src, dst):
    if dst.exists():
        return dst
    if src.endswith('.zip'):
        with zipfile.ZipFile(src) as z:
            n = [x for x in z.namelist() if x.endswith('.repl26a')][0]
            dst.write_bytes(z.read(n))
    else:
        shutil.copyfile(src, dst)
    return dst


def extract_all(chosen, work, jobs):
    (work / 'raw').mkdir(parents=True, exist_ok=True)
    (work / 'ent').mkdir(exist_ok=True)

    def one(c):
        out = work / 'ent' / f"{c['key']}.json"
        if out.exists():
            return out
        raw = raw_replay(c['replay'], work / 'raw' / f"{c['key']}.repl26a")
        tmp = out.with_suffix('.tmp')
        r = subprocess.run(['node', str(HERE / 'extract.mjs'), str(tmp), f"{raw}:{c['side']}:{c['key']}"], capture_output=True, text=True)
        if r.returncode or not tmp.exists() or tmp.stat().st_size == 0:
            log('extract failed', c['key'], r.stderr[-500:])
            return None
        tmp.rename(out)
        return out

    with cf.ThreadPoolExecutor(jobs) as ex:
        outs = list(ex.map(one, chosen))
    return [c for c, o in zip(chosen, outs) if o]


def write_entries(cs, work, name):
    p = work / name
    with open(p, 'w') as f:
        for c in cs:
            f.write((work / 'ent' / f"{c['key']}.json").read_text().strip() + '\n')
    return p


def copy_bot(host, dst):
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    shutil.copytree(host / 'src', dst / 'src')


def build(bot):
    r = subprocess.run(['cambc', 'build', str(bot), '--release'], capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        raise RuntimeError(f'build {bot} failed:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}')


def record(cs, a, work, host, tag):
    """Plays the games not yet recorded; returns key -> fingerprints (list of hex strings per body) for exact ones."""
    fpfile = work / 'fp.json'
    fps = json.loads(fpfile.read_text()) if fpfile.exists() else {}
    badfile = work / 'bad.json'
    bad = json.loads(badfile.read_text()) if badfile.exists() else {}
    todo = [c for c in cs if c['key'] not in fps and c['key'] not in bad]
    log(f'record: {len(todo)} games to play ({len(fps)} recorded, {len(bad)} failed before)')
    if todo:
        ents = write_entries(todo, work, 'todo.jsonl')
        rec, pup = ROOT / 'bots/variants' / f'{host.name}-rec-{tag}', ROOT / 'bots/variants' / f'{host.name}-pup-{tag}'
        copy_bot(host, rec), copy_bot(host, pup)
        for bot, team, mode in ((rec, 'ours', 'record'), (pup, 'opp', 'puppet')):
            subprocess.run([sys.executable, str(HERE / 'build_book.py'), str(ents), str(bot / 'src/book/book_data.h'), '--team', team, '--mode', mode], check=True)
        with cf.ThreadPoolExecutor(2) as ex:
            list(ex.map(build, (rec, pup)))
        runs = work / 'runs'
        runs.mkdir(exist_ok=True)
        lines = []
        for c in todo:
            out = runs / f"{c['key']}.repl26a"
            if out.exists():
                out.unlink()
            A, B = (rec, pup) if c['side'] == 'a' else (pup, rec)
            lines.append(f"{A} {B} {map_path(c['map'])} {out}")
        man = work / f'manifest-{tag}.txt'
        man.write_text('\n'.join(lines) + '\n')
        env = dict(os.environ, CAMBC_BIN=str(FAST), FASTRUNNER_MODE='native')
        r = subprocess.run([str(FAST), 'run-batch', str(man), '--jobs', str(a.jobs), '--slot-dir', str(cpu_slots.DIR), '--slots', str(cpu_slots.SIZE),
                            '--release', '--color', 'never'], capture_output=True, text=True, env=env, cwd=ROOT)
        (work / f'run-{tag}.log').write_text(r.stdout + r.stderr)

        def check(c):
            out = runs / f"{c['key']}.repl26a"
            if not out.exists():
                return c['key'], None, 'no replay'
            r = subprocess.run(['node', str(HERE / 'cmp.mjs'), str(work / 'raw' / f"{c['key']}.repl26a"), str(out)], capture_output=True, text=True)
            try:
                v = json.loads(r.stdout.strip().splitlines()[-1])
            except Exception:
                return c['key'], None, 'cmp failed ' + r.stderr[-300:]
            if v['firstDiff'] != -1 or not v['finalSame']:
                return c['key'], None, f"differs from round index {v['firstDiff']}"
            with zipfile.ZipFile(out) as z:
                text = z.read(f"team-{c['side']}.stdout").replace(b'\0', b'').decode()
            ent = json.loads((work / 'ent' / f"{c['key']}.json").read_text())
            nb, last = len(ent['ours']['bodies']), ent['rounds']
            fp = [['0'] * last for _ in range(nb)]
            errs = 0
            for line in text.splitlines():
                p = line.split()
                if p and p[0] == 'BKFP' and len(p) == 4:
                    rnd, b = int(p[1]), int(p[2])
                    if 1 <= rnd <= last and 0 <= b < nb:
                        fp[b][rnd - 1] = p[3]
                elif p and p[0] == 'BKERR':
                    errs += 1
            if errs:
                return c['key'], None, f'{errs} action errors'
            return c['key'], [''.join(x) for x in fp], None

        with cf.ThreadPoolExecutor(min(a.jobs, 24)) as ex:
            for key, fp, why in ex.map(check, todo):
                if fp is None:
                    bad[key] = why
                    log('  not reproduced:', key, why)
                else:
                    fps[key] = fp
        fpfile.write_text(json.dumps(fps))
        badfile.write_text(json.dumps(bad, indent=1))
    return fps


def verify(cs, a, work, host):
    """The shipped bot (play mode: fingerprints checked, hand-over armed) against a puppet of the opponent in every
    entry: each must reproduce its live game round for round. One puppet an opponent (its blind pick is the entry's)."""
    res = []
    for tag in sorted({c.get('opp', 'fish') for c in cs}):
        res += verify_one([c for c in cs if c.get('opp', 'fish') == tag], a, work, host, tag)
    bad = [(k, w) for k, w in res if w]
    for k, w in bad:
        log('  VERIFY FAILED:', k, w)
    log(f'verify: {len(cs) - len(bad)}/{len(cs)} live games reproduced by the shipped bot against the opponent puppet')
    (work / 'verify.json').write_text(json.dumps(dict(res)))


def verify_one(cs, a, work, host, tag):
    ents = write_entries(cs, work, f'verify-{tag}.jsonl')
    pup = ROOT / 'bots/variants' / f'{host.name}-pup-{tag}'
    copy_bot(host, pup)
    subprocess.run([sys.executable, str(HERE / 'build_book.py'), str(ents), str(pup / 'src/book/book_data.h'), '--team', 'opp', '--mode', 'puppet'], check=True)
    build(pup)
    runs = work / f'verify-{tag}'
    shutil.rmtree(runs, ignore_errors=True)
    runs.mkdir()
    lines = []
    for c in cs:
        A, B = (host, pup) if c['side'] == 'a' else (pup, host)
        lines.append(f"{A} {B} {map_path(c['map'])} {runs / (c['key'] + '.repl26a')}")
    man = work / f'verify-{tag}.txt'
    man.write_text('\n'.join(lines) + '\n')
    env = dict(os.environ, CAMBC_BIN=str(FAST), FASTRUNNER_MODE='native')
    r = subprocess.run([str(FAST), 'run-batch', str(man), '--jobs', str(a.jobs), '--slot-dir', str(cpu_slots.DIR), '--slots', str(cpu_slots.SIZE),
                        '--release', '--color', 'never'], capture_output=True, text=True, env=env, cwd=ROOT)
    (work / f'verify-{tag}.log').write_text(r.stdout + r.stderr)

    def check(c):
        out = runs / f"{c['key']}.repl26a"
        if not out.exists():
            return c['key'], 'no replay'
        # A plain-priority book's games differ from the live ones in our own priority values, and in nothing else.
        cmp = ['cmp2.mjs', c['side']] if getattr(a, 'prio', None) == 'plain' else ['cmp.mjs']
        r = subprocess.run(['node', str(HERE / cmp[0]), str(work / 'raw' / f"{c['key']}.repl26a"), str(out)] + cmp[1:], capture_output=True, text=True)
        try:
            v = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            return c['key'], 'cmp failed'
        return c['key'], None if v['firstDiff'] == -1 and v['finalSame'] else f"differs from round index {v['firstDiff']}"

    with cf.ThreadPoolExecutor(min(a.jobs, 24)) as ex:
        return list(ex.map(check, cs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', required=True, help='bot dir under bots/ that gets the book (its src/ is the host)')
    ap.add_argument('--opp', action='append', help='NAME:REFSET, repeatable (default "Intercontinental Fish" with --refset)')
    ap.add_argument('--refset', default='r8')
    ap.add_argument('--versions', default='117,118,119')
    ap.add_argument('--host-version', type=int)
    ap.add_argument('--extra')
    ap.add_argument('--host-repro', help="hostcheck.py's outputs (comma-separated, lines MAP SIDE OPP): of --host-version's live "
                    "wins, only the cells the host build replays exactly are left to it; the others get entries")
    ap.add_argument('--work', default=str(Path.home() / 'tmp-offload/rbook/fish'))
    ap.add_argument('--jobs', type=int, default=32)
    ap.add_argument('--no-build', action='store_true')
    ap.add_argument('--verify-only', action='store_true', help="only build --host and check it reproduces --work's book "
                    "(book_cells.json): for another build of the same book, such as a masked upload copy")
    ap.add_argument('--cells', help="the strength dial: only these cells (build_book.py's --cells)")
    ap.add_argument('--cap', type=int, help="the strength dial: at most N entries, smallest first (build_book.py's --cap)")
    ap.add_argument('--keys', help='only these entries: a file of game keys, one a line (pick_entries.py writes it; --cells cannot '
                    'keep one opponent\'s entry on a cell and drop the other\'s)')
    ap.add_argument('--prio', choices=['recorded', 'plain', 'seeded'], default='recorded', help="build_book.py's --prio")
    ap.add_argument('--force-versions', help="versions of ours whose draft is not the host's: their entries' picks are forced "
                    "(the draft plays them while the opponent's picks match); 117-119 draft as 525 does")
    a = ap.parse_args()
    work = Path(a.work).expanduser()
    work.mkdir(parents=True, exist_ok=True)
    host = ROOT / 'bots' / a.host
    if a.verify_only:
        # Another build of a book made here (e.g. the live upload's masked copy): its book_data.h is left as it is,
        # and its entries are the keys in that header's row comments.
        import re
        keys = re.findall(r'^  \{0x.*// (\S+)$', (host / 'src/book/book_data.h').read_text(), re.M)
        tags = {c['key']: c.get('opp', 'fish') for c in json.loads((work / 'book_cells.json').read_text())} if (work / 'book_cells.json').exists() else {}
        cs = []
        for k in keys:
            m = re.match(r'^(.+)-([ab])-v(\d+)-', k)
            cs.append(dict(key=k, map=m.group(1), side=m.group(2), version=int(m.group(3)), rounds=None,
                           replay=str(work / 'raw' / f'{k}.repl26a'), opp=tags.get(k, 'fish')))
        missing = [c['key'] for c in cs if not Path(c['replay']).exists()]
        if missing:
            raise SystemExit(f'{len(missing)} live replays missing from {work}/raw: {missing[:3]}')
        cs = extract_all(cs, work, min(a.jobs, 16))
        log(f'verify-only: {len(cs)} entries from {host}')
        build(host)
        verify(cs, a, work, host)
        return
    chosen, cs, fps = [], [], {}
    for opp, refset, tag in opponents(a):
        ch = select(a, opp, refset, tag)
        c = extract_all(ch, work, min(a.jobs, 16))
        log(f'extract {tag}: {len(c)} entries')
        fps.update(record(c, a, work, host, tag))
        chosen += ch
        cs += c
    final = [c for c in cs if c['key'] in fps]
    if a.keys:
        keep = {l.split()[0] for l in open(a.keys) if l.strip() and not l.startswith('#')}
        final = [c for c in final if c['key'] in keep]
    ents = write_entries(final, work, 'book.jsonl')
    (work / 'fp_book.json').write_text(json.dumps({c['key']: fps[c['key']] for c in final}))
    (work / 'book_cells.json').write_text(json.dumps([{k: c[k] for k in ('key', 'map', 'side', 'version', 'rounds', 'opp')} for c in final], indent=0))
    dial = (['--cells', a.cells] if a.cells else []) + (['--cap', str(a.cap)] if a.cap is not None else [])
    if a.force_versions:
        fv = {int(v) for v in a.force_versions.split(',')}
        forced = [c['key'] for c in final if c.get('version') in fv]
        (work / 'force.txt').write_text(''.join(k + '\n' for k in forced))
        dial += ['--force', str(work / 'force.txt')]
        log(f'force: {len(forced)} entries play their own picks (versions {sorted(fv)})')
    if a.prio != 'recorded':
        dial += ['--prio', a.prio]
    r = subprocess.run([sys.executable, str(HERE / 'build_book.py'), str(ents), str(host / 'src/book/book_data.h'), '--team', 'ours', '--mode', 'play',
                        '--fp', str(work / 'fp_book.json')] + dial, capture_output=True, text=True)
    sys.stderr.write(r.stderr)
    if r.returncode:
        raise SystemExit('build_book failed')
    kept = {l.split()[3] for l in r.stderr.splitlines() if l.startswith('cell ')}
    final = [c for c in final if c['key'] in kept]
    (work / 'book_cells.json').write_text(json.dumps([{k: c[k] for k in ('key', 'map', 'side', 'version', 'rounds', 'opp')} for c in final], indent=0))
    log(f'book: {len(final)} entries of {len(chosen)} cells selected')
    if not a.no_build:
        build(host)
        verify(final, a, work, host)
        out = work / 'bundle.zip'
        out.unlink(missing_ok=True)  # cambc bundle leaves an existing file alone
        r = subprocess.run(['cambc', 'bundle', str(host), '--output', str(out)], capture_output=True, text=True, cwd=ROOT)
        if out.exists():
            log(f'bundle: {out.stat().st_size} bytes (platform limit 5 MB compressed)')
        else:
            log('bundle:', r.stdout[-500:], r.stderr[-500:])


if __name__ == '__main__':
    main()
