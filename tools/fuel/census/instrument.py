"""Adds the fuel census's scopes to a copy of astraeus (debug-only instrumentation, never for a real bot).

    py tools/fuel/census/instrument.py bots/variants/astraeus-cen/src [--fine]

Copy tools/fuel/census/census.h into the src first. --fine adds scopes inside World::update, Safety, want_home and
the farm loop. Each replacement must match exactly once (checked against the bot as of CHANGES 220); a changed bot
fails loudly here. Scopes inside debug_block cost ~10 fuel each. The whole run is in tools/README.md (Fuel).
"""
import sys
from pathlib import Path

SRC = Path(sys.argv[1])
# --lenient skips (and lists) replacements that no longer match, for a partial census of a moved bot.
LENIENT = "--lenient" in sys.argv


def sub(name, pairs):
    p = SRC / name
    s = p.read_bytes().decode()
    crlf = "\r\n" in s
    for a, b in pairs:
        if crlf:
            a, b = a.replace("\n", "\r\n"), b.replace("\n", "\r\n")
        if LENIENT and s.count(a) != 1:
            print(f"skipped in {name}: {a.splitlines()[0].strip()[:90]}", file=sys.stderr)
            continue
        assert s.count(a) == 1, (name, a)
        s = s.replace(a, b)
    p.write_bytes(s.encode())


sub("util.h", [
    ("#include <vector>\n", "#include <vector>\n#include \"census.h\"\n"),
    ("    explicit FuelMeter(const char* label) : label_{label} {\n",
     "    explicit FuelMeter(const char* label) : label_{label} {\n        debug_block({ census::enter(label); });\n"),
    ("    ~FuelMeter() {\n", "    ~FuelMeter() {\n        debug_block({ census::exit(); });\n"),
])

sub("main.cc", [
    ("""template <class F> bool run(const char* phase, F&& f) {
    debug_block({ aph::fuel_phase() = phase; });
""", """template <class F> bool run(const char* phase, F&& f) {
    debug_block({ aph::fuel_phase() = phase; });
    CENSUS(phase);
"""),
    ("""    [[gnu::flatten]] void play_turn(bool late) {
""", """    [[gnu::flatten]] void play_turn(bool late) {
        debug_block({ aph::census::begin(late); });
"""),
    ("""            instance.play_turn(late);
""", """        {
            instance.play_turn(late);
            debug_block({ aph::census::end(); });
        }
"""),
])

CTX = """    debug_block({
        auto& c = census::st();
        c.type = static_cast<int>(world.me().type);
        for (const auto& e : world.enemies)
            if (e.alive && e.visible) ++c.enemies, c.near_enemies += dist(e.pos, world.me().pos) <= 6;
        for (const auto& a : world.allies)
            if (!a.is_self && a.alive && a.visible) ++c.allies;
        for (const auto& cb : world.camps) c.awake += cb.awake == Awake::awake;
    });
"""

sub("bot.cc", [
    ("""void play_turn(World& world, Pathing& pathing, Memory& memory) {
    Safety safety{world};
""", """void play_turn(World& world, Pathing& pathing, Memory& memory) {
""" + CTX + """    std::optional<Safety> safety_holder;
    {
        CENSUS("safety_ctor");
        safety_holder.emplace(world);
    }
    Safety& safety = *safety_holder;
"""),
    ("""    try {
        act(world, pathing, safety, memory);""", """    try {
        CENSUS("act");
        act(world, pathing, safety, memory);"""),
    ("""        if (!world.is_stale()) see_stuns(world, safety);
        set_turn_order(world, safety);""", """        CENSUS("turn_order");
        if (!world.is_stale()) see_stuns(world, safety);
        set_turn_order(world, safety);"""),
    ("""    if (!world.is_stale()) publish_turn_order(world, comms::priority_payload(world));""",
     """    if (!world.is_stale()) {
        CENSUS("publish_order");
        publish_turn_order(world, comms::priority_payload(world));
    }"""),
    ("""    if (const int g = walk_target(world, pathing, memory); g >= 0) pathing.approach(g, walk_range(world, g));
    const int claim = memory.claim;
    decide(world, pathing, safety, memory);""", """    if (const int g = walk_target(world, pathing, memory); g >= 0) {
        CENSUS("approach_walk");
        pathing.approach(g, walk_range(world, g));
    }
    const int claim = memory.claim;
    {
        CENSUS("decide_fn");
        decide(world, pathing, safety, memory);
    }"""),
    ("""    if (world.me().alive && see_revealed(world, pathing, safety)) search.chose = false;
    if (!support_owned && strike_after(world, pathing, safety).searched) note_search(true);""", """    {
        CENSUS("see_revealed");
        if (world.me().alive && see_revealed(world, pathing, safety)) search.chose = false;
    }
    {
        CENSUS("strike_after");
        if (!support_owned && strike_after(world, pathing, safety).searched) note_search(true);
    }
    CENSUS("act_end");"""),
    ("""    const bool leave = !mend && (home ? *home : want_home(world, pathing, safety, memory));""", """    bool leave;
    {
        CENSUS("want_home");
        leave = !mend && (home ? *home : want_home(world, pathing, safety, memory));
    }"""),
    ("""    const bool working = willow_free && support_work(world, pathing, safety, memory);
    const bool strikes = !working && strike_possible(world);""", """    bool working, strikes;
    {
        CENSUS("support_work");
        working = willow_free && support_work(world, pathing, safety, memory);
    }
    {
        CENSUS("strike_possible");
        strikes = !working && strike_possible(world);
    }"""),
    ("""    if (((prism && !mend) || (willow_free && !working)) && support_endpoint(world, !willow)
        && local_support(world, pathing, safety, memory, leave, mate_eligible))
        return;""", """    {
        CENSUS("local_support");
        if (((prism && !mend) || (willow_free && !working)) && support_endpoint(world, !willow)
            && local_support(world, pathing, safety, memory, leave, mate_eligible))
            return;
    }"""),
    ("""    if (leave) {
        retreat(world, pathing, safety, memory);
        return;
    }

    guard_steps(world, pathing, safety);
    if (join_marcella_capture(world, pathing, safety, memory)) return;
    if (yield_capture(world, pathing, safety, memory)) return;
    if (take_capture_handoff(world, pathing, safety, memory)) return;
    const bool contested = contesting(world);
    const bool holding = holding_capture(world, pathing) || contested;
    const bool attacked = strikes && search_strikes(world, pathing, safety, memory, holding, contested);""",
     """    if (leave) {
        CENSUS("retreat");
        retreat(world, pathing, safety, memory);
        return;
    }

    {
        CENSUS("guard_steps");
        guard_steps(world, pathing, safety);
    }
    {
        CENSUS("captures");
        if (join_marcella_capture(world, pathing, safety, memory)) return;
        if (yield_capture(world, pathing, safety, memory)) return;
        if (take_capture_handoff(world, pathing, safety, memory)) return;
    }
    bool contested, holding;
    {
        CENSUS("holding");
        contested = contesting(world);
        holding = holding_capture(world, pathing) || contested;
    }
    bool attacked;
    {
        CENSUS("strike_search");
        attacked = strikes && search_strikes(world, pathing, safety, memory, holding, contested);
    }"""),
    ("""    if (!my_can_attack() || !my_can_cast()) pathing.settle_guard(), see_stuns(world, safety), safety.refresh();
    // The guard was placed around the tile we started on: the goal steps from where the search left us.
    if (my_position() != world.turn_start && (my_can_move() || my_can_cast())) guard_steps(world, pathing, safety);""",
     """    {
        CENSUS("post_search");
        if (!my_can_attack() || !my_can_cast()) pathing.settle_guard(), see_stuns(world, safety), safety.refresh();
    }
    // The guard was placed around the tile we started on: the goal steps from where the search left us.
    if (my_position() != world.turn_start && (my_can_move() || my_can_cast())) {
        CENSUS("guard_steps2");
        guard_steps(world, pathing, safety);
    }"""),
    ("""    if (holding) {
        hold_capture(world, memory, attacked);
        return;
    }
    if (banks_bag(world, pathing)) {
        carry_bag(world, pathing, safety, memory, attacked);
        return;
    }""", """    if (holding) {
        CENSUS("hold_capture");
        hold_capture(world, memory, attacked);
        return;
    }
    if (banks_bag(world, pathing)) {
        CENSUS("carry_bag");
        carry_bag(world, pathing, safety, memory, attacked);
        return;
    }"""),
    ("""    if (my_can_move() && wants_shop(world, pathing, safety, memory)) {""",
     """    CENSUS("goal");
    if (my_can_move() && wants_shop(world, pathing, safety, memory)) {"""),
    ("""    if (chase(world, pathing, safety)) return;
    if (contest_capture(world, pathing, memory)) {""", """    {
        CENSUS("chase");
        if (chase(world, pathing, safety)) return;
    }
    if (contest_capture(world, pathing, memory)) {"""),
    ("""    if (world.map().shared_gems ? kite(world, pathing, memory) : siege(world, pathing, memory)) {
        decision = Branch::siege;
        return;
    }
    farm(world, pathing, safety, memory);""", """    {
        CENSUS("siege_kite");
        if (world.map().shared_gems ? kite(world, pathing, memory) : siege(world, pathing, memory)) {
            decision = Branch::siege;
            return;
        }
    }
    CENSUS("farm");
    farm(world, pathing, safety, memory);"""),
    ("""    if (state.contains(cambc::champion_state::submitting_gems) && continue_tribute(world, pathing, safety, memory, home)) return;
    if (state.contains(cambc::champion_state::recalling) && continue_recall(world, pathing, safety, memory, home, recall_farm)) return;""",
     """    {
        CENSUS("channels");
        if (state.contains(cambc::champion_state::submitting_gems) && continue_tribute(world, pathing, safety, memory, home)) return;
        if (state.contains(cambc::champion_state::recalling) && continue_recall(world, pathing, safety, memory, home, recall_farm)) return;
    }"""),
    ("""    if (place_ward(world, memory, false)) {
        see_again(world, pathing, safety);
        home.reset();
    }""", """    {
        CENSUS("ward_planned");
        if (place_ward(world, memory, false)) {
            see_again(world, pathing, safety);
            home.reset();
        }
    }"""),
    ("""    if (const auto* ender = game_ender(world)) {""", """    CENSUS("decide_main");
    if (const auto* ender = game_ender(world)) {"""),
])
if "--fine" in sys.argv:
    sub("model/world.cc", [
        ("""template <class F> void guard(const char* what, F&& f) {
    try {""", """template <class F> void guard(const char* what, F&& f) {
    CENSUS(what);
    try {"""),
        ("""    for (auto& b : enemies) guard("champion", [&] { update_champion(b, full); });""",
         """    for (auto& b : enemies) guard("champion_enemy", [&] { update_champion(b, full); });"""),
        ("""void World::read_vision() {
""", """void World::read_vision() {
    CENSUS("read_vision");
"""),
        ("""void World::rank_turns() {
""", """void World::rank_turns() {
    CENSUS("rank_turns");
"""),
    ])
    sub("model/safety.cc", [
        ("""Safety::Bound Safety::bound(vec2 p, float blow_scale) {
""", """Safety::Bound Safety::bound(vec2 p, float blow_scale) {
    CENSUS("s.bound");
"""),
        ("""Trade Safety::fight_of(std::uint32_t key, bool falls, std::uint32_t late, bool settle) {
""", """Trade Safety::fight_of(std::uint32_t key, bool falls, std::uint32_t late, bool settle) {
    CENSUS("s.fight_of");
"""),
        ("""Trade Safety::stand(vec2 p, int approach, bool falls, bool unseen, int joined) {
""", """Trade Safety::stand(vec2 p, int approach, bool falls, bool unseen, int joined) {
    CENSUS("s.stand");
"""),
        ("""bool Safety::lethal(vec2 p) {
""", """bool Safety::lethal(vec2 p) {
    CENSUS("s.lethal");
"""),
    ])
    sub("combat/fight.cc", [
        ("""bool outmatched(const World& world, Pathing& pathing, Safety& safety) {
""", """bool outmatched(const World& world, Pathing& pathing, Safety& safety) {
    CENSUS("wh.outmatched");
"""),
        ("""bool camp_trapped(const World& world, Pathing& pathing, Safety& safety, vec2 here, float health, bool sieging) {
""", """bool camp_trapped(const World& world, Pathing& pathing, Safety& safety, vec2 here, float health, bool sieging) {
    CENSUS("wh.camp_trapped");
"""),
    ])
    # farm_turn: its group loop, and the walk after it (farm's own self is what comes before the loop).
    sub("economy/farm.cc", [
        ("""    int k = 0;
    for (; k < evaluated && room(); ++k) {""", """    debug_block({ census::enter("farm.loop"); });
    int k = 0;
    for (; k < evaluated && room(); ++k) {"""),
        ("""    if (k < evaluated) note_shortcut("farm-partial-evaluation");""", """    debug_block({ census::exit(); });
    CENSUS("farm.post");
    if (k < evaluated) note_shortcut("farm-partial-evaluation");"""),
    ])
# --trace: every fuel() read and fuel_ok() check records its call site (census.h's CTR line).
if "--trace" in sys.argv:
    sub("util.h", [
        ("inline std::uint64_t fuel() { return static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining()); }",
         """inline std::uint64_t fuel(const char* file = __builtin_FILE(), int line = __builtin_LINE()) {
    const auto v = static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining());
    debug_block({ census::note('r', file, line, v, 0); });
    return v;
}"""),
        ("inline bool fuel_ok(std::uint64_t needed) { return fuel() >= needed; }",
         """inline bool fuel_ok(std::uint64_t needed, const char* file = __builtin_FILE(), int line = __builtin_LINE()) {
    const auto v = static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining());
    debug_block({ census::note(v >= needed ? 'c' : 'f', file, line, v, needed); });
    return v >= needed;
}"""),
    ])
if "--trace" in sys.argv:
    # farm's loop check reads fuel() raw: as a check, with what it needed.
    sub("economy/farm.cc", [
        ("        return left >= ample || left >= loop_floor + loop_reserve();",
         """        const bool ok = left >= ample || left >= loop_floor + loop_reserve();
        debug_block({ census::note(ok ? 'c' : 'f', __FILE__, __LINE__, left, left >= ample ? ample : loop_floor + loop_reserve()); });
        return ok;"""),
        ("        if (g < 0) return false;\n        if (map.any_group_hop() && beyond_walk(world, pathing, g)) return cross(g);",
         "        CENSUS(\"walk_on\");\n        if (g < 0) return false;\n        if (map.any_group_hop() && beyond_walk(world, pathing, g)) return cross(g);"),
    ])
    sub("economy/bank.cc", [
        ("    if (retaining_gems(world, pathing)) return;\n    world.throw_if_stale();\n    if (submit_here(world, safety, memory)) return;",
         "    CENSUS(\"bank_gems\");\n    if (retaining_gems(world, pathing)) return;\n    world.throw_if_stale();\n    if (submit_here(world, safety, memory)) return;"),
    ])
    sub("combat/guard.cc", [
        ("void step_safely(const World& world, Pathing& pathing, const Field& field, Safety& safety) {\n",
         "void step_safely(const World& world, Pathing& pathing, const Field& field, Safety& safety) {\n    CENSUS(\"step_safely\");\n"),
    ])
    sub("model/pathing.cc", [
        ("bool Pathing::step_towards(const Field& field, const bitboard* avoid, std::optional<vec2> aim) {\n",
         "bool Pathing::step_towards(const Field& field, const bitboard* avoid, std::optional<vec2> aim) {\n    CENSUS(\"step_field\");\n"),
        ("    if (!my_can_move()) return false;\n    // Only a hidden blocker makes a retry worth its search.\n",
         "    if (!my_can_move()) return false;\n    CENSUS(\"step_goals\");\n    // Only a hidden blocker makes a retry worth its search.\n"),
    ])
    sub("util.h", [
        ("inline Field make_field(const bitboard& walls, const bitboard& goals) {\n",
         "inline Field make_field(const bitboard& walls, const bitboard& goals) {\n    CENSUS(\"make_field\");\n"),
        ("inline std::optional<Field> make_field(const bitboard& walls, const bitboard& goals, int max_layers, int* layers_out = nullptr) {\n",
         "inline std::optional<Field> make_field(const bitboard& walls, const bitboard& goals, int max_layers, int* layers_out = nullptr) {\n    CENSUS(\"make_field_cap\");\n"),
    ])

def scope_fn(name, prefix, label):
    """A scope at the top of the one definition whose first line starts with `prefix` and ends with '{'."""
    p = SRC / name
    lines = p.read_text().split("\n")
    # The signature may run over a few lines: the scope goes after the first that ends with '{'.
    hits = [i for i, l in enumerate(lines) if l.startswith(prefix) and not l.rstrip().endswith(";")]
    assert len(hits) == 1 or LENIENT, (name, prefix, len(hits))
    for i in hits[:1]:
        j = next(k for k in range(i, i + 4) if lines[k].rstrip().endswith("{"))
        lines.insert(j + 1, f'    CENSUS("{label}");')
    p.write_text("\n".join(lines))


if "--trace" in sys.argv:
    for name, prefix, label in [
        ("economy/camps.cc", "float min_camp_damage(const World& world, int g,", "min_camp_damage"),
        ("economy/camps.cc", "float home_ground(", "home_ground"),
        ("economy/camps.cc", "float spell_clear_rounds(const World& world,", "spell_clear_rounds"),
        ("economy/camps.cc", "float fastest_clear(", "fastest_clear"),
        ("economy/camps.cc", "float reflected_clear(", "reflected_clear"),
        ("economy/farm.cc", "bool beyond_spare(", "beyond_spare"),
        ("economy/farm.cc", "bool pick_up(", "pick_up"),
        ("economy/capture.cc", "bool ally_engaged(", "ally_engaged"),
        ("economy/shop.cc", "HomeTrip home_trip(", "home_trip"),
        ("economy/bank.cc", "int bankable_bag(", "bankable_bag"),
        ("economy/bank.cc", "bool retaining_gems(", "retaining_gems"),
        ("economy/bank.cc", "bool can_tribute_safely(", "can_tribute_safely"),
        ("economy/bank.cc", "bool may_chain(", "may_chain"),
        ("economy/bank.cc", "bool closing(", "closing"),
        ("combat/abilities.cc", "bool cast_at_camp_on_approach(", "cast_on_approach"),
        ("combat/self_abilities.cc", "bool dash_towards(const World& world, Pathing& pathing, const bitboard& goals", "dash_towards"),
        ("combat/self_abilities.cc", "bool dash_across(", "dash_across"),
        ("combat/fight.cc", "float recall_line(", "recall_line"),
        ("model/world.cc", "std::optional<int> StaticMap::drafted_spawn_steps(", "drafted_spawn_steps"),
        ("model/world.cc", "const std::vector<std::uint8_t>* StaticMap::nearest_groups(", "nearest_groups"),
        ("economy/camps.cc", "void clear_fire(", "clear_fire"),
        ("economy/camps.cc", "bool attack_camp_target(", "attack_camp_target"),
        ("combat/abilities.cc", "Cast camp_cast(", "camp_cast"),
        ("combat/abilities.cc", "bool cast_at_camp(", "cast_at_camp"),
        ("combat/self_abilities.cc", "bool reset_and_attack_camp(", "reset_attack_camp"),
        ("combat/self_abilities.cc", "bool heal_ally(", "heal_ally"),
        ("combat/self_abilities.cc", "bool shield_if_needed(", "shield_if_needed"),
        ("economy/farm.cc", "bool step_onto_cleared(", "step_onto_cleared"),
        ("economy/farm.cc", "[[gnu::noinline]] const bitboard* farm_attack_tiles(", "farm_attack_tiles"),
        ("model/pathing.cc", "void Pathing::attack_tiles(", "p.attack_tiles"),
        ("model/world.cc", "bitboard StaticMap::drafted_attack_tiles(", "drafted_attack_tiles"),
    ]:
        scope_fn(name, prefix, label)
    sub("economy/camps.cc", [
        ("    if (static_cast<int>(t.slot.size()) == n) return t;\n",
         "    if (static_cast<int>(t.slot.size()) == n) return t;\n    CENSUS(\"stand_reach_build\");\n"),
        ("    if (n > 1)\n        std::sort(left, left + n,", "    CENSUS(\"clear_fire_sort\");\n    if (n > 1)\n        std::sort(left, left + n,"),
    ])
    sub("economy/farm.cc", [
        ("    const auto struggling = [&](int g) __attribute__((always_inline)) {\n",
         "    const auto struggling = [&](int g) __attribute__((always_inline)) {\n        CENSUS(\"struggling\");\n"),
        ("    const auto crew_work = [&](int g, int working, int waiting) __attribute__((always_inline)) {\n",
         "    const auto crew_work = [&](int g, int working, int waiting) __attribute__((always_inline)) {\n        CENSUS(\"crew_work\");\n"),
        ("    const auto stop_from = [&](int k) {\n", "    const auto stop_from = [&](int k) {\n        CENSUS(\"stop_from\");\n"),
    ])
print("ok")
