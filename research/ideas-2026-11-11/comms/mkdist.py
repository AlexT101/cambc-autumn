"""Build the distance variants on top of mkfinal.py's candidate: py mkdist.py NAME near|dist

A tile frame says how far the ally is from the centre of the group it claims.
near: exactly, within slot_near of it; farther off (or with no claim) the frame is its cell, as in mkfinal.py.
dist: exactly, up to the slot's last code ("farther"); no cells, so Willow's follow has no told tile."""
import pathlib, subprocess, sys
R = pathlib.Path(__file__).resolve().parents[3]
name, mode = sys.argv[1], sys.argv[2]
assert mode in ('near', 'dist')
near = mode == 'near'
subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name('mkfinal.py')), name], check=True, cwd=R)
src = R / 'bots/variants' / name / 'src'
SZ = 'static_cast<std::size_t>'

def edit(path, pairs):
    p = src / path
    s = p.read_text()
    for old, new in pairs:
        assert s.count(old) == 1, (path, old[:60], s.count(old))
        s = s.replace(old, new)
    p.write_text(s)

edit('params.h', [("""and every slot_refresh rounds, and the ally's own tile otherwise (a c x c cell, c the
// smallest that fits). It replaces comms_ally's record. With it, a claimer out of sight still counts in
// its group's crew while the tile in its slot is no farther from the group than we are, by 2.
""", ("""and every slot_refresh rounds. Otherwise it says where the ally is: within slot_near of
// the centre of the group it claims, that distance; else its own tile (a c x c cell, c the smallest that
// fits). It replaces comms_ally's record. With it, a claimer out of sight still counts in its group's crew
// while that puts it no farther from the group than we are, by 2.
""" if near else """and every slot_refresh rounds, and otherwise how far the ally is from the centre of the
// group it claims. It replaces comms_ally's record. With it, a claimer out of sight still counts in its
// group's crew while that puts it no farther from the group than we are, by 2.
""")), ("inline constexpr int slot_refresh = 8;\n", "inline constexpr int slot_refresh = 8;\n" + ("""// The distance is exact while the ally could see the centre (the vision radius).
inline constexpr int slot_near = 9;
""" if near else ""))])

edit('economy/crew.cc', [("""            // Out of sight, the tile it posts (comms_slots) says whether it is at the group.
            if (vec2 at{-1, -1}; !counts && params::comms_slots) {
                if (int told = -1; comms::told_ally(x.a->index, at, told)) {
                    const vec2 centre = allies.world->map().groups[g].centre;
                    counts = std::max(0, dist(at, centre) - x.a->facts().attack_range())
                             <= std::max(0, dist(allies.here, centre) - allies.world->me().facts().attack_range()) + 2;
                }
            }
""", """            // Out of sight, what it posts (comms_slots) says whether it is at the group.
            if (int d = 0; !counts && params::comms_slots) {
                if (const vec2 centre = allies.world->map().groups[g].centre; comms::told_distance(x.a->index, centre, d))
                    counts = std::max(0, d - x.a->facts().attack_range())
                             <= std::max(0, dist(allies.here, centre) - allies.world->me().facts().attack_range()) + 2;
            }
""")])

edit('model/comms.h', [("// With params::comms_slots: the centre of the cell in its slot now, posted at its latest turn.\n",
                        ("// With params::comms_slots: the centre of the cell in its slot now, posted at its latest turn.\n" if near
                         else "// With params::comms_slots: never (a slot holds no tile).\n")),
    ("// What teammates posted since our previous turn, merged into the world.\n",
     "// params::comms_slots: how far an ally was from `centre`, the centre of the group it claims, at its latest\n"
     "// turn; false while its slot holds its claim.\n"
     "bool told_distance(int ally, vec2 centre, int& d);\n"
     "// What teammates posted since our previous turn, merged into the world.\n")])

told_k3 = f"""    if (const auto& L = layout_; L.pos_on) {{
        if (ally < 0 || ally >= L.team) return false;
        const int cell = static_cast<int>(L.claim[{SZ}(ally)].get(state.now)) - L.pos_base, h = L.cell / 2;
        if (cell < 0) return false;
        at = {{std::min(cell / L.cells_y * L.cell + h, L.max_x), std::min(cell % L.cells_y * L.cell + h, L.max_y)}};
        round = state.now_round;
        return true;
    }}
"""
claim_fn = "void claim(int group) { detail::posts.mine = group < max_group ? group : -1; }\n"
head = f"""bool told_distance(int ally, vec2 centre, int& d) {{
    const auto& L = layout_;
    if (!L.pos_on || ally < 0 || ally >= L.team) return false;
    const int code = static_cast<int>(L.claim[{SZ}(ally)].get(state.now)) - L.pos_base;
"""
if near:
    edit('model/comms.cc', [
        ("""    // comms_slots: a slot value below pos_base is a claim + 1, from it on a cell. pos_on: the cells fit.
    bool pos_on = false;
    int pos_base = 1 << 30, max_x = 0, max_y = 0;
""", """    // comms_slots: a slot value below pos_base is a claim + 1; from it on `near` distances to the claimed
    // group's centre, then a cell. pos_on: those fit.
    bool pos_on = false;
    int pos_base = 1 << 30, near = 0, max_x = 0, max_y = 0;
"""),
        ("            if (nx * ny <= room) L.cell = c, L.cells_y = static_cast<int>(ny), L.pos_base = base, L.pos_on = true;\n",
         "            if (nx * ny + static_cast<std::uint64_t>(params::slot_near) <= room)\n"
         "                L.cell = c, L.cells_y = static_cast<int>(ny), L.near = params::slot_near, L.pos_base = base, L.pos_on = true;\n"),
        ("            else value = static_cast<std::uint64_t>(L.pos_base + now.x / L.cell * L.cells_y + now.y / L.cell);\n",
         f"""            else {{
                const int d = claim != 0 ? dist(now, world.map().groups[{SZ}(mine)].centre) : L.near;
                value = static_cast<std::uint64_t>(L.pos_base + (d < L.near ? d : L.near + now.x / L.cell * L.cells_y + now.y / L.cell));
            }}
"""),
        (told_k3, told_k3.replace("- L.pos_base, h", "- L.pos_base - L.near, h")),
        (claim_fn, head + """    if (code < 0) return false;
    if (code < L.near) return d = code, true;
    vec2 at{-1, -1};
    int round = -1;
    if (!told_ally(ally, at, round)) return false;
    return d = dist(at, centre), true;
}

""" + claim_fn)])
else:
    edit('model/comms.cc', [
        ("""    // comms_slots: a slot value below pos_base is a claim + 1, from it on a cell. pos_on: the cells fit.
    bool pos_on = false;
    int pos_base = 1 << 30, max_x = 0, max_y = 0;
""", """    // comms_slots: a slot value below pos_base is a claim + 1; from it on `near` distances to the claimed
    // group's centre, then one value for "farther". pos_on: there is room for a distance.
    bool pos_on = false;
    int pos_base = 1 << 30, near = 0;
"""),
        ("""        for (int c = 1; c <= std::max(map.width, map.height) && !L.pos_on; ++c) {
            const auto nx = static_cast<std::uint64_t>((map.width + c - 1) / c), ny = static_cast<std::uint64_t>((map.height + c - 1) / c);
            if (nx * ny <= room) L.cell = c, L.cells_y = static_cast<int>(ny), L.pos_base = base, L.pos_on = true;
        }
        L.max_x = map.width - 1, L.max_y = map.height - 1;
""", """        if (room >= 2) L.near = static_cast<int>(room) - 1, L.pos_base = base, L.pos_on = true;
"""),
        ("            else value = static_cast<std::uint64_t>(L.pos_base + now.x / L.cell * L.cells_y + now.y / L.cell);\n",
         f"            else value = static_cast<std::uint64_t>(L.pos_base + (claim != 0 ? std::min(dist(now, world.map().groups[{SZ}(mine)].centre), L.near) : L.near));\n"),
        (told_k3, "    if (layout_.pos_on) return false;\n"),
        (claim_fn, head + """    if (code < 0 || code >= L.near) return false;
    return d = code, true;
}

""" + claim_fn)])
print(name, mode)
