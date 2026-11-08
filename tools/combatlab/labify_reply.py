"""A combat-lab copy of a reply-model bot (bots/variants/oc-reply and its kin): labify.py, then the feature block.

    python3 tools/combatlab/labify_reply.py BOT DST [--off]

The copy also holds a 8 KiB feature block (magic "CAMBC-LAB-FEAT-1") that `fastrunner scenario --hitlog` copies
into each turn's hit record: at the end of every play turn the bot writes reply::dump's rows (combat/reply.cc),
our end tile's danger and pressure features against each visible enemy within 8. --off compiles the reply terms
out (params::reply::on false), so the copy plays as its base while logging. Rebuild with `cambc build bots/DST`.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

FEAT = """
// The reply model's feature block (tools/combatlab/labify_reply.py): read by `fastrunner scenario --hitlog`.
struct LabFeat {
    char magic[16];
    std::uint32_t version, size;
    std::int32_t round;
    std::uint32_t used; // bytes of data written this round
    float data[2048];
};
extern "C" {
[[gnu::used, gnu::visibility("default")]] inline LabFeat cambc_feat = {{'C', 'A', 'M', 'B', 'C', '-', 'L', 'A', 'B', '-', 'F', 'E', 'A', 'T', '-', '1'}, 1, sizeof(LabFeat), -1, 0, {}};
}
"""


def sub(text, old, new, what, scope=None):
    """labify.py's: replace the one occurrence of `old` (within the function starting at `scope`)."""
    lo, hi = 0, len(text)
    if scope:
        if text.count(scope) != 1:
            sys.exit(f"labify_reply: {what}: scope found {text.count(scope)} times")
        lo = text.index(scope)
        hi = text.index("\n}\n", lo) + 3
    part = text[lo:hi]
    if part.count(old) != 1:
        sys.exit(f"labify_reply: {what}: anchor {old[:70]!r} found {part.count(old)} times")
    return text[:lo] + part.replace(old, new) + text[hi:]


def patch(path, edits):
    s = path.read_text()
    for e in edits:
        s = sub(s, *e)
    path.write_text(s)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    off = "--off" in sys.argv
    if len(args) != 2:
        sys.exit(__doc__)
    src, dst = args
    subprocess.run([sys.executable, str(HERE / "labify.py"), src, dst], check=True)
    d = ROOT / "bots" / dst.removeprefix("bots/") / "src"
    lab = d / "lab.h"
    lab.write_text(lab.read_text().rstrip() + "\n" + FEAT)
    PT = "void play_turn(World& world, Pathing& pathing, Memory& memory) {"
    patch(d / "bot.cc", [
        ("    Safety safety{world};\n", "    Safety safety{world};\n    const vec2 lab_here = world.me().pos;\n", "reply here", PT),
        ("    comms::claim(memory.claim);\n",
         "    if (lab_on() && !world.is_stale() && world.me().alive) try {\n"
         "            cambc_feat.used = 4u * static_cast<std::uint32_t>(reply::dump(world, safety, lab_here, cambc_feat.data, 2048));\n"
         "            cambc_feat.round = world.round;\n"
         "        } catch (...) {\n"
         "        }\n"
         "    comms::claim(memory.claim);\n", "reply dump", PT),
    ])
    bot = (d / "bot.cc").read_text()
    if '#include "combat/reply.h"' not in bot:
        (d / "bot.cc").write_text(bot.replace('#include "bot_parts.h"\n', '#include "bot_parts.h"\n#include "combat/reply.h"\n', 1))
        assert '#include "combat/reply.h"' in (d / "bot.cc").read_text(), "bot.cc: no bot.h include to anchor on"
    if off:
        p = d / "params.h"
        s = p.read_text()
        old = "inline constexpr bool on = true; // reply model"
        assert s.count(old) == 1, "params.h: no reply on switch"
        p.write_text(s.replace(old, old.replace("true", "false")))
    print(f"labify_reply: bots/{dst.removeprefix('bots/')} ({'reply off' if off else 'reply on'})")


main()
