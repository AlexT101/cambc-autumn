"""Extra census scopes inside the strike search (plan.cc), on top of tools/fuel/census/instrument.py --fine --trace.

    python3 research/ideas-2026-11-05/fuel5-tools/strike_scopes.py bots/variants/oc-fuel5-cen/src

Profiling only: scopes cost ~10 fuel each and change inlining, so the copy's fuel is not the real bot's.
"""
import sys
from pathlib import Path

SRC = Path(sys.argv[1])


def sub(name, pairs):
    p = SRC / name
    s = p.read_text()
    for a, b in pairs:
        assert s.count(a) == 1, (name, a[:80], s.count(a))
        s = s.replace(a, b)
    p.write_text(s)


sub("combat/plan.cc", [
    ("#include \"../model/follow.h\"\n", "#include \"../model/follow.h\"\n#include <optional>\n"),
    # plan_strikes' phases
    ("""    if (!S.read()) {
        if constexpr (debug_strike_free) {""", """    bool read_ok;
    {
        CENSUS("ss.read");
        read_ok = S.read();
    }
    if (!read_ok) {
        if constexpr (debug_strike_free) {"""),
    ("""    if (S.walk_only) throw_if_stale(), ++S.nodes, S.settle(S.root());
    else S.grow(S.root());
    mark(1);""", """    {
        CENSUS("ss.grow");
        if (S.walk_only) throw_if_stale(), ++S.nodes, S.settle(S.root());
        else S.grow(S.root());
    }
    mark(1);
    std::optional<::aph::census::Scope> price_scope;
    price_scope.emplace("ss.price");"""),
    ("""    mark(2);
    held.release();""", """    price_scope.reset();
    mark(2);
    CENSUS("ss.act");
    held.release();"""),
    ("""            const float b = safety_params::hit_given_reach * safety.blow(*sk.e, p).damage;
            ++queries;""", """            float b;
            {
                CENSUS("ss.blow");
                b = safety_params::hit_given_reach * safety.blow(*sk.e, p).damage;
            }
            ++queries;"""),
    ("""        if (!cut && kept && sh > 0) {
            sh = S.shield_at(p);""", """        if (!cut && kept && sh > 0) {
            CENSUS("ss.shield_at");
            sh = S.shield_at(p);"""),
    ("""        if (dist(p, here) >= 2) {
            Unwritten<Safety::ThreatAt, 16> threats;""", """        if (dist(p, here) >= 2) {
            CENSUS("ss.unseen_threats");
            Unwritten<Safety::ThreatAt, 16> threats;"""),
    ("""        if (dist(p, here) == grid_r && safety.lethal(p)) continue;
        t.exact = true;""", """        bool lethal_far;
        {
            CENSUS("ss.lethal");
            lethal_far = dist(p, here) == grid_r && safety.lethal(p);
        }
        if (lethal_far) continue;
        t.exact = true;"""),
    ("""    void resolve_guard() {
        maybe_guarded = 0;""", """    void resolve_guard() {
        CENSUS("ss.resolve_guard");
        maybe_guarded = 0;"""),
    ("""    else if (const Field* field = unguarded >= 2 && S.walks ? goal_field(world, pathing, intent) : nullptr)""",
     """    else if (const Field* field = unguarded >= 2 && S.walks ? [&] { CENSUS("ss.goal_field"); return goal_field(world, pathing, intent); }() : nullptr)"""),
    ("""        const float camp = camp_at(p);
        t.bound -= camp;""", """        float camp;
        {
            CENSUS("ss.camp_at");
            camp = camp_at(p);
        }
        t.bound -= camp;"""),
    # Search internals
    ("void Search::settle(const Node& s) {\n", "void Search::settle(const Node& s) {\n    CENSUS(\"ss.settle\");\n"),
    ("bool Search::legal_at(Node& s, Grid legal) {\n", "bool Search::legal_at(Node& s, Grid legal) {\n    CENSUS(\"ss.legal_at\");\n"),
    ("void Search::hit_centre(const Centre& c, int slot, Node& s) {\n", "void Search::hit_centre(const Centre& c, int slot, Node& s) {\n    CENSUS(\"ss.hit_centre\");\n"),
    ("bool Search::spell_unit(const Spell& sp, int t, Node& s) {\n", "bool Search::spell_unit(const Spell& sp, int t, Node& s) {\n    CENSUS(\"ss.spell_unit\");\n"),
])
sub("combat/fight.cc", [
    ("bool outmatched(const World& world, Safety& safety, HoldAt& hold) {\n",
     "bool outmatched(const World& world, Safety& safety, HoldAt& hold) {\n    CENSUS(\"wh.outmatched\");\n"),
])

# Round 2: finer scopes in the stand and the fight sim, and in Search::read's foe loop.
def scope_line(name, prefix, label):
    p = SRC / name
    lines = p.read_text().split("\n")
    hits = [i for i, l in enumerate(lines) if l.startswith(prefix) and not l.rstrip().endswith(";")]
    assert len(hits) == 1, (name, prefix, len(hits))
    i = hits[0]
    j = next(k for k in range(i, i + 4) if lines[k].rstrip().endswith("{"))
    lines.insert(j + 1, f'    CENSUS("{label}");')
    p.write_text("\n".join(lines))

for name, prefix, label in [
    ("model/safety.cc", "Safety::StandReach Safety::stand_reach(", "s.stand_reach"),
    ("model/safety.cc", "Safety::StandRoster Safety::stand_roster(", "s.stand_roster"),
    ("model/safety.cc", "Trade Safety::stand_trade(", "s.stand_trade"),
    ("model/safety.cc", "int Safety::approach(const ChampionBelief& e, vec2 p, int horizon) {", "s.approach"),
    ("model/safety.cc", "int Safety::unseen_approach(", "s.unseen_approach"),
    ("model/safety.cc", "float Safety::camp_damage(vec2 p, bool worst, bool next) {", "s.camp_damage"),
    ("model/safety.cc", "void fill(Side& side, const World& world,", "s.fill"),
    ("model/safety.cc", "Trade trade(Side& us, Side& them,", "s.trade"),
    ("model/safety.cc", "std::uint32_t Safety::fight_key_with(", "s.fight_key_with"),
    ("model/safety.cc", "bool Safety::unseen_may_hit_within(", "s.unseen_may_hit"),
    ("model/safety.cc", "int Safety::turns_to_kill_idle(", "s.ttk_idle"),
    ("combat/fight.cc", "int hold_rounds(const World& world, Pathing& pathing, vec2 p) {", "wh.hold_rounds"),
    ("combat/fight.cc", "bool paying_soon(", "wh.paying_soon"),
    ("combat/guard.cc", "bool own_ground(const World& world, vec2 p) {", "own_ground"),
    ("combat/guard.cc", "bool in_pack_zone(", "in_pack_zone"),
    ("combat/fight.cc", "bool hold_outlasts(", "wh.hold_outlasts"),
]:
    scope_line(name, prefix, label)
sub("combat/plan.cc", [
    ("""    const auto& enemy_spawn = world.map().enemy_spawn;
    for (const auto& e : world.enemies) {
        if (foes == max_foes) break;""", """    const auto& enemy_spawn = world.map().enemy_spawn;
    std::optional<::aph::census::Scope> foe_scope;
    foe_scope.emplace("ss.r.foes");
    for (const auto& e : world.enemies) {
        if (foes == max_foes) break;"""),
    ("""    n = foes;
    if (foes == 0) return false;
    if (auto* b = const_cast""", """    foe_scope.reset();
    n = foes;
    if (foes == 0) return false;
    if (auto* b = const_cast"""),
    ("""        x.stun = arms && x.stunnable ? stun_worth(world, e, true) : 0.0f;
        x.stop = kill_stops(world, e);""", """        { CENSUS("ss.r.stun_worth"); x.stun = arms && x.stunnable ? stun_worth(world, e, true) : 0.0f; }
        { CENSUS("ss.r.kill_stops"); x.stop = kill_stops(world, e); }"""),
    ("""        x.partner = partner_bound(world, e);
        x.bag = params::gem_value * static_cast<float>(pair_gems(world, e));""", """        { CENSUS("ss.r.partner_bound"); x.partner = partner_bound(world, e); }
        { CENSUS("ss.r.pair_gems"); x.bag = params::gem_value * static_cast<float>(pair_gems(world, e)); }"""),
    ("""        if (stuns && x.stunnable && turns_before_ours(world, e) == 1) x.drop_stun""", """        CENSUS("ss.r.tail");
        if (stuns && x.stunnable && turns_before_ours(world, e) == 1) x.drop_stun"""),
    ("""        x.legal = (can_attack || reset_ready) && dist(here, e.pos) <= grid_r + range ? viewers(e.pos, range) : 0;
        h[foes++] = x.health;""", """        { CENSUS("ss.r.viewers"); x.legal = (can_attack || reset_ready) && dist(here, e.pos) <= grid_r + range ? viewers(e.pos, range) : 0; }
        h[foes++] = x.health;"""),
    ("""        try {
            const auto* record = visible_record(e.handle);
            if (!record) continue;""", """        CENSUS("ss.r.live");
        try {
            const auto* record = visible_record(e.handle);
            if (!record) continue;"""),
    ("""    if (lands && (dash_ready || vendetta)) {
        try {
            const float raw = my_damage(dash);""", """    if (lands && (dash_ready || vendetta)) {
        CENSUS("ss.r.land");
        try {
            const float raw = my_damage(dash);"""),
    ("""    const Grid blocked = read_grid(pathing.blocked());""", """    Grid blocked;
    { CENSUS("ss.g.blocked"); blocked = read_grid(pathing.blocked()); }"""),
    ("""    const auto& terrain = terrain_grid(world.map(), here, box, t);""", """    const TerrainGrid* terrain_p;
    { CENSUS("ss.g.terrain"); terrain_p = &terrain_grid(world.map(), here, box, t); }
    const auto& terrain = *terrain_p;"""),
    ("""        static bitboard foes_seen{cambc::uninitialized};
        camps_into(t);""", """        CENSUS("ss.g.pass");
        static bitboard foes_seen{cambc::uninitialized};
        camps_into(t);"""),
])

# Round 3: the price stage's parts.
sub("combat/plan.cc", [
    ("""    std::array<Striker, 16> strikers;
    int ns = 0;""", """    std::optional<::aph::census::Scope> part;
    part.emplace("sp.strikers");
    std::array<Striker, 16> strikers;
    int ns = 0;"""),
    ("""    Unwritten<Safety::CampHit, 24> camp_hits;""", """    part.reset();
    part.emplace("sp.camps");
    Unwritten<Safety::CampHit, 24> camp_hits;"""),
    ("""    int nt = 0;
    const float shield_top""", """    int nt = 0;
    part.reset();
    part.emplace("sp.tiles");
    const float shield_top"""),
    ("""    float best_total = -1e30f;
    int chosen = -1, queries = 0, priced = 0, share_stops = 0, bound_stops = 0;""", """    part.reset();
    part.emplace("sp.loop");
    float best_total = -1e30f;
    int chosen = -1, queries = 0, priced = 0, share_stops = 0, bound_stops = 0;"""),
    ("""    // Unpriced tiles keep their Strike price, and no shield.""", """    part.reset();
    part.emplace("sp.capped");
    // Unpriced tiles keep their Strike price, and no shield."""),
    ("""    price_scope.reset();
    mark(2);""", """    part.reset();
    price_scope.reset();
    mark(2);"""),
    ("""        const int nk = gather(t.c);
        bool kept = false;""", """        std::optional<::aph::census::Scope> tile_part;
        tile_part.emplace("sp.tile_prep");
        const int nk = gather(t.c);
        bool kept = false;"""),
    ("""        float total = top();
        bool cut = false;
        for (int m = 0; m < no && !cut; ++m) {""", """        tile_part.reset();
        tile_part.emplace("sp.tile_queries");
        float total = top();
        bool cut = false;
        for (int m = 0; m < no && !cut; ++m) {"""),
    ("""        ++priced;
        t.total = total;""", """        tile_part.reset();
        ++priced;
        t.total = total;"""),
])

print("ok")
