// probe-stun-b (team B): scripted, passive target team for probe-stun (see probe-stun/src/bot.cpp header).
// SCENARIO in src/scenario.h must match probe-stun.
// Scenario 1: Varg, Marcella, Tavi walk to the packs centre and stand still; when stunned they
// try every action type; scripted recalls / teleport give channels for A to interrupt.
#include "bot.h"
#include "probe.h"
#include "scenario.h"

#if SCENARIO == 1
static bool home = false; // once back on spawn after a recall, stay there

// Attempt each action type, logging what the engine says (used while stunned).
static void try_everything() {
    auto& me = self();
    std::string s = "try prio=" + act([&] { me.set_priority(7); });
    s += " ward=" + act([&] { return me.place_ward(me.position() + vec2{-1, 0}); });
    s += " buy=" + act([&] { me.buy(item_type::power_shard_of_strength, 1); });
    s += " tpc=" + act([&] { return me.consumables()[consumable_type::tp_crystal].use(me.position() + vec2{0, -2}); });
    s += " cast0=" + act([&] { return me.abilities()[0].use(); });
    std::optional<champion> tgt;
    for (auto& e : vision::champions(team::enemy)) if (e.is_visible()) { tgt = e; if (me.attack_tiles().is_set(e.position())) break; }
    s += " attack=" + (tgt ? act([&] { me.attack(*tgt); }) : std::string("noTarget"));
    s += " move=" + act([&] { return me.move(vec2{0, 1}); });
    s += " recall=" + act([&] { me.recall(); });
    if (me.is_recalling()) s += " cancel=" + act([&] { me.cancel_recall(); });
    log(s + " | " + self_desc());
}

void Bot::play_turn() {
    auto& me = self();
    const auto t = me.champion_name();
    const int R = static_cast<int>(round_number());
    if (R == 1) log("buyTp=" + act([&] { me.buy(consumable_type::tp_crystal); }) + " | " + self_desc());
    if (R >= 26) log("self " + self_desc());
    if (!me.is_alive()) return;

    // Who of A's casters has already acted this round (turn-order evidence).
    if (R >= 29 && R <= 41) {
        std::string s = "order";
        for (auto& e : vision::champions(team::enemy)) s += std::string(" ") + cname(e.champion_name()) + ".done=" + q([&] { return e.has_completed_turn(); });
        log(s);
    }

    auto b = me.buffs();
    if ((b.has_stun() || !me.restrictions().is_empty()) && !me.is_recalling() && !me.is_teleporting()) try_everything();

    if (me.is_recalling() || me.is_teleporting()) return;
    if (R > 20 && map::spawn_region(team::ally).is_set(me.position())) home = true;
    if (home) return;

    if (t == champion_type::varg) {
        if (R == 45) { log("startRecall=" + act([&] { me.recall(); }) + " " + self_desc()); return; }
        if (R == 55) { log("startTp=" + act([&] { return me.consumables()[consumable_type::tp_crystal].use(vec2{17, 14}); }) + " " + self_desc()); return; }
        if (R == 65) { log("startRecall=" + act([&] { me.recall(); }) + " " + self_desc()); return; }
    }
    if (t == champion_type::tavi) {
        if (R == 50) { log("startRecall=" + act([&] { me.recall(); }) + " " + self_desc()); return; }
        if (R == 60) {
            std::string s = "recallTwice r1=" + act([&] { me.recall(); });
            s += " cancel=" + act([&] { me.cancel_recall(); });
            s += " r2=" + act([&] { me.recall(); });
            log(s + " " + self_desc());
            return;
        }
        if (R == 61 && !me.is_recalling()) { log("startRecall=" + act([&] { me.recall(); }) + " " + self_desc()); return; }
    }
    vec2 goal = t == champion_type::varg ? vec2{17, 17} : t == champion_type::marcella ? vec2{16, 17} : vec2{17, 16};
    walk_to(goal);
}
#endif

#if SCENARIO == 0
void Bot::play_turn() {} // scenario 0: idle
#endif

#if SCENARIO == 2
// Scenario 2: B Tavi (victim) farms the centre gold/gem group with Varg & Willow, captures alone,
// recalls, buys a tp crystal + 1 health shard, walks back, channels the crystal (A stuns it), then
// stands still to be killed. Willow stands still to be killed next. Varg recalls home late.
static const vec2 group_tile{19, 13};
static int stage = 0; // tavi: 0 farm, 1 capture, 2 recall, 3 shop, 4 walk back / tp, 5 idle

static std::optional<map::camp_group> centre_group() {
    for (auto& g : map::camp_groups()) if (g.spawn_tiles().is_set(group_tile)) return g;
    return std::nullopt;
}
static bool group_alive() {
    auto g = centre_group();
    try { return g && std::holds_alternative<map::camp_group_alive>(g->state()); } catch (...) { return true; } // not in vision yet
}
static void attack_group_camp() {
    auto& me = self();
    auto g = centre_group();
    for (auto& c : vision::camps())
        if (g && g->spawn_tiles().is_set(c.spawn_position()) && me.can_attack() && me.attack_tiles().is_set(c.position())) { try { me.attack(c); } catch (...) {} return; }
}

void Bot::play_turn() {
    auto& me = self();
    const auto t = me.champion_name();
    const int R = static_cast<int>(round_number());
    std::string extra = " canShopItem=" + can_shop(false) + " canShopCons=" + can_shop(true);
    log("self " + self_desc() + extra);
    if (!me.is_alive()) {
        // Dead: try shopping (Tavi has 30 gold left, Willow none).
        log("deadBuy item=" + act([&] { me.buy(item_type::power_shard_of_focus, 1); }) + " cons=" + act([&] { me.buy(consumable_type::altar_lock); }));
        return;
    }
    if (me.is_recalling() || me.is_teleporting()) return;

    const vec2 stand = t == champion_type::tavi ? vec2{17, 16} : t == champion_type::varg ? vec2{17, 17} : vec2{16, 17};
    const vec2 farm = t == champion_type::tavi ? vec2{21, 15} : t == champion_type::varg ? vec2{20, 13} : vec2{21, 14};

    if (t == champion_type::tavi) {
        if (stage == 0) {
            if (!group_alive() && R > 5) stage = 1;
            else { attack_group_camp(); walk_to(farm); return; }
        }
        if (stage == 1) {
            if (me.gold_count() > 0) { log("captured " + self_desc()); stage = 2; }
            else { walk_to(group_tile); return; }
        }
        if (stage == 2) {
            if (map::spawn_region(team::ally).is_set(me.position())) stage = 3;
            else { log("startRecall=" + act([&] { me.recall(); })); return; }
        }
        if (stage == 3) {
            log("shop cons=" + act([&] { me.buy(consumable_type::tp_crystal); }) + " shard=" + act([&] { me.buy(item_type::power_shard_of_health, 1); }) + " " + self_desc());
            stage = 4;
        }
        if (stage == 4) {
            if (me.position() == stand && R >= 50) {
                log("startTp=" + act([&] { return me.consumables()[consumable_type::tp_crystal].use(vec2{17, 19}); }) + " " + self_desc());
                stage = 5; return;
            }
            walk_to(stand); return;
        }
        walk_to(stand); return;
    }
    // Varg & Willow: help farm until the group dies, then stand at their spots.
    if (t == champion_type::varg && R >= 150) {
        if (!map::spawn_region(team::ally).is_set(me.position())) log("startRecall=" + act([&] { me.recall(); }));
        return;
    }
    if (group_alive() || R < 5) { attack_group_camp(); walk_to(farm); return; }
    walk_to(stand);
}
#endif

#if SCENARIO == 3
// Scenario 3: stand at the centre (Ren stuns Varg R22, Willow R31); Willow does a non-stunned control
// action set at R20. From R45 farm the wolf pair at (22,27)/(22,28): Marcella starts a recall the first
// time a wolf hits her (camp-damage interrupt test). Varg captures alone, recalls, buys 5 Home shards,
// walks out and recalls again (Home recall timing). Willow logs actions on its respawn turn.
static const vec2 wolf_tile{22, 27};
static int stage = 0;
static float last_hp = -1;
static bool was_dead = false, marc_test = false, farmed = false;

static std::optional<map::camp_group> wolf_group() {
    for (auto& g : map::camp_groups()) if (g.spawn_tiles().is_set(wolf_tile)) return g;
    return std::nullopt;
}
static bool wolves_alive() {
    auto g = wolf_group();
    try { return g && std::holds_alternative<map::camp_group_alive>(g->state()); } catch (...) { return true; }
}
static void attack_wolf() {
    auto& me = self(); auto g = wolf_group();
    for (auto& c : vision::camps())
        if (g && g->spawn_tiles().is_set(c.spawn_position()) && me.can_attack() && me.attack_tiles().is_set(c.position())) { try { me.attack(c); } catch (...) {} return; }
}
static std::string control_actions() {
    auto& me = self();
    std::string s = "prio=" + act([&] { me.set_priority(0); });
    s += " ward=" + act([&] { return me.place_ward(me.position() + vec2{-1, 0}); });
    s += " buy=" + act([&] { me.buy(item_type::power_shard_of_strength, 1); });
    s += " tpc=" + act([&] { return me.consumables()[consumable_type::tp_crystal].use(me.position() + vec2{0, -2}); });
    return s;
}

void Bot::play_turn() {
    auto& me = self();
    const auto t = me.champion_name();
    const int R = static_cast<int>(round_number());
    log("self " + self_desc());
    if (!me.is_alive()) { was_dead = true; return; }
    if (was_dead) {
        was_dead = false;
        std::optional<champion> tgt;
        for (auto& e : vision::champions(team::enemy)) if (e.is_visible()) tgt = e;
        log("respawnTurn " + control_actions() + " cast0=" + act([&] { return me.abilities()[0].use(me); })
            + " attack=" + (tgt ? act([&] { me.attack(*tgt); }) : std::string("noTarget"))
            + " move=" + act([&] { return me.move(vec2{-1, -1}); }) + " | " + self_desc());
        return;
    }
    const float hp = me.health();
    const bool hit = last_hp >= 0 && hp < last_hp;
    last_hp = hp;
    if (me.restrictions().bits() != 0 || me.buffs().has_stun()) log("stunnedTurn " + control_actions());
    if (t == champion_type::willow && R == 20) log("controlTurn " + control_actions());
    if (me.is_recalling() || me.is_teleporting()) return;

    const vec2 stand = t == champion_type::varg ? vec2{17, 17} : t == champion_type::marcella ? vec2{16, 17} : vec2{17, 16};
    const vec2 farm = t == champion_type::varg ? vec2{23, 26} : t == champion_type::marcella ? vec2{23, 28} : vec2{25, 27};
    if (R < 45) { walk_to(stand); return; }

    if (t == champion_type::marcella && hit && !marc_test && wolves_alive()) {
        marc_test = true;
        log("campHitRecall=" + act([&] { me.recall(); }) + " " + self_desc());
        return;
    }
    if (t == champion_type::varg) {
        if (stage == 0) { if (!wolves_alive()) stage = 1; else { attack_wolf(); walk_to(farm); return; } }
        if (stage == 1) { if (me.gold_count() > 0) { log("captured " + self_desc()); stage = 2; } else { walk_to(wolf_tile); return; } }
        if (stage == 2) {
            if (map::spawn_region(team::ally).is_set(me.position())) stage = 3;
            else { log("startRecall=" + act([&] { me.recall(); })); return; }
        }
        if (stage == 3) { log("buyHome=" + act([&] { me.buy(item_type::home_shard_of_health, 5); }) + " " + self_desc()); stage = 4; }
        if (stage == 4) {
            if (me.position() == vec2{25, 25}) { log("homeRecall=" + act([&] { me.recall(); }) + " " + self_desc()); stage = 5; return; }
            walk_to({25, 25}); return;
        }
        if (stage == 5 && R >= 170) {
            if (me.position() == vec2{28, 25}) {
                log("submit=" + act([&] { me.submit_gems({28, 24}); }) + " " + self_desc() + " teamGems=" + std::to_string(global_submitted_gems(team::ally)));
                stage = 6; return;
            }
            walk_to({28, 25});
        }
        if (stage == 6) log("trib " + self_desc() + " sub=" + q([&] { return me.is_submitting_gems(); }) + " teamGems=" + std::to_string(global_submitted_gems(team::ally)));
        return; // stage 5/6: stay
    }
    if (!farmed && wolves_alive()) { attack_wolf(); walk_to(farm); return; }
    farmed = true;
    // Kill phase: stop wherever we are (outside bushes) so A can reach us.
    if (R >= 100 && !map::bushes().is_set(me.position())) return;
    walk_to(stand);
}
#endif
