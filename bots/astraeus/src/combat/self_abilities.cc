#include "self_abilities.h"
#include <algorithm>
#include <array>
#include <compare>
#include <optional>
#include <vector>
#include "abilities.h"
#include "../champions.h"
#include "../emblems.h"
#include "../params.h"
#include "../model/pathing.h"
#include "../model/safety.h"
#include "../model/world.h"

namespace aph {

namespace {

// No visible enemy this close for a travel dash: one we could still see from its landing.
constexpr int travel_dash_clearance = vision_radius + dash_range;
constexpr float heal_min_share = 0.6f; // of the heal amount restored
// dash_to_attack chases an enemy below this health fraction and below ours.
constexpr float chase_health = 0.4f;
constexpr int failed_search_pause = 4; // rounds without a travel-dash search after one finds no gain

// The slot of `kind` if it can be cast now, else -1.
int ready(const World& world, AbilityKind kind) {
    const auto& self = world.me();
    const int slot = self.facts().slot_of(kind);
    // The belief is exact for ourselves at turn start; only a Vendetta kill readies a slot mid-turn.
    if (slot < 0 || !self.alive
        || (!self.ability_ready(slot, world.round) && self.facts().passive != Passive::reset_on_kill))
        return -1;
    if (!my_can_cast() || my_cooldown(slot) > 0) return -1;
    return slot;
}

bool cast(int slot, vec2 tile = {-1, -1}) {
    try {
        return cast_slot(slot, tile);
    } catch (const cambc::error&) {
        return false;
    }
}

struct Hazard {
    vec2 pos;
    int reach;
    bool camp;
};

// Enemies and, with `camps`, awake monsters that could reach a tile within a dash of `here` before
// our next turn. A scratch vector, valid until the next call: allocating costs more than the work.
// `dead`: an enemy we killed this turn, still alive in the beliefs.
const std::vector<Hazard>& threats_near(const World& world, vec2 here, vec2 dead = {-1, -1}, bool camps = true) {
    static std::vector<Hazard> out;
    out.clear();
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible || e.pos == dead) continue;
        const int reach = threat_strike(world, e).reach;
        if (reach >= 0 && dist(here, e.pos) <= reach + dash_range) out.push_back({e.pos, reach, false});
    }
    if (!camps) return out;
    const auto& groups = world.map().groups;
    for (int g : world.map().groups_near(here, world.map().max_camp_reach + dash_range)) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.awake == Awake::asleep) continue;
        for (std::size_t i = 0; i < groups[g].members.size(); ++i) {
            const auto& m = groups[g].members[i];
            if (c.health[i] > 0 && m.strength > 0 && !c.member_asleep(i) && dist(here, m.pos) <= m.reach + dash_range)
                out.push_back({m.pos, m.reach, true});
        }
    }
    return out;
}

// How deep a tile sits inside the threats' reach. A camp strikes as hard anywhere in its reach.
int danger(const std::vector<Hazard>& threats, vec2 p) {
    int d = 0;
    for (const auto& t : threats) {
        const int depth = t.reach - dist(p, t.pos) + 1;
        if (depth > 0) d += t.camp ? 2 : depth;
    }
    return d;
}

// A hidden unit on a landing fails the cast without spending it, so a few are tried.
struct Landings {
    static constexpr int tries = 3;
    std::array<vec2, tries> tiles;
    int count = 0;
};

// A landing's score when several things count: lower is better, compared field by field.
struct Rank {
    bool out_of_range = false; // dash_to_attack: the target is beyond our attack from it
    int danger = 0, steps = 0;
    auto operator<=>(const Rank&) const = default;
};

// The first landings in increasing `score` (an int or a Rank), ties in board order, keeping only
// those `keep` accepts.
template <class Score, class Keep> Landings ranked(const bitboard& landings, Score score, Keep keep) {
    using S = decltype(score(vec2{}));
    Landings out;
    std::array<S, Landings::tries> scores{};
    for (auto p : Tiles<5 * 5>{landings}) {
        const S s = score(p);
        if (!keep(p, s)) continue;
        int i = out.count < Landings::tries ? out.count++ : Landings::tries;
        for (; i > 0 && scores[i - 1] > s; --i)
            if (i < Landings::tries) out.tiles[i] = out.tiles[i - 1], scores[i] = scores[i - 1];
        if (i < Landings::tries) out.tiles[i] = p, scores[i] = s;
    }
    return out;
}

// Our landing hits enemies within `radius`, unseen ones too, and Ren strikes back even while dying.
bool landing_suicidal(const World& world, vec2 p, int radius, vec2 dead) {
    float health = -1; // read on first need: most enemies never strike back
    const float taken = world.me().taken;
    for (const auto& e : world.enemies) {
        if (!e.alive || e.retaliation() <= 0 || (e.visible ? (e.pos == dead || dist(p, e.pos) > radius) : !e.tracked)) continue;
        if (health < 0) health = my_health_and_shield(world);
        if (e.visible ? e.retaliation() * taken >= health : (unseen_suicidal(e, health, taken) && any_within(e.possible, p, radius))) return true;
    }
    return false;
}

// Heart of Ruin's landing damages around it: keep it off sleeping groups that strike and off enemies
// whose retaliation would kill us. `dead`: as threats_near's.
bool landing_harmful(const World& world, vec2 p, vec2 dead = {-1, -1}) {
    const auto& f = world.me().facts();
    const int slot = f.slot_of(AbilityKind::dash);
    if (slot < 0 || !f.abilities[slot].lands()) return false;
    const int radius = f.abilities[slot].radius;
    return landing_wakes(world, p, radius) || landing_suicidal(world, p, radius, dead);
}

bool dash_to_first(int dash, Pathing& pathing, const Landings& landings) {
    for (int i = 0; i < landings.count; ++i)
        if (cast(dash, landings.tiles[i])) {
            pathing.invalidate();
            return true;
        }
    return false;
}

int travel_dash_ready(const World& world) {
    if (!world.me().facts().has_dash()) return -1;
    if (enemy_within(world, my_position(), travel_dash_clearance)) return -1;
    return ready(world, AbilityKind::dash);
}

// To the landing nearest by `steps_at`, gaining at least a dash's steps, no deeper in the threats'
// reach than here (camps' too with `camps`).
bool travel_dash(const World& world, Pathing& pathing, int dash, int here_steps, auto steps_at, bool camps = true) {
    if (here_steps == 0 || here_steps == unreachable) return false;
    const vec2 here = my_position();
    const auto& threats = threats_near(world, here, {-1, -1}, camps);
    const int here_danger = danger(threats, here);
    const auto landings = ranked(
        pathing.dash_landings(), [&](vec2 p) { return steps_at(p); },
        [&](vec2 p, int steps) {
            return steps <= here_steps - dash_range && danger(threats, p) <= here_danger && !landing_harmful(world, p);
        });
    return dash_to_first(dash, pathing, landings);
}

// dash_away's landings, best first: less deep in the threats' reach than here, then nearest `home`.
// None when `here` is out of reach.
Landings escape_landings(const World& world, Pathing& pathing, vec2 here, const std::vector<Hazard>& threats, const Field& home, vec2 dead) {
    const int here_danger = danger(threats, here);
    if (here_danger == 0) return {};
    return ranked(
        pathing.dash_landings(), [&](vec2 p) { return Rank{.danger = danger(threats, p), .steps = home.at(p)}; },
        [&](vec2 p, const Rank& r) { return r.danger < here_danger && !landing_harmful(world, p, dead); });
}

// Varg's reset and shield share the turn's one cast, and the shield absorbs more than a hit that
// does not kill: keep the cast for it while a visible enemy can reach us.
bool shield_wanted(const World& world) {
    if (ready(world, AbilityKind::shield) < 0) return false;
    const vec2 here = my_position();
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && dist(here, e.pos) <= threat_strike(world, e).reach) return true;
    return false;
}

} // namespace

std::optional<cambc::handle_champion_t> attack_target(const World& world, bool stunnable_only) {
    const vec2 here = my_position();
    const int range = world.me().facts().attack_range();
    const bool splash = world.me().facts().passive == Passive::splash_attack;
    const auto& enemy_spawn = world.map().enemy_spawn;
    struct Seen {
        cambc::handle_champion_t c;
        vec2 pos;
        float health, retaliation;
        bool stunnable;
        float partner; // Cassi or Issac: the visible other body's health
        float taken;   // damage it takes per point of our Strength (a Durability emblem)
        float full, bag, stop; // max health with the shield; hit_worth's bag; kill_stops
    };
    static std::vector<Seen> seen; // kept across calls: allocating costs more than the work
    seen.clear();
    for (auto p : positions_within(live_champion_tiles(team::enemy), here, range + (splash ? splash_radius : 0))) {
        try {
            const auto c = champion_at(p);
            const auto& kind = facts(static_cast<cambc::champion_type>(identity_of(c).type));
            const auto passive = kind.passive;
            const auto& live = record_of(c);
            const float health = live.health;
            const float retaliation = passive == Passive::retaliation ? retaliation_share * live.focus : 0.0f;
            const bool stunnable = stunnable_only && passive != Passive::stun_immune && !stun_pending(c);
            // A shield must be hit through before health: counted as health.
            float shield = 0, taken = 1, partner = 1e9f, full = live.max_health, bag = 0, stop = 0;
            for (const auto& e : world.enemies) {
                if (!e.alive || !e.visible) continue;
                if (e.pos == p) {
                    if (kind.has(AbilityKind::shield) && e.shield > 0) shield = shield_value(c);
                    taken = e.taken;
                    bag = params::gem_value * static_cast<float>(pair_gems(world, e));
                    stop = kill_stops(world, e);
                } else if (passive == Passive::linked_pair && e.facts().passive == Passive::linked_pair) {
                    partner = e.health;
                }
            }
            seen.push_back({c, p, health + shield, retaliation, stunnable, partner, taken, full + shield, bag, stop});
        } catch (const cambc::error&) {
        }
    }
    if (seen.empty()) return std::nullopt;
    const float health = my_health(), strength = my_strength() * damage_scale(world.me().facts().passive, health, my_max_health()) * champion_dealt_factor();
    // Retaliation reaches us after our Durability and drains our shield first.
    const float taken = world.me().taken, guard = health + my_live_shield(world);
    // As the strike search values a hit.
    const auto worth = [&](const Seen& s) {
        const float dealt = strength * s.taken;
        return hit_worth(dealt, s.health, test(enemy_spawn, s.pos), s.bag, s.partner, s.full) + (dealt >= s.health - 0.01f ? s.stop : 0.0f);
    };
    std::optional<cambc::handle_champion_t> best;
    float best_value = 0, best_health = 0, best_pair = 0;
    for (const auto& t : seen) {
        if (dist(here, t.pos) > range || (stunnable_only && !t.stunnable)) continue;
        float value = worth(t), retaliation = t.retaliation;
        if (splash)
            for (const auto& o : seen)
                if (&o != &t && dist(o.pos, t.pos) <= 1) value += worth(o), retaliation += o.retaliation;
        if ((value <= 0 && !stunnable_only) || retaliation * taken >= guard) continue;
        // Ties (equal damage) go to the weakest, a pair by its weaker body.
        const float pair = std::min(t.health, t.partner);
        if (!best || value > best_value || (value == best_value && (pair < best_pair || (pair == best_pair && t.health < best_health))))
            best = t.c, best_value = value, best_health = t.health, best_pair = pair;
    }
    return best;
}

bool reset_and_attack_enemy(const World& world, bool stunning_only) {
    const auto& f = world.me().facts();
    const int slot = f.slot_of(AbilityKind::attack_reset);
    if (slot < 0 || (stunning_only && !f.abilities[slot].stuns) || my_can_attack()) return false;
    const int reset = ready(world, AbilityKind::attack_reset);
    if (reset < 0) return false;
    const auto target = attack_target(world, stunning_only);
    if (!target) return false;
    float taken = 1, shield = 0;
    for (const auto& e : world.enemies)
        if (e.handle == *target) taken = e.taken, shield = e.shield;
    if (shield > 0) shield = shield_value(*target);
    const bool kills = record_of(*target).health + shield <= my_strength() * champion_dealt_factor() * taken;
    if ((!kills && shield_wanted(world)) || !cast(reset)) return false;
    try {
        attack_champion(*target);
    } catch (const cambc::error&) {
    }
    return true;
}

// Monsters never move: the tiles within each range of a camp tile are kept.
bool camp_in_reach(const World& world, vec2 p, int range) {
    static std::array<std::optional<bitboard>, 4> near;
    if (range < 0 || range >= static_cast<int>(near.size())) return true;
    auto& tiles = near[static_cast<std::size_t>(range)];
    if (!tiles) {
        // Camp tiles are the members' tiles: a few whole-board operations rather than a square each.
        tiles.emplace();
        square_dilate(world.map().camp_tiles, range, *tiles);
    }
    return tiles->is_set(p);
}

bool reset_and_attack_camp(const World& world, int group) {
    const auto& f = world.me().facts();
    const auto& map = world.map();
    if (!f.has_attack_reset() || my_can_attack() || group < 0 || (map.groups[group].has_monolith && group != siege_group()))
        return false;
    const vec2 here = my_position();
    const int range = f.attack_range();
    if (!camp_in_reach(world, here, range)) return false;
    const int reset = ready(world, AbilityKind::attack_reset);
    if (reset < 0) return false;
    const auto& members = map.groups[group].members;
    std::optional<cambc::camp> best;
    float best_health = 0;
    for (auto p : positions_within(live_camp_tiles(), here, range)) {
        if (map.group_at(p) != group) continue;
        for (int i = 0; i < static_cast<int>(members.size()); ++i) {
            if (members[i].pos != p) continue;
            try {
                auto camp = map.groups[group].camp(i);
                const float h = camp.health();
                if (!best || h < best_health) best = camp, best_health = h;
            } catch (const cambc::error&) {
            }
        }
    }
    if (!best) return false;
    // A Vendetta kill readies the reset again, so it need not be held.
    const bool refunded = f.passive == Passive::reset_on_kill && best_health <= my_strength() * camp_dealt_factor();
    if (!refunded && engagement_near(world, here, f.basic_reach() + (f.ranged ? 0 : 1))) return false;
    if (!cast(reset)) return false;
    try {
        cambc::self().attack(*best);
    } catch (const cambc::error&) {
    }
    ++camp_hits();
    return true;
}

bool dash_towards(const World& world, Pathing& pathing, const Field& field) {
    const int dash = travel_dash_ready(world);
    return dash >= 0
           && travel_dash(world, pathing, dash, field.at(my_position()), [&](vec2 p) { return field.at(p); });
}

bool dash_across(const World& world, Pathing& pathing, const Field& field) {
    if (!world.me().facts().has_dash() || !test(world.map().near_crossable, my_position())) return false;
    // Near an enemy the dash is kept for the fight: farm may run after a ranged attack spent the walk.
    const int dash = travel_dash_ready(world);
    // The walk goes into camp reach anyway; only enemies are kept from.
    return dash >= 0
           && travel_dash(world, pathing, dash, field.at(my_position()), [&](vec2 p) { return field.at(p); }, false);
}

bool dash_towards(const World& world, Pathing& pathing, const bitboard& goals, int max_steps, const Field** follow) {
    if (follow) *follow = nullptr;
    static int paused_until = -1;
    if (world.round < paused_until) return false;
    // Most champions have no dash: check before anything costly.
    const int dash = travel_dash_ready(world);
    if (dash < 0) return false;
    const vec2 here = my_position();
    // A goal within a dash is a walk or two away: not worth the cooldown or the search.
    if (any_within(goals, here, dash_range)) return false;
    static bitboard origin, visited{cambc::uninitialized};
    static Field field{.goals = bitboard{cambc::uninitialized}};
    auto& open_goals = field.goals;
    const auto& walls = pathing.blocked();
    // goals & ~walls
    and_into(goals, walls, open_goals);
    xor_into(open_goals, goals, open_goals);
    if (board_empty(open_goals)) return false;
    // Searching out from the goals until it reaches us labels every tile nearer than ours.
    clear_board(origin);
    set_tile(origin, here);
    field.steps.compute_to(walls, open_goals, origin, visited, static_cast<std::uint16_t>(std::min<int>(max_steps, unreachable)));
    if (test(visited, here)
        && travel_dash(world, pathing, dash, field.at(here),
                       [&](vec2 p) { return test(visited, p) ? field.at(p) : unreachable; })) {
        if (follow) *follow = &field;
        return true;
    }
    paused_until = world.round + failed_search_pause;
    return false;
}

bool dash_to_attack(const World& world, Pathing& pathing, const ChampionBelief* target) {
    if (!world.me().facts().has_dash()) return false;
    const bool target_given = target != nullptr;
    if (!my_can_attack() || (!target_given && my_health() < params::hurt_health_fraction * my_max_health())) return false;
    const vec2 here = my_position();
    const int range = world.me().facts().attack_range();
    if (enemy_within(world, here, range)) return false;
    const int dash = ready(world, AbilityKind::dash);
    if (dash < 0) return false;
    if (!target_given) {
        const float strength = my_strength() * damage_scale(world.me().facts().passive, my_health(), my_max_health()) * champion_dealt_factor();
        const float my_fraction = my_health() / my_max_health();
        for (const auto& e : world.enemies) {
            if (!e.alive || !e.visible || dist(here, e.pos) > range + dash_range || test(world.map().enemy_spawn, e.pos))
                continue;
            const float fraction = e.health / e.max_health;
            const bool finish = e.health + e.shield <= strength * e.taken || (fraction < chase_health && fraction < my_fraction);
            if (finish && (!target || e.health < target->health)) target = &e;
        }
    }
    // A melee walk is free of the attack: a landing a step short of range still strikes.
    const int walk = target_given && world.me().facts().walk_and_attack_independent() && my_can_move() ? 1 : 0;
    if (!target || dist(here, target->pos) > range + walk + dash_range) return false;
    const auto& threats = threats_near(world, here);
    const auto& spawn = world.map().from_ally_spawn();
    const vec2 at = target->pos;
    const auto landings = ranked(
        within(pathing.dash_landings(), at, range + walk),
        [&](vec2 p) { return Rank{dist(p, at) > range, danger(threats, p), spawn.at(p)}; },
        [&](vec2 p, const Rank&) { return !landing_harmful(world, p); });
    return dash_to_first(dash, pathing, landings);
}

bool dash_away(const World& world, Pathing& pathing, const Field& home, vec2 dead) {
    if (!world.me().facts().has_dash()) return false;
    const int dash = ready(world, AbilityKind::dash);
    if (dash < 0) return false;
    const vec2 here = my_position();
    return dash_to_first(dash, pathing, escape_landings(world, pathing, here, threats_near(world, here, dead), home, dead));
}

EscapeDashQuote quote_escape_dash(const World& world, Pathing& pathing, const Field& home, vec2 dead) {
    EscapeDashQuote quote;
    if (!world.me().facts().has_dash()) return quote;
    const int dash = ready(world, AbilityKind::dash);
    if (dash < 0) return quote;
    const vec2 here = my_position();
    const auto& threats = threats_near(world, here, dead);
    const auto landings = escape_landings(world, pathing, here, threats, home, dead);
    if (landings.count == 0) return quote;
    static_assert(Landings::tries == std::tuple_size_v<decltype(quote.tiles)>);
    quote.slot = dash;
    quote.from = here;
    quote.count = landings.count;
    for (int i = 0; i < quote.count; ++i) quote.tiles[i] = landings.tiles[i];
    quote.clears = danger(threats, quote.tiles[0]) == 0;
    return quote;
}

bool cast_escape_dash(const World& world, Pathing& pathing, const EscapeDashQuote& quote) {
    world.throw_if_stale();
    if (quote.slot < 0 || quote.count == 0 || my_position() != quote.from || ready(world, AbilityKind::dash) != quote.slot) return false;
    if (cast(quote.slot, quote.tiles[0])) {
        pathing.invalidate();
        return true;
    }
    return false;
}

bool dash_clears(const World& world, Pathing& pathing, vec2 dead) {
    if (!world.me().facts().has_dash() || ready(world, AbilityKind::dash) < 0) return false;
    const auto& threats = threats_near(world, my_position(), dead);
    for (auto p : Tiles<5 * 5>{pathing.dash_landings()})
        if (danger(threats, p) == 0 && !landing_harmful(world, p, dead)) return true;
    return false;
}

bool dash_onto(const World& world, Pathing& pathing, const bitboard& tiles) {
    if (!world.me().facts().has_dash()) return false;
    const int dash = ready(world, AbilityKind::dash);
    if (dash < 0) return false;
    const auto& spawn = world.map().from_ally_spawn();
    const auto landings = ranked(
        tiles, [&](vec2 p) { return int{spawn.at(p)}; },
        [&](vec2 p, int) { return !landing_harmful(world, p); });
    return dash_to_first(dash, pathing, landings);
}

bool worth_healing(float amount, float gain, float fraction) {
    return gain > 0 && (gain >= heal_min_share * amount || fraction < params::hurt_health_fraction);
}

bool heal_ready(const World& world, const ChampionBelief& healer, float& amount) {
    if (!healer.alive || !healer.visible || !healer.can_act(world.round)) return false;
    const auto* live = visible_record(healer.handle);
    if (!live) return false;
    const auto state = cambc::champion_state::from_bits_retain(live->state);
    if (state.contains(cambc::champion_state::submitting_gems) || state.contains(cambc::champion_state::teleporting)) return false;
    if (healer.is_self) {
        if (!state.contains(cambc::champion_state::can_cast) || state.contains(cambc::champion_state::recalling)) return false;
    } else if (healer.stun_pending
               || (state.contains(cambc::champion_state::recalling)
                   && kept_recall(healer.handle, healer.recall_turns()))) {
        // An ally's turn allowances are not ours to read between its turns. A recall started at a
        // turn end is cancelled next turn unless wanted: only one kept through a turn stops the heal.
        return false;
    }
    const float focus = live->focus;
    const int slot = healer.facts().slot_of(AbilityKind::heal);
    if (slot < 0) return false;
    std::int32_t cooldown = 0;
    ok(cambc::detail::sdk_champion_cooldown(static_cast<std::uint32_t>(healer.handle), slot, &cooldown));
    if (cooldown > 0) return false;
    amount = healer.facts().abilities[slot].multiplier * focus;
    return true;
}

std::optional<HealTarget> heal_target(const World& world, const ChampionBelief& a, float amount) {
    if (a.is_self || !a.alive || !a.visible || test(world.map().ally_spawn, a.pos)) return std::nullopt;
    const auto* live = visible_record(a.handle);
    if (!live) return std::nullopt;
    const HealTarget t{&a, {live->x, live->y}, std::min(amount, live->max_health - live->health), live->health / live->max_health};
    if (!worth_healing(amount, t.gain, t.fraction) || kept_recall(a.handle, a.recall_turns())) return std::nullopt;
    return t;
}

bool heal_ally(const World& world) {
    if (!world.me().facts().heals()) return false; // cheaper than ready() for the rest
    const int heal = ready(world, AbilityKind::heal);
    if (heal < 0) return false;
    const float amount = my_heal(heal);
    const vec2 here = my_position();
    const int range = world.me().facts().abilities[heal].range();
    std::optional<cambc::handle_champion_t> best;
    float best_gain = 0, best_fraction = 0;
    // Read live: allies come into sight as we move.
    for (auto p : positions_within(live_champion_tiles(team::ally), here, range)) {
        if (p == here || test(world.map().ally_spawn, p)) continue;
        try {
            const auto c = champion_at(p);
            const auto& live = record_of(c);
            const float gain = std::min(amount, live.max_health - live.health);
            const float fraction = live.health / live.max_health;
            if (!worth_healing(amount, gain, fraction)) continue;
            int recall = static_cast<int>(cambc::constants::recall_time);
            for (const auto& a : world.allies)
                if (a.handle == c) recall = a.recall_turns();
            // One keeping a recall going will reach spawn and heal there.
            if (kept_recall(c, recall)) continue;
            if (!best || gain > best_gain || (gain == best_gain && fraction < best_fraction))
                best = c, best_gain = gain, best_fraction = fraction;
        } catch (const cambc::error&) {
        }
    }
    if (!best) return false;
    try {
        return cast_slot_on(heal, *best);
    } catch (const cambc::error&) {
        return false;
    }
}

bool shield_if_needed(const World& world, Safety& safety, int farmed) {
    if (!world.me().facts().has(AbilityKind::shield)) return false; // cheaper than ready() for the rest
    const int shield = ready(world, AbilityKind::shield);
    if (shield < 0) return false;
    const vec2 here = my_position();
    if (test(world.map().ally_spawn, here)) return false;
    for (auto left = safety.seen_enemies(); left; left &= left - 1)
        if (safety.blow(world.enemies[static_cast<std::size_t>(std::countr_zero(left))], here).hits) return cast(shield);
    const int range = world.me().facts().attack_range();
    const auto& groups = world.map().groups;
    for (int g : world.map().groups_near(here, world.map().max_camp_reach)) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || groups[g].strength <= 0) continue;
        const bool hit = g == farmed || !my_can_attack();
        bool in_reach = false, awake_in_reach = false, hitting = false;
        for (std::size_t i = 0; i < groups[g].members.size(); ++i) {
            if (c.health[i] <= 0) continue;
            const auto& m = groups[g].members[i];
            const int d = dist(here, m.pos);
            const bool reaches = d <= m.reach && m.strength > 0;
            in_reach |= reaches;
            awake_in_reach |= reaches && !c.member_asleep(i);
            hitting |= hit && d <= range;
        }
        if (awake_in_reach || (in_reach && hitting)) return cast(shield);
    }
    return false;
}

} // namespace aph
