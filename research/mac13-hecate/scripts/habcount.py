"""Per game, from an ab.py --debug batch's replays: h-ab's burst counters on the CAND side.
HABG: work-guard turns refusing burst-lethal tiles (and tiles refused); HABR: burst retreats; HABS: retreat steps
ranked last as burst-lethal; HABL: lethal() true by the burst alone (visible / unseen Prism).
usage: habcount.py REPLAY_DIR"""
import sys, re, zipfile, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
G = re.compile(rb'^[\s\0]*HABG \d+ \d+ \S+ tiles (\d+)', re.M)
R = re.compile(rb'^[\s\0]*HABR ', re.M)
S = re.compile(rb'^[\s\0]*HABS ', re.M)
L = re.compile(rb'^[\s\0]*HABL \d+ \d+ \S+ visible (\d)', re.M)
def one(f):
    z = zipfile.ZipFile(f)
    side = 'a' if f.name.rsplit('-', 1)[1].startswith('12') else 'b'  # 12: CAND is team A
    s = z.read(f'team-{side}.stdout'); c = collections.Counter()
    for m in G.finditer(s): c['guard_turns'] += 1; c['guard_tiles'] += int(m[1])
    c['retreats'] = len(R.findall(s)); c['ranked_last'] = len(S.findall(s))
    for m in L.finditer(s): c['lethal_visible' if m[1] == b'1' else 'lethal_unseen'] += 1
    return c
if __name__ == '__main__':
    files = sorted(Path(sys.argv[1]).rglob('*.repl26a'))
    tot = collections.Counter(); fired = collections.Counter()
    with ProcessPoolExecutor(16) as ex:
        for c in ex.map(one, files, chunksize=8):
            tot.update(c); fired.update({k: 1 for k, v in c.items() if v})
    n = len(files); print('games', n)
    for k in ('guard_turns', 'guard_tiles', 'retreats', 'ranked_last', 'lethal_visible', 'lethal_unseen'):
        print(f'{k:15s} total {tot[k]:6d}  per game {tot[k] / max(n, 1):7.3f}  games with any {fired[k]}')
