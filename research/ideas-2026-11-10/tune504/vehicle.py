"""Exact-site tunification and plain-source export, without building or playing."""
import argparse
import json
import math
from pathlib import Path
import re
import shutil
import struct

HERE = Path(__file__).resolve().parent
R = HERE.parents[2]
SPEC = json.loads((HERE / 'parameters.json').read_text())
MAGIC = 'DIANA-TUNE-BLK1'


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def literal(x):
    s = repr(f32(x))
    return s + ('f' if '.' in s or 'e' in s else '.0f')


def transform(originals, values=None):
    out = dict(originals)
    vehicle = values is None
    if not vehicle:
        assert set(values) == {p['name'] for p in SPEC['parameters']}
    for i, p in enumerate(SPEC['parameters']):
        file, old = p['file'], p['original']
        assert out[file].count(old) == 1, (file, p['name'], 'site drift')
        if vehicle:
            ref = f'diana_tune.f[{i}]'
            if p['name'] == 'cycle_horizon_scale':
                new = old.replace('return 100 *', f'return {ref} *')
            else:
                lead = 'inline ' if old.startswith('inline ') else ''
                qualifier = '' if p['mutable'] else 'const '
                new = f"{lead}{qualifier}float& {p['symbol']} = {ref};"
        else:
            v = values[p['name']]
            assert math.isfinite(v) and p['range'][0] <= v <= p['range'][1], p['name']
            if f32(v) == f32(p['default']):
                new = old  # Defaults reconstruct the source byte for byte, including the integer100 expression.
            elif p['name'] == 'cycle_horizon_scale':
                new = old.replace('return 100 *', f'return {literal(v)} *')
            else:
                new = old[:old.index('=') + 1] + ' ' + literal(v) + ';'
        out[file] = out[file].replace(old, new, 1)
    if vehicle:
        assert out['params.h'].count('#include <cambc.h>') == 1
        out['params.h'] = out['params.h'].replace('#include <cambc.h>', '#include <cambc.h>\n#include "tune.h"')
        fs = ', '.join(literal(p['default']) for p in SPEC['parameters'])
        out['tune.h'] = f'''#pragma once
// This block is patched only in isolated training copies.
struct DianaTune {{ char magic[16]; float f[{len(SPEC['parameters'])}]; int i[1]; }};
extern "C" {{
[[gnu::used, gnu::visibility("default")]] inline DianaTune diana_tune = {{"{MAGIC}", {{{fs}}}, {{0}}}};
}}
'''
        out['tune.json'] = json.dumps({'magic': MAGIC, 'floats': [[p['name'], p['default']] for p in SPEC['parameters']], 'ints': []}, indent=1) + '\n'
    return out


def make(destination, values=None):
    base = R / 'bots' / SPEC['base']
    assert not destination.exists(), f'Refusing overwrite: {destination}'
    shutil.copytree(base, destination, ignore=shutil.ignore_patterns('.cambc', 'build', 'target', '.cache', 'compile_commands.json'))
    src = base / 'src'
    originals = {str(p.relative_to(src)): p.read_text() for p in src.rglob('*') if p.is_file()}
    changed = transform(originals, values)
    for file, content in changed.items():
        (destination / 'src' / file).write_text(content)
    assert set(changed) == set(originals) | ({'tune.h', 'tune.json'} if values is None else set())


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('destination', type=Path)
    ap.add_argument('--values', type=Path)
    a = ap.parse_args()
    make(a.destination, json.loads(a.values.read_text()) if a.values else None)
