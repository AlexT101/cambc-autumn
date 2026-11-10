"""heavy.py GAMES_A GAMES_B: per-turn fuel saving of B vs A (identical games), all play turns and turns where A >= 85k / 70k."""
import struct, sys, zipfile
from pathlib import Path
def turns(f, side):
    d = zipfile.ZipFile(f).read(f'team-{side}.fuel'); return [struct.unpack_from('<Q', d, i)[0] for i in range(77, len(d) - 7, 8)]
a, b = sys.argv[1:3]; S = {'all': [0, 0, 0], '>=70k': [0, 0, 0], '>=85k': [0, 0, 0]}; skipped = 0
for d in sorted(Path(a).iterdir()):
    side = d.name.rsplit('-', 1)[1]
    fa = next(d.glob('*.repl26a'), None); fb = next((Path(b) / d.name).glob('*.repl26a'), None)
    if not fa or not fb: continue
    ta, tb = turns(fa, side), turns(fb, side)
    if len(ta) != len(tb): skipped += 1; continue
    for x, y in zip(ta[10:], tb[10:]):  # skip draft/first turns
        for k, lo in (('all', 0), ('>=70k', 70000), ('>=85k', 85000)):
            if x >= lo: S[k][0] += 1; S[k][1] += x - y; S[k][2] += x
print('skipped', skipped)
for k, (n, s, t) in S.items(): print(f'{k:6s} turns {n:7d}  saving {s/max(1,n):7.0f}/turn  {100*s/max(1,t):5.2f}%')
