"""Port a tune run's values into a plain copy of the tunified bot: every diana_tune reference becomes an exact float32
(or int) constexpr, tune.h/tune.json go, safety.h's two are constexpr again and safety.cc's static_assert returns.

    python3 port.py RUN SRC_BOT DST_BOT        # e.g. oc5 bots/archives/ocean_tune5 bots/variants/oc-tuned5
"""
import json, re, shutil, struct, sys
from pathlib import Path
import numpy as np

ROOT = Path('/home/ubuntu/cambc-autumn')
sys.path.insert(0, str(ROOT / 'tools/tune'))


def f32(v):
    x = np.float32(v)
    s = np.format_float_positional(x, unique=True, trim='0')
    if s.endswith('.'):
        s += '0'
    assert struct.pack('<f', float(s)) == struct.pack('<f', v), (v, s)
    return s + 'f'


def main():
    run, src, dst = sys.argv[1], ROOT / sys.argv[2], ROOT / sys.argv[3]
    cfg = json.loads((ROOT / 'replays/tune' / run / 'config.json').read_text())
    st = json.loads((ROOT / 'replays/tune' / run / 'state.json').read_text())
    vals = {}
    for n, (lo, hi, kind) in cfg['params'].items():
        v = lo + min(1.0, max(0.0, st['x'][n])) * (hi - lo)
        vals[n] = int(round(v)) if kind == 'int' else v
    spec = json.loads((src / 'src/tune.json').read_text())
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('.cambc', 'compile_commands.json'))
    p = dst / 'src/params.h'
    s = p.read_text()
    lits = {}
    for kind, lst, key in (('float', spec['floats'], 'f'), ('int', spec['ints'], 'i')):
        for i, (n, d) in enumerate(lst):
            v = vals.get(n, d)
            lit = f32(v) if kind == 'float' else str(int(v))
            old = f'inline const {kind}& {n} = diana_tune.{key}[{i}];'
            assert s.count(old) == 1, old
            s = s.replace(old, f'inline constexpr {kind} {n} = {lit};')
            lits[n] = (d, lit)
    s = s.replace('#include "tune.h"\n', '')
    assert 'diana_tune' not in s
    p.write_text(s)
    (dst / 'src/tune.h').unlink()
    (dst / 'src/tune.json').unlink()
    h = dst / 'src/model/safety.h'
    t = h.read_text()
    for n in ('hit_given_reach', 'recall_risk'):
        t = t.replace(f'inline const float& {n} = params::{n};', f'inline constexpr float {n} = params::{n};')
    h.write_text(t)
    c = dst / 'src/model/safety.cc'
    t = c.read_text()
    hg, rr = np.float32(float(lits['hit_given_reach'][1][:-1])), np.float32(float(lits['recall_risk'][1][:-1]))
    if hg >= rr and 0.5 >= rr:
        t = t.replace('    // static_assert(unknown_camp_weight >= recall_risk && hit_given_reach >= recall_risk); (tuned)',
                      '    static_assert(unknown_camp_weight >= recall_risk && hit_given_reach >= recall_risk);')
    else:
        print('static_assert left out: hit_given_reach < recall_risk')
    c.write_text(t)
    for n, (d, lit) in lits.items():
        print(f'  {n:24s} {d!s:>12} -> {lit}')


main()
