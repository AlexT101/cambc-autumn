"""The live mask's per-game seed for a recorded game of a masked version of ours (v106-v120), so that the book can
store our recorded priorities without the mask's noise (build_book.py --prio seeded).

    py seeds.py place [--jobs 32]     map facts for every ladder cell -> place.json (next to this file)
    py seeds.py check ENT.json...     how well each entry's priorities unmask (the share whose round tag comes out 0)

tools/livemask/prio_stream.h: a masked build publishes rank << 16 | tag << 14 | (payload ^ mask), mask and tag drawn
from game.seed = mix(mix(place ^ key[1]) ^ picks ^ key[0]). place is the map's size, group count and our spawn centre,
picks our side and bodies. `place` plays a host copy that prints those facts at World's init and resigns, on each cell;
seed() then needs only the key file, which is read here and never printed or stored. The bot gets the seed, not the key."""
import argparse, json, os, re, shutil, subprocess, sys, zipfile
from pathlib import Path

import rbuild

ROOT, HERE = rbuild.ROOT, rbuild.HERE
M = (1 << 64) - 1
PLACE = HERE / 'place.json'
ANCHOR = '            init_beliefs();\n'
PRINT = ANCHOR + '''            {
                const auto& s = map();
                std::printf("BKPLACE %d %d %d %d %d %d", static_cast<int>(s.width), static_cast<int>(s.height), static_cast<int>(s.groups.size()),
                            static_cast<int>(s.ally_spawn_centre.x), static_cast<int>(s.ally_spawn_centre.y), s.team_a ? 1 : 0);
                for (const auto& b : allies) std::printf(" %d", static_cast<int>(b.type));
                std::printf("\\n");
                std::fflush(nullptr);
                (void)cambc::detail::sdk_resign();
            }
'''


def mix(z):
    z = ((z ^ (z >> 30)) * 0xbf58476d1ce4e5b9) & M
    z = ((z ^ (z >> 27)) * 0x94d049bb133111eb) & M
    return z ^ (z >> 31)


def key():
    kb = (ROOT / 'tools/livemask/livemask.key').read_bytes()
    return int.from_bytes(kb[:8], 'little'), int.from_bytes(kb[8:16], 'little')


def body_types(picks):
    out = []
    for d in picks:  # champion_draft -> champion_type: Cassi & Issac is one pick, two bodies
        out += [3, 4] if d == 3 else [d if d < 3 else d + 1]
    return out


def seed(map_name, side, picks, place=None):
    place = place or json.loads(PLACE.read_text())
    w, h, groups, cx, cy, team_a = place[f'{map_name}:{side}']
    p = (w << 48) ^ (h << 32) ^ (groups << 16) ^ ((cx * 256 + cy) & M)
    pk = 0x5a if team_a else 0xa5
    for t in body_types(picks):
        pk = (pk * 0x100000001b3 + t + 1) & M
    k0, k1 = key()
    return mix((mix(p ^ k1) ^ pk) ^ k0)


def word(sd, w, index):
    """What the mask xors into the low 16 bits of body `index`'s priority published in round w."""
    tag = (w + (mix(sd ^ 0x7a6) & 3)) & 3
    return tag << 14 | (mix(sd ^ (w * 0x9e3779b97f4a7c15 & M)) >> ((index & 7) * 7)) & 0x3fff


def place_run(a):
    bot = ROOT / 'bots/variants/rbook-placebot'
    rbuild.copy_bot(ROOT / 'bots/variants/chy-525f', bot)
    p = bot / 'src/model/world.cc'
    s = p.read_text()
    assert s.count(ANCHOR) == 1
    p.write_text(s.replace(ANCHOR, PRINT))
    rbuild.build(bot)
    other = ROOT / 'bots/variants/chy-525f'
    maps = set()
    for line in open(rbuild.GAMES):
        g = json.loads(line)
        if g.get('refset') in ('r8', 'r9', 'r10'):
            maps.add(g['map'])
    out = Path.home() / 'tmp-offload/rbook/place'
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    lines = []
    for m in sorted(maps):
        for side in 'ab':
            A, B = (bot, other) if side == 'a' else (other, bot)
            lines.append(f"{A} {B} {rbuild.map_path(m)} {out / f'{m}:{side}.repl26a'}")
    (out / 'manifest.txt').write_text('\n'.join(lines) + '\n')
    env = dict(os.environ, CAMBC_BIN=str(rbuild.FAST), FASTRUNNER_MODE='native')
    r = subprocess.run([str(rbuild.FAST), 'run-batch', str(out / 'manifest.txt'), '--jobs', str(a.jobs), '--slot-dir', str(rbuild.cpu_slots.DIR),
                        '--slots', str(rbuild.cpu_slots.SIZE), '--release', '--color', 'never'], capture_output=True, text=True, env=env, cwd=ROOT)
    (out / 'run.log').write_text(r.stdout + r.stderr)
    place, types = {}, {}
    for m in sorted(maps):
        for side in 'ab':
            f = out / f'{m}:{side}.repl26a'
            if not f.exists():
                continue
            with zipfile.ZipFile(f) as z:
                t = z.read(f'team-{side}.stdout').replace(b'\0', b'').decode(errors='replace')
            x = re.search(r'^BKPLACE (.*)$', t, re.M)
            if x:
                v = list(map(int, x.group(1).split()))
                place[f'{m}:{side}'] = v[:6]
                types[f'{m}:{side}'] = v[6:]
    PLACE.write_text(json.dumps(place, indent=0, sort_keys=True))
    print(f'{len(place)} of {2 * len(maps)} cells; team_a wrong on {sum((v[5] == 1) != k.endswith(":a") for k, v in place.items())}')
    print('sample body types', list(types.items())[:3])


def check(a):
    place = json.loads(PLACE.read_text())
    for f in a.files:
        e = json.loads(Path(f).read_text())
        m = re.match(r'^(.+)-([ab])-v\d+-', e['key'])
        sd = seed(m.group(1), m.group(2), e['ours']['picks'], place)
        n = ok = 0
        vals = set()
        for b, body in enumerate(e['ours']['bodies']):
            for r, (roll, acts) in enumerate(body['turns']):
                for x in acts:
                    if x[0] == 4:
                        c = (x[3] & 0xffff) ^ word(sd, r + 1, b)
                        n += 1
                        ok += c >> 14 == 0
                        vals.add(c)
        print(e['key'], f'{n} priorities, tag clear on {100 * ok / max(1, n):.1f}%, {len(vals)} distinct unmasked low halves')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['place', 'check'])
    ap.add_argument('files', nargs='*')
    ap.add_argument('--jobs', type=int, default=32)
    a = ap.parse_args()
    place_run(a) if a.cmd == 'place' else check(a)
