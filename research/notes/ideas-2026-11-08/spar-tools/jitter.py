"""Seeded spar copies: SRC (a spar bot dir, F or M) -> DST with a few float knobs scaled by 1 + SD * N(0, 1), so
deterministic games re-draw their chaotic outcomes at about the same strength.   py jitter.py SRC DST SEED [SD]"""
import sys, re, random, subprocess
from pathlib import Path
R = Path('/home/ubuntu/cambc-autumn')
src, dst, seed = sys.argv[1], sys.argv[2], int(sys.argv[3]); sd = float(sys.argv[4]) if len(sys.argv) > 4 else 0.03
KNOBS = ['life_value', 'gem_value', 'camp_risk', 'home_power', 'crew_stickiness', 'chip_value', 'hurt_retreat_ratio', 'home_retreat_ratio']
subprocess.run([str(R / 'copybot'), '-f', src, dst], check=True, capture_output=True)
p = R / 'bots' / dst.removeprefix('bots/') / 'src/params.h'; s = p.read_text(); rng = random.Random(seed)
for k in KNOBS:
    m = re.search(rf'^inline constexpr float {k} = ([0-9.]+)f;', s, re.M); assert m, k
    v = float(m[1]) * (1 + sd * rng.gauss(0, 1))
    s = s[:m.start(1)] + f'{v:.6g}' + s[m.end(1):]
p.write_text(s)
