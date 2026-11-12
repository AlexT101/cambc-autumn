"""Fetch published maps that `cambc maps pull` does not serve, from big-arm's capture of ranked games.

    python3 research/ideas-2026-11-12/pool170/fetch_new_maps.py [--days 2026-11-11,2026-11-12] [--install]

The platform's pool (`cambc match-groups quota --json`, 170 maps from 2026-11-11) lists maps that the pull endpoint
(/api/v1/maps/pool, still the 128) does not serve. Each captured replay holds its map's exact .map26a bytes after a
14-byte header; big-arm's per-day archive gives each map's sha256 and the matches played on it. For every pool map
missing from maps/, this copies one captured replay back, cuts the map out where the running sha256 matches, and
stages it in ~/tmp-offload/pool170/staged/. --install copies staged maps into maps/, never over an existing file.
Afterwards: add the names to nothing (tools/ladder128.txt stays the 128); `ladder-new` picks them up.
"""
import argparse, hashlib, io, json, os, shutil, subprocess, sys, tarfile, zipfile
from pathlib import Path

R = Path(__file__).resolve().parents[3]
STAGE = Path.home() / 'tmp-offload/pool170/staged'

REMOTE = r'''
import json, os, sys, numpy as np
want = set(sys.argv[2].split(','))
A = os.path.expanduser('~/cambc-autumn/.oarena/archive'); C = os.path.expanduser('~/cambc-autumn/.oarena/capture/replays')
out = {}
for day in sys.argv[1].split(','):
    d = f'{A}/{day}/data'
    if not os.path.exists(d): continue
    maps = json.load(open(d + '/meta.json'))['maps']
    for h, mid in zip(np.load(d + '/g_map_hash.npy'), np.load(d + '/matches.npy')):
        mp = maps[int(h)]
        if mp['name'] in want and mp['name'] not in out:
            p = f'{day[:7]}/{mid.decode()}.zip'
            if os.path.exists(f'{C}/{p}'): out[mp['name']] = (mp['sha256'] if 'sha256' in mp else mp['hash'], p)
json.dump(out, open(os.path.expanduser('~/pool170-sel.json'), 'w'))
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--days', default='2026-11-11,2026-11-12,2026-11-13,2026-11-14')
    ap.add_argument('--install', action='store_true')
    a = ap.parse_args()
    STAGE.mkdir(parents=True, exist_ok=True)
    pool = json.loads(subprocess.run(['cambc', 'match-groups', 'quota', '--json'], capture_output=True, text=True, check=True).stdout)['maps']
    # The CLI files a pool name with '_' as '-' (03the_front -> 03the-front.map26a); stage under the CLI's file name so a
    # later `cambc maps pull` finds the same file instead of adding a second copy.
    have = {p.stem for p in (R / 'maps').glob('*.map26a')} | {p.stem for p in STAGE.glob('*.map26a')}
    missing = sorted(m['name'] for m in pool if m['name'].replace('_', '-') not in have)
    print(f'pool {len(pool)}, missing locally {len(missing)}: {" ".join(missing)}')
    if missing:
        subprocess.run(['ssh', 'big-arm', 'python3', '-', a.days, ','.join(missing)], input=REMOTE, text=True, check=True)
        sel = json.loads(subprocess.run(['ssh', 'big-arm', 'cat ~/pool170-sel.json; rm -f ~/pool170-sel.json'],
                                        capture_output=True, text=True, check=True).stdout)
        if sel:
            tar = subprocess.run(['ssh', 'big-arm', 'cd ~/cambc-autumn/.oarena/capture/replays && tar cf - ' + ' '.join(p for _, p in sel.values())],
                                 capture_output=True, check=True).stdout
            with tarfile.open(fileobj=io.BytesIO(tar)) as tf:
                for name, (h, p) in sorted(sel.items()):
                    body = zipfile.ZipFile(io.BytesIO(tf.extractfile(p).read())).read('replay.repl26a')[14:]
                    sha = hashlib.sha256()
                    for n in range(1, len(body) + 1):
                        sha.update(body[n - 1:n])
                        if sha.copy().hexdigest() == h:
                            (STAGE / f"{name.replace('_', '-')}.map26a").write_bytes(body[:n]); print(f'staged {name} ({n} bytes)'); break
                    else: print(f'FAILED {name}: no prefix matches its sha256')
        print(f'not captured yet: {" ".join(sorted(set(missing) - set(sel))) or "none"}')
    if a.install:
        for f in sorted(STAGE.glob('*.map26a')):
            dst = R / 'maps' / f.name
            if dst.exists(): continue
            shutil.copyfile(f, dst); print(f'installed {dst.relative_to(R)}')


if __name__ == '__main__':
    main()
