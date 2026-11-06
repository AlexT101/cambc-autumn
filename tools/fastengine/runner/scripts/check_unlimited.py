"""Check native unlimited fuel, side swapping, and default parity against stock.

Run from the repository root: python3 tools/fastengine/runner/scripts/check_unlimited.py
"""
from pathlib import Path
import os
import re
import struct
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[4]
RUNNER = ROOT / "tools/fastengine/runner/fastrunner"
SOURCE = r'''
#include <cambc.h>
#include <cstdio>
int main() {
    while (true) {
        if (!cambc::is_draft()) {
            const unsigned before = cambc::round_number();
            volatile unsigned work = 0;
            for (unsigned i = 0; i < 50000; ++i) work = work + i;
            std::printf("WORK %u %u %u\n", before, cambc::round_number(), unsigned(work));
        }
        cambc::end_turn();
    }
}
'''


def main():
    env = os.environ.copy()
    env["FASTRUNNER_MODE"] = "native"
    env.pop("FASTRUNNER_UNLIMITED_BOTS", None)
    env.pop("FASTRUNNER_BOT_FUEL", None)
    with tempfile.TemporaryDirectory(prefix="teacher-fuel-check-") as directory:
        root = Path(directory)
        bots = [root / "unlimited_probe", root / "normal_probe"]
        for bot in bots:
            (bot / "src").mkdir(parents=True)
            (bot / "src/main.cpp").write_text(SOURCE)

        def play(name, fast, unlimited=False, swap=False, quantum=None):
            out = root / name
            settings = env.copy()
            if unlimited:
                settings["FASTRUNNER_UNLIMITED_BOTS"] = bots[0].name
            if quantum:
                settings["FASTRUNNER_BOT_FUEL"] = f"{bots[0].name}:{quantum}"
            result = subprocess.run([str(RUNNER) if fast else "cambc", "run",
                                     *map(str, bots[::-1] if swap else bots), "--map", "00corners",
                                     "--rounds", "12", "-o", str(out)], cwd=ROOT, env=settings,
                                    capture_output=True, text=True)
            assert result.returncode == 0, result.stdout + result.stderr
            with zipfile.ZipFile(next(out.glob("*.repl26a"))) as z:
                return {n: z.read(n) for n in z.namelist() if not n.endswith(".debug")}

        stock, native = play("stock", False), play("native", True)
        assert stock == native, "default native replay/fuel/stdout differs from stock"
        for swap, quantum in ((False, None), (True, None), (False, 1000000), (True, 1000000)):
            game = play(f"unlimited-{swap}-{quantum}", True, quantum is None, swap, quantum)
            teacher, normal = ("b", "a") if swap else ("a", "b")
            def turns(side):
                return [(int(a), int(b)) for a, b in re.findall(rb"WORK (\d+) (\d+)", game[f"team-{side}.stdout"])]
            assert turns(teacher) and all(a == b for a, b in turns(teacher)), "teacher was suspended"
            assert any(a < b for a, b in turns(normal)), "normal opponent was not suspended"
            fuel = game[f"team-{teacher}.fuel"][77:]
            assert max(v[0] for v in struct.iter_unpack("<Q", fuel)) > 200_000, "teacher did not exceed the normal budget"
        print("PASS: default stock parity; unlimited and per-bot generous fuel complete work on both sides; normal opponent still exhausts fuel")


if __name__ == "__main__":
    main()
