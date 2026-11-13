"""Instrument a copy of nyx-vl(-fuel)'s place_ward with WPROF lines (debug_block): python3 wardprof_patch.py BOT/src/bot.cc"""
import sys
p = sys.argv[1]
s = open(p).read()
def rep(a, b):
    global s
    assert s.count(a) == 1, a
    s = s.replace(a, b)
rep("""bool place_ward(const World& world, Memory& memory, bool start) {
    world.throw_if_stale();""", """struct WardProf {
    bool start; int round; std::uint64_t t0, t_memo = 0, t_grow = 0, t_site = 0, t_old = 0, t_cand = 0; int ncand = 0, exitc = 0, site_built = 0;
    ~WardProf() {
        const std::uint64_t t1 = fuel();
        debug_block({ std::printf("WPROF %d %u %d %llu %llu %llu %llu %llu %llu %llu %d %d %d\\n", round, my_handle(), start ? 1 : 0,
            (unsigned long long)t0, (unsigned long long)(t0 - t1), (unsigned long long)t_memo, (unsigned long long)t_grow,
            (unsigned long long)t_site, (unsigned long long)t_old, (unsigned long long)t_cand, ncand, exitc, site_built); });
    }
};
bool place_ward(const World& world, Memory& memory, bool start) {
    world.throw_if_stale();""")
rep("""    const vec2 here = my_position();
    if (here.x < 0) return false;
    int site = ward_site(map, memory);""", """    const vec2 here = my_position();
    if (here.x < 0) return false;
    WardProf wp{start, world.round, fuel()};
    std::uint64_t mark = wp.t0;
    const auto lap = [&](std::uint64_t& slot) { const auto f = fuel(); slot += mark - f; mark = f; };
    int site = ward_site(map, memory);""")
rep("""    if (looked.here == here && looked.ward == memory.ward && looked.site == site && looked.allied == allied_near) return false;""",
    """    lap(wp.t_memo);
    if (looked.here == here && looked.ward == memory.ward && looked.site == site && looked.allied == allied_near) { wp.exitc = 1; return false; }""")
rep("""    // Growth may have spent down to its floor.""", """    lap(wp.t_grow);
    // Growth may have spent down to its floor.""")
rep("""        boards_site = -1; // the boards are rewritten whether or not they finish""", """        boards_site = -1; // the boards are rewritten whether or not they finish
        wp.site_built = 1;""")
if "    bool boards = false;\n" in s:
    rep("    bool boards = false;\n", "    lap(wp.t_site);\n    bool boards = false;\n")
elif "    champion_sight_into(map, here, own);\n    for (auto* b" in s:
    rep("    champion_sight_into(map, here, own);\n    for (auto* b", "    lap(wp.t_site);\n    champion_sight_into(map, here, own);\n    for (auto* b")
else:
    rep("""    ward_sight_from(map, here, vision_radius, own);
    for (auto* b""", """    lap(wp.t_site);
    ward_sight_from(map, here, vision_radius, own);
    for (auto* b""")
rep("""    const auto remember = [&] { looked = {here, memory.ward, asked_site, allied_near}; };""", """    lap(wp.t_old);
    const auto remember = [&] { looked = {here, memory.ward, asked_site, allied_near}; };""")
rep("""        if (site == asked_site) remember();
        return false;
    }""", """        if (site == asked_site) remember();
        wp.exitc = 2;
        return false;
    }""")
a = "        const int v = ward_value(map, p, near, far);\n" if "const int v = ward_value(map, p, near, far);" in s else "        const int v = value(p);\n"
rep(a, a + "        ++wp.ncand;\n")
tail = "    if (!start && !cut && n == 0 && site == asked_site) remember();" if "if (!start && !cut" in s else "    if (!cut && n == 0 && site == asked_site) remember();"
rep(tail, "    lap(wp.t_cand);\n    wp.exitc = cut ? 4 : n == 0 ? 3 : 5;\n" + tail)
open(p, "w").write(s)
