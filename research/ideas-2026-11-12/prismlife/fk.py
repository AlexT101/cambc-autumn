"""The Prism's farm loop under the fuel reserve (variants/pl-prof's FK lines): python3 fk.py BATCHGLOB
FK round handle k evaluated stop fuel-at-loop-start fuel-at-loop-end reserve banks opening: k of `evaluated` groups
reached before the loop ended (k < evaluated: cut by the reserve); `stop`: the index past which only claimed, held or
hop groups are still read."""
import glob, sys, zipfile
rows = []
for f in glob.glob(sys.argv[1] + '/*.repl26a'):
    side = 'b' if f.rsplit('.', 1)[0].endswith('-21') else 'a'
    for line in zipfile.ZipFile(f).read(f'team-{side}.stdout').decode('utf-8', 'replace').replace('\x00', '').splitlines():
        v = line.split()
        if len(v) == 11 and v[0] == 'FK':
            try: rows.append(tuple(int(x) for x in v[1:]))
            except ValueError: pass
n = len(rows)
print(n, 'farm loops of the Prism')


def line(name, S):
    if not S: return
    cut = [r for r in S if r[2] < r[3]]
    med = lambda xs: sorted(xs)[len(xs) // 2] if xs else 0
    print(f'  {name:30s} {len(S):7d} ({100 * len(S) / n:5.1f}%)  cut short {100 * len(cut) / len(S):5.1f}%  groups {med([r[3] for r in S]):3d}  fuel at start {med([r[5] for r in S]):6d}  loop cost {med([r[5] - r[6] for r in S]):6d} (p90 {sorted(r[5] - r[6] for r in S)[int(.9 * len(S))]:6d})  reserve {med([r[7] for r in S]):6d}'
          + (f'  when cut: reached {med([r[2] for r in cut])} of {med([r[3] for r in cut])}, fuel at start {med([r[5] for r in cut])}, reserve {med([r[7] for r in cut])}' if cut else ''))


line('all', rows)
line('opening (first turn)', [r for r in rows if r[9]])
line('later, banking', [r for r in rows if not r[9] and r[8]])
line('later, not banking', [r for r in rows if not r[9] and not r[8]])
for lo, hi in ((0, 20), (20, 40), (40, 70), (70, 999)): line(f'groups {lo}-{hi}', [r for r in rows if not r[9] and lo <= r[3] < hi])
for lo, hi in ((0, 30000), (30000, 50000), (50000, 70000), (70000, 200000)): line(f'fuel at start {lo // 1000}-{hi // 1000}k', [r for r in rows if not r[9] and lo <= r[5] < hi])
