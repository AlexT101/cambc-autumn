"""The Prism's real fuel need a turn when allowed 200k (variants/pl-capnpq's PQ lines): python3 pq.py BATCHGLOB
PQ round handle start left near seen allies decision: fuel at the turn's start and left before the turn-end queue."""
import glob, sys, zipfile
rows = []
for f in glob.glob(sys.argv[1] + '/*.repl26a'):
    side = 'b' if f.rsplit('.', 1)[0].endswith('-21') else 'a'
    for line in zipfile.ZipFile(f).read(f'team-{side}.stdout').decode('utf-8', 'replace').replace('\x00', '').splitlines():
        v = line.split()
        if len(v) == 9 and v[0] == 'PQ':
            try:
                r, st, left = int(v[1]), int(v[3]), int(v[4])
                if r > 2: rows.append((st - left, int(v[5]), int(v[6]), int(v[7]), v[8]))
            except ValueError: pass
n = len(rows)
print(n, 'Prism turns (finished, round 3 on)')


def line(name, S):
    if not S: return
    u = sorted(r[0] for r in S)
    q = lambda p: u[min(len(u) - 1, int(p * len(u)))]
    print(f'  {name:36s} {len(S):7d} ({100 * len(S) / n:5.1f}%)  need: median {q(.5):6d}  p90 {q(.9):6d}  p99 {q(.99):6d}  over 90k {100 * sum(1 for x in u if x > 90000) / len(u):5.2f}%  over 100k {100 * sum(1 for x in u if x > 100000) / len(u):5.2f}%  over 130k {100 * sum(1 for x in u if x > 130000) / len(u):5.2f}%')


line('all', rows)
line('no enemy in sight', [r for r in rows if r[2] == 0])
for k in (1, 2, 3, 4): line(f'enemies in sight: {k}{"+" if k == 4 else ""}', [r for r in rows if min(r[2], 4) == k])
line('enemy within 5', [r for r in rows if r[1] <= 5])
for d in 'FRCBTAPG': line(f'enemy in sight, decision {d}', [r for r in rows if r[2] > 0 and r[4] == d])
for k in (0, 1, 2, 3): line(f'2+ enemies in sight, allies in sight {k}{"+" if k == 3 else ""}', [r for r in rows if r[2] >= 2 and min(r[3], 3) == k])
