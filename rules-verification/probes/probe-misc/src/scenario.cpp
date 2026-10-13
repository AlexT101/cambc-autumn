// Scenario scripts. SCENARIO (scenario.h) and SIDE (side.h: 0 = probe-misc/team A, 1 = probe-misc-b/team B).
// Run: bash rules-verification/probes/probe-misc/run.sh <scenario> <map> <rounds>
//  1 monolith 140: monolith attack range (Vesper d3/d4 straight, Tavi d3 diagonal, Ryth d4/d5 via ground spell)
//  2 packs 200:    capture contest (B adjacent to group 3 while A captures; B steps onto group 2 tile mid-capture)
//  3 packs 520:    damage modifiers (Jungle, Jungle+Durability on Ryth; Monster on Vendetta), spawn/field/dead Health buys, inventory
//  4 packs 600:    altar locks (range, cancel enemy/own channel, owner tribute, tribute->attack conversion, double lock, spells, persistence)
//  5 packs 200:    as 4 but B attacks/locks 8 rounds later (clean own-lock-vs-own-channel and owner-tribute checks)
#include "bot.h"
#include "scenario.h"
#include "side.h"
#include <iostream>
#include <memory>

using cambc::champion_draft;
using cambc::champion_type;
using cambc::vec2;
using cambc::team;
using S = Step;
using IT = cambc::item_type;

static int it(IT x) { return static_cast<int>(static_cast<std::uint32_t>(x)); }

// Basic-attack the visible camp standing on `t`, logging its health before and after.
static bool attack_camp_at(vec2 t) {
    auto& me = cambc::self();
    for (const auto& c : cambc::vision::camps()) {
        if (c.position() != t) continue;
        float before = c.health();
        std::string res = "ok";
        try { me.attack(c); } catch (const std::exception& e) { res = err_str(e); }
        probe_prefix("attack");
        std::cout << " target=" << cambc::to_string(c.kind()) << "@(" << t.x << "," << t.y << ") from=(" << me.position().x << ","
                  << me.position().y << ") res=" << res << " before=" << before << " after=" << c.health() << '\n';
        return res == "ok";
    }
    probe_prefix("attack");
    std::cout << " no visible camp at (" << t.x << "," << t.y << ")\n";
    return false;
}

static bool cast_ground(int slot, vec2 t) {
    auto& me = cambc::self();
    std::string res = "ok";
    bool ret = false;
    try { ret = me.abilities()[slot].use(t); } catch (const std::exception& e) { res = err_str(e); }
    probe_prefix("cast");
    std::cout << " slot=" << slot << " at=(" << t.x << "," << t.y << ") res=" << res << " ret=" << ret;
    log_camps_near(t, 1);
    log_locks();
    std::cout << '\n';
    return res == "ok";
}

static bool step_to(vec2 t) {
    auto& me = cambc::self();
    if (me.position() == t) return true;
    cambc::bitboard g; g.clear(); g.set(t);
    move_towards_closest(g);
    return me.position() == t;
}

// Monolith tester: from its current tile, `wake` at k=0, then walk the per-turn path, then retreat.
static Step mono_test(std::function<bool()> wake, std::vector<vec2> path, vec2 retreat) {
    auto fleeing = std::make_shared<bool>(false);
    return S{Op::fn, {}, 0, 0, 0, [=](int k) {
        auto& me = cambc::self();
        if (me.health() < 320) *fleeing = true;
        if (!*fleeing && k == 0) { wake(); return false; }
        if (!*fleeing && k - 1 < static_cast<int>(path.size())) {
            step_to(path[k - 1]);
            probe_prefix("mono_pos");
            std::cout << " k=" << k << " pos=(" << me.position().x << "," << me.position().y << ") cheb="
                      << me.position().chebyshev_distance({1, 1}) << '\n';
            return false;
        }
        return step_to(retreat);
    }};
}

static const vec2 g0{8, 2}, g4{16, 2}, g6{24, 2};   // packs team-A wolf pairs
static const vec2 g2{11, 17}, g3{18, 12};            // packs central cluster groups (2 gold + 2 gem clusters)

// ---------------- scenario 2 helpers (B side contest) ----------------
static bool enemy_on(std::initializer_list<vec2> tiles) {
    auto enemies = cambc::vision::champion_tiles(team::enemy);
    for (auto t : tiles) if (enemies.is_set(t)) return true;
    return false;
}

// ---------------- scenario 4 helpers ----------------
static const vec2 X{2, 15};  // contested altar
static const vec2 X2{2, 24}; // persistence altar

// Try to tribute at `alt` every turn; logs the lock before/after and a follow-up basic attack on the lock.
static Step tribute_vs_lock(vec2 alt, int start_round) {
    return S{Op::fn, {}, 0, 0, 0, [=](int) {
        auto& me = cambc::self();
        if (static_cast<int>(cambc::round_number()) < start_round) return false;
        if (me.is_submitting_gems()) return false;
        if (me.gem_count() == 0) return true;
        probe_prefix("trib_try");
        std::cout << " can_attack=" << me.can_attack() << " gems=" << me.gem_count();
        log_locks();
        std::string res = "ok";
        try { me.submit_gems(alt); } catch (const std::exception& e) { res = err_str(e); }
        std::cout << " | res=" << res << " submitting=" << me.is_submitting_gems() << " can_attack_after=" << me.can_attack();
        log_locks();
        // follow-up basic attack on the lock in the same turn
        for (const auto& l : cambc::vision::altar_locks()) {
            if (l.position() != alt || l.is_ally()) continue;
            std::string r2 = "ok";
            try { me.attack(l); } catch (const std::exception& e) { r2 = err_str(e); }
            std::cout << " | followup_attack=" << r2;
            log_locks();
        }
        std::cout << '\n';
        return false;
    }};
}

std::vector<champion_draft> scenario_draft() {
    if (SIDE == 1) {
        switch (SCENARIO) {
        case 2: return {champion_draft::ren, champion_draft::varg, champion_draft::marcella};
        case 4: case 5: return {champion_draft::varg, champion_draft::ryth, champion_draft::ren};
        default: return {champion_draft::marcella, champion_draft::willow, champion_draft::stellar, champion_draft::prism, champion_draft::ren};
        }
    }
    switch (SCENARIO) {
    case 1: return {champion_draft::vesper_vale, champion_draft::tavi, champion_draft::ryth, champion_draft::vendetta, champion_draft::varg};
    case 2: return {champion_draft::vendetta, champion_draft::ryth, champion_draft::vesper_vale};
    case 3: return {champion_draft::ryth, champion_draft::vendetta, champion_draft::tavi};
    case 4: case 5: return {champion_draft::vendetta, champion_draft::vesper_vale, champion_draft::tavi};
    default: return {champion_draft::vesper_vale, champion_draft::ryth, champion_draft::vendetta};
    }
}

static std::vector<Step> side_a(champion_type who) {
    switch (SCENARIO) {
    case 1: {  // monolith (1,1); staging far away, testers one at a time
        const vec2 mono{1, 1};
        auto shoot = [mono] { return attack_camp_at(mono); };
        if (who == champion_type::vesper_vale)  // d3 straight (1,4) -> d4 (1,5) -> d3 -> d4 -> d3
            return {S{Op::go, {1, 4}}, S{Op::until, {}, 70},
                    mono_test(shoot, {{1, 5}, {1, 4}, {1, 5}, {1, 4}}, {9, 5}), S{Op::idle}};
        if (who == champion_type::tavi)  // diagonal d3 (4,4), then stays 4 turns without damaging (sleep rule), then d4 diag (5,5)
            return {S{Op::go, {12, 4}}, S{Op::until, {}, 80}, S{Op::go, {4, 4}}, S{Op::until, {}, 92},
                    mono_test(shoot, {{4, 4}, {4, 4}, {4, 4}}, {12, 4}), S{Op::idle}};
        if (who == champion_type::ryth)  // wake with ground spell from d4 (5,1) targeting (2,1); then d4, d5 (6,1), d4, d3 (4,2)
            return {S{Op::go, {12, 2}}, S{Op::until, {}, 100}, S{Op::go, {5, 1}}, S{Op::until, {}, 112},
                    mono_test([] { return cast_ground(0, {2, 1}); }, {{5, 1}, {6, 1}, {6, 1}, {5, 1}, {4, 2}, {4, 2}}, {12, 2}),
                    S{Op::idle}};
        return {S{Op::idle}};
    }
    case 2: {  // A captures group 3 (B adjacent) then group 2 (B steps on a spawn tile mid-capture)
        std::vector<Step> v{S{Op::kill, g3}};
        if (who == champion_type::vendetta) {
            v.push_back(S{Op::go, g3}); v.push_back(S{Op::wait_reward, {}, 30});
            v.push_back(S{Op::kill, g2}); v.push_back(S{Op::go, g2}); v.push_back(S{Op::wait_reward, {}, 60});
            v.push_back(S{Op::go, {9, 14}});
        } else {
            v.push_back(S{Op::go, who == champion_type::ryth ? vec2{15, 9} : vec2{16, 9}});
            v.push_back(S{Op::fn, {}, 0, 0, 0, [](int k) { return group_state(group_of(g3)).rfind("respawning", 0) == 0 || k > 60; }});
            v.push_back(S{Op::kill, g2});
            v.push_back(S{Op::go, who == champion_type::ryth ? vec2{9, 15} : vec2{9, 16}});
        }
        v.push_back(S{Op::idle});
        return v;
    }
    case 3: {
        // P2..P4: Jungle/Monster/Durability purchases and fights; P5/P6: extra wolf kills so Tavi can fill its inventory.
        const int P2 = 50, P3 = 110, P4 = 190, P5 = 235, P6 = 290;
        auto helper_tail = [&](vec2 home) {
            return std::vector<Step>{S{Op::until, {}, P5}, S{Op::kill, g4}, S{Op::go, home}, S{Op::until, {}, P6},
                                     S{Op::kill, g6}, S{Op::go, home}, S{Op::idle}};
        };
        std::vector<Step> v;
        if (who == champion_type::vendetta) {  // captures g0 -> Monster emblem (strength); then fights g4, g6, g0
            v = {S{Op::kill, g0}, S{Op::go, g0}, S{Op::wait_reward},
                 S{Op::buy, {}, 5, it(IT::monster_shard_of_strength)}, S{Op::go, {1, 0}}, S{Op::until, {}, P2},
                 S{Op::kill, g4}, S{Op::go, {1, 0}}, S{Op::until, {}, P3},
                 S{Op::kill, g6}, S{Op::go, {1, 0}}, S{Op::until, {}, P4},
                 S{Op::kill, g0}, S{Op::go, {1, 0}}};
            auto t = helper_tail({1, 0}); v.insert(v.end(), t.begin(), t.end());
            return v;
        }
        if (who == champion_type::ryth) {  // captures g4 -> Jungle (health); g6 -> Durability (health); tanks
            v = {S{Op::kill, g0}, S{Op::go, {0, 0}}, S{Op::until, {}, P2},
                 S{Op::kill, g4}, S{Op::go, g4}, S{Op::wait_reward},
                 S{Op::buy, {}, 5, it(IT::jungle_shard_of_health)}, S{Op::until, {}, P3},
                 S{Op::kill, g6}, S{Op::go, g6}, S{Op::wait_reward},
                 S{Op::buy, {}, 5, it(IT::durability_shard_of_health)}, S{Op::until, {}, P4},
                 S{Op::kill, g0}, S{Op::go, {0, 0}}};
            auto t = helper_tail({0, 0}); v.insert(v.end(), t.begin(), t.end());
            return v;
        }
        if (who == champion_type::tavi) {  // captures g0, g4, g6 (2nd time each); field health buy; distinct shards; dies and buys
            v = {S{Op::kill, g0}, S{Op::go, {0, 1}}, S{Op::until, {}, P2},
                 S{Op::kill, g4}, S{Op::go, {0, 1}}, S{Op::until, {}, P3},
                 S{Op::kill, g6}, S{Op::go, {0, 1}}, S{Op::until, {}, P4},
                 S{Op::kill, g0}, S{Op::go, g0}, S{Op::wait_reward},
                 S{Op::buy, {}, 1, it(IT::monster_shard_of_health), 1}};  // field Health buy (Tavi passive)
            // one shard of each other family/stat, in the field (inventory cap probe): 17 distinct shards, 30 gold kept
            const IT kinds[] = {IT::power_shard_of_health, IT::durability_shard_of_health, IT::treasure_shard_of_health,
                                IT::jungle_shard_of_health,
                                IT::home_shard_of_health, IT::bruiser_shard_of_health, IT::monster_shard_of_focus,
                                IT::power_shard_of_focus, IT::durability_shard_of_focus, IT::treasure_shard_of_focus,
                                IT::jungle_shard_of_focus, IT::home_shard_of_focus, IT::bruiser_shard_of_focus,
                                IT::monster_shard_of_strength, IT::power_shard_of_strength, IT::durability_shard_of_strength};
            for (int i = 0; i < 4; ++i) v.push_back(S{Op::buy, {}, 1, it(kinds[i]), 1});
            v.push_back(S{Op::until, {}, P5});
            v.push_back(S{Op::kill, g4}); v.push_back(S{Op::go, g4}); v.push_back(S{Op::wait_reward});
            for (int i = 4; i < 10; ++i) v.push_back(S{Op::buy, {}, 1, it(kinds[i]), 1});
            v.push_back(S{Op::until, {}, P6});
            v.push_back(S{Op::kill, g6}); v.push_back(S{Op::go, g6}); v.push_back(S{Op::wait_reward});
            for (int i = 10; i < 16; ++i) v.push_back(S{Op::buy, {}, 1, it(kinds[i]), 1});
            // die to awake g0 wolves, then buy Health while dead
            v.push_back(S{Op::fn, {}, 0, 0, 0, [](int k) {
                auto& me = cambc::self();
                if (!me.is_alive()) return true;
                if (k == 0) { probe_prefix("suicide_start"); std::cout << " gold=" << me.gold_count() << '\n'; }
                for (vec2 w : {vec2{8, 2}, vec2{8, 3}})
                    if (me.can_attack() && me.position().chebyshev_distance(w) <= 3 && cambc::vision::camp_tiles().is_set(w)) {
                        attack_camp_at(w);
                        return false;
                    }
                move_towards_closest(around(g0, 3));
                return false;
            }});
            v.push_back(S{Op::buy, {}, 1, it(IT::monster_shard_of_health)});
            v.push_back(S{Op::idle});
            return v;
        }
        return {S{Op::idle}};
    }
    case 4: case 5: {  // A: farm group 2 (3-way split), buy locks, altar X tests
        const int T0 = 140;
        std::vector<Step> v{S{Op::kill, g2}};
        if (who == champion_type::vendetta) {  // A1 tributer, starts at T0 while A3 locks at T0+1 (own channel survives?)
            v.insert(v.end(), {S{Op::go, {11, 17}}, S{Op::wait_reward}, S{Op::buy_lock}, S{Op::go, {3, 14}}, S{Op::until, {}, T0},
                               S{Op::tribute, X}, S{Op::idle}});
        } else if (who == champion_type::vesper_vale) {  // A2: place from Chebyshev 3 (5,15) at T0; at T0+2 from (4,16) onto A-locked altar
            v.insert(v.end(), {S{Op::go, {12, 18}}, S{Op::wait_reward}, S{Op::buy_lock}, S{Op::go, {5, 15}}, S{Op::until, {}, T0},
                               S{Op::place_lock, X}, S{Op::go, {4, 16}}, S{Op::until, {}, T0 + 2}, S{Op::place_lock, X}, S{Op::until, {}, T0 + 13},
                               S{Op::fn, {}, 0, 0, 0, [](int k) {  // plain basic attacks on the enemy lock at X
                                   auto& me = cambc::self();
                                   for (const auto& l : cambc::vision::altar_locks()) {
                                       if (l.position() != X || l.is_ally()) continue;
                                       std::string r = "ok";
                                       try { me.attack(l); } catch (const std::exception& e) { r = err_str(e); }
                                       probe_prefix("lock_attack"); std::cout << " res=" << r << " before=" << l.hits_remaining(); log_locks(); std::cout << '\n';
                                       return false;
                                   }
                                   return k > 10;
                               }}, S{Op::idle}});
        } else if (who == champion_type::tavi) {  // A3: place from diagonal Chebyshev 2 (4,13) at T0+1; then tribute at own-locked altar
            v.insert(v.end(), {S{Op::go, {11, 18}}, S{Op::wait_reward}, S{Op::buy_lock}, S{Op::go, {4, 13}}, S{Op::until, {}, T0 + 1},
                               S{Op::place_lock, X}, S{Op::go, {1, 14}}, S{Op::until, {}, T0 + 2}, S{Op::tribute, X}, S{Op::idle}});
        }
        return v;
    }
    default: return {S{Op::idle}};
    }
}

static std::vector<Step> side_b(champion_type who) {
    switch (SCENARIO) {
    case 2: {
        if (who == champion_type::ren || who == champion_type::varg) {
            // phase 1: stand adjacent to group 3 (diag (20,14) / orth (20,13) of member (19,13)) until A has captured it
            const vec2 adj = who == champion_type::ren ? vec2{20, 14} : vec2{20, 13};
            std::vector<Step> v{S{Op::go, adj},
                S{Op::fn, {}, 0, 0, 0, [](int k) {
                    auto st = group_state(group_of(g3));
                    return st.rfind("respawning", 0) == 0 || k > 120;
                }}};
            if (who == champion_type::varg) { v.push_back(S{Op::go, {20, 9}}); v.push_back(S{Op::idle}); return v; }
            // phase 2: Ren waits at Chebyshev 2 from (12,18); when A sits on a group-2 tile for 2 turns, step onto (12,18) for 10 turns
            auto seen = std::make_shared<int>(0);
            v.push_back(S{Op::go, {14, 20}});
            v.push_back(S{Op::fn, {}, 0, 0, 0, [seen](int) {
                if (enemy_on({{11, 17}, {12, 18}, {11, 18}, {12, 17}})) ++*seen; else *seen = 0;
                if (*seen >= 2) { probe_prefix("contest_go"); std::cout << '\n'; }
                return *seen >= 2;
            }});
            v.push_back(S{Op::go, {12, 18}});
            v.push_back(S{Op::fn, {}, 0, 0, 0, [](int k) { probe_prefix("contest_on"); std::cout << " k=" << k << '\n'; return k >= 10; }});
            v.push_back(S{Op::go, {15, 22}});
            v.push_back(S{Op::idle});
            return v;
        }
        return {S{Op::idle}};
    }
    case 4: case 5: {  // B: farm group 3 (3-way split), buy locks, altar X tests (scenario 5: B lock actions delayed by 8)
        const int T0 = 140, D = SCENARIO == 5 ? 8 : 0;
        std::vector<Step> v{S{Op::kill, g3}};
        if (who == champion_type::varg) {  // B1 tributer: starts at T0 (cancelled by A's lock at T0+1?), then tributes vs lock each turn
            v.insert(v.end(), {S{Op::go, {18, 12}}, S{Op::wait_reward}, S{Op::buy_lock}, S{Op::go, {1, 16}}, S{Op::until, {}, T0},
                               S{Op::fn, {}, 0, 0, 0, [](int) { auto& me = cambc::self(); std::string r = "ok"; try { me.submit_gems(X); } catch (const std::exception& e) { r = err_str(e); } probe_prefix("trib_start"); std::cout << " res=" << r << " submitting=" << me.is_submitting_gems() << " ch=" << (me.is_submitting_gems() ? me.remaining_channel_time() : -1) << '\n'; return true; }},
                               tribute_vs_lock(X, T0 + 2 + D), S{Op::idle}});
        } else if (who == champion_type::ryth) {  // B2: place B lock onto A-locked X at T0+2; ground spell on X at T0+4
            v.insert(v.end(), {S{Op::go, {19, 13}}, S{Op::wait_reward}, S{Op::buy_lock}, S{Op::go, {4, 17}}, S{Op::until, {}, T0 + 2 + D},
                               S{Op::place_lock, X}, S{Op::until, {}, T0 + 3 + D},
                               S{Op::fn, {}, 0, 0, 0, [](int) { cast_ground(0, {2, 16}); return true; }}, S{Op::idle}});
        } else if (who == champion_type::ren) {  // B3: lock altar X2 and sit next to it (persistence)
            v.insert(v.end(), {S{Op::go, {19, 12}}, S{Op::wait_reward}, S{Op::buy_lock}, S{Op::go, {2, 22}}, S{Op::until, {}, T0 + 6},
                               S{Op::place_lock, X2}, S{Op::idle}});
        }
        return v;
    }
    default: return {S{Op::idle}};
    }
}

std::vector<Step> scenario_script(champion_type who) { return SIDE == 0 ? side_a(who) : side_b(who); }
