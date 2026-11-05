// probe-designs: dump the engine's champion and camp designs, item table, game settings and camp-group rewards,
// and measure the fuel cost of reading champion designs at runtime.
//   cambc run tools/probes/probe-designs tools/probes/probe-designs --map maps/01boss-battle.map26a --rounds 2 --fuel 50000000
#include <cambc.h>
#include <cstdio>
#include <map>
#include <variant>

namespace {

void dump_ability(int slot, const cambc::ability& a) {
    const auto& info = a.info();
    if (!info) { std::printf("    slot%d empty\n", slot); return; }
    std::visit([&](const auto& x) {
        using A = std::decay_t<decltype(x)>;
        std::printf("    slot%d cd=%d excl=%d targets=%u ", slot, x.max_cooldown, x.exclusive_with_movement ? 1 : 0,
                    static_cast<unsigned>(x.valid_targets.bits()));
        if constexpr (std::is_same_v<A, cambc::ability_attack_reset>) std::printf("attack_reset enhanced=%d\n", x.enhanced_attack ? 1 : 0);
        else if constexpr (std::is_same_v<A, cambc::ability_damage>) std::printf("damage range=%g mod=%g\n", x.range, x.modifier);
        else if constexpr (std::is_same_v<A, cambc::ability_aoe_damage>) std::printf("aoe range=%g mod=%g radius=%g dur=%d\n", x.range, x.modifier, x.radius, x.duration);
        else if constexpr (std::is_same_v<A, cambc::ability_cc>) std::printf("cc range=%g mod=%g dur=%d\n", x.range, x.modifier, x.duration);
        else if constexpr (std::is_same_v<A, cambc::ability_heal>) std::printf("heal range=%g mod=%g\n", x.range, x.modifier);
        else if constexpr (std::is_same_v<A, cambc::ability_dash>) std::printf("dash range=%g radius=%g mod=%g dur=%d\n", x.range, x.radius, x.modifier, x.duration);
        else if constexpr (std::is_same_v<A, cambc::ability_shield>) std::printf("shield range=%g mod=%g dur=%d\n", x.range, x.modifier, x.duration);
    }, *info);
}

void dump_designs() {
    const auto& s = cambc::detail::cached_game_settings;
    std::printf("settings capture=%d sleep=%d respawn=%d recall=%d gem_mult=%g gem_base=%d gem_min=%d gem_range=%d max_rounds=%u win=%u "
                "kill_gold=%u assist_gold=%u passive_gold=%u spawn_heal=%g active_wards=%u ward_charges=%u ward_cd=%d ward_life=%d "
                "ward_vision=%g ward_place=%g lock_hits=%u tp_crystal=%d\n",
                s.capture_time, s.camp_sleep_time, s.respawn_time, s.recall_time, s.submit_gem_duration_multiplier, s.submit_gem_base_duration,
                s.submit_gem_minimum_duration, s.submit_gems_range, s.max_rounds, s.winning_gems, s.kill_gold, s.assist_gold, s.passive_gold,
                s.spawn_healing, s.active_wards, s.ward_charges, s.ward_cooldown, s.ward_lifetime, s.ward_vision_radius, s.ward_placement_radius,
                s.altar_lock_hits, s.tp_crystal_time);
    for (const auto& d : cambc::champion_designs) {
        const auto b = d.base_stats();
        std::printf("champion %s passive=%s range=%d vision=%d hp=[%g,%g] str=[%g,%g] focus=[%g,%g] camp_mult=%g\n",
                    cambc::to_string(d.champion_name()).c_str(), cambc::to_string(d.passive()).c_str(), b.base_attack_range, b.vision_radius,
                    b.base_health, b.health_growth, b.base_strength, b.strength_growth, b.base_focus, b.focus_growth, b.camp_damage_multiplier);
        for (int slot = 0; slot < 2; ++slot) dump_ability(slot, d.abilities()[slot]);
    }
    for (int t = 0; t <= static_cast<int>(cambc::camp_type::golem); ++t) {
        cambc::detail::camp_design v{};
        cambc::detail::check(cambc::detail::sdk_camp_design(t, &v));
        const auto& b = v.base_stats;
        std::printf("camp %s range=%d vision=%g hp=%g str=%g\n", cambc::to_string(static_cast<cambc::camp_type>(t)).c_str(),
                    b.base_attack_range, b.vision_radius, b.base_health, b.base_strength);
    }
    for (std::uint32_t i = 0; i < static_cast<std::uint32_t>(cambc::item_type::enum_type::count); ++i) {
        const cambc::item_type it{static_cast<cambc::item_type::enum_type>(i)};
        const auto x = it.info();
        std::printf("item %s cost=%u combine=%u result=%s hp=%d str=%d focus=%d passive=%s mag=%g buy=%d\n", cambc::to_string(it).c_str(),
                    x.cost, x.combine_count, x.result ? cambc::to_string(*x.result).c_str() : "-", x.health_points, x.strength_points,
                    x.focus_points, x.passive ? cambc::to_string(*x.passive).c_str() : "-", x.passive_magnitude, x.purchasable ? 1 : 0);
    }
    for (const auto& g : cambc::map::camp_groups()) {
        std::map<std::string, int> count;
        for (const auto& c : g.camps()) ++count[cambc::to_string(c.kind())];
        std::printf("group gold=%u gems=%u respawn=%d members=", g.gold_value(), g.gem_value(), g.max_respawn_timer());
        for (const auto& [k, n] : count) std::printf("%s:%d ", k.c_str(), n);
        std::printf("\n");
    }
}

// Fuel of building a full stat table from the engine, and of one design read.
void measure() {
    struct Row { float hp, hpg, str, strg, foc, focg; int range; };
    static Row table[13];
    auto f0 = cambc::fuel_remaining();
    for (const auto& d : cambc::champion_designs) {
        const auto b = d.base_stats();
        table[static_cast<int>(d.champion_name())] = {b.base_health, b.health_growth, b.base_strength, b.strength_growth, b.base_focus, b.focus_growth, b.base_attack_range};
    }
    auto f1 = cambc::fuel_remaining();
    const auto one = cambc::champion_designs[3].base_stats();
    auto f2 = cambc::fuel_remaining();
    volatile float sink = table[3].str + one.base_strength;
    auto f3 = cambc::fuel_remaining();
    const cambc::champion fresh{cambc::champion_type::ren};
    auto f4 = cambc::fuel_remaining();
    const auto mod = cambc::self().abilities()[0].info();
    auto f5 = cambc::fuel_remaining();
    (void)sink; (void)fresh; (void)mod;
    std::printf("fuel table13=%llu one_base_stats=%llu table_read=%llu new_design_champion=%llu self_ability_info=%llu\n",
                static_cast<unsigned long long>(f0 - f1), static_cast<unsigned long long>(f1 - f2), static_cast<unsigned long long>(f2 - f3),
                static_cast<unsigned long long>(f3 - f4), static_cast<unsigned long long>(f4 - f5));
}

} // namespace

int main() {
    bool dumped = false;
    while (true) {
        try {
            if (cambc::is_draft()) {
                cambc::draft::pick(cambc::champion_draft::heart_of_ruin);
            } else if (!dumped && cambc::self().team() == cambc::team::ally && cambc::round_number() >= 1) {
                dumped = true;
                if (cambc::self().champion_name() == cambc::champion_type::heart_of_ruin) dump_designs();
                measure();
            }
        } catch (const std::exception& e) {
            std::printf("PROBE err %s\n", e.what());
        }
        cambc::end_turn();
    }
}
