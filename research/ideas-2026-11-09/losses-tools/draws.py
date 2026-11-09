"""Noise bodies' knob draws per (map, team, seed k, epoch) from the dvp-printer runs -> draws.npz (diverse agent).
    python3 draws.py PRINTER_BATCHES_TXT OUT.npz"""
import sys, re, glob, zipfile, os, numpy as np
keys, vals = [], []
for line in open(sys.argv[1]):
    v, b = line.split(); off = 300 if v.endswith('300') else 0  # the printer prints the round, not the seed
    for f in glob.glob(f'/home/ubuntu/cambc-autumn/{b}/*.repl26a'):
        mp = re.sub(r'^\d+-', '', os.path.basename(f)).rsplit('-', 1)[0]
        z = zipfile.ZipFile(f)
        a_first = f.endswith('-12.repl26a')  # bot 1 is team A; both bots are printers, so files name teams directly
        for t, member in (('a', 0), ('b', 1)):
            s = z.read(f'team-{t}.stdout').decode(errors='replace')
            for m in re.findall(r'DVP(?: -?\d+){28}', s):
                x = list(map(int, m.split()[1:]))
                keys.append((mp, member, x[0] + off, x[1])); vals.append(x[2:])
D = {}
for k, v in zip(keys, vals): D[k] = v
ks = sorted(D); np.savez(sys.argv[2], keys=np.array([f'{a}|{b}|{c}|{d}' for a, b, c, d in ks]), vals=np.array([D[k] for k in ks], dtype=np.int16))
print(len(ks), 'draws;', len({(a, b) for a, b, c, d in ks}), 'map-teams;', 'seeds', min(k[2] for k in ks), max(k[2] for k in ks))
