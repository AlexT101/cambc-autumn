#!/usr/bin/env python3
"""Instrument a copy of astraeus with WLK lines: on farm turns after the loop's exit, one line per top-level walk
(step_route, step_field, walk_down, descend, step_towards_funded, prepare_approach) with the fuel of each part and
an event per search (kind, layers, cap, fuel) and per kept-route test (hit or why it missed). Debug builds only.

    python3 research/walkfuel-2026-11-05/winst.py bots/variants/astraeus-wi/src"""
import sys
from pathlib import Path

src = Path(sys.argv[1])

HEADER = r'''
// ---- WLK instrumentation (measurement copies only) ----
struct WalkTrace {
    bool on = false, cut = false, bank = false;
    int depth = 0;
    std::uint64_t start = 0;
    char entry = '?';
    std::uint64_t acc[48] = {};
    int calls[48] = {};
    char ev[900] = {};
    int nev = 0;
};
inline WalkTrace& wt() { static WalkTrace t; return t; }
struct WtShadow {
    cambc::distance_field field;
    bitboard goals{cambc::uninitialized}, walls{cambc::uninitialized};
    int layer = -1;
    bool crossing = false;
};
struct WtShadows {
    static constexpr int n = 6;
    WtShadow s[n];
    int next = 0;
};
inline WtShadows& wt_shadows() { static WtShadows* p = new WtShadows; return *p; }
struct WtScope {
    int k;
    std::uint64_t s = 0;
    explicit WtScope(int kind) : k(kind) { debug_block({ if (wt().on && wt().depth > 0) s = cambc::fuel_remaining(); }); }
    ~WtScope() {
        debug_block({
            if (s) {
                const auto now = cambc::fuel_remaining();
                if (now <= s) wt().acc[k] += s - now, ++wt().calls[k];
            }
        });
    }
};
#define WT_EV(...) debug_block({ auto& t_ = wt(); if (t_.on && t_.depth > 0 && t_.nev < 860) t_.nev += std::snprintf(t_.ev + t_.nev, sizeof t_.ev - t_.nev, __VA_ARGS__); })
#define WT_MARK(name) std::uint64_t name = 0; debug_block({ name = cambc::fuel_remaining(); })
#define WT_ADD(k, name) debug_block({ auto& t_ = wt(); if (name && t_.on && t_.depth > 0) { const auto now_ = cambc::fuel_remaining(); if (now_ <= name) t_.acc[k] += name - now_, ++t_.calls[k]; } })
#define WT_COUNT(k, n) debug_block({ auto& t_ = wt(); if (t_.on && t_.depth > 0) t_.acc[k] += (n), ++t_.calls[k]; })
struct WtEntry {
    bool top = false, counted = false;
    explicit WtEntry(char c) {
        debug_block({
            auto& t = wt();
            if (t.on) {
                counted = true;
                if (t.depth++ == 0) {
                    top = true, t.start = cambc::fuel_remaining(), t.entry = c, t.nev = 0, t.ev[0] = 0;
                    for (auto& a : t.acc) a = 0;
                    for (auto& n : t.calls) n = 0;
                }
            }
        });
    }
    ~WtEntry() {
        debug_block({
            auto& t = wt();
            if (counted) {
                --t.depth;
                if (top) {
                    const auto now = cambc::fuel_remaining();
                    std::printf("WLK %u %u %c %d %d %llu %llu |", cambc::round_number(), my_handle(), t.entry,
                                t.cut ? 1 : 0, t.bank ? 1 : 0, (unsigned long long)(now <= t.start ? t.start - now : 0),
                                (unsigned long long)search_chunks());
                    for (int i = 0; i < 48; ++i)
                        if (t.calls[i]) std::printf(" %d:%llu/%d", i, (unsigned long long)t.acc[i], t.calls[i]);
                    std::printf(" | %s\n", t.nev ? t.ev : "-");
                }
            }
        });
    }
};
'''

OPTIONAL = False  # set for the finer marks: an anchor the code no longer has is skipped


def patch(rel, old, new, count=1):
    p = src / rel
    s = p.read_text()
    if s.count(old) != count:
        if OPTIONAL:
            print(f"skipped: {old[:60]!r}")
            return
        sys.exit(f"{rel}: anchor found {s.count(old)} times, want {count}: {old[:70]!r}")
    p.write_text(s.replace(old, new))

def head(rel, line, add, count=1):
    patch(rel, line, line + add, count)

def scope(rel, line, k, count=1):
    head(rel, line, "    WtScope wt_scope{%d};\n" % k, count)

def entry(rel, line, c, count=1):
    head(rel, line, "    WtEntry wt_entry{'%s'};\n" % c, count)

# util.h: the header goes before search_cost_estimate's users; search_chunks is defined above note_shortcut? put it
# after search_chunks.
p = src / "util.h"
s = p.read_text()
i = s.index("// The most an uncapped field has cost so far, 0 before the first.")
p.write_text(s[:i] + HEADER + "\n" + s[i:])

# Turn start: off. Farm loop exit: on.
patch("main.cc", "        const auto start = aph::fuel();\n        aph::FuelMeter meter{\"turn\"};\n",
      "        const auto start = aph::fuel();\n        debug_block({ aph::wt() = aph::WalkTrace{}; });\n        aph::FuelMeter meter{\"turn\"};\n")
patch("economy/farm.cc", '    if (k < evaluated) note_shortcut("farm-partial-evaluation");\n',
      '    if (k < evaluated) note_shortcut("farm-partial-evaluation");\n'
      '    debug_block({ auto& t = wt(); t = WalkTrace{}; t.on = true, t.cut = k < evaluated, t.bank = banks_bag; });\n')

pc = "model/pathing.cc"
# Entries.
entry(pc, "[[gnu::flatten]] bool Pathing::step_route(const TravelDash& given, const bitboard& goals, const bitboard* avoid, int max_steps,\n                                          std::optional<vec2> aim) {\n", "r")
entry(pc, "bool Pathing::step_field(const Field& field, const bitboard* avoid, std::optional<vec2> aim, const Descended* failed) {\n", "f")
entry(pc, "bool Pathing::walk_down(const Field& field, const bitboard* avoid, std::optional<vec2> aim) {\n", "w")
entry(pc, "bool Pathing::descend_with(const TravelDash& td, const Field& field, const bitboard* avoid, std::optional<vec2> aim) {\n", "d")
entry(pc, "bool Pathing::step_towards_funded(const bitboard& goals, std::uint64_t fuel_floor) {\n", "u")
entry(pc, "[[gnu::flatten]] const Field* Pathing::prepare_approach(int group, int range, std::uint64_t fuel_floor) {\n", "a")

# Scopes.
scope(pc, "Pathing::Route Pathing::route(const bitboard& goals, const bitboard* avoid, int max_steps, std::optional<vec2> aim) {\n", 0)
scope(pc, "                                                      std::optional<vec2> aim, const bitboard* guard) {\n", 1)
scope(pc, "void Pathing::occupied_into(bitboard& out) {\n", 2)
scope(pc, "int Pathing::kept_steps(const KeptRoute& k, const bitboard& goals, const bitboard& walls, vec2 me, int cap) {\n", 4)
patch(pc, "                                std::optional<vec2> aim) {\n    // An enemy a refused move revealed makes the dash the fight's",
      "                                std::optional<vec2> aim) {\n    WtScope wt_scope{5};\n    // An enemy a refused move revealed makes the dash the fight's")
scope(pc, "Pathing::Ahead Pathing::ahead(const cambc::distance_field& d, const bitboard& goals, int here, int horizon) {\n", 6)
patch(pc, "            const Crossing walk{crossing_, false}, proof{walking_round_, true};\n            around = route(goals, avoid, cap, aim);\n",
      "            const Crossing walk{crossing_, false}, proof{walking_round_, true};\n            WtScope wt_scope{7};\n            around = route(goals, avoid, cap, aim);\n")
scope(pc, "                            std::span<const vec2> around, const bitboard* avoid, std::optional<vec2> aim, bool may_wait) {\n", 8)
patch(pc, "    const bitboard* veto = travel_landing_veto(world_, me);\n",
      "    const bitboard* veto = [&] { WtScope wt_scope{9}; return travel_landing_veto(world_, me); }();\n")
patch("model/pathing.h", "            guard_ = fn(world_, *guard_safety_, guard_here_, guard_radius_);\n",
      "            WtScope wt_scope{10};\n            guard_ = fn(world_, *guard_safety_, guard_here_, guard_radius_);\n")
patch("model/pathing.h", "        out = guard_cover_(world_, *guard_safety_, guard_here_, guard_radius_);\n",
      "        WtScope wt_scope{11};\n        out = guard_cover_(world_, *guard_safety_, guard_here_, guard_radius_);\n")
patch(pc, "            route_cover_ = guard_cover_(world_, *guard_safety_, guard_here_, guard_radius_);\n",
      "            { WtScope wt_scope{11}; route_cover_ = guard_cover_(world_, *guard_safety_, guard_here_, guard_radius_); }\n")
scope(pc, "bool Pathing::move_to(vec2 tile, bool* refused) {\n", 12)
scope(pc, "bool Pathing::dash_to(int slot, vec2 land) {\n", 13)
scope(pc, "int Pathing::pull(vec2 p) {\n", 14)
scope(pc, "bool Pathing::fight_near(bool live) {\n", 15)
scope(pc, "Pathing::TravelDash Pathing::travel_dash() {\n", 16)
scope(pc, "bool Pathing::enclosed(const bitboard& walls, const bitboard& goals, vec2 me) {\n", 17)
scope(pc, "bool Pathing::descend_with(const TravelDash& td, const Field& field, const bitboard* avoid, std::optional<vec2> aim) {\n    WtEntry wt_entry{'d'};\n", 18)
scope(pc, "bool Pathing::step_field(const Field& field, const bitboard* avoid, std::optional<vec2> aim, const Descended* failed) {\n    WtEntry wt_entry{'f'};\n", 19)
scope(pc, "const Field* Pathing::search_approach(int group, int range, int steps) {\n", 20)
scope(pc, "bool Pathing::make_way(const bitboard& goals, const bitboard* avoid, int max_steps) {\n", 21)
scope(pc, "bool Pathing::labelled_ally_beside(const bitboard& allies, const bitboard& goals, const bitboard* avoid) {\n", 21)
scope(pc, "void Pathing::know_failure(const bitboard& goals, const bitboard* avoid, int max_steps) {\n", 22)
scope(pc, "const bitboard& Pathing::blocked() {\n", 23)
scope(pc, "Pathing::Neighbours Pathing::closer_neighbours(const Field& field, const bitboard* avoid, std::optional<vec2> aim) {\n", 24)
scope(pc, "bool Pathing::walk_parted(const bitboard& goals, vec2 me) {\n", 25)
scope(pc, "bool Pathing::round_fails(const bitboard& goals, const bitboard& walls, vec2 me, int cap) {\n", 26)
scope(pc, "const bitboard& Pathing::near_crossings() {\n", 27)
scope(pc, "Pathing::Travel Pathing::take(const TravelDash& td, const Plan& p) {\n", 28)

# The search itself (3), with an event: kind (w walk round, c crossings open, r walking), layers, cap, fuel, our label.
patch(pc, "            layers = route_field_.compute_to_with_expansion_count(walls, goals, origin, route_labelled_, static_cast<std::uint16_t>(cap));\n",
      """            std::uint64_t wt_s = 0;
            debug_block({ wt_s = cambc::fuel_remaining(); });
            {
                WtScope wt_scope{3};
                layers = route_field_.compute_to_with_expansion_count(walls, goals, origin, route_labelled_, static_cast<std::uint16_t>(cap));
            }
            WT_EV("S%c%d/%d/%llu/%d ", walking_round_ ? 'w' : crossing_ ? 'c' : 'r', layers, cap,
                  (unsigned long long)(wt_s - cambc::fuel_remaining()), steps_at(route_field_, me));
""")
patch(pc, "            layers = std::min(f.layers, cap);\n            here = unreachable;\n        } else if (walking_round_ && round_fails(goals, walls, me, cap)) {\n            return r;\n",
      "            layers = std::min(f.layers, cap);\n            here = unreachable;\n            WT_EV(\"F \");\n        } else if (walking_round_ && round_fails(goals, walls, me, cap)) {\n            WT_EV(\"O \");\n            return r;\n")
patch(pc, "            if (enclosed(walls, goals, me)) {\n                route_exhausted_ = true;\n                return r;\n",
      "            if (enclosed(walls, goals, me)) {\n                route_exhausted_ = true;\n                WT_EV(\"E \");\n                return r;\n")

# The kept-route test: why it missed, the changed count, and whether testing every changed tile would have passed.
patch(pc, "    int here = kept_steps(kept, goals, walls, me, cap);\n",
      r"""    int here = kept_steps(kept, goals, walls, me, cap);
    debug_block({
        auto& t = wt();
        if (t.on && t.depth > 0) {
            const auto& k = kept;
            char why = 'H';
            int changed_n = -1, gdiff = -1, wide = -1, steps = -2;
            static bitboard ch{cambc::uninitialized};
            if (k.layer < 0) why = 'N';
            else {
                steps = steps_at(k.field, me);
                if (!(goals == k.goals)) {
                    why = 'G';
                    xor_into(goals, k.goals, ch);
                    gdiff = static_cast<int>(board_count(ch));
                } else if (steps == unreachable) why = 'U';
                else if (steps > k.layer) why = 'L';
                else if (steps > cap) why = 'C';
                else {
                    xor_into(walls, k.walls, ch);
                    changed_n = static_cast<int>(board_count(ch));
                    wide = 1;
                    for (const vec2 q : ch.positions()) {
                        if (test(walls, q)) {
                            if (steps_at(k.field, q) < steps) wide = 0;
                            continue;
                        }
                        if (test(goals, q)) { wide = 0; continue; }
                        for (const auto d : directions)
                            if (in_bounds(q + d) && steps_at(k.field, q + d) + 1 < steps) wide = 0;
                    }
                    if (here == unreachable) why = changed_n > 4 ? 'M' : 'T';
                }
            }
            if (t.nev < 860) t.nev += std::snprintf(t.ev + t.nev, sizeof t.ev - t.nev, "K%c%c%d/%d/%d/%d/%d ", why, crossing_ ? 'c' : walking_round_ ? 'w' : 'r', changed_n, gdiff, wide, steps, k.layer);
            // Older found searches (a shadow ring, newest first): would one pass kept_steps' test here?
            if (here == unreachable) {
                auto& sh = wt_shadows();
                int hit = -1, age = 0;
                for (int j = 0; j < WtShadows::n && hit < 0; ++j) {
                    const auto& s = sh.s[(sh.next - 1 - j + 2 * WtShadows::n) % WtShadows::n];
                    if (s.layer < 0 || s.crossing != crossing_) continue;
                    ++age;
                    if (age == 1) continue; // the kept route itself
                    if (!(goals == s.goals)) continue;
                    const int st = steps_at(s.field, me);
                    if (st == unreachable || st > s.layer || st > cap) continue;
                    xor_into(walls, s.walls, ch);
                    bool okk = true;
                    int nn = 0;
                    for (const vec2 q : ch.positions()) {
                        ++nn;
                        if (test(walls, q)) { if (steps_at(s.field, q) < st) okk = false; continue; }
                        if (test(goals, q)) { okk = false; continue; }
                        for (const auto d : directions)
                            if (in_bounds(q + d) && steps_at(s.field, q + d) + 1 < st) okk = false;
                    }
                    if (okk) hit = age, changed_n = nn;
                }
                if (t.nev < 860) t.nev += std::snprintf(t.ev + t.nev, sizeof t.ev - t.nev, "Z%d/%d ", hit, hit >= 0 ? changed_n : -1);
            }
        }
    });
""")
patch(pc, "        walls.swap(kept.walls);\n", """        walls.swap(kept.walls);
        debug_block({
            if (true) {
                auto& sh = wt_shadows();
                auto& s = sh.s[sh.next];
                sh.next = (sh.next + 1) % WtShadows::n;
                s.field.copy_from(kept.field);
                copy_into(kept.goals, s.goals);
                copy_into(kept.walls, s.walls);
                s.layer = here, s.crossing = crossing_;
            }
        });
""")
patch(pc, "    const bitboard* const guard = guard_cover(cover) && !cover ? nullptr : this->guard();\n",
      "    WT_MARK(wt_g0);\n    const bitboard* const guard = guard_cover(cover) && !cover ? nullptr : this->guard();\n    WT_ADD(38, wt_g0);\n")
OPTIONAL = True
# Finer marks: plan's boards (29), its ends loop (30), ends weighed (31, a count), the walking field read (32, a
# count); route_around's walls (33), first steps (34), a found search's bookkeeping (35); ahead's tiles (36, a count);
# make_pull (37).
patch(pc, "    const auto& walls = blocked();\n    const bitboard* cover = nullptr;\n",
      "    WT_MARK(wt_p0);\n    const auto& walls = blocked();\n    const bitboard* cover = nullptr;\n")
patch(pc, "    const bool walk_costs = !world_.me().facts().walk_and_attack_independent();\n",
      "    WT_ADD(29, wt_p0);\n    WT_MARK(wt_p1);\n    const bool walk_costs = !world_.me().facts().walk_and_attack_independent();\n")
patch(pc, "    if (best_b < 0) return best;\n    const std::uint64_t end = std::uint64_t{1} << best_b;\n",
      "    WT_ADD(30, wt_p1);\n    WT_COUNT(31, __builtin_popcountll(dashed | then_walk | walk_then));\n    WT_COUNT(32, l.w ? 1 : 0);\n"
      "    if (best_b < 0) return best;\n    const std::uint64_t end = std::uint64_t{1} << best_b;\n")
patch(pc, "    // Scratch kept between calls: the host overwrites every output in full.\n    static bitboard walls{cambc::uninitialized}, origin;\n",
      "    WT_MARK(wt_r0);\n    // Scratch kept between calls: the host overwrites every output in full.\n    static bitboard walls{cambc::uninitialized}, origin;\n")
patch(pc, "    const int cap = std::min<int>(max_steps, unreachable);\n    auto& kept = kept_routes_[crossing_];\n",
      "    WT_ADD(33, wt_r0);\n    const int cap = std::min<int>(max_steps, unreachable);\n    auto& kept = kept_routes_[crossing_];\n")
patch(pc, "    const auto& field = kept.field;\n    r.steps = here;\n", "    WT_MARK(wt_r1);\n    const auto& field = kept.field;\n    r.steps = here;\n")
patch(pc, "    return r;\n}\n\n// make_way reads the failed search's labels", "    WT_ADD(34, wt_r1);\n    return r;\n}\n\n// make_way reads the failed search's labels")
patch(pc, "        FuelMeter meter{\"route\"};\n", "        FuelMeter meter{\"route\"};\n        WT_MARK(wt_r2);\n")
patch(pc, "        kept.layer = here;\n    }\n", "        kept.layer = here;\n        WT_ADD(35, wt_r2);\n    }\n")
patch(pc, "    while (!t.found && !t.ended && t.count <= horizon) {\n        const vec2 q = t.tiles[static_cast<std::size_t>(t.count - 1)];\n",
      "    while (!t.found && !t.ended && t.count <= horizon) {\n        WT_COUNT(36, 1);\n        const vec2 q = t.tiles[static_cast<std::size_t>(t.count - 1)];\n")
scope(pc, "void Pathing::make_pull() {\n", 37)
patch(pc, "    WT_MARK(wt_p0);\n    const auto& walls = blocked();\n",
      "    WT_MARK(wt_p0);\n    WT_MARK(wt_b0);\n    const auto& walls = blocked();\n    WT_ADD(39, wt_b0);\n")
patch(pc, "    const std::uint64_t shut = bits({&walls, avoid, guard});\n",
      "    WT_MARK(wt_b1);\n    const std::uint64_t shut = bits({&walls, avoid, guard});\n    WT_ADD(40, wt_b1);\n")
patch(pc, "    camps_into(no_dash);\n    const std::uint64_t passes",
      "    WT_MARK(wt_b2);\n    camps_into(no_dash);\n    const std::uint64_t passes")
if "wt_b2" in (src / pc).read_text(): patch(pc, "    const bitboard* veto = [&]", "    WT_ADD(41, wt_b2);\n    const bitboard* veto = [&]")
patch(pc, "    const std::uint64_t dashed = dash_from(window::centre);\n",
      "    WT_MARK(wt_b3);\n    const std::uint64_t dashed = dash_from(window::centre);\n")
patch(pc, "    WT_ADD(29, wt_p0);\n", "    WT_ADD(42, wt_b3);\n    WT_ADD(29, wt_p0);\n")
scope(pc, "int Pathing::turns_at(const Labels& l, vec2 q, int d, int c) const {\n", 44)
patch(pc, "    std::array<std::uint16_t, 8> around{};\n    std::uint16_t best = unreachable;\n",
      "    WT_MARK(wt_n0);\n    std::array<std::uint16_t, 8> around{};\n    std::uint16_t best = unreachable;\n")
patch(pc, "            if (around[i] == best) r.first_steps[r.count++] = me + directions[i];\n",
      "            if (around[i] == best) r.first_steps[r.count++] = me + directions[i];\n    WT_ADD(45, wt_n0);\n    WT_COUNT(46, r.count);\n")
print("instrumented", src)
