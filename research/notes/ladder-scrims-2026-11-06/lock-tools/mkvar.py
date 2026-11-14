#!/usr/bin/env python3
"""mkvar.py NAME key=value...: bots/variants/oc-lock-NAME = bots/variants/oc-lock-dev with params::plock knobs set.

    mkvar.py l1 on=true seek_steps=12
    mkvar.py h1t on=true holders=1 timed=true margin=1
"""
import re, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
name, sets = sys.argv[1], sys.argv[2:]
dst = ROOT / 'bots/variants' / f'oc-lock-{name}'
subprocess.run([str(ROOT / 'tools' / 'copybot'), '-f', 'variants/oc-lock-dev', f'variants/oc-lock-{name}'], check=True, stdout=subprocess.DEVNULL)
p = dst / 'src/params.h'
s = p.read_text()
head, body = s.split('namespace plock {', 1)
body, tail = body.split('} // namespace plock', 1)
for kv in sets:
    k, v = kv.split('=', 1)
    body, n = re.subn(rf'(inline constexpr (?:bool|int|float) {k} = )[^;]+;', rf'\g<1>{v};', body)
    if n != 1: sys.exit(f'mkvar: knob {k} not found')
p.write_text(head + 'namespace plock {' + body + '} // namespace plock' + tail)
print(dst.relative_to(ROOT), ' '.join(sets))
