"""Make bots/variants/lockpol-<tag> from lockpol-base, differing only in params::lock_policy (params.h)."""
import re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "bots/variants/lockpol-base"
VARIANTS = {
    "cancel": {"preempt": "false"},
    "preempt": {"cancel": "false", "hard_stop": "false"},
    "win": {"cancel_only_winning": "true", "preempt": "false"},
    "nohard": {"hard_stop": "false"},
    "alt2": {"buy_max_altars": "2"},
    "alt3": {"buy_max_altars": "3"},
    "eopt1": {"buy_max_enemy_options": "1"},
    "alt2-else-cancel": {"preempt_max_altars": "2"},
    "end500": {"buy_min_threat": "500"},
    "end700": {"buy_min_threat": "700", "threat_counts_bag": "true"},
    # Our side already holds the contested altars: on <= 3 altars add the enemy's side (its only option included).
    "contest": {"preempt_enemy_side": "true"},
    # Pre-emptive locks only where the enemy tributes too: contested altars (and the guarded one).
    "precontest": {"preempt_only_contested": "true"},
    "rich": {"buy_min_spent": "300"},
    "bag20": {"cancel_min_bag": "20", "preempt": "false"},
    # Extras: the hard-stop approach apart from the placements.
    "cancel-nohard": {"preempt": "false", "hard_stop": "false"},
    # Non-winning cancels only where the enemies could not kill us within tribute_window (lockuse: deaths after cancels).
    "safe": {"cancel_safe": "true"},
    "safe-cancel": {"cancel_safe": "true", "preempt": "false"},
    # Buys and carries locks but never places one nor counts it as a stop: the cost of buying alone.
    "inert": {"cancel": "false", "preempt": "false", "hard_stop": "false"},
    "win-nohard": {"cancel_only_winning": "true", "preempt": "false", "hard_stop": "false"},
}


def make(tag, sets):
    dst = ROOT / f"bots/variants/lockpol-{tag}"
    subprocess.run([str(ROOT / "copybot"), "-f", "variants/lockpol-base", f"variants/lockpol-{tag}"], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL)
    p = dst / "src/params.h"
    s = p.read_text()
    head, body = s.split("namespace lock_policy {", 1)
    block, tail = body.split("} // namespace lock_policy", 1)
    for k, v in sets.items():
        block, n = re.subn(rf"(inline constexpr (?:int|bool) {k} = )[^;]+;", rf"\g<1>{v};", block)
        assert n == 1, (tag, k)
    p.write_text(head + "namespace lock_policy {" + block + "} // namespace lock_policy" + tail)


if __name__ == "__main__":
    for tag in sys.argv[1:] or VARIANTS:
        make(tag, VARIANTS[tag])
        print(tag)
