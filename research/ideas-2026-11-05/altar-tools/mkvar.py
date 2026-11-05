#!/usr/bin/env python3
"""mkvar.py NAME key=value ...: bots/variants/oc-altar-NAME from oc-altar-dev with params::altar knobs set."""
import re, subprocess, sys
name, sets = sys.argv[1], sys.argv[2:]
dst = f'variants/oc-altar-{name}'
subprocess.run(['./copybot', '-f', 'variants/oc-altar-dev', dst], check=True, cwd='/home/ubuntu/cambc-autumn',
               stdout=subprocess.DEVNULL)
p = f'/home/ubuntu/cambc-autumn/bots/{dst}/src/params.h'
s = open(p).read()
i = s.index('namespace altar {'); j = s.index('} // namespace altar')
blk = s[i:j]
for kv in sets:
    k, v = kv.split('=')
    blk, n = re.subn(rf'(\b{k} = )[^,;]+', rf'\g<1>{v}', blk)
    assert n == 1, kv
open(p, 'w').write(s[:i] + blk + s[j:])
print(dst)
