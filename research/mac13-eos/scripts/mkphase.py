#!/usr/bin/env python3
"""Phase-knob probe variants: bots/variants/ph-<id>-<o|m>-<u|d>, copies of ph-base with one knob set.

    python3 research/mac13-eos/scripts/mkphase.py        # (re)creates all 24 (copybot -f)
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PHASES = {"o": (1, 200), "m": (201, 500)}
# id: (up, down) multipliers. 3: home_power's exponent; 4: mid_exposure's premium over 1.
MULTS = {1: (1.4, 0.7), 2: (1.4, 0.7), 3: (2.0, 0.5), 4: (2.0, 0.0), 5: (1.4, 0.7), 6: (1.4, 0.7)}


def main():
    for knob, (up, down) in MULTS.items():
        for ph, (lo, hi) in PHASES.items():
            for tag, mult in (("u", up), ("d", down)):
                name = f"ph-{knob}-{ph}-{tag}"
                subprocess.run([str(ROOT / "copybot"), "-f", "variants/ph-base", f"variants/{name}"], check=True, stdout=subprocess.DEVNULL)
                path = ROOT / "bots/variants" / name / "src/params.h"
                s = path.read_text()
                block = (f"namespace phaseknob {{\nconstexpr int which = {knob};\n"
                         f"constexpr int lo = {lo}, hi = {hi};\nconstexpr float mult = {mult}f;\n}} // namespace phaseknob")
                s, n = re.subn(r"namespace phaseknob \{.*?\} // namespace phaseknob", block, s, flags=re.S)
                assert n == 1, name
                path.write_text(s)
                print(name, knob, lo, hi, mult)


if __name__ == "__main__":
    main()
