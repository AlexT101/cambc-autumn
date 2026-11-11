"""Build the merge candidate from variants/oc-dfuel-506: py mkfinal.py NAME

NAME = base + slot comms (claim on change, else the ally's tile as a 2D cell, decoded on demand from the
word read this turn: no per-turn state on the reader) + the crew count from told tiles."""
import pathlib, subprocess, sys
R = pathlib.Path(__file__).resolve().parents[3]
name = sys.argv[1]
subprocess.run([str(R / 'copybot'), '-f', 'variants/oc-dfuel-506', f'variants/{name}'], check=True, cwd=R)
src = R / 'bots/variants' / name / 'src'
SZ = 'static_cast<std::size_t>'

def edit(path, pairs):
    p = src / path
    s = p.read_text()
    for old, new in pairs:
        assert s.count(old) == 1, (path, old[:60], s.count(old))
        s = s.replace(old, new)
    p.write_text(s)

edit('params.h', [("inline constexpr bool comms_ally = true;\n", """inline constexpr bool comms_ally = true;
// Slot comms: each ally's claim field is one slot, as wide as the shared bytes allow after the bag and camp
// records. It holds the claim when that changes (for two turns, so teammates on both sides of the turn
// order read it) and every slot_refresh rounds, and the ally's own tile otherwise (a c x c cell, c the
// smallest that fits). It replaces comms_ally's record. With it, a claimer out of sight still counts in
// its group's crew while the tile in its slot is no farther from the group than we are, by 2.
inline constexpr bool comms_slots = true;
inline constexpr int slot_refresh = 8;
""")])

edit('bot_parts.h', [("""    vec2 here{};
    // The living allies other than us that claim a group, in ally order""", """    vec2 here{};
    const World* world = nullptr;
    // The living allies other than us that claim a group, in ally order""")])

edit('economy/crew.cc', [("""    out.here = {me.x, me.y};
""", """    out.here = {me.x, me.y};
    out.world = &world;
"""), (f"""        if (const int i = allies.claiming[{SZ}(k)]; allies.at[{SZ}(i)].seen && allies.at[{SZ}(i)].claim == g)
            bits |= 1u << i;
""", f"""        if (const int i = allies.claiming[{SZ}(k)]; allies.at[{SZ}(i)].claim == g) {{
            const auto& x = allies.at[{SZ}(i)];
            bool counts = x.seen;
            // Out of sight, the tile it posts (comms_slots) says whether it is at the group.
            if (vec2 at{{-1, -1}}; !counts && params::comms_slots) {{
                if (int told = -1; comms::told_ally(x.a->index, at, told)) {{
                    const vec2 centre = allies.world->map().groups[g].centre;
                    counts = std::max(0, dist(at, centre) - x.a->facts().attack_range())
                             <= std::max(0, dist(allies.here, centre) - allies.world->me().facts().attack_range()) + 2;
                }}
            }}
            if (counts) bits |= 1u << i;
        }}
""")])

edit('main.cc', [("aph::comms::send(*world, moved, refresh);", "aph::comms::send(*world, now, moved, refresh);")])
edit('model/comms.h', [("void send(World& world, bool moved, bool refresh);", "void send(World& world, vec2 now, bool moved, bool refresh);"),
    ("// An ally's (by index) own position as it last posted it (params::comms_ally), to within 2; false if never.\n",
     "// An ally's (by index) own position as it last posted it (params::comms_ally), to within 2; false if never.\n"
     "// With params::comms_slots: the centre of the cell in its slot now, posted at its latest turn.\n")])

edit('model/comms.cc', [("""    int cell = 1, cells_y = 1;
""", """    int cell = 1, cells_y = 1;
    // comms_slots: a slot value below pos_base is a claim + 1, from it on a cell. pos_on: the cells fit.
    bool pos_on = false;
    int pos_base = 1 << 30, max_x = 0, max_y = 0;
"""), (f"""    for (int i = 0; i < L.team; ++i) L.claim[{SZ}(i)] = field(claim_width);
    L.bag = field(bag_width);
    const int camp_width = static_cast<int>(std::bit_width(static_cast<std::uint64_t>(L.camp_offset.back())));
""", f"""    const int camp_width = static_cast<int>(std::bit_width(static_cast<std::uint64_t>(L.camp_offset.back())));
    // The camp record stays wherever it fitted before; the slots share what is left.
    const bool camp_fits = L.team * claim_width + bag_width + camp_width <= 64;
    const int slot_width = params::comms_slots ? std::min(16, (64 - bag_width - (camp_fits ? camp_width : 0)) / L.team) : claim_width;
    for (int i = 0; i < L.team; ++i) L.claim[{SZ}(i)] = field(slot_width);
    L.bag = field(bag_width);
"""), ("""    if (params::comms_ally && L.camp_on)
""", """    if (params::comms_slots) {
        const int base = std::min(groups, L.claim_cap) + 1;
        const auto room = (std::uint64_t{1} << slot_width) - static_cast<std::uint64_t>(base);
        for (int c = 1; c <= std::max(map.width, map.height) && !L.pos_on; ++c) {
            const auto nx = static_cast<std::uint64_t>((map.width + c - 1) / c), ny = static_cast<std::uint64_t>((map.height + c - 1) / c);
            if (nx * ny <= room) L.cell = c, L.cells_y = static_cast<int>(ny), L.pos_base = base, L.pos_on = true;
        }
        L.max_x = map.width - 1, L.max_y = map.height - 1;
    }
    if (params::comms_ally && L.camp_on && !params::comms_slots)
"""), ("""std::array<Told, 8> told_allies;
""", """std::array<Told, 8> told_allies;

// comms_slots, our own slot: the claim as last posted, the turns it still stays up, and its round.
struct Slot {
    std::uint64_t claim = 0;
    int hold = 0, round = -(1 << 20);
};
Slot slot;
"""), (f"""        detail::posts.claims[a.index] = p >= 0 ? static_cast<int>(p & 0xff) - 1 : static_cast<int>(L.claim[{SZ}(a.index)].get(bits)) - 1;
""", f"""        // A slot holding a tile leaves the claim as last read.
        if (const int v = static_cast<int>(L.claim[{SZ}(a.index)].get(bits)); p >= 0) detail::posts.claims[a.index] = static_cast<int>(p & 0xff) - 1;
        else if (v < L.pos_base) detail::posts.claims[a.index] = v - 1;
"""), ("""        if (field.get(bits) != claim) field.set(bits, claim), dirty = true;
""", """        auto value = claim;
        if (L.pos_on) {
            if (claim != slot.claim) slot.claim = claim, slot.hold = 1, slot.round = round;
            else if (slot.hold > 0) --slot.hold, slot.round = round;
            else if (round - slot.round >= params::slot_refresh || !world.me().alive || now.x < 0) slot.round = round;
            else value = static_cast<std::uint64_t>(L.pos_base + now.x / L.cell * L.cells_y + now.y / L.cell);
        }
        if (field.get(bits) != value) field.set(bits, value), dirty = true;
"""), ("void send(World& world, bool moved, bool refresh) {", "void send(World& world, vec2 now, bool moved, bool refresh) {"),
    ("""bool told_ally(int ally, vec2& at, int& round) {
""", f"""bool told_ally(int ally, vec2& at, int& round) {{
    if (const auto& L = layout_; L.pos_on) {{
        if (ally < 0 || ally >= L.team) return false;
        const int cell = static_cast<int>(L.claim[{SZ}(ally)].get(state.now)) - L.pos_base, h = L.cell / 2;
        if (cell < 0) return false;
        at = {{std::min(cell / L.cells_y * L.cell + h, L.max_x), std::min(cell % L.cells_y * L.cell + h, L.max_y)}};
        round = state.now_round;
        return true;
    }}
""")])
print(name)
