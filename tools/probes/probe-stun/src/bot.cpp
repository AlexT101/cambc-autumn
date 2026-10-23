// probe-stun (team A): scripted stunner / attacker for stun, kill-reward, death/respawn, recall and spawn probes.
// Pick the scenario by setting SCENARIO in BOTH tools/probes/probe-stun/src/scenario.h and tools/probes/probe-stun-b/src/scenario.h,
// then: cambc build probe-stun && cambc build probe-stun-b && cambc run probe-stun probe-stun-b --map packs ...
// Scenarios: 0 camp scout, 1 stun durations/restrictions/recall interrupts/spawn entry, 2 teleport stun + kill gold
// (Vesper vs Tavi killer) + death/respawn + spawn damage, 3 Ren stun watch, Vendetta reset, camp-hit recall,
// Home recall, tribute damage/stun. Add --statistics <file.json> on a full game for kills/assists per champion.
// Scenario 1 (packs): A = Tavi, Cassi&Issac, Prism vs probe-stun-b = Varg, Marcella, Tavi.
//   cambc run probe-stun probe-stun-b --map packs --rounds 110 --fuel 2000000 -o <dir>
#include "bot.h"
#include "probe.h"
#include "scenario.h"

#if SCENARIO == 1
// Cast `slot` on visible enemy `t`, logging target state before and after.
static void cast_on(int slot, champion_type t, const char* tag) {
    auto& me = self();
    auto e = find_enemy(t);
    if (!e) { log(std::string(tag) + " target_not_visible"); return; }
    log(std::string(tag) + " pre " + cname(t) + " " + desc(*e));
    auto r = act([&] { return me.abilities()[slot].use(*e); });
    log(std::string(tag) + " cast slot" + std::to_string(slot) + "=" + r + " post " + desc(*e));
}

void Bot::play_turn() {
    auto& me = self();
    const auto t = me.champion_name();
    const int R = static_cast<int>(round_number());
    if (R == 1 || R >= 26) log("self " + self_desc());
    if (!me.is_alive()) return;

    vec2 goal = t == champion_type::tavi ? vec2{13, 13} : t == champion_type::cassi ? vec2{14, 13}
              : t == champion_type::issac ? vec2{13, 14} : vec2{13, 12};
    // Q6: late game Issac walks to B's spawn, Cassi goes to shoot onto it.
    if (R >= 75 && t == champion_type::issac) goal = {27, 27};
    if (R >= 75 && t == champion_type::cassi) goal = {25, 25};

    if (t == champion_type::tavi) {
        if (R == 30) cast_on(1, champion_type::varg, "stunA");
        if (R >= 46 && R <= 49) { auto v = find_enemy(champion_type::varg); if (v && v->is_recalling()) { cast_on(1, champion_type::varg, "stunRecall"); } }
    }
    if (t == champion_type::cassi) {
        if (R == 31) cast_on(1, champion_type::tavi, "stunB");
        if (R == 40) cast_on(1, champion_type::marcella, "stunMarc");
        if (R >= 51 && R <= 54) {
            auto e = find_enemy(champion_type::tavi);
            if (e && e->is_recalling()) {
                log("dmgRecall pre " + desc(*e));
                auto r = act([&] { me.attack(*e); });
                log("dmgRecall attack=" + r + " post " + desc(*e));
            }
        }
        if (R >= 80) {
            for (auto& e : vision::champions(team::enemy)) {
                if (!e.is_visible() || !map::spawn_region(team::enemy).is_set(e.position())) continue;
                if (!me.attack_tiles().is_set(e.position()) || !me.can_attack()) continue;
                log(std::string("spawnAtk pre ") + cname(e.champion_name()) + " " + desc(e));
                auto r = act([&] { me.attack(e); });
                log("spawnAtk attack=" + r + " post " + desc(e));
                break;
            }
        }
    }
    if (t == champion_type::prism) {
        if (R == 34) cast_on(0, champion_type::tavi, "stunC");
        if (R >= 56 && R <= 58) { auto v = find_enemy(champion_type::varg); if (v && v->is_teleporting()) cast_on(0, champion_type::varg, "stunTp"); }
    }
    if (t == champion_type::issac && R >= 80 && me.position() == vec2{27, 27}) {
        // Try to step into the enemy spawn region.
        log("enterSpawn move(28,28)=" + act([&] { return me.move_absolute({28, 28}); }) + " pos=" + pos_s(me.position()));
    }
    walk_to(goal);
}
#endif

#if SCENARIO == 0
// Scenario 0: scout camp groups (type, tiles, gold, gems) on any map.
void Bot::play_turn() {
    if (round_number() != 1 || self().position() != map::spawn_region(team::ally).positions()[0]) return;
    for (auto& g : map::camp_groups()) {
        std::string s = "group gold=" + std::to_string(g.gold_value()) + " gems=" + std::to_string(g.gem_value());
        for (auto& c : g.camps()) s += " " + std::to_string((int)c.kind()) + "@" + pos_s(c.spawn_position());
        log(s);
    }
}
#endif

#if SCENARIO == 2
// Scenario 2 (packs): A = Vesper, Tavi, Cassi&Issac vs B = Tavi(victim), Varg, Willow.
//   cambc run probe-stun probe-stun-b --map packs --rounds 220 --fuel 2000000 -o <dir>
// Phase tp: A Tavi stuns B Tavi while it channels a teleport crystal.
// Phase kill1 (R>=62): focus B Tavi, Vesper must land the last hit (non-killers hold off at low hp).
// Phase kill2: focus B Willow, A Tavi must land the last hit. Then Cassi shoots B units on their spawn.
static int phase_target(champion_type& victim, champion_type& killer) {
    // Victim order: B tavi, then B willow (whichever is still alive/visible decides via engine state).
    auto bt = find_enemy(champion_type::tavi);
    victim = champion_type::tavi; killer = champion_type::vesper_vale;
    static bool tavi_dead = false;
    if (!tavi_dead && round_number() > 70 && !bt) tavi_dead = true; // not visible any more after kill phase
    if (tavi_dead) { victim = champion_type::willow; killer = champion_type::tavi; }
    return 0;
}

void Bot::play_turn() {
    auto& me = self();
    const auto t = me.champion_name();
    const int R = static_cast<int>(round_number());
    log("self " + self_desc());
    if (!me.is_alive()) return;

    vec2 goal = t == champion_type::tavi ? vec2{13, 13} : t == champion_type::cassi ? vec2{14, 13}
              : t == champion_type::issac ? vec2{13, 14} : vec2{13, 12};

    // Teleport-channel stun test.
    if (t == champion_type::tavi && R < 62) {
        auto e = find_enemy(champion_type::tavi);
        if (e && e->is_teleporting()) {
            log("stunTp pre " + desc(*e));
            auto r = act([&] { return me.abilities()[1].use(*e); });
            log("stunTp cast=" + r + " post " + desc(*e));
        }
    }

    if (R >= 62) {
        champion_type victim, killer; phase_target(victim, killer);
        auto e = find_enemy(victim);
        const bool is_killer = t == killer;
        if (e && e->is_visible() && e->is_alive()) {
            const float hp = e->health();
            std::string s = std::string("focus ") + cname(victim) + " hp=" + q([&] { return e->health(); });
            // Spells only while the target is healthy (non-killers), killer may reset its attack.
            if (!is_killer && hp > 400) {
                int slot = t == champion_type::tavi ? 1 : t == champion_type::cassi ? 0 : -1;
                if (slot >= 0 && me.abilities()[slot].is_ready()) s += " cast" + std::to_string(slot) + "=" + act([&] { return me.abilities()[slot].use(*e); });
            }
            const bool in_range = me.attack_tiles().is_set(e->position());
            if (in_range && me.can_attack() && (is_killer || e->health() > 150)) {
                s += " attack=" + act([&] { me.attack(*e); });
                if (is_killer && e->is_visible() && e->health() > 0 && me.abilities()[0].is_attack_reset() && me.abilities()[0].is_ready()) {
                    s += " reset=" + act([&] { return me.abilities()[0].use(); });
                    if (e->is_visible() && e->health() > 0) s += " attack2=" + act([&] { me.attack(*e); });
                }
            }
            s += " after: alive=" + q([&] { return e->is_alive(); }) + " hp=" + q([&] { return e->health(); }) + " mygold=" + q([&] { return me.gold_count(); }) + " mygems=" + q([&] { return me.gem_count(); });
            log(s);
            if (!in_range) goal = approach_tile(e->position(), me.attack_range());
        }
        // After kill2, Cassi goes to shoot onto B's spawn.
        if (R >= 140 && t == champion_type::cassi) {
            goal = {26, 27};
            for (auto& x : vision::champions(team::enemy)) {
                if (!x.is_visible() || !map::spawn_region(team::enemy).is_set(x.position())) continue;
                if (!me.attack_tiles().is_set(x.position()) || !me.can_attack()) continue;
                log(std::string("spawnAtk pre ") + cname(x.champion_name()) + " " + desc(x));
                auto r = act([&] { me.attack(x); });
                log("spawnAtk attack=" + r + " post " + desc(x));
                break;
            }
        }
    }
    walk_to(goal);
}
#endif

#if SCENARIO == 3
// Scenario 3 (packs): A = Ren, Vendetta, Tavi vs B = Varg, Marcella, Willow.
//   cambc run probe-stun probe-stun-b --map packs --rounds 260 --fuel 2000000 -o <dir>
// R22 Ren stuns B Varg, R31 Ren stuns B Willow; every A champion logs the target's buff each turn
// for 3 rounds after. From R110 A focuses B Willow with Vendetta as the killer (cooldown reset check).
void Bot::play_turn() {
    auto& me = self();
    const auto t = me.champion_name();
    const int R = static_cast<int>(round_number());
    log("self " + self_desc());
    if (!me.is_alive()) return;
    vec2 goal = t == champion_type::ren ? vec2{13, 13} : t == champion_type::vendetta ? vec2{14, 13} : vec2{13, 14};

    if (R >= 22 && R <= 25) if (auto e = find_enemy(champion_type::varg)) log("watch varg " + desc(*e));
    if (R >= 31 && R <= 34) if (auto e = find_enemy(champion_type::willow)) log("watch willow " + desc(*e));
    if (t == champion_type::ren && (R == 22 || R == 31)) {
        auto tt = R == 22 ? champion_type::varg : champion_type::willow;
        if (auto e = find_enemy(tt)) {
            log(std::string("stunRen pre ") + cname(tt) + " " + desc(*e));
            auto r = act([&] { return me.abilities()[0].use(*e); });
            log("stunRen cast=" + r + " post " + desc(*e));
        } else log("stunRen target_not_visible");
    }

    // Tribute test: from R165 A Tavi watches B Varg at the (28,24) altar: 1st submitting turn basic-attacks it,
    // 2nd submitting turn stuns it.
    if (t == champion_type::tavi && R >= 150) {
        static int seen = 0;
        if (auto v = find_enemy(champion_type::varg); v && v->is_submitting_gems()) {
            ++seen;
            if (seen == 1) { log("tribAtk pre " + desc(*v)); auto r = act([&] { me.attack(*v); }); log("tribAtk attack=" + r + " post " + desc(*v)); }
            else if (seen == 2) { log("tribStun pre " + desc(*v)); auto r = act([&] { return me.abilities()[1].use(*v); }); log("tribStun cast=" + r + " post " + desc(*v)); }
        }
        walk_to({25, 22});
        return;
    }
    if (R >= 110) {
        const bool is_killer = t == champion_type::vendetta;
        auto e = find_enemy(champion_type::willow);
        if (e && e->is_visible() && e->is_alive()) {
            std::string s = std::string("focus willow hp=") + q([&] { return e->health(); });
            if (!is_killer && e->health() > 400) {
                int slot = t == champion_type::tavi ? 1 : 0;
                if (me.abilities()[slot].is_ready()) s += " cast" + std::to_string(slot) + "=" + act([&] { return me.abilities()[slot].use(*e); });
            }
            bool in_range = me.attack_tiles().is_set(e->position());
            if (is_killer && !in_range && me.abilities()[1].is_ready()) {
                vec2 to = approach_tile(e->position(), 1);
                if (to.chebyshev_distance(me.position()) <= 2) { s += " dash=" + act([&] { return me.abilities()[1].use(to); }); in_range = me.attack_tiles().is_set(e->position()); }
            }
            if (in_range && me.can_attack() && (is_killer || e->health() > 150)) {
                s += " attack=" + act([&] { me.attack(*e); });
                if (is_killer && e->is_visible() && e->health() > 0 && me.abilities()[0].is_ready()) {
                    s += " reset=" + act([&] { return me.abilities()[0].use(); });
                    if (e->is_visible() && e->health() > 0) s += " attack2=" + act([&] { me.attack(*e); });
                }
            }
            s += " after: alive=" + q([&] { return e->is_alive(); }) + " hp=" + q([&] { return e->health(); }) + " | " + self_desc();
            log(s);
            if (!in_range) goal = approach_tile(e->position(), me.attack_range());
        }
    }
    walk_to(goal);
}
#endif
