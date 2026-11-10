"""Check the actual ChampionFacts arithmetic against its old formula, bit for bit.
The SDK stub supplies only metadata types; this pure arithmetic check uses no host calls.
Usage: py check_output.py [bots/ocean]
"""
from pathlib import Path
import subprocess, sys, tempfile
root = Path(__file__).resolve().parents[3]
bot = root / (sys.argv[1] if len(sys.argv) > 1 else 'bots/ocean')
with tempfile.TemporaryDirectory() as d:
    p = Path(d)
    (p/'cambc.h').write_text('''#pragma once
namespace cambc {
enum class champion_type { ryth, vesper_vale, vendetta, cassi, issac, stellar, prism, marcella, willow, ren, varg, tavi, heart_of_ruin };
namespace constants::passive_abilities {
inline constexpr int varg_splash_radius = 1, marcella_tribute_gold_per_gem = 2;
inline constexpr float ren_retaliation_focus_ratio = 0.2f, heart_of_ruin_missing_health_damage_max_bonus = 0.5f;
}}
''')
    subprocess.run(['clang++','-std=c++20','-O2','-ffp-contract=off','-I',str(p),'-I',str(bot/'src'),str(Path(__file__).with_suffix('.cc')),'-o',str(p/'check')],check=True)
    subprocess.run([str(p/'check')],check=True)
