"""Turn chosen params.h constants into reads of one patchable block (diana_tune) in the wasm's data.

    python3 tools/tune/tunify.py bots/archives/diana [NAME...]   # default: TUNABLE below

Each `inline constexpr float|int NAME = V;` becomes `inline const float& NAME = diana_tune.f[i];` (ints: .i[j]);
the block starts with a 16-byte magic so tune.py can find and patch it in .cambc/build/bot-injected.wasm.
Writes src/tune.h and src/tune.json ({"floats": [[name, default]...], "ints": [...]}).
"""
import json, re, sys
from pathlib import Path

TUNABLE = """recall_health_fraction safe_recall_health_fraction draft_recall_health_fraction hurt_health_fraction
finish_camp_health_fraction camp_risk home_power crew_trip_risk crew_stickiness crew_rival_factor mono_gather_share
mono_stickiness pair_hold_share hurt_retreat_ratio home_retreat_ratio heal_trip_fraction gold_farmer_weight
gold_price_scale siege_hit_share siege_pool_share siege_commit_slack siege_gather_share own_ground_share mid_low_share
mid_exposure mid_edge chip_value
threat_radius partner_radius crew_available_radius crew_near_radius crew_wait_rounds crew_seen_rounds crew_enemy_radius
crew_ban_rounds mono_max_wait help_radius pick_up_radius chain_bag_limit pack_ally_radius brake_bag
tribute_window max_wait siege_rounds siege_respawn_wait burst_rounds siege_max_wait kite_early siege_stickiness
ostrich_rounds track_horizon""".split()
MAGIC = "DIANA-TUNE-BLK1"  # 15 chars + NUL = 16 bytes

def main():
    bot = Path(sys.argv[1]); names = sys.argv[2:] or TUNABLE
    p = bot / "src" / "params.h"; s = p.read_text()
    fl, it = [], []
    for n in names:
        m = re.search(rf"inline constexpr (float|int) {n} = ([^;]+);", s)
        if not m: print("skip", n); continue
        kind, v = m.group(1), m.group(2).strip().rstrip("f")
        try: val = float(v) if kind == "float" else int(v)
        except ValueError: print("skip (not a literal)", n, v); continue
        lst = fl if kind == "float" else it
        ref = f"diana_tune.{'f' if kind == 'float' else 'i'}[{len(lst)}]"
        lst.append([n, val])
        s = s[:m.start()] + f"inline const {kind}& {n} = {ref};" + s[m.end():]
    # Constants defined from tuned ones stop being constant expressions.
    for n, _ in fl + it:
        s = re.sub(rf"inline constexpr (float|int) (\w+) = {n};", rf"inline const \1& \2 = {n};", s)
    if '#include "tune.h"' not in s:
        s = s.replace("#include <cambc.h>\n", '#include <cambc.h>\n#include "tune.h"\n', 1)
    p.write_text(s)
    fvals = ", ".join(f"{v!r}f" if "." in repr(v) or "e" in repr(v) else f"{v}.0f" for _, v in fl)
    ivals = ", ".join(str(v) for _, v in it)
    (bot / "src" / "tune.h").write_text(f"""#pragma once
// Tuned constants (tools/tune/tunify.py): tune.py patches the values after the magic in the built wasm.
struct DianaTune {{
    char magic[16];
    float f[{max(len(fl), 1)}];
    int i[{max(len(it), 1)}];
}};
extern "C" {{
[[gnu::used, gnu::visibility("default")]] inline DianaTune diana_tune = {{"{MAGIC}", {{{fvals}}}, {{{ivals}}}}};
}}
""")
    (bot / "src" / "tune.json").write_text(json.dumps({"magic": MAGIC, "floats": fl, "ints": it}, indent=1))
    print(len(fl), "floats,", len(it), "ints")

main()
