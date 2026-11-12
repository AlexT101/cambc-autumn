"""What opp_detect (oppd_trace builds) read against an opponent: per game, the class at the last OPPD line, and the
round it first read Mite. OPPD round handle class reads bc bc_core fish fish_core mite mite_core (0 unknown, 1 fish,
2 mite, 3 battlecats).
    py oppd_read.py REPLAY_DIR..."""
import sys, zipfile, glob, collections, statistics
CLS = {'0': 'unknown', '1': 'fish', '2': 'mite', '3': 'battlecats'}
for d in sys.argv[1:]:
    last = collections.Counter(); ever = collections.Counter(); first = []; n = 0
    for f in sorted(glob.glob(d + '/*.repl26a')):
        z = zipfile.ZipFile(f)
        for t in ('team-a.stdout', 'team-b.stdout'):
            L = [l.split() for l in z.read(t).decode(errors='replace').replace('\x00', '').splitlines() if l.startswith('OPPD')]
            if not L: continue
            n += 1
            # one line stream per body (handle): the game's read is the latest line of any body
            L.sort(key=lambda l: int(l[1]))
            last[CLS[L[-1][3]]] += 1
            for c in {CLS[l[3]] for l in L}: ever[c] += 1
            m = [int(l[1]) for l in L if l[3] == '2']
            if m: first.append(m[0])
    print(f'{d}: {n} games; final class {dict(last)}; ever {dict(ever)}; first Mite read round median '
          f'{statistics.median(first) if first else None}')
