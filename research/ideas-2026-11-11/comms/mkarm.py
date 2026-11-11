"""Freeze an arm of the comms dev copy: py mkarm.py NAME [knob=value ...] [--from variants/cm2-dev]

Copies the dev copy to bots/variants/NAME and sets `inline constexpr <type> knob = value;` in its params.h."""
import pathlib, re, subprocess, sys
R = pathlib.Path(__file__).resolve().parents[3]
args = sys.argv[1:]
src = 'variants/cm2-dev'
if '--from' in args:
    i = args.index('--from'); src = args[i + 1]; del args[i:i + 2]
name, knobs = args[0], dict(a.split('=') for a in args[1:])
subprocess.run([str(R / 'copybot'), '-f', src, f'variants/{name}'], check=True, cwd=R)
p = R / 'bots/variants' / name / 'src/params.h'
s = p.read_text()
for k, v in knobs.items():
    s, n = re.subn(rf'(inline constexpr \w+ {k} = )[^;]+;', rf'\g<1>{v};', s)
    assert n == 1, k
p.write_text(s)
print(name, knobs)
