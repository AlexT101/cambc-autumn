"""The fallback test: the opponent leaves the recorded game mid-book; do our bodies hand over, and do the ones already
off the book read their still on-book allies' priority payloads (the recorded, masked ones) correctly?

    py fallbacktest.py --host variants/rbook-ff --work ~/tmp-offload/rbook/ff [--n 24] [--truncate 150] [--unmasked]
Builds debug copies of HOST with two traces (BKOFF with the body; CLAIMRD: each claim read from an ally's payload and
the map's group count), one masked by tools/livemask/stream_patch.py (the live build; --unmasked also plays the plain
one as a control), and a puppet of the opponent whose book ends at round --truncate. Plays --n entries (the long ones)
and counts, per reader and ally state, the claims that name a group of the map or none (valid). An off-book reader
of an on-book ally must be ~100% valid in the masked build. The masked copy is deleted afterwards."""
import argparse, collections, json, os, random, shutil, subprocess, sys, zipfile
from pathlib import Path

import rbuild

ROOT, HERE = rbuild.ROOT, rbuild.HERE
TRACES = [
    ('book/book.cc', '    else debug_block({ std::printf("BKOFF %u %s\\n", round, why); });',
     '    else debug_block({ std::printf("BKOFF %u %s body %d\\n", round, why, play_state.body); });'),
    ('model/comms.cc',
     '        detail::posts.claims[a.index] = p >= 0 ? static_cast<int>(p & 0xff) - 1 : static_cast<int>(L.claim[static_cast<std::size_t>(a.index)].get(bits)) - 1;\n',
     '        detail::posts.claims[a.index] = p >= 0 ? static_cast<int>(p & 0xff) - 1 : static_cast<int>(L.claim[static_cast<std::size_t>(a.index)].get(bits)) - 1;\n'
     '        if (p < 0 && a.priority_round == world.round && a.next_priority != 0)\n'
     '            debug_block({ std::printf("CLAIMIG %u %d %d\\n", world.round, world.me().index, a.index); });\n'
     '        if (p >= 0)\n'
     '            debug_block({ std::printf("CLAIMRD %u %d %d %d %d\\n", world.round, world.me().index, a.index, static_cast<int>(p & 0xff) - 1,\n'
     '                                      static_cast<int>(world.map().groups.size())); });\n'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', required=True)
    ap.add_argument('--work', required=True)
    ap.add_argument('--n', type=int, default=24)
    ap.add_argument('--truncate', type=int, default=150)
    ap.add_argument('--unmasked', action='store_true')
    ap.add_argument('--plain', action='store_true', help='an unmasked host (the final): only the plain build; CLAIMIG counts the '
                    'payloads it left unread (an ally whose plain bit is not set)')
    ap.add_argument('--jobs', type=int, default=24)
    a = ap.parse_args()
    work = Path(a.work).expanduser()
    host = ROOT / 'bots' / a.host
    V = ROOT / 'bots/variants'
    fb, fbm, pup = V / f'{host.name}-fb', V / f'{host.name}-fb-m', V / f'{host.name}-fb-pup'
    rbuild.copy_bot(host, fb)
    for rel, old, new in TRACES:
        p = fb / 'src' / rel
        s = p.read_text()
        assert s.count(old) == 1, f'trace anchor missing in {rel}'
        p.write_text(s.replace(old, new))
    if not a.plain:
        rbuild.copy_bot(fb, fbm)
        r = subprocess.run([sys.executable, str(ROOT / 'tools/livemask/stream_patch.py'), str(fbm)], capture_output=True)  # output never shown
        if r.returncode:
            raise SystemExit('stream_patch failed')
    cells = json.loads((work / 'book_cells.json').read_text())
    ents = {}
    for l in open(work / 'book.jsonl'):
        e = json.loads(l)
        ents[e['key']] = e['rounds']
    long = sorted(c['key'] for c in cells if ents.get(c['key'], 0) > 3 * a.truncate)
    random.Random(5).shuffle(long)
    keys = long[:a.n]
    by = {c['key']: c for c in cells}
    rbuild.copy_bot(host, pup)
    subprocess.run([sys.executable, str(HERE / 'build_book.py'), str(work / 'book.jsonl'), str(pup / 'src/book/book_data.h'), '--team', 'opp',
                    '--mode', 'puppet', '--keys', ','.join(keys), '--truncate', str(a.truncate)], check=True, capture_output=True)
    out = work / 'fallback'
    shutil.rmtree(out, ignore_errors=True)
    builds = [('plain', fb)] if a.plain else [('masked', fbm)] + ([('unmasked', fb)] if a.unmasked else [])
    lines = []
    for tag, bot in builds:
        (out / tag).mkdir(parents=True)
        for k in keys:
            c = by[k]
            A, B = (bot, pup) if c['side'] == 'a' else (pup, bot)
            lines.append(f"{A} {B} {rbuild.map_path(c['map'])} {out / tag / (k + '.repl26a')}")
    (out / 'manifest.txt').write_text('\n'.join(lines) + '\n')
    env = dict(os.environ, CAMBC_BIN=str(rbuild.FAST), FASTRUNNER_MODE='native')
    r = subprocess.run([str(rbuild.FAST), 'run-batch', str(out / 'manifest.txt'), '--jobs', str(a.jobs), '--slot-dir', str(rbuild.cpu_slots.DIR),
                        '--slots', str(rbuild.cpu_slots.SIZE), '--color', 'never'], capture_output=True, text=True, env=env, cwd=ROOT)  # debug builds
    (out / 'run.log').write_text(r.stdout + r.stderr)
    shutil.rmtree(fbm, ignore_errors=True)
    for tag, _ in builds:
        st, ig = collections.Counter(), collections.Counter()
        games = wins = handed = bodies = 0
        last_off = []
        for k in keys:
            f = out / tag / (k + '.repl26a')
            if not f.exists():
                continue
            side = by[k]['side']
            with zipfile.ZipFile(f) as z:
                t = z.read(f'team-{side}.stdout').replace(b'\0', b'').decode(errors='replace')
            off, reads, unread = {}, [], []
            for l in t.splitlines():
                p = l.split()
                if p[:1] == ['BKOFF'] and len(p) >= 5:
                    off.setdefault(int(p[4]), int(p[1]))
                elif p[:1] == ['CLAIMRD'] and len(p) == 6:
                    reads.append(tuple(map(int, p[1:])))
                elif p[:1] == ['CLAIMIG'] and len(p) == 4:
                    unread.append(tuple(map(int, p[1:])))
            games += 1
            handed += len(off)
            if off:
                last_off.append(max(off.values()) - min(off.values()))
            for rnd, i, j, c, G in reads:
                ri, aj = i in off and off[i] <= rnd, j in off and off[j] <= rnd
                st[(('reader off' if ri else 'reader on') + (', ally on-book' if not aj else ', ally off-book'), -1 <= c < G)] += 1
            for rnd, i, j in unread:
                ig[', ally on-book' if not (j in off and off[j] <= rnd) else ', ally off-book'] += 1
        print(f'{tag}: {games} games, {handed} bodies handed over; rounds from the first to the last hand-over in a game: '
              f'median {sorted(last_off)[len(last_off) // 2] if last_off else None}, max {max(last_off, default=None)}')
        for kind in sorted({k for k, _ in st}):
            ok, bad = st[(kind, True)], st[(kind, False)]
            print(f'   {kind:32s} valid {ok:6d}  invalid {bad:6d}  ({100 * ok / max(1, ok + bad):.1f}% valid)')
        for kind, n in sorted(ig.items()):
            print(f'   payload left unread{kind}: {n}')


if __name__ == '__main__':
    main()
