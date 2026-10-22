#include "abilities.h"
#include <algorithm>
#include <array>
#include <optional>
#include <vector>
#include "safety.h"
#include "params.h"
#include "pathing.h"
#include "world.h"

namespace aph {

namespace {

// Values are in enemy health points.
constexpr float stun_value = 80;
constexpr float winning_tribute_value = 5000; // a stun that stops the enemy's game-winning tribute
constexpr float min_value = 40;
constexpr float min_landing_value = 250; // a landing moves us off the goal's way
constexpr float min_camp_value = 50;
constexpr int max_unseen_tiles = 9; // unseen enemies spread over more tiles are not aimed at
constexpr int hold_range = 6;       // camp casts wait while a visible enemy is this close

bool walked(const World& world) { return my_position() != world.me().pos; }

bool castable(const World& world, int slot) {
    const auto& a = world.me().facts().abilities[slot];
    return a.hits_enemies() && !(a.excludes_walking && walked(world)) && world.me().ability_ready(slot, world.round);
}

struct Cast {
    int slot = -1;
    float value = 0;
    std::optional<cambc::handle_champion_t> champion;
    std::optional<cambc::camp> camp;
    vec2 tile{-1, -1};
    bool dash = false; // a landing on `tile`

    void offer(const Cast& other) {
        if (other.slot >= 0 && other.value > value) *this = other;
    }
    bool execute() const {
        if (slot < 0) return false;
        try {
            if (champion) return cast_slot_on(slot, *champion);
            if (camp) return cast_slot_on(slot, static_cast<cambc::handle_camp_t>(*camp));
            const bool cast = cast_slot(slot, tile);
            outside_dashes() += cast && dash;
            return cast;
        } catch (const cambc::error&) {
            return false;
        }
    }
};

float raw_damage(int slot) {
    try {
        return my_damage(slot);
    } catch (const cambc::error&) {
        return 0;
    }
}

// Health lost after mitigation and shields, capped at health.
float damage_to(int slot, cambc::handle_champion_t target, float raw) {
    if (raw <= 0) return 0;
    try {
        return my_damage_to(slot, target);
    } catch (const cambc::error&) {
        return std::min(raw, record_of(target).health);
    }
}

bool camp_stunned(std::uint32_t camp) {
    static std::array<cambc::detail::camp_buff_data, static_cast<std::size_t>(cambc::buff_types::count)> buffs;
    std::uint32_t n = 0;
    ok(cambc::detail::sdk_camp_buffs(camp, buffs.data(), static_cast<std::uint32_t>(buffs.size()), &n));
    for (std::uint32_t i = 0; i < n && i < buffs.size(); ++i)
        if (buffs[i].type == static_cast<std::uint32_t>(cambc::buff_types::stun)) return true;
    return false;
}

bool kept_recall(const ChampionBelief& e) {
    return e.channel == Channel::recall && e.visible
           && aph::kept_recall(e.handle, e.fast_recall ? home_recall_time : static_cast<int>(cambc::constants::recall_time));
}

// A kill takes the bag, both bags for Cassi and Issac, who die together. Other damage to an
// enemy on its spawn heals at its turn end, and damage to the healthier of Cassi and Issac only
// counts once it takes that body below the other.
float hit_worth(const World& world, const ChampionBelief& e, float damage, float health, bool on_spawn) {
    if (health > 0 && damage >= health - 0.01f) {
        return health + params::life_value + params::gem_value * static_cast<float>(pair_gems(world, e));
    }
    if (on_spawn || damage <= 0) return 0;
    return useful_damage(damage, health, linked_partner_health(world, e)) + (kept_recall(e) ? params::recall_value : 0);
}

} // namespace

float stun_worth(const World& world, const ChampionBelief& e, bool damaging) {
    if (e.facts().passive == Passive::stun_immune) return 0;
    float v = stun_value;
    if (e.channel == Channel::tribute) v += params::tribute_value + params::gem_value * static_cast<float>(e.gems);
    if (e.channel == Channel::tribute && enemy_tribute_wins(world, e)) v += winning_tribute_value;
    if (!damaging && kept_recall(e)) v += params::recall_value;
    return v;
}

bool landing_wakes(const World& world, vec2 p, int radius) {
    const auto& groups = world.map().groups;
    for (int g : world.map().groups_near(p, radius)) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.fully_awake() || groups[g].strength <= 0 || g == siege_group()) continue;
        for (std::size_t i = 0; i < groups[g].members.size(); ++i)
            if (c.health[i] > 0 && dist(p, groups[g].members[i].pos) <= radius) return true;
    }
    return false;
}

namespace {

struct Target {
    vec2 pos;
    float weight; // chance the enemy is on this tile
    float worth;  // if hit
};

// The scratch vectors and boards here are kept across calls: allocating costs more than the work.

void draw_alive_members(const World& world, int g, bitboard& out, int radius = 1) {
    const auto& members = world.map().groups[g].members;
    for (std::size_t i = 0; i < members.size(); ++i)
        if (world.camps[g].health[i] > 0) draw_square(out, members[i].pos, static_cast<float>(radius));
}

// Ground centres to skip: their 3x3 would hit a member of a sleeping group, which wakes whole,
// with a monster near us, or of a sleeping Monolith group other than the siege target. In a
// scratch board valid until the next call.
const bitboard& wake_risk(const World& world, vec2 here, int reach) {
    const auto& groups = world.map().groups;
    static bitboard risk{cambc::uninitialized};
    clear_board(risk);
    for (int g : world.map().groups_near(here, reach)) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.fully_awake() || groups[g].strength <= 0) continue;
        bool near = groups[g].has_monolith && g != siege_group();
        for (std::size_t i = 0; i < groups[g].members.size() && !near; ++i)
            near = c.health[i] > 0 && groups[g].members[i].strength > 0 && c.maybe_asleep(i)
                   && dist(here, groups[g].members[i].pos) <= groups[g].members[i].reach;
        if (near) draw_alive_members(world, g, risk);
    }
    return risk;
}

// Centres within `range` of `here`, off `skip`.
Cast best_ground(int slot, float min_weight_value, const std::vector<Target>& targets, vec2 here, int range,
                 const bitboard& skip, const std::vector<vec2>* harmful = nullptr) {
    constexpr int max_range = 5; // ability ranges are 4
    Cast best;
    if (targets.empty()) return best;
    range = std::min(range, max_range);
    const int side = 2 * range + 1;
    std::array<float, (2 * max_range + 1) * (2 * max_range + 1)> value;
    // Only the cells around a target are read: clear those alone when fewer.
    const auto around = [&](const Target& t, auto&& f) {
        for (int dy = -1; dy <= 1; ++dy)
            for (int dx = -1; dx <= 1; ++dx) {
                const int x = t.pos.x + dx - here.x + range, y = t.pos.y + dy - here.y + range;
                if (x >= 0 && x < side && y >= 0 && y < side) f(value[static_cast<std::size_t>(y * side + x)]);
            }
    };
    if (9 * targets.size() < static_cast<std::size_t>(side * side))
        for (const auto& t : targets) around(t, [](float& v) { v = 0; });
    else
        std::fill_n(value.begin(), side * side, 0.0f);
    static bitboard centres{cambc::uninitialized};
    clear_board(centres);
    for (const auto& t : targets) {
        if (dist(t.pos, here) > range + 1) continue; // no centre in range
        draw_square(centres, t.pos, 1);
        around(t, [&](float& v) { v += t.weight * t.worth; });
    }
    static bitboard box{cambc::uninitialized};
    clear_board(box);
    draw_square(box, here, static_cast<float>(range));
    and_into(centres, box, centres);
    and_into(centres, skip, box);
    xor_into(centres, box, centres);
    // In board order, which breaks ties.
    for (auto c : Tiles<17 * 17>{centres}) {
        const float v = value[(c.y - here.y + range) * side + (c.x - here.x + range)];
        if (!(v > best.value && v >= min_weight_value)) continue;
        if (harmful) {
            int hits = 0;
            for (auto p : *harmful)
                if (dist(c, p) <= 1 && ++hits >= 2) break;
            if (hits < 2) continue;
        }
        best.slot = slot, best.value = v, best.tile = c;
    }
    return best;
}

// The landing that `keep` accepts whose `radius` around it hits most, nearest `here` on ties.
template <class Keep>
Cast best_landing(int slot, float min_value, const std::vector<Target>& targets, const bitboard& landings, vec2 here,
                  int radius, Keep keep) {
    Cast best;
    if (targets.empty()) return best;
    // Dash landings are within 2 of `here`. Each cell adds its targets in their order, as summing per landing would.
    constexpr int reach = 2, side = 2 * reach + 1;
    std::array<float, side * side> value{};
    for (const auto& t : targets) {
        const int x0 = std::max(t.pos.x - radius, here.x - reach), x1 = std::min(t.pos.x + radius, here.x + reach);
        const int y0 = std::max(t.pos.y - radius, here.y - reach), y1 = std::min(t.pos.y + radius, here.y + reach);
        for (int y = y0; y <= y1; ++y)
            for (int x = x0; x <= x1; ++x) value[(y - here.y + reach) * side + (x - here.x + reach)] += t.weight * t.worth;
    }
    int best_dist = 0;
    for (auto p : Tiles<5 * 5>{landings}) {
        const int d = dist(p, here);
        const float v = value[(p.y - here.y + reach) * side + (p.x - here.x + reach)];
        if (v < min_value || v < best.value || (v == best.value && d >= best_dist) || !keep(p)) continue;
        best.slot = slot, best.value = v, best.tile = p, best.dash = true, best_dist = d;
    }
    return best;
}

Cast enemy_cast(const World& world, float walk, bool landings) {
    Cast best;
    if (!my_can_cast()) return best;
    const vec2 here = my_position();
    const auto& f = world.me().facts();
    // Most turns no enemy is in reach: skip the engine reads below.
    int reach = -1;
    bool ground = false;
    for (const auto& a : f.abilities)
        if (a.hits_enemies() && (landings || !a.lands()))
            reach = std::max(reach, a.reach()), ground |= a.target == Targeting::ground || a.lands();
    int visible = 0, unseen = 0;
    for (const auto& e : world.enemies) {
        if (!e.alive) continue;
        if (e.visible) visible += dist(here, e.pos) <= reach;
        else unseen += ground && e.tracked;
    }
    if (visible + unseen == 0) return best;
    const auto& enemy_spawn = world.map().enemy_spawn;
    if (!my_can_move()) walk = 0;
    // A stun takes its target's walk as the cast takes ours: with every visible enemy that could
    // reach us next turn stunned, keeping the walk gains nothing. `free_stun`: centres that do so.
    std::array<const ChampionBelief*, 16> reaching;
    int n_reaching = 0;
    bool unstoppable = false;
    if (walk > 0)
        for (const auto& e : world.enemies) {
            if (n_reaching == 16) break;
            if (!e.alive || !e.visible || !strike(e, next_turn_round(world, e)).hits(dist(here, e.pos))) continue;
            if (!visible_record(e.handle) || has_stun(e.handle)) continue;
            unstoppable |= e.facts().passive == Passive::stun_immune;
            reaching[n_reaching++] = &e;
        }
    const bool walk_matters = n_reaching == 0 || unstoppable;
    static bitboard not_free{cambc::uninitialized}; // ~free_stun
    if (!walk_matters) {
        static bitboard free_stun{cambc::uninitialized};
        free_stun.fill();
        static bitboard around{cambc::uninitialized};
        for (int i = 0; i < n_reaching; ++i) {
            clear_board(around);
            draw_square(around, reaching[i]->pos, 1);
            and_into(free_stun, around, free_stun);
        }
        not_free.fill();
        xor_into(not_free, free_stun, not_free);
    }
    const bitboard* risk = nullptr;
    for (int s = 0; s < 2; ++s) {
        if (!castable(world, s)) continue;
        const auto& a = f.abilities[s];
        const float threshold = min_value + (a.excludes_walking ? walk : 0.0f);
        const float raw = raw_damage(s);
        const auto suicidal = [&](const ChampionBelief& e) { return raw > 0 && e.retaliation() >= my_health(); };
        if (a.lands()) {
            if (!landings) continue;
            // It moves us: worth only what an excludes-walking cast must be worth to keep the walk.
            static std::vector<Target> targets;
            targets.clear();
            static bitboard off{cambc::uninitialized};
            clear_board(off);
            for (const auto& e : world.enemies) {
                if (!e.alive) continue;
                if (e.visible) {
                    if (dist(here, e.pos) > a.reach()) continue;
                    const auto* live = visible_record(e.handle);
                    if (!live) continue;
                    const float health = live->health;
                    const float damage = damage_to(s, e.handle, raw);
                    if (suicidal(e)) {
                        draw_square(off, e.pos, static_cast<float>(a.radius));
                        continue;
                    }
                    const float stun = a.stuns && !has_stun(e.handle) ? stun_worth(world, e, raw > 0) : 0;
                    targets.push_back({e.pos, 1, hit_worth(world, e, damage, health, test(enemy_spawn, e.pos)) + stun});
                } else if (e.tracked && !board_empty(e.possible)) {
                    const int n = static_cast<int>(board_count(e.possible));
                    if (n > max_unseen_tiles) continue;
                    const auto near = positions_within(e.possible, here, a.reach());
                    if (near.empty()) continue;
                    if (suicidal(e)) {
                        for (auto p : near) draw_square(off, p, static_cast<float>(a.radius));
                        continue;
                    }
                    const float health = e.health > 0 ? e.health : e.max_health;
                    const float stun = a.stuns ? stun_worth(world, e, raw > 0) : 0;
                    for (auto p : near)
                        targets.push_back({p, 1.0f / static_cast<float>(n),
                                           hit_worth(world, e, std::min(raw, health), health, test(enemy_spawn, p)) + stun});
                }
            }
            if (targets.empty()) continue;
            best.offer(best_landing(s, min_landing_value, targets, dash_landings_from(world.map(), here, &off), here, a.radius,
                                    [&](vec2 p) { return !landing_wakes(world, p, a.radius); }));
        } else if (a.target == Targeting::unit) {
            for (const auto& e : world.enemies) {
                if (!e.alive || !e.visible || dist(here, e.pos) > a.range() || suicidal(e)) continue;
                const auto* live = visible_record(e.handle);
                if (!live) continue;
                const float health = live->health;
                float v = hit_worth(world, e, damage_to(s, e.handle, raw), health, test(enemy_spawn, e.pos));
                if (a.stuns && !has_stun(e.handle)) v += stun_worth(world, e, raw > 0);
                const bool free = a.stuns && !walk_matters && n_reaching == 1 && reaching[0] == &e;
                if (v >= (free ? min_value : threshold) && v > best.value) best = Cast{s, v, e.handle, std::nullopt, {}};
            }
        } else if (a.target == Targeting::ground) {
            static std::vector<Target> targets;
            targets.clear();
            // The area hits every enemy in it, unseen too: keep it off a Ren whose retaliation kills us.
            static bitboard off{cambc::uninitialized};
            clear_board(off);
            for (const auto& e : world.enemies) {
                if (!e.alive) continue;
                if (e.visible) {
                    if (dist(here, e.pos) > a.reach()) continue;
                    if (suicidal(e)) {
                        draw_square(off, e.pos, 1);
                        continue;
                    }
                    const auto* live = visible_record(e.handle);
                    if (!live) continue;
                    const float health = live->health;
                    const float stun = a.stuns && !has_stun(e.handle) ? stun_worth(world, e, raw > 0) : 0;
                    const float hit = hit_worth(world, e, damage_to(s, e.handle, raw), health, test(enemy_spawn, e.pos));
                    targets.push_back({e.pos, 1, hit + stun});
                } else if (e.tracked && !board_empty(e.possible)) {
                    const int n = static_cast<int>(board_count(e.possible));
                    if (n > max_unseen_tiles) continue;
                    const auto near = positions_within(e.possible, here, a.reach());
                    if (near.empty()) continue;
                    if (suicidal(e)) {
                        for (auto p : near) draw_square(off, p, 1);
                        continue;
                    }
                    const float health = e.health > 0 ? e.health : e.max_health;
                    const float hit = std::min(raw, health);
                    const float stun = a.stuns ? stun_worth(world, e, raw > 0) : 0;
                    for (auto p : near)
                        targets.push_back({p, 1.0f / static_cast<float>(n),
                                           hit_worth(world, e, hit, health, test(enemy_spawn, p)) + stun});
                }
            }
            if (targets.empty()) continue;
            if (!risk) risk = &wake_risk(world, here, a.reach());
            static bitboard skip{cambc::uninitialized};
            or_into(*risk, off, skip);
            best.offer(best_ground(s, threshold, targets, here, a.range(), skip));
            if (a.stuns && threshold > min_value && !walk_matters) {
                or_into(skip, not_free, skip);
                best.offer(best_ground(s, min_value, targets, here, a.range(), skip));
            }
        }
    }
    return best;
}

Cast camp_cast(const World& world, int group, bool attackers_only, bool any_value, bool approach = false) {
    if (!my_can_cast()) return {};
    const auto& f = world.me().facts();
    const std::array<bool, 2> ready{castable(world, 0), castable(world, 1)};
    if (!ready[0] && !ready[1]) return {};
    const bool stuns = (ready[0] && f.abilities[0].stuns) || (ready[1] && f.abilities[1].stuns);
    const vec2 here = my_position();
    const auto& g = world.map().groups[group];
    const bool harmless_approach = approach && g.strength <= 0;
    if ((g.has_monolith && group != siege_group()) || world.camps[group].state != CampState::alive) return {};
    if (enemy_within(world, here, hold_range)) return {};
    // A ranged walk also spends the basic: require our native position to be unchanged.
    const bool post_basic = !approach && !attackers_only && !my_can_attack() && !walked(world);
    bool all_visible = post_basic;

    struct Member {
        int index; // in the group
        vec2 pos;
        float health, stun;
        bool harmful;
    };
    static std::vector<Member> members;
    static std::vector<vec2> harmful;
    members.clear();
    harmful.clear();
    for (int i = 0; i < static_cast<int>(g.members.size()); ++i) {
        all_visible = all_visible && test(world.visible, g.members[i].pos);
        if ((!post_basic && world.camps[group].health[i] <= 0) || (attackers_only && g.members[i].strength <= 0)
            || !cambc::vision::has_camp(g.members[i].pos))
            continue;
        const auto handle = static_cast<std::uint32_t>(g.members[i].handle);
        static cambc::detail::camp_state record;
        const auto code = cambc::detail::sdk_camp(handle, &record);
        if (code == static_cast<std::int32_t>(cambc::error_code::api_not_in_vision)
            || code == static_cast<std::int32_t>(cambc::error_code::api_not_found)) {
            all_visible = false;
            continue;
        }
        ok(code);
        const float health = record.health;
        if (health <= 0) continue;
        // A stunned monster skips its next attack, which goes to the nearest champion: one of us
        // when we are in its reach, enemies being held off above.
        bool exposed = dist(here, g.members[i].pos) <= g.members[i].reach;
        // At a Monolith, a stun spares whichever of us it would hit.
        if (g.has_monolith)
            for (const auto& a : world.allies)
                exposed |= !exposed && a.alive && a.visible && dist(a.pos, g.members[i].pos) <= g.members[i].reach;
        const float stun = stuns && exposed && !camp_stunned(handle) ? g.members[i].strength : 0;
        const bool harms = g.members[i].strength > 0;
        members.push_back({i, g.members[i].pos, health, stun, harms});
        if (approach && harms) harmful.push_back(g.members[i].pos);
    }
    if (members.empty()) return {};
    const bool sole_finish = all_visible && members.size() == 1;
    float finish_factor = 1.0f;
    if (sole_finish) {
        const auto& owned = my_items();
        if (owned[cambc::item_type::monster_emblem_of_strength] > 0
            || owned[cambc::item_type::monster_emblem_of_focus] > 0
            || owned[cambc::item_type::monster_emblem_of_health] > 0)
            finish_factor = 1.1f;
    }

    Cast best;
    for (int s = 0; s < 2; ++s) {
        if (!ready[s] || (harmless_approach && f.abilities[s].target != Targeting::ground)) continue;
        const auto& a = f.abilities[s];
        const float raw = raw_damage(s);
        // Native raw already includes outgoing passives; Monster is target-dependent and applies once.
        const bool finishes = sole_finish && !a.lands() && raw * finish_factor >= members[0].health;
        // A stun that deals nothing and keeps the walk costs only its cooldown.
        const float floor = finishes ? 0.0f
                            : any_value || (g.has_monolith && a.stuns && raw <= 0 && !a.excludes_walking) ? 1.0f : min_camp_value;
        if (a.target == Targeting::unit) {
            for (const auto& m : members) {
                if ((approach && !m.harmful) || dist(here, m.pos) > a.range()) continue;
                const float v = std::min(raw, m.health) + (a.stuns ? m.stun : 0);
                if (v >= floor && v > best.value) best = Cast{s, v, std::nullopt, g.camp(m.index), {}};
            }
        } else if (a.target == Targeting::ground) {
            static std::vector<Target> targets;
            targets.clear();
            for (const auto& m : members) targets.push_back({m.pos, 1, std::min(raw, m.health) + (a.stuns ? m.stun : 0)});
            static bitboard skip{cambc::uninitialized};
            clear_board(skip);
            for (int other : world.map().groups_near(here, a.reach()))
                if (other != group && world.camps[other].state == CampState::alive) draw_alive_members(world, other, skip);
            best.offer(best_ground(s, finishes ? 0.0f : any_value ? 1.0f : min_camp_value, targets, here, a.range(), skip,
                                   approach && !harmless_approach ? &harmful : nullptr));
        } else if (a.lands()) {
            // A dash off a cleared group gives up its capture.
            if (const int at = world.map().group_at(here); at >= 0 && world.camps[at].state == CampState::cleared) continue;
            static std::vector<Target> targets;
            targets.clear();
            for (const auto& m : members) targets.push_back({m.pos, 1, std::min(raw, m.health) + (a.stuns ? m.stun : 0)});
            static bitboard skip{cambc::uninitialized};
            clear_board(skip);
            for (int other : world.map().groups_near(here, a.reach()))
                if (other != group && world.camps[other].state == CampState::alive) draw_alive_members(world, other, skip, a.radius);
            const auto& lands_ = dash_landings_from(world.map(), here, &skip);
            // Not into the reach of another group's monsters. Landings are within 2 of `here`: each
            // group's monsters that could reach one are listed the first time it is asked about.
            struct Threat {
                vec2 pos;
                int reach;
            };
            static std::vector<Threat> threats;
            static std::vector<std::array<int, 3>> listed; // group, its first threat, its end
            threats.clear();
            listed.clear();
            const auto keep = [&](vec2 p) {
                for (int other : world.map().groups_near(p, world.map().max_camp_reach)) {
                    if (other == group || world.camps[other].state != CampState::alive) continue;
                    auto it = std::find_if(listed.begin(), listed.end(), [&](const auto& l) { return l[0] == other; });
                    if (it == listed.end()) {
                        const int from = static_cast<int>(threats.size());
                        const auto& ms = world.map().groups[other].members;
                        for (std::size_t i = 0; i < ms.size(); ++i) {
                            const int d = dist(here, ms[i].pos);
                            if (world.camps[other].health[i] > 0 && ms[i].strength > 0 && d > ms[i].reach && d <= ms[i].reach + 2)
                                threats.push_back({ms[i].pos, ms[i].reach});
                        }
                        listed.push_back({other, from, static_cast<int>(threats.size())});
                        it = listed.end() - 1;
                    }
                    for (int k = (*it)[1]; k < (*it)[2]; ++k)
                        if (dist(p, threats[k].pos) <= threats[k].reach) return false;
                }
                return true;
            };
            best.offer(best_landing(s, any_value ? 1.0f : min_camp_value, targets, lands_,
                                    here, a.radius, keep));
        }
    }
    return best;
}

} // namespace

bool enemy_tribute_wins(const World& world, const ChampionBelief& e) {
    return e.alive && e.visible && e.channel == Channel::tribute
           && world.score.enemy + e.gems >= static_cast<int>(cambc::constants::winning_gems);
}

bool cast_at_enemies(const World& world, float walk) {
    world.throw_if_stale();
    try {
        return enemy_cast(world, walk, true).execute();
    } catch (const cambc::error&) {
        return false;
    }
}

bool cast_at_camp(const World& world, int group, bool attackers_only, bool any_value) {
    world.throw_if_stale();
    try {
        const auto selected = camp_cast(world, group, attackers_only, any_value);
        world.throw_if_stale();
        const bool cast = selected.execute();
        world.throw_if_stale();
        camp_hits() += cast;
        return cast;
    } catch (const cambc::error&) {
        return false;
    }
}

bool cast_at_camp_on_approach(const World& world, int group) {
    world.throw_if_stale();
    if (world.me().type != cambc::champion_type::prism
        || (!world.me().ability_ready(0, world.round) && !world.me().ability_ready(1, world.round))
        || !my_can_cast() || walked(world))
        return false;
    const auto& c = world.camps[group];
    if (c.state != CampState::alive) return false;
    const auto& map = world.map();
    const auto& g = map.groups[group];
    const bool harmless = g.strength <= 0;
    if (harmless ? g.members.size() <= 1 : c.awake != Awake::awake) return false;
    const vec2 here = my_position();
    const int range = world.me().facts().attack_range();
    for (std::size_t i = 0; i < g.members.size(); ++i)
        if ((harmless || c.health[i] > 0) && dist(here, g.members[i].pos) <= range && cambc::vision::has_camp(g.members[i].pos))
            return false;
    for (int other : map.groups_near(here, map.max_camp_reach)) {
        if (world.camps[other].state != CampState::alive) continue;
        const auto& members = map.groups[other].members;
        for (std::size_t i = 0; i < members.size(); ++i)
            if (world.camps[other].health[i] > 0 && members[i].strength > 0 && dist(here, members[i].pos) <= members[i].reach)
                return false;
    }
    try {
        const auto selected = camp_cast(world, group, false, false, true);
        world.throw_if_stale();
        const bool cast = selected.execute();
        world.throw_if_stale();
        camp_hits() += cast;
        return cast;
    } catch (const cambc::error&) {
        return false;
    }
}

} // namespace aph
