"""Segment marks for a v87-nof2 copy (checkpoint(need, file, line)): py gapinst3.py bots/variants/X/src (gap.h copied in first)."""
import sys
from pathlib import Path
S = Path(sys.argv[1])
def sub(name, pairs):
    p = S / name; s = p.read_text()
    for a, b in pairs:
        assert s.count(a) == 1, (name, a[:80]); s = s.replace(a, b)
    p.write_text(s)
RAW = "static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining())"
FL = "const char* file = __builtin_FILE(), int line = __builtin_LINE()"
sub("util.h", [
    ("#include <vector>\n", "#include <vector>\n#include \"gap.h\"\n"),
    ("    checkpoint(0, file, line);\n    return fuel() >= needed;\n",
     f"    checkpoint(0, file, line);\n    const bool ok = {RAW} >= needed;\n    debug_block({{ ::aph::gap::mark(file, line, ok ? 'g' : 'n', needed); }});\n    return ok;\n"),
    ("inline std::uint64_t fuel() { return static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining()); }",
     f"inline std::uint64_t fuel({FL}) {{ debug_block({{ ::aph::gap::mark(file, line, 'n', 0); }}); return {RAW}; }}"),
    (f"inline void checkpoint(std::uint64_t need = 0, {FL}) {{\n",
     f"inline void checkpoint(std::uint64_t need = 0, {FL}) {{\n    debug_block({{ ::aph::gap::mark(file, line, deadline_floor >= 8000 ? 'd' : deadline_floor ? 'q' : 'c', need); }});\n"),
])
sub("main.cc", [
    ("            instance.play_turn(late);\n",
     "        {\n            debug_block({ ::aph::gap::begin(); });\n            instance.play_turn(late);\n            debug_block({ ::aph::gap::end(aph::my_handle()); });\n        }\n"),
])
