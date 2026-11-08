#!/usr/bin/env python3
"""Write a tune.json's values as plain constants into a bot's params.h.
port_tune.py TUNE_JSON BOTDIR [--keep name,...]  (keep = leave the bot's own value)"""
import json, re, sys, struct
tj, bot = sys.argv[1], sys.argv[2]
keep = set(sys.argv[sys.argv.index('--keep') + 1].split(',')) if '--keep' in sys.argv else set()
t = json.load(open(tj))
path = f'{bot}/src/params.h'
src = open(path).read()
def f32(x): return '%.9gf' % struct.unpack('f', struct.pack('f', x))[0]
vals = [(n, f32(v)) for n, v in t['floats']] + [(n, str(v)) for n, v in t['ints']]
for n, v in vals:
    if n in keep: continue
    pat = re.compile(r'^(inline (?:constexpr )?(?:float|int) %s = )([^;]+);' % re.escape(n), re.M)
    m = pat.findall(src)
    assert len(m) == 1, (n, m)
    old = m[0][1]
    src = pat.sub(lambda mm: mm.group(1) + v + ';', src)
    print(f'{n}: {old} -> {v}')
open(path, 'w').write(src)
