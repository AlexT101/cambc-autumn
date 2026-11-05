"""mklite.py SRC DST: bots/DST = bots/SRC + one "ML round handle o b c k n L" line per farm loop (debug_block):
opening, banking, cut, groups reached, groups, the loop's fuel."""
import shutil, sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
src, dst = root / "bots" / sys.argv[1], root / "bots" / sys.argv[2]
if dst.exists():
    shutil.rmtree(dst)
shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".cambc", "build", "target", ".cache", "compile_commands.json"))
f = dst / "src/economy/farm.cc"
s = f.read_text()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a)
    s = s.replace(a, b)


rep("""    int k = 0;
    for (; k < evaluated && room(); ++k) {
""", """    int k = 0;
    std::uint64_t ml_start = 0;
    debug_block({ ml_start = fuel(); });
    for (; k < evaluated && room(); ++k) {
""")
rep("""    if (k < evaluated) note_shortcut("farm-partial-evaluation");
""", """    debug_block({
        if (!cambc::is_draft())
            std::printf("ML %d %u %d %d %d %d %d %llu\\n", cambc::round_number(), static_cast<unsigned>(static_cast<cambc::handle_champion_t>(cambc::self())),
                        opening ? 1 : 0, banks_bag ? 1 : 0, k < evaluated ? 1 : 0, k, n_groups, (unsigned long long)(ml_start - fuel()));
    });
    if (k < evaluated) note_shortcut("farm-partial-evaluation");
""")
f.write_text(s)
print("patched", f)
