"""Per game and bot, from an ab.py --debug batch's replays: contest starts ('X' runs in the D lines, both bots), X turns,
and h-deny's CONTEST-START/RESET/TOOK/DEATH counters (gems/gold of the groups reset and taken).
usage: denycount.py REPLAY_DIR [CAND_NAME]   (results.json maps each replay to its sides)"""
import sys, re, json, zipfile, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
D_RE = re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
C_RE = re.compile(rb'^[\s\0]*CONTEST-(START|RESET|TOOK|DEATH) (\d+) (\d+)((?: -?\d+)*)\s*$', re.M)
def one(f):
    z = zipfile.ZipFile(f); out = {}
    for side in ('a', 'b'):
        s = z.read(f'team-{side}.stdout'); st = collections.Counter(); last = {}
        for m in D_RE.finditer(s):
            r, h, b = int(m[1]), int(m[2]), m[3]
            if b == b'X':
                st['x_turns'] += 1
                if last.get(h) != r - 1: st['x_starts'] += 1
                last[h] = r
        for m in C_RE.finditer(s):
            k = m[1].decode().lower(); a = [int(x) for x in m[4].split()]
            st[k] += 1
            if k in ('reset', 'took'): st[k + '_gems'] += a[1]; st[k + '_gold'] += a[2]
            if k in ('start', 'reset'): st[k + ('_deny' if a[-1] else '_ref')] += 1
        out[side] = st
    return f.name, out
if __name__ == '__main__':
    d = Path(sys.argv[1]); cand = sys.argv[2] if len(sys.argv) > 2 else 'h-deny'
    files = sorted(d.glob('*.repl26a'))
    # <n>-<map>-<12|21>.repl26a: 12 means bot 1 (CAND) is team A
    tot = {'cand': collections.Counter(), 'ref': collections.Counter()}; n = 0
    with ProcessPoolExecutor(32) as ex:
        for name, o in ex.map(one, files, chunksize=8):
            n += 1; ca = name.rsplit('-', 1)[1].startswith('12')
            tot['cand'].update(o['a' if ca else 'b']); tot['ref'].update(o['b' if ca else 'a'])
    print('games', n)
    keys = sorted(set(tot['cand']) | set(tot['ref']))
    for k in keys: print(f"{k:14s} cand {tot['cand'][k]/n:8.3f}  ref {tot['ref'][k]/n:8.3f}")
