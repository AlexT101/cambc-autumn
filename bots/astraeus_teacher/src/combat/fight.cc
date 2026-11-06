// Fights: chasing prey, stopping a game-ending tribute, kills in reach, and retreats.
#include "../bot_parts.h"

namespace aph {

namespace {

constexpr float escape_step_value = 210; // a retreat's or a game-ender intercept's walk, in enemy health

bool attack_enemy(const World& world) {
    if (!my_can_attack()) return false;
    const auto target = attack_target(world);
    if (!target) return false;
    try {
        attack_champion(*target);
        return true;
    } catch (const cambc::error&) {
        return false;
    }
}

// Walking steps, around walls, holes and live camps, to the nearest standable tile outside
// camp_area() or spawn tile whose fire we outlast (home_exits: the turn end there heals).
// Champions are left out: they move, and one in a corridor would wall the way out.
// `dash`: through a dasher's walls instead, which cross hole lines
// (a crossing counts one step); under fire a landing wakes nothing new.
const Field& camp_exit_field(const World& world, Pathing& pathing, Safety& safety, bool dash) {
    struct Made {
        Field field;
        int round = -1;
        std::uint32_t champion = 0, generation = 0, camps = 0, members = 0;
    };
    static Made made[2];
    static bitboard walls{cambc::uninitialized}, visited{cambc::uninitialized};
    auto& m = made[dash];
    const auto me = static_cast<std::uint32_t>(world.me().handle);
    const auto& area = safety.camp_area();
    if (m.round == world.round && m.champion == me && m.generation == Safety::generation()
        && m.camps == world.camps_version && m.members == safety.members_found) return m.field;
    or_into(dash ? world.map().dash_walls : world.map().blocked_for_us, pathing.live_camps(), walls);
    not_into(area, m.field.goals);
    m.field.goals &= world.map().standable;
    home_exits(world, safety, m.field.goals);
    m.field.steps.compute(walls, m.field.goals, visited);
    m.round = world.round, m.champion = me, m.generation = Safety::generation();
    m.camps = world.camps_version, m.members = safety.members_found;
    return m.field;
}

// Existing finite risk estimate for an unreachable exit, in turns at the current tile's rate.
int no_exit_risk_turns(const World& world) { return 4 * (world.map().max_camp_reach + 1); }

// The walk out, or with no walk a dasher's way out across a hole line (a pocket only a dash reaches).
const Field* camp_exit_way(const World& world, Pathing& pathing, Safety& safety, vec2 here, bool* dashing = nullptr) {
    if (const auto& walk = camp_exit_field(world, pathing, safety, false); walk.at(here) != unreachable) return &walk;
    if (!world.me().facts().has_dash()) return nullptr;
    const auto& dash = camp_exit_field(world, pathing, safety, true);
    if (dash.at(here) == unreachable) return nullptr;
    if (dashing) *dashing = true;
    return &dash;
}

// Minimum camp damage after p and before a goal, over all paths descending the field. The cache
// belongs to one decision, shared by its first steps; no damage survives a move or Safety refresh.
class ExitHits {
public:
    ExitHits(const Field& field, Safety& safety) : field_(field), safety_(safety), width_(cambc::map::width()) {}

    float from(vec2 p) {
        const int steps = field_.at(p);
        if (steps == unreachable) return std::numeric_limits<float>::infinity();
        if (steps <= 1) return 0;
        if (memo_.empty()) memo_.resize(static_cast<std::size_t>(width_ * cambc::map::height()));
        const int root = index(p);
        if (memo_[root].after >= 0) return memo_[root].after;
        pending_.push_back({p, steps});
        while (!pending_.empty()) {
            auto& f = pending_.back();
            if (f.next == 8) {
                memo_[index(f.p)].after = f.best;
                pending_.pop_back();
                continue;
            }
            const vec2 q = f.p + directions[static_cast<std::size_t>(f.next)];
            if (!in_bounds(q) || field_.at(q) != f.steps - 1) {
                ++f.next;
                continue;
            }
            auto& c = memo_[index(q)];
            if (f.steps == 2) c.after = 0;
            if (c.after < 0) {
                // A full field may have a long winding path: use an explicit stack.
                pending_.push_back({q, f.steps - 1});
                continue;
            }
            if (c.damage < 0) c.damage = safety_.camp_damage(q);
            f.best = std::min(f.best, c.damage + c.after);
            ++f.next;
        }
        return memo_[root].after;
    }

private:
    struct Cost { float after = -1, damage = -1; };
    struct Pending {
        vec2 p;
        int steps, next = 0;
        float best = std::numeric_limits<float>::infinity();
    };
    int index(vec2 p) const { return p.x + width_ * p.y; }
    const Field& field_;
    Safety& safety_;
    int width_;
    std::vector<Cost> memo_;
    std::vector<Pending> pending_;
};

// Out of the camps' reach first, a step down the walking steps to the nearest tile they do not
// reach (or our spawn, camp_exit_field): walking home past an awake camp takes a hit every step,
// while a recall started outside its reach goes home untouched. Distance as the crow flies would
// aim at exits across holes, and pricing the walk at one tile's rate would trade steps back and
// forth between two camps' reach: only steps down count, ranked by the hits on their whole walk
// out, then steps home.
bool flee_camps(const World& world, Pathing& pathing, Safety& safety, const Field& home) {
    if (!my_can_move()) return false;
    const vec2 here = my_position();
    if (safety.camp_damage(here) <= 0) return false;
    const auto* way = camp_exit_way(world, pathing, safety, here);
    if (!way) return false;
    const auto& exit = *way;
    const int out = exit.at(here);
    ExitHits hits(exit, safety);
    const auto& blocked = pathing.blocked();
    std::optional<vec2> best;
    float best_damage = 0;
    int best_home = 0;
    for (auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || test(blocked, p) || exit.at(p) != out - 1) continue;
        const float damage = safety.damage_bound(p, false, world.me().taken) + hits.from(p);
        const int steps = home.at(p);
        if (!best || damage < best_damage || (damage == best_damage && steps < best_home)) best = p, best_damage = damage, best_home = steps;
    }
    return best && pathing.try_move(*best) == Pathing::Move::moved;
}

// A step home whose walk onto our spawn survives, or none: a turn ended there heals to full before
// any enemy acts (rules rounds.turn_end), and enemies can attack into it but never enter it. The walk
// goes down `home`, each enemy yet to act counted twice (damage_bound): the damage on the tiles
// before the spawn must leave us alive, and the spawn tile's must leave us more than `keep`. All
// descending continuations are considered, sharing their damage bounds. Only walks no recall
// started now beats are looked at: a recall heals at the end of its arrival turn, after
// its turn ends; a walk at the end of its last step's turn.
class HomeWalk {
public:
    // The rules' recall (5 turn ends) and its arrival turn.
    static constexpr int max_walk = 6;
    HomeWalk(const World& world, Pathing& pathing, Safety& safety, const Field& home)
        : world_(world), pathing_(pathing), safety_(safety), home_(home), here_(my_position()), now_(my_health_and_shield(world)),
          full_(now_ - my_health() + my_max_health()) {}

    static int horizon(const World& world) { return std::min(max_walk, world.me().recall_turns() + 1); }
    float now() const { return now_; }

    // Whether the walk home that starts with step p survives.
    bool walk_from(vec2 p, float keep) {
        const int steps = home_.at(here_);
        // The spawn must leave more than `keep` of full health.
        if (steps == 0 || steps > horizon(world_) || keep >= full_) return false;
        if (!in_bounds(p) || home_.at(p) != steps - 1 || test(pathing_.blocked(), p)) return false;
        if (!have_keep_ || keep != keep_) {
            have_keep_ = true, keep_ = keep;
            remaining_known_.fill(0);
        }
        return remaining(p) < now_;
    }

private:
    float remaining(vec2 p) {
        const int i = index(p);
        auto& known = remaining_known_[i >> 6];
        if (known >> (i & 63) & 1) return remaining_[i];
        known |= std::uint64_t{1} << (i & 63);
        float least = std::numeric_limits<float>::infinity();
        const int steps = home_.at(p);
        if (steps == 0) {
            if (full_ - doubled(p) > keep_) least = 0;
        } else {
            // Depth is at most the unchanged recall horizon, not the map's path length.
            for (auto d : directions)
                if (const vec2 q = p + d; in_bounds(q) && home_.at(q) == steps - 1 && !test(pathing_.blocked(), q))
                    least = std::min(least, remaining(q));
            least += doubled(p);
        }
        return remaining_[i] = least;
    }

    static constexpr int side = 2 * max_walk + 1;
    int index(vec2 p) const { return (p.y - here_.y + max_walk) * side + (p.x - here_.x + max_walk); }
    float doubled(vec2 p) {
        const int i = index(p);
        auto& known = known_[i >> 6];
        if (!(known >> (i & 63) & 1)) known |= std::uint64_t{1} << (i & 63), memo_[i] = safety_.damage_bound(p, true, world_.me().taken);
        return memo_[i];
    }

    const World& world_;
    Pathing& pathing_;
    Safety& safety_;
    const Field& home_;
    vec2 here_;
    float now_, full_;
    std::array<std::uint64_t, (side * side + 63) / 64> known_{};
    std::array<float, side * side> memo_;
    bool have_keep_ = false;
    float keep_ = 0;
    std::array<std::uint64_t, (side * side + 63) / 64> remaining_known_{};
    std::array<float, side * side> remaining_;
};

// Inside danger the shortest walk home, ties in compass order, can lead along the enemies we flee:
// rank the steps by the damage they risk, then stun-free first, then steps home, then distance from
// visible enemies. A sideways step wins only on damage; one away from home only if it leaves every
// reach and no other step does: still in reach, it only delays, as the pursuer takes the step back
// next turn. With no homeward step clear, those whose walk onto our spawn survives and heals us
// (HomeWalk) come first: else a clear step away wins, and an enemy reach that alternates with turn
// order walks us back.
void retreat_step(const World& world, Pathing& pathing, Safety& safety, const Field& home) {
    if (!my_can_move()) return;
    const vec2 here = my_position();
    if (!safety.avoid_within(here, vision_radius)) {
        pathing.step_towards(home);
        return;
    }
    const auto& avoid = safety.avoid();
    if (!test(avoid, here) && pathing.step_towards(home, &avoid)) return;
    const int steps = home.at(here);
    const auto& blocked = pathing.blocked();
    struct Option {
        vec2 p;
        float damage;
        bool stuns;
        int steps, gap, pull;
        bool home;
        Safety::Tally t;
    };
    Unwritten<Option, 8> scratch;
    auto& options = scratch.a;
    int n = 0;
    bool clear = false;
    // An option is summed only to its first damage until it may rank first: one with damage ranks
    // after every clear step.
    const auto price = [&](Option& o) {
        if (o.t.left) safety.finish(o.t, o.p, world.me().taken);
        o.damage = o.t.damage, o.stuns = o.t.stuns;
    };
    const auto add = [&](bool longer) {
        for (auto d : directions) {
            const vec2 p = here + d;
            if (!in_bounds(p) || test(blocked, p)) continue;
            const int s = home.at(p);
            if (s == unreachable || (s > steps) != longer) continue;
            // A longer step is kept only untouched, where bound() would be all zero.
            if (longer && safety.touched(p, world.me().taken)) continue;
            const auto t = longer ? Safety::Tally{} : safety.tally(p, world.me().taken);
            // A stun alone, with no damage, still takes our next turn while the pursuers close in.
            const bool reached = t.damage > 0 || t.hits;
            int gap = unreachable;
            for (const auto& e : world.enemies)
                if (e.alive && e.visible) gap = std::min(gap, dist(p, e.pos));
            options[n++] = {p, t.damage, t.stuns, s, gap, pathing.pull(p), false, t};
            clear |= !reached;
        }
    };
    add(false);
    if (!clear) {
        // Worth it only if the spawn leaves us healthier than the clear step away would.
        HomeWalk w(world, pathing, safety, home);
        for (int i = 0; i < n; ++i) options[i].home = w.walk_from(options[i].p, w.now());
        add(true);
    }
    const auto by = [](const Option& a, const Option& b) {
        if (a.home != b.home) return a.home;
        if (a.damage != b.damage) return a.damage < b.damage;
        if (a.stuns != b.stuns) return b.stuns;
        if (a.steps != b.steps) return a.steps < b.steps;
        if (a.gap != b.gap) return a.gap > b.gap;
        return a.pull < b.pull;
    };
    // The options that rank before every one with damage, tried first in the full order; the rest,
    // priced, only if every one of those fails.
    Unwritten<Option, 8> rest_scratch;
    auto& rest = rest_scratch.a;
    int lead = 0, later = 0;
    for (int i = 0; i < n; ++i) {
        auto& o = options[i];
        if (o.home) price(o);
        if (o.home || (!o.t.left && o.damage == 0 && !o.stuns)) options[lead++] = o;
        else rest[later++] = o;
    }
    std::stable_sort(options.begin(), options.begin() + lead, by);
    for (int i = 0; i < lead; ++i)
        if (pathing.try_move(options[i].p) == Pathing::Move::moved) return;
    for (int i = 0; i < later; ++i)
        price(rest[i]);
    std::stable_sort(rest.begin(), rest.begin() + later, by);
    for (int i = 0; i < later; ++i)
        if (pathing.try_move(rest[i].p) == Pathing::Move::moved) return;
    pathing.step_towards(home);
}

// The rounds until the payout of the hold we would keep at p (one not yet counting starts now), or
// -1 if we would hold none there.
int hold_rounds(const World& world, Pathing& pathing, vec2 p) {
    if (const int g = world.map().group_at(p); g < 0 || world.camps[g].state != CampState::cleared) return -1;
    if (!(p == my_position() ? holding_capture(world, pathing) : holding_capture_now(world, pathing, p))) return -1;
    const int g = world.map().group_at(p);
    const auto& c = world.camps[g];
    return c.held_since >= 0 ? std::max(0, c.payout_round() - world.round) : capture_rounds(world, pathing, g, p);
}

// A capture we hold at p, paying in `turns` (hold_rounds), is worth finishing when it pays before any
// credible enemy could walk into reach of us (an unseen one from the tiles it may be on).
bool paying_soon(const World& world, Safety& safety, vec2 p, int turns) {
    // A hold we would start at p counts there as one under way does: next turn it is.
    if (turns < 0 || (p == my_position() && world.camps[world.map().group_at(p)].held_since < 0)) return false;
    return turns == 0 || !safety.may_reach_within(p, turns - 1);
}

// Camps keep hitting while we walk out of their reach: leave while the health still covers that,
// with one hit to spare unless the camp is nearly dead. A siege (Memory::siege) keeps its own
// health limits for its group's hits.
bool camp_trapped(const World& world, Pathing& pathing, Safety& safety, vec2 here, float health, bool sieging) {
    if (sieging) return false;
    const float dps = safety.camp_damage(here);
    if (dps <= 0) return false;
    health += my_live_shield(world);
    // The coming camp phase if we stay this turn, then the tiles walked through.
    if (health <= dps) return true;
    bool dashing = false;
    const auto* field = camp_exit_way(world, pathing, safety, here, &dashing);
    float hits;
    if (!field) {
        hits = dps * static_cast<float>(no_exit_risk_turns(world));
    } else {
        // A dash way waits at our tile for the dash.
        const int wait = dashing ? my_cooldown(world.me().facts().slot_of(AbilityKind::dash)) : 0;
        // Each tile passed through takes at most every member's hit: health above that (with a
        // margin for rounding) needs no walk priced.
        float most = 0;
        for (const auto& m : safety.awake_members()) most += std::max(0.0f, m.strength);
        const float bound = dps + static_cast<float>(std::max(0, field->at(here) - 1)) * most + dps * static_cast<float>(wait) + dps;
        if (health > 1.001f * bound) return false;
        ExitHits exit(*field, safety);
        hits = exit.from(here);
        if (dashing) hits += dps * static_cast<float>(wait);
    }
    const float cost = dps + hits;
    return health <= cost || (health <= cost + dps && !finishing_camp(world));
}

// Whether Safety::credible_enemy_may_hit_within(p, radius) can hold: it reads no farther than a
// strike's reach, at most max_reach. On the first turn its foes are not built yet (~1.5k each).
[[gnu::noinline]] bool enemy_within_strike(const World& world, vec2 p, int radius) {
    const int far = Strike::max_reach + radius;
    for (const auto& e : world.enemies) {
        if (!e.alive) continue;
        if (e.visible ? e.teleport_pending() && in_bounds(e.tp_dest) && dist(p, e.tp_dest) <= far
                      : e.tracked && possible_within(e, p, far))
            return true;
    }
    return false;
}

// The share of max health below which we go home from p. A low champion is mainly an easy kill, so
// with no enemy near enough to reach us soon the line is lower; camps are priced separately (camp_trapped).
float recall_line_uncached(const World& world, Safety& safety, vec2 p) {
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && enemy_reach::within(world, e, enemy_reach::origin(e), p, Strike::max_reach + params::threat_radius))
            return params::recall_health_fraction;
    if (world.round == world.first_round && !enemy_within_strike(world, p, params::threat_radius)) return params::safe_recall_health_fraction;
    return safety.may_reach_within(p, params::threat_radius) ? params::recall_health_fraction : params::safe_recall_health_fraction;
}
// Kept for the last tile asked, in the Safety.
float recall_line(const World& world, Safety& safety, vec2 p) {
    if (safety.recall_line_known && safety.recall_line_at == p) return safety.recall_line_share;
    safety.recall_line_share = recall_line_uncached(world, safety, p);
    safety.recall_line_at = p, safety.recall_line_known = true;
    return safety.recall_line_share;
}
float recall_line(const World& world, Safety& safety) { return recall_line(world, safety, my_position()); }

// A hold paying in `rounds` keeps us at p while it outlasts what can reach us there, to the payout
// and our turn after it, as tribute_safe judges a channel: nothing can kill us there before our next
// turn (lethal: the unseen threats too), last round's loss (`damage`) repeated leaves us alive
// (camps hit from out of sight, bush attackers stay unseen), and the enemies (the unseen from the
// tiles they may be on) and the camps cannot kill us by then even if we never act. Leaving forfeits the reward; staying risks only what
// this counts.
bool hold_outlasts(Safety& safety, float damage, vec2 p, int rounds) {
    const int window = rounds + 1;
    if (damage * static_cast<float>(window) >= my_health() || safety.lethal(p)) return false;
    const int kill = safety.turns_to_kill_idle(p, window + 1);
    return kill == 0 || kill > window;
}

namespace {

// The hold we would keep at p (hold_rounds), and whether it outlasts what can reach us there
// (hold_outlasts), each worked out on first need.
struct HoldAt {
    const World& world;
    Pathing& pathing;
    vec2 p;
    float damage;
    int rounds_ = -2; // -2: not worked out yet
    int keeps = -1;
    HoldAt(const World& world, Pathing& pathing, vec2 p, float damage) : world(world), pathing(pathing), p(p), damage(damage) {}
    int rounds() {
        if (rounds_ == -2) rounds_ = hold_rounds(world, pathing, p);
        return rounds_;
    }
    bool keeps_us(Safety& safety) {
        if (keeps < 0) keeps = rounds() >= 0 && hold_outlasts(safety, damage, p, rounds());
        return keeps == 1;
    }
};

// A pack's zone sends us home from p unless a hold there pays before any enemy could reach us.
bool outmatched(const World& world, Safety& safety, HoldAt& hold) {
    return in_pack_zone(world, safety, hold.p) && !paying_soon(world, safety, hold.p, hold.rounds());
}

// Low under p's recall line (bar finishing a camp), or in a pack's zone there.
bool drawn_home(const World& world, Safety& safety, HoldAt& hold) {
    const float health = my_health();
    // Either line is at most recall_health_fraction: above it, no line needs working out.
    if (health < params::recall_health_fraction * my_max_health() && health < recall_line(world, safety, hold.p) * my_max_health()
        && !finishing_camp(world, hold.p) && !hold.keeps_us(safety))
        return true;
    return outmatched(world, safety, hold) && !hold.keeps_us(safety);
}

// A stand at p we lose, or, linked or lethal there, one we fall in. Healthy on our own ground, they
// have no reason to come for us, unless we carry a bag: a kill takes it. Every input is read at p.
bool stand_lost_at(const World& world, Safety& safety, HoldAt& hold) {
    const vec2 p = hold.p;
    // lethal(p), worked out where read: an enemy that hits p now leaves the roster blind to it, so
    // only `falls` reads it then, and a partner settles that.
    int lethal_at = -1;
    const auto lethal = [&] {
        if (lethal_at < 0) lethal_at = safety.lethal(p);
        return lethal_at == 1;
    };
    // With nobody in sight and no unseen enemy that may strike p within the pursuers' walk, no roster
    // forms here.
    if (!enemy_seen(world) && !safety.unseen_may_hit_within(p, params::pursuit_steps)) return false;
    if (hold.keeps_us(safety)) return false;
    // Either pursuit horizon reads as far as the joiners'.
    static_assert(params::pursuit_steps >= 0);
    auto reach = safety.stand_reach(p, params::pursuit_steps);
    // With a hit, the roster reads neither whether we are pursued nor the unseen; with no walker, not
    // whether we are pursued. own_ground builds the spawn field on first need, and farm prices by a
    // bound until it exists: pursued is read until then, so that skipping it never changes farm's pricing.
    bool pursued = false, unseen = false;
    if (!reach.hit) unseen = lethal();
    if ((!reach.hit && (reach.walking | reach.pending)) || !world.map().from_ally_spawn_ready()) {
        const float health = my_health();
        pursued = !paying_soon(world, safety, p, hold.rounds())
                  && !(own_ground(world, p) && health >= params::hurt_health_fraction * my_max_health() && bag_at_stake(world) < params::brake_bag);
    }
    if (reach.hit || pursued) safety.stand_walks(p, params::pursuit_steps, reach);
    const auto roster = safety.stand_roster(p, reach, pursued ? params::pursuit_steps : 0, unseen);
    if (roster.key == Safety::no_fight) return false;
    const bool falls = partner(world) != nullptr || lethal();
    const auto t = safety.stand_trade(roster, falls);
    return t.lost || (falls && t.self_falls);
}

} // namespace

bool drawn_home_at(const World& world, Pathing& pathing, Safety& safety, vec2 p, float damage) {
    HoldAt hold(world, pathing, p, damage);
    return drawn_home(world, safety, hold);
}

// Retreat: low under the recall line (bar finishing a camp), a pack's zone (drawn_home), a camp we
// could no longer walk out of, or a stand we lose (stand_lost_at). A hold that outlasts what can
// reach us to its payout keeps us through all but the camps (hold_outlasts). The work guard keeps
// the economy's steps off the tiles beside us that the zone or the recall line would send us back
// from (combat/guard.cc).
bool want_home(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    world.throw_if_stale();
    const vec2 here = my_position();
    if (test(world.map().ally_spawn, here)) return false;
    const float health = my_health();
    HoldAt hold(world, pathing, here, memory.damage);
    if (drawn_home(world, safety, hold)) return true;
    const int mono = mono_trapped(world, pathing, safety, memory, health);
    if (mono >= 0 ? mono == 1 : camp_trapped(world, pathing, safety, here, health, memory.siege)) return true;
    // Once camps sent us home, only a heal brings us back: stepping back into their reach to work
    // would take the hits again from no more health.
    if (memory.camp_fled >= 0 && !memory.siege) return true;
    // Willow holds no fight: an enemy likely to hit it sends it home (its stations' guard keeps it off
    // the same tiles), bar on a capture, which pays without one.
    if (world.me().facts().heals() && !holding_capture(world, pathing) && !contesting(world) && exposure_here(world, safety).enemy)
        return true;
    return stand_lost_at(world, safety, hold);
}

// The last round we act before e's channel completes, at its turn start in channel_end_round.
int last_round_before_channel_ends(const World& world, const ChampionBelief& e) {
    const int end = e.channel_end_round;
    const bool first = end == world.round ? !e.acted : world.slot(world.me(), end) < world.slot(e, end);
    return first ? end : end - 1;
}

// Where a carrier starts walking to an altar: where its teleport under way lands, once it does.
struct CarrierWalk {
    vec2 from;
    int delay = 0;
};
CarrierWalk carrier_walk(const World& world, const ChampionBelief& e) {
    if (!e.teleport_pending()) return {e.pos, 0};
    return {in_bounds(e.tp_dest) ? e.tp_dest : e.pos, std::max(0, e.channel_end_round - world.round)};
}

// An enemy's static walk to a tile within tribute range of altar a, over its walls (a dasher's
// across the lines its dash jumps). Kept per altar.
const Field& enemy_altar_field(const StaticMap& map, int a, bool dasher) {
    static std::vector<std::optional<Field>> fields[2];
    auto& slots = fields[dasher];
    if (slots.size() < map.altars.size()) slots.resize(map.altars.size());
    auto& f = slots[a];
    if (!f) {
        bitboard goals;
        draw_square(goals, map.altars[a].pos, static_cast<float>(cambc::constants::submit_gems_range));
        goals &= map.open_for_them;
        f = make_field(dasher ? map.their_dash_walls() : map.blocked_for_them, goals);
    }
    return *f;
}

// A carrier's quickest tribute: the walk to an altar and the break of our lock there, and the
// rounds until its tribute lands, counted as win_lands counts ours; turns is unreachable with no
// altar. Cassi and Issac each channel their own bag: a pair that wins only with both bags wins at
// the later of the two, each by its own walk, altar and channel; else e's own scores. `altar` is e's.
struct CarrierTribute {
    const vec2* altar = nullptr;
    int turns = unreachable;
};
CarrierTribute body_tribute(const World& world, const ChampionBelief& e, CarrierWalk w) {
    const int submit = cambc::constants::submit_gems_range;
    const auto& map = world.map();
    CarrierTribute t;
    int to_altar = unreachable;
    for (int a = 0; a < static_cast<int>(map.altars.size()); ++a) {
        int d = enemy_altar_field(map, a, e.facts().has_dash()).at(w.from);
        if (d == unreachable) continue;
        if (const auto& b = world.altars[a]; b.ally_lock)
            d += lock_turns(b.ally_lock_hits > 0 ? b.ally_lock_hits : static_cast<int>(cambc::constants::altar_lock_hits), e, d,
                            world.round + w.delay);
        if (d < to_altar) t.altar = &map.altars[a].pos, to_altar = d;
    }
    // No walk reaches one (a crystal's pocket): the nearest as the crow flies.
    if (!t.altar)
        for (const auto& a : map.altars)
            if (const int d = std::max(0, dist(w.from, a.pos) - submit); d < to_altar) t.altar = &a.pos, to_altar = d;
    if (t.altar) t.turns = w.delay + to_altar + tribute_turns(e.gems, e.fast_tribute);
    return t;
}
CarrierTribute carrier_tribute(const World& world, const ChampionBelief& e, CarrierWalk w) {
    CarrierTribute t = body_tribute(world, e, w);
    const auto* p = linked_partner(world, e);
    const int need = static_cast<int>(cambc::constants::winning_gems) - world.score.enemy;
    if (!t.altar || !p || !p->alive || p->gems <= 0 || e.gems >= need || e.gems + p->gems < need) return t;
    // A partner channelling already lands at its channel's end; one last seen walks from there, one
    // never seen as if from e's tile.
    int other = unreachable;
    if (p->channel == Channel::tribute && p->channel_end_round >= world.round) other = p->channel_end_round - world.round;
    else if (p->pos.x >= 0) other = body_tribute(world, *p, carrier_walk(world, *p)).turns;
    if (other == unreachable) other = w.delay + tribute_turns(p->gems, p->fast_tribute) + (t.turns - w.delay - tribute_turns(e.gems, e.fast_tribute));
    t.turns = std::max(t.turns, other);
    return t;
}

// Our steps from `from` until p is within `range`, round our static walls by our dash kind
// (enemy_reach::steps_within), where open ground reads dist - range; unreachable if no walk gets there.
int walk_within(const World& world, vec2 from, vec2 p, int range) {
    auto who = enemy_reach::ally_profile(world.me().facts());
    who.act = range;
    return enemy_reach::steps_within(world, who, from, p);
}

// The turn (0: this one) our basic attacks alone kill e from `here`, walking into range first;
// a melee hit can follow the last step in its turn. On its spawn it heals to full every turn end.
int kill_turn(const World& world, const ChampionBelief& e, vec2 here) {
    const auto& self = world.me();
    const int walk = walk_within(world, here, e.pos, self.facts().attack_range());
    if (walk == unreachable) return unreachable;
    const float hit = my_strength() * damage_scale(self.facts().passive, my_health(), my_max_health()) * champion_dealt_factor();
    if (hit <= 0) return unreachable;
    const float hits = std::max(1.0f, std::ceil(effective_hp(e) / hit));
    if (hits > 1 && test(world.map().enemy_spawn, e.pos)) return unreachable;
    return hits > unreachable ? unreachable : (self.facts().ranged ? walk : std::max(0, walk - 1)) + static_cast<int>(hits) - 1;
}

// Our turns (walking: steps) from `here` to stop a carrier's bag from scoring, unreachable if it
// scores first. A tribute or teleport under way: a stun or (tributes) a lock on its altar cancels
// it (a lock even Marcella's), a kill takes the bag; the turn it happens in, 0 for this one.
// Walking, it outpaces nobody but stops at an altar, carrier_tribute's (its walk there and our lock's
// hits): we must reach that altar before its tribute there lands.
int intercept_steps(const World& world, const ChampionBelief& e, vec2 here) {
    const auto& self = world.me();
    const auto& altars = world.map().altars;
    const int range = self.facts().attack_range();
    int steps = walk_within(world, here, e.pos, range);
    if (e.channel == Channel::tribute || e.teleport_pending()) {
        const int last = last_round_before_channel_ends(world, e);
        const int turns = last - world.round;
        int hard = unreachable; // a stun or a lock
        if (e.facts().passive != Passive::stun_immune)
            if (const int reach = self.ready_stun_reach(last, true); reach >= 0) hard = walk_within(world, here, e.pos, reach);
        if (e.channel == Channel::tribute)
            if (const int a = tribute_altar(world, e.pos); a >= 0 && carried_locks() > 0)
                if (const int w = walk_within(world, here, altars[a].pos, altar_lock_range); w != unreachable)
                    hard = std::min(hard, std::max(0, w - 1)); // placed after the last step
        // Damage interrupts neither channel: reaching attack range stops it only through a kill.
        const int stop = std::min(hard, kill_turn(world, e, here));
        debug_block({
            if (steps <= turns && stop > turns) std::printf("STOP-RANGE %d %u\n", world.round, static_cast<unsigned>(self.handle));
        });
        if (e.channel == Channel::tribute) return stop <= turns ? stop : unreachable;
        // A teleport not stopped in time lands, and it walks on from there.
        if (stop <= turns) return stop;
    }
    const auto w = carrier_walk(world, e);
    steps = walk_within(world, here, w.from, range);
    const auto t = carrier_tribute(world, e, w);
    if (!t.altar) return unreachable;
    const int submit = cambc::constants::submit_gems_range;
    return walk_within(world, here, *t.altar, submit + range) < t.turns ? steps : unreachable;
}

// prey's tests before the fight: e is worth chasing from `here` if that fight is won. `held`: the
// gems of a cleared group it stands on.
bool preyable(const World& world, Safety& safety, const ChampionBelief& e, vec2 here, int range, int& held) {
    if (dist(here, e.pos) > vision_radius || test(world.map().near_enemy_spawn, e.pos)) return false;
    // A teleport under way cannot fight back, but leaves unless we reach it before it lands.
    if (e.teleport_pending() && walk_within(world, here, e.pos, range) > last_round_before_channel_ends(world, e) - world.round)
        return false;
    // Out of reach on its own ground only when hurt or carrying a bag we can stop: fights at
    // central altars straddle the line, and a beaten enemy otherwise escapes a step across it,
    // but a bag has to stop at an altar to score, and a kill takes it. An enemy holding a
    // cleared group is taking its gems: killing it is how a capture is contested.
    const int g = world.map().group_at(e.pos);
    held = g >= 0 && world.camps[g].state == CampState::cleared ? world.map().groups[g].gems : 0;
    if (dist(here, e.pos) > range && !own_ground(world, e.pos) && e.health >= params::hurt_health_fraction * e.max_health && held == 0
        && (pair_gems(world, e) == 0 || intercept_steps(world, e, here) == unreachable))
        return false;
    // Every tile in reach of it would make us retreat at once.
    return !pack_covers(world, safety, e.pos, range);
}

// The fight we press: a visible enemy we struck or chased on our previous turn, off its spawn's edge,
// with a smaller share of its health left than ours; the hurtest such, or null.
const ChampionBelief* pressed(const World& world) {
    if (!engaged_before || world.me().facts().heals()) return nullptr;
    const float ours = my_health() / my_max_health();
    const ChampionBelief* out = nullptr;
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && engaged_last_turn(static_cast<std::uint32_t>(e.handle)) && e.health < ours * e.max_health
            && (!out || e.health * out->max_health < out->health * e.max_health) && !test(world.map().near_enemy_spawn, e.pos))
            out = &e;
    return out;
}

// The fight a teammate presses: a visible enemy, off its spawn's edge, in a visible ally's attack
// range with a smaller share of its health left than that ally; the hurtest such, or null.
const ChampionBelief* team_pressed(const World& world) {
    if (world.me().facts().heals()) return nullptr;
    // The visible enemies, in index order: at most 6 bodies (5 picks, Cassi and Issac two).
    std::array<const ChampionBelief*, 16> seen;
    std::size_t n = 0;
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && n < seen.size()) seen[n++] = &e;
    if (n == 0) return nullptr;
    const ChampionBelief* out = nullptr;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible) continue;
        const int reach = a.facts().attack_range();
        for (std::size_t k = 0; k < n; ++k)
            // The board test, a host call, last.
            if (const auto& e = *seen[k]; dist(a.pos, e.pos) <= reach && e.health * a.max_health < a.health * e.max_health
                && (!out || e.health * out->max_health < out->health * e.max_health) && !test(world.map().near_enemy_spawn, e.pos))
                out = &e;
    }
    return out;
}

// Where the strike search's walk heads when it strikes nothing: the nearest visible enemy we
// chased or struck on our previous turn that prey could still take, else {-1, -1}. The search
// walks first, and chase gets no walk after one.
vec2 chase_aim(const World& world, Safety& safety) {
    vec2 aim{-1, -1};
    if (world.me().facts().heals()) return aim;
    const vec2 here = my_position();
    const int range = world.me().facts().attack_range();
    int best = unreachable, held = 0;
    // A teammate's pressed fight when we have none of our own.
    if (!engaged_before) {
        if (const auto* t = team_pressed(world); t && preyable(world, safety, *t, here, range, held)) aim = t->pos;
        return aim;
    }
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && engaged_last_turn(static_cast<std::uint32_t>(e.handle)) && dist(here, e.pos) < best
            && preyable(world, safety, e, here, range, held))
            aim = e.pos, best = dist(here, e.pos);
    return aim;
}

// Enemies (bits by index) we chased or struck on our previous turn that have since left our sight,
// while every tile they could be on lies within it: walking towards those tiles finds them again.
std::uint32_t lost_prey(const World& world, vec2 here) {
    if (!engaged_before) return 0;
    std::uint32_t out = 0;
    static bitboard outside{cambc::uninitialized}, near{cambc::uninitialized};
    bool drawn = false;
    for (const auto& e : world.enemies) {
        if (!e.alive || e.visible || !e.tracked || !engaged_last_turn(static_cast<std::uint32_t>(e.handle)) || e.possible.is_empty()) continue;
        if (!drawn) near.clear(), near.draw_chebyshev(here, static_cast<float>(vision_radius)), drawn = true;
        outside.clear();
        outside |= e.possible;
        drop(outside, near);
        if (outside.is_empty()) out |= 1u << e.index;
    }
    return out;
}

// The visible enemy whose kill pays most a turn to reach and kill it, among those whose local
// fight we win even when they strike first; never one on or next to its spawn, where it heals.
// An enemy we were fighting that slipped out of sight (lost_prey) is tested at its last tile and
// ranked by the walk to the nearest tile it may be on.
const ChampionBelief* prey(const World& world, Safety& safety) {
    world.throw_if_stale();
    // Willow holds no fight (want_home): a chase walks it into reach only to leave next turn.
    if (world.me().facts().heals()) return nullptr;
    const vec2 here = my_position();
    const std::uint32_t lost_sight = lost_prey(world, here);
    if (!enemy_seen(world) && !lost_sight) return nullptr;
    const int range = world.me().facts().attack_range();
    // want_home kept us in a fight we press: a lost play-out here would only hand the turn to the
    // farm, walking off mid-fight from a hurter enemy, not take us out of danger.
    if (const auto* p = pressed(world)) {
        int held = 0;
        if (preyable(world, safety, *p, here, range, held)) return p;
    }
    // A teammate's pressed fight is joined as our own.
    if (const auto* p = team_pressed(world)) {
        int held = 0;
        if (preyable(world, safety, *p, here, range, held)) return p;
    }
    std::optional<float> strength; // read once a candidate needs it
    // Cassi or Issac falling takes the other body and both bags: a won fight that costs us is lost.
    const bool linked = partner(world) != nullptr;
    // Best first (ties in index order), so fights are simulated only up to the first won.
    Unwritten<std::pair<float, const ChampionBelief*>, 8> candidates;
    auto& order = candidates.a;
    int n = 0;
    for (auto left = safety.seen_enemies() | lost_sight; left; left &= left - 1) {
        const auto& e = world.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (n == static_cast<int>(order.size())) continue;
        int held = 0;
        if (!preyable(world, safety, e, here, range, held)) continue;
        if (!strength) strength = std::max(1.0f, output(world.me()));
        // One out of sight, from the nearest tile it may be on.
        vec2 at = e.pos;
        if (!e.visible) {
            int best = unreachable;
            for (const vec2 q : e.possible.positions())
                if (const int d = dist(here, q); d < best) best = d, at = q;
        }
        const int walk = walk_within(world, here, at, range);
        if (walk == unreachable) continue;
        const float turns = static_cast<float>(walk) + effective_hp(e) / *strength;
        // Turns per gem a kill is worth: the life (abilities' life_value, in gems) and the bag.
        const float cost = turns / (params::life_value / params::gem_value + static_cast<float>(pair_gems(world, e) + held));
        int i = n++;
        for (; i > 0 && order[i - 1].first > cost; --i) order[i] = order[i - 1];
        order[i] = {cost, &e};
    }
    if (n == 0) return nullptr;
    const auto live = my_record();
    const auto state = cambc::champion_state::from_bits_retain(live.state);
    const bool can_move = state.contains(cambc::champion_state::can_move);
    const bool can_cast = state.contains(cambc::champion_state::can_cast);
    // prey also tests whether to cancel a recall/tribute; that restriction is not a spent cast.
    const bool cancelable = state.contains(cambc::champion_state::recalling) || state.contains(cambc::champion_state::submitting_gems);
    const bool channel = cancelable || state.contains(cambc::champion_state::teleporting);
    const bool cast_available = can_cast || cancelable;
    std::array<int, 2> cooldowns;
    for (int s = 0; s < 2; ++s) {
        std::int32_t remaining{};
        ok(cambc::detail::sdk_champion_cooldown(my_handle(), static_cast<std::uint32_t>(s), &remaining));
        cooldowns[s] = std::max(0, static_cast<int>(remaining));
    }
    world.throw_if_stale();
    const auto& self = world.me();
    unsigned ready = 0;
    bool helps = false;
    for (int s = 0; s < 2; ++s) {
        if (!can_cast || cooldowns[s] > 0) continue;
        ready |= 1u << s;
        const auto& a = self.facts().abilities[s];
        helps |= (a.kind == AbilityKind::heal || a.kind == AbilityKind::shield) && a.multiplier > 0 && live.focus > 0;
    }
    // Delayed as allies are: by our strike this turn, walking first, unless a heal or shield helps now.
    const Strike ours = strike_with(self, ready);
    // The fights already lost: chase_trade reads only these and the turn's state, not the target.
    Unwritten<std::pair<std::uint64_t, std::uint32_t>, 8> lost_fights;
    auto& lost = lost_fights.a;
    int n_lost = 0;
    for (int i = 0; i < n; ++i) {
        const auto& target = *order[i].second;
        const auto key = safety.fight_key(target.pos);
        std::uint32_t delayed = 0;
        if (key != Safety::no_fight)
            for (auto left = key & 0xFFFFu; left; left &= left - 1) {
                const int j = std::countr_zero(left);
                const auto& a = world.allies[static_cast<std::size_t>(j)];
                if (a.is_self) {
                    // Intent only: blocked routes are pessimistic; post-cancel walking stays baseline.
                    if (const int d = dist(here, target.pos); !channel && can_move && !helps && !ours.hits(d)) delayed |= 1u << j;
                    continue;
                }
                if (!a.alive || !a.visible) continue;
                const int next = next_turn_round(world, a);
                if (strike(a, next).hits(dist(a.pos, target.pos))) continue;
                bool support = false;
                for (int s = 0; s < 2; ++s) {
                    const auto& ability = a.facts().abilities[s];
                    support |= a.ability_ready(s, next) && a.focus > 0 && ability.multiplier > 0
                        && (ability.kind == AbilityKind::heal || ability.kind == AbilityKind::shield);
                }
                if (!support) delayed |= 1u << j;
            }
        // Enemies who walk to the target in time join the fight.
        const auto late = key == Safety::no_fight ? 0u : safety.late(target.pos, key);
        const std::pair<std::uint64_t, std::uint32_t> fight{std::uint64_t{key} << 32 | delayed, late};
        if (std::find(lost.begin(), lost.begin() + n_lost, fight) != lost.begin() + n_lost) continue;
        const auto t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late);
        debug_block({
            static int traced = 0;
            if (delayed && traced < 64) {
                ++traced;
                std::printf("CHASE-AVAIL %d %u %u %u %u %d %d %d\n", world.round, my_handle(),
                            static_cast<std::uint32_t>(target.handle), key, delayed, static_cast<int>(t.lost), t.turns_to_kill_us, t.turns_to_kill_them);
            }
        });
        if (!t.lost && !(linked && t.self_falls)) return &target;
        lost[n_lost++] = fight;
    }
    return nullptr;
}

bool chase(const World& world, Pathing& pathing, Safety& safety, bool searched) {
    // After the strike search, chase only walks: the search priced and passed on its dash and casts,
    // and strike_after makes the hits from where the walk ends.
    if (searched && !my_can_move()) return false;
    const auto* target = prey(world, safety);
    if (!target) return false;
    note_engaged(static_cast<std::uint32_t>(target->handle));
    decision = Branch::chase;
    if constexpr (debug_fights) log_fight("FC", world, safety, target->pos, safety.fight(target->pos), static_cast<int>(target->handle));
    const int range = world.me().facts().attack_range();
    // Out of sight it is wherever it could be: a step onto one of those tiles shows it, or finds it
    // there (a hidden blocker).
    const bool unseen = !target->visible;
    // A walk alone cannot reach range this turn; a melee walk can follow the dash.
    if (!searched && !unseen && dist(my_position(), target->pos) > range + 1 && my_can_move()) dash_to_attack(world, pathing, &safety, target);
    bool stuck = false;
    if ((unseen || dist(my_position(), target->pos) > range) && my_can_move()) {
        const auto* zone = pack_zone(world, safety);
        static bitboard goals{cambc::uninitialized};
        clear_board(goals);
        if (unseen) goals |= target->possible;
        else draw_square(goals, target->pos, static_cast<float>(range));
        and_into(goals, world.map().open_for_us, goals);
        if (zone) drop(goals, *zone);
        stuck = !pathing.step_towards(goals, zone, 2 * vision_radius) && (unseen || dist(my_position(), target->pos) > range);
    }
    if (searched) return !stuck;
    bool hit = attack_enemy(world);
    hit |= reset_and_attack_enemy(world); // after an attack, or a ranged walk
    hit |= cast_at_enemies(world);
    // No step and no hit: the target is out of our walk's reach (across live camps), so the turn goes on.
    return hit || !stuck;
}

// A champion's turn start in `round`, where its channel completes.
Moment turn_start(const World& world, const ChampionBelief& c, int round) { return {round, world.slot(c, round) - 1}; }

// The earliest our winning bag's win lands: our tribute's end, or, none under way, the walk to an
// altar, the break of its enemy lock and a whole channel; and no sooner than the allies' tributes in
// sight that gems_short counts.
Moment win_lands(const World& world, Pathing& pathing) {
    Moment m{world.round, -1};
    if (const int bag = static_cast<int>(my_gems()); bag > 0) {
        const vec2 here = my_position();
        int r = world.round;
        if (my_state().contains(cambc::champion_state::submitting_gems)) {
            r += my_channel_time();
        } else {
            const auto& altars = world.map().altars;
            int walk = unreachable;
            for (int a = 0; a < static_cast<int>(altars.size()); ++a)
                if (const int w = pathing.to_altar(a).at(here); w != unreachable)
                    walk = std::min(walk, w + lock_turns(world.altars[a], world.me(), w, world.round));
            // No walk reaches one (a crystal's pocket): the nearest as the crow flies.
            if (walk == unreachable)
                for (const auto& a : altars) walk = std::min(walk, std::max(0, dist(here, a.pos) - cambc::constants::submit_gems_range));
            r += walk + tribute_turns(world, bag);
        }
        m = turn_start(world, world.me(), r);
    }
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && a.channel == Channel::tribute)
            m = std::max(m, turn_start(world, a, a.channel_end_round));
    return m;
}

// A visible enemy whose tribute wins them the game, in reach of a ready stun of ours, and lands
// before our bag's win if ours wins; null if none.
const ChampionBelief* stoppable_winning_tribute(const World& world, Pathing& pathing) {
    if (!enemy_seen(world)) return nullptr;
    const auto& self = world.me();
    // Cancelling our tribute frees the walk.
    const bool walk = my_can_move() || my_state().contains(cambc::champion_state::submitting_gems);
    std::optional<Moment> win;
    for (const auto& e : world.enemies)
        if (enemy_tribute_wins(world, e) && e.facts().passive != Passive::stun_immune
            && dist(self.pos, e.pos) <= self.ready_stun_reach(world.round, walk)) {
            if (!winning_bag(world)) return &e;
            if (!win) win = win_lands(world, pathing);
            if (turn_start(world, e, e.channel_end_round) < *win) return &e;
        }
    return nullptr;
}

// A visible ally out of channels, acting before an enemy's tribute lands, can stop it alone (its
// game_ender sees the race as we do): a ready stun in reach (after a walk, if it allows one), or a
// carried lock within a walk and 2 of the altar, unless that altar is ours too (its place_lock
// spares our winning tribute). An enemy in a bush is seen only from its cluster: not counted.
bool ally_stops(const World& world, const ChampionBelief& e) {
    if (test(world.map().bushes, e.pos)) return false;
    const Moment lands = turn_start(world, e, e.channel_end_round);
    const int altar = tribute_altar(world, e.pos);
    const bool lockable = altar >= 0 && tribute_altar(world, my_position()) != altar;
    const bool stunnable = e.facts().passive != Passive::stun_immune;
    const auto& map = world.map();
    // Tiles off bushes that e (off bushes) is in sight from, sight being symmetric: made on first need.
    std::optional<bitboard> sees;
    // q sees e: from a bush its own cluster is transparent (rules vision.occlusion), so cast from q.
    const auto sees_from = [&](vec2 q) {
        if (!test(map.bushes, q)) {
            if (!sees) sees.emplace(map.sight_off_bushes(e.pos, vision_radius));
            return test(*sees, q);
        }
        static bitboard opaque{cambc::uninitialized}, cast{cambc::uninitialized};
        copy_into(map.walls_and_bushes, opaque);
        drop(opaque, map.bush_cluster(q).tiles);
        opaque.shadow_cast_into(q, static_cast<std::uint16_t>(vision_radius), cast);
        return test(cast, e.pos);
    };
    // Its tile, or a step onto a free open tile with no live camp on it.
    const auto stands = [&](const ChampionBelief& a, vec2 q) {
        if (q == a.pos) return true;
        if (!in_bounds(q) || !test(map.open_for_us, q) || live_camp_on(world, q)) return false;
        for (const auto* side : {&world.allies, &world.enemies})
            for (const auto& o : *side)
                if (o.alive && (o.is_self ? my_position() == q : o.visible && o.pos == q)) return false;
        return true;
    };
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible || held_by_channel(a)) continue;
        const int r = a.acted ? world.round + 1 : world.round;
        if (!a.can_act(r) || !(turn_start(world, a, r) < lands) || stun_pending(a.handle)) continue;
        const auto& f = a.facts();
        // The caster's own ward's sight counts for unit targets (rules abilities.unit_target).
        const auto* ward = ward_sight(world, static_cast<std::uint32_t>(a.handle));
        const bool ward_sees = ward && test(*ward, e.pos);
        if (stunnable)
            for (int s = 0; s < 2; ++s) {
                const auto& ab = f.abilities[s];
                if (!ab.stuns || !a.ability_ready(s, r)) continue;
                // Heart of Ruin's landing strikes round where it lands: its reach already counts the dash.
                if (ab.lands()) {
                    if (dist(a.pos, e.pos) <= f.stun_reach_with_walk(s)) return true;
                    continue;
                }
                const int reach = f.stun_reach(s);
                const bool sight = ab.target != Targeting::ground; // a unit target, or Marcella's attack
                for (int dx = -1; dx <= 1; ++dx)
                    for (int dy = -1; dy <= 1; ++dy) {
                        const vec2 q{a.pos.x + dx, a.pos.y + dy};
                        if ((dx || dy) && ab.excludes_walking) continue;
                        if (dist(q, e.pos) > reach || !stands(a, q)) continue;
                        if (sight && !ward_sees && !sees_from(q)) continue;
                        return true;
                    }
            }
        bool lock_tile = false;
        if (lockable)
            for (int dx = -1; dx <= 1 && !lock_tile; ++dx)
                for (int dy = -1; dy <= 1 && !lock_tile; ++dy) {
                    const vec2 q{a.pos.x + dx, a.pos.y + dy};
                    lock_tile = dist(q, map.altars[altar].pos) <= altar_lock_range && stands(a, q);
                }
        if (lock_tile) {
            std::array<std::uint32_t, 4> counts{};
            const auto lock = cambc::detail::raw_consumable_ids[static_cast<std::size_t>(cambc::consumable_type::altar_lock)];
            if (cambc::detail::sdk_champion_consumables(static_cast<std::uint32_t>(a.handle), counts.data()) == 0 && counts[lock] > 0)
                return true;
        }
    }
    return false;
}

// A visible enemy whose bag (both, for a walking Cassi and Issac) ends the game once tributed and that we
// can stop: nothing we gain meanwhile counts unless our own bag wins first. The nearest; null if none.
const ChampionBelief* game_ender(const World& world, Pathing& pathing) {
    const int need = static_cast<int>(cambc::constants::winning_gems) - world.score.enemy;
    if (!enemy_seen(world)) return nullptr;
    // No pair carries more than every living enemy's bag together.
    int carried = 0;
    for (const auto& e : world.enemies) carried += e.alive ? e.gems : 0;
    if (carried < need) return nullptr;
    std::optional<vec2> here; // and when our bag's win lands if it wins, once one qualifies
    std::optional<Moment> win;
    const ChampionBelief* best = nullptr;
    int best_steps = unreachable;
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible) continue;
        const bool tributing = e.channel == Channel::tribute;
        // A tribute scores only the tributing body's bag; one by its spawn can still be stunned or locked.
        if ((tributing ? e.gems : pair_gems(world, e)) < need || (!tributing && test(world.map().near_enemy_spawn, e.pos))) continue;
        if (!here) {
            here = my_position();
            if (winning_bag(world)) win = win_lands(world, pathing);
        }
        // Our winning bag wins unless their tribute lands first: under way, or at the end of a walk.
        if (win) {
            if (tributing) {
                if (!(turn_start(world, e, e.channel_end_round) < *win)) continue;
            } else {
                const auto t = carrier_tribute(world, e, carrier_walk(world, e));
                if (!t.altar || !(turn_start(world, e, world.round + t.turns) < *win)) continue;
                debug_block({ std::printf("ENDER-WALK %d %u\n", world.round, static_cast<unsigned>(world.me().handle)); });
            }
        }
        if (const int steps = intercept_steps(world, e, *here); steps < best_steps) best = &e, best_steps = steps;
    }
    return best;
}

// Into reach of the enemy whose bag ends the game, whatever the risk: a stun or a lock if it is
// tributing, else attacks, followed until it stops at an altar.
void stop_game_ender(const World& world, Pathing& pathing, Memory& memory, const ChampionBelief& e) {
    auto& me = cambc::self();
    decision = Branch::stop_ender;
    memory.claim = -1;
    pathing.set_guard(nullptr);
    const bool tributing = e.channel == Channel::tribute;
    const auto act = [&] {
        place_lock(world);
        cast_at_enemies(world, !tributing && dist(me.position(), e.pos) > world.me().facts().attack_range() ? escape_step_value : 0.0f);
        if (attack_enemy(world)) reset_and_attack_enemy(world);
    };
    act();
    if (!me.can_move()) return;
    const int range = world.me().facts().attack_range();
    static bitboard goals{cambc::uninitialized};
    goals.clear();
    int reach = range;
    if (tributing && e.facts().passive != Passive::stun_immune) reach = std::max(reach, world.me().ready_stun_reach(world.round + 1));
    goals.draw_chebyshev(e.pos, static_cast<float>(reach));
    if (const int a = tributing ? tribute_altar(world, e.pos) : -1; a >= 0 && carried_locks() > 0) goals |= world.map().altars[a].lock_tiles();
    goals &= world.map().open_for_us;
    if (test(goals, me.position())) return;
    // A stun a walk away comes from the walk's tile: a dash first may land out of it (Heart of Ruin).
    const bool walk_stuns = tributing && e.facts().passive != Passive::stun_immune
                            && dist(me.position(), e.pos) <= world.me().ready_stun_reach(world.round, true);
    if (dist(me.position(), e.pos) > range + 1 && !walk_stuns) dash_to_attack(world, pathing, nullptr, &e);
    if (!test(goals, me.position())) pathing.step_towards_funded(goals, end_reserve);
    act();
}

// Our health with our shield, which Ren's retaliation drains first, and a basic attack's damage to
// a champion before its Durability, read once for a batch of sure_kill() calls: valid until we act
// (Ren's retaliation changes our health).
struct OurHit {
    float health, damage;
};
OurHit our_hit(const World& world) {
    const auto& r = my_record();
    const float health = r.health, strength = r.strength, max_health = r.max_health;
    return {health + my_live_shield(world), strength * damage_scale(world.me().facts().passive, health, max_health) * champion_dealt_factor()};
}

// A visible enemy within `range` of `from` that one basic attack kills.
const ChampionBelief* sure_kill(const World& world, const OurHit& us, vec2 from, int range) {
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible || dist(from, e.pos) > range || e.retaliation() * world.me().taken >= us.health) continue;
        const float shield = e.shield > 0 ? shield_value(e.handle) : 0.0f;
        if (e.health + shield <= us.damage * e.taken) return &e;
    }
    return nullptr;
}
const ChampionBelief* sure_kill(const World& world, vec2 from, int range) { return sure_kill(world, our_hit(world), from, range); }

// Nothing but `enemy` could hit us at p before our next turn.
bool only_threat(Safety& safety, vec2 p, int enemy) {
    return safety.camp_damage(p, true, true) <= 0 && !safety.other_hits(p, enemy);
}

// A sure kill from a tile a step away (melee: the walk keeps the attack) or a ready dash away,
// where nothing but the victim reaches us: the victim's tile, else {-1, -1}.
vec2 step_to_kill(const World& world, Pathing& pathing, Safety& safety, int range, bool melee) {
    const vec2 here = my_position();
    const bool walk = melee && my_can_move();
    const bool dash = world.me().facts().has_dash() && my_can_cast();
    if (!walk && !dash) return {-1, -1};
    const auto us = our_hit(world);
    if (!sure_kill(world, us, here, range + (dash ? dash_range : 1))) return {-1, -1};
    const auto hit = [&](const ChampionBelief& kill) {
        try {
            attack_champion(kill.handle);
            return true;
        } catch (const cambc::error&) {
            return false;
        }
    };
    if (walk) {
        const auto& blocked = pathing.blocked();
        for (const auto d : directions) {
            const vec2 p = here + d;
            if (!in_bounds(p) || test(blocked, p)) continue;
            if (const auto* kill = sure_kill(world, us, p, range); kill && only_threat(safety, p, kill->index) && pathing.try_move(p) == Pathing::Move::moved)
                return hit(*kill) ? kill->pos : vec2{-1, -1};
        }
    }
    if (dash) {
        static bitboard tiles{cambc::uninitialized};
        clear_board(tiles);
        const ChampionBelief* victim = nullptr;
        for (auto p : Tiles<5 * 5>{pathing.dash_landings()})
            if (const auto* kill = sure_kill(world, us, p, range); kill && (!victim || kill == victim) && only_threat(safety, p, kill->index))
                victim = kill, tiles.set(p);
        if (victim && dash_onto(world, pathing, tiles) && hit(*victim)) return victim->pos;
    }
    return {-1, -1};
}

// After our hits: an enemy we killed stays a live threat around its tile in World (dash landings,
// retreat steps) and, once refresh() has read it alive, in Safety: read vision again.
void see_kills(World& world, Pathing& pathing, Safety& safety) {
    pathing.settle_guard();
    const bool stunned = world.read_stuns();
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && !is_alive(e.handle)) {
            see_again(world, pathing, safety);
            return;
        }
    if (stunned) {
        std::destroy_at(&safety);
        std::construct_at(&safety, world);
    }
    safety.refresh();
}

// One adjacent walk taking no modelled damage or stun before our next turn, nearest our spawn. Quotes
// are legal-looking only: a hidden unit can still refuse the move.
std::optional<vec2> quote_escape_walk(const World& world, Pathing& pathing, Safety& safety,
                                      const std::array<vec2, 8>& rejected, int count) {
    const vec2 here = my_position();
    const auto& blocked = pathing.blocked();
    const auto* guard = pathing.guard();
    const auto& home = pathing.to_ally_spawn();
    std::optional<vec2> best;
    int best_home = unreachable;
    for (const auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || !test(world.map().open_for_us, p) || test(blocked, p) || (guard && test(*guard, p))) continue;
        bool refused = false;
        for (int i = 0; i < count; ++i) refused |= rejected[i] == p;
        if (refused) continue;
        if (safety.touched(p)) continue;
        const int steps = home.at(p);
        if (!best || steps < best_home) best = p, best_home = steps;
    }
    return best;
}

// The one visible enemy that threatens `here`, the only one a walk-excluding cast may take the
// escape walk for; -1 if there are others, unseen ones or a next-phase camp hit.
int sole_escape_threat(const World& world, Safety& safety, vec2 here) {
    if (safety.camp_damage(here, true, true) > 0) return -1;
    std::array<Safety::ThreatAt, 16> at;
    const int n = safety.threats_at(here, at);
    int sole = -1;
    for (int i = 0; i < n; ++i) {
        if (!at[i].blow.hits) continue;
        const auto& e = world.enemies[at[i].enemy];
        if (sole >= 0 || !e.visible) return -1;
        sole = e.index;
    }
    return sole;
}

// A champion whose casts at enemies exclude walking (Prism, Stellar, Ryth, Marcella, Tavi, Ren,
// Cassi), on a lethal tile with a safe step: no cast's worth buys away that walk, bar a cast that
// kills or stuns in time the only threat (a unit cast, or a ground stun centred within 1 of it).
// Each refused move is looked at again before the next; `looked`: vision was read again.
bool escape_walk(World& world, Pathing& pathing, Safety& safety, bool* looked = nullptr) {
    const auto& f = world.me().facts();
    if (!(f.abilities[0].excludes_walking && f.abilities[0].hits_enemies()) && !(f.abilities[1].excludes_walking && f.abilities[1].hits_enemies()))
        return false;
    const auto look = [&] {
        see_again(world, pathing, safety);
        if (looked) *looked = true;
    };
    std::array<vec2, 8> rejected;
    int count = 0;
    bool consider_cast = true;
    while (count < static_cast<int>(rejected.size())) {
        world.throw_if_stale();
        if (!my_can_move() || !safety.lethal(my_position())) return false;
        const auto quote = quote_escape_walk(world, pathing, safety, rejected, count);
        if (!quote) return false;
        if (consider_cast) {
            consider_cast = false;
            bool attempted = false;
            if (cast_at_enemies_for_escape(world, sole_escape_threat(world, safety, my_position()), escape_step_value, attempted))
                return true;
            if (attempted) {
                // A failed cast can reveal changed vision or legality: quote the walk again.
                look();
                continue;
            }
        }
        if (pathing.try_move(*quote) == Pathing::Move::moved) {
            look();
            return true;
        }
        rejected[count++] = *quote;
        look();
    }
    return false;
}

// Below the recall line with an escape dash ready whose cast a cast at enemies would take (Heart of
// Ruin's landing, Ren's stun): when the escape dash lands untouched, only a cast that kills goes
// before it; otherwise escape_walk's rule, then any cast, and the escape follows if the cast is
// left. True if the turn is done (dead or tributing).
bool dash_retreat_casts(World& world, Pathing& pathing, Safety& safety, Memory& memory, vec2 dead) {
    see_kills(world, pathing, safety);
    if (!cambc::self().is_alive()) return true;
    if (can_tribute_safely(world, pathing, safety, memory)) {
        bank_gems(world, pathing, safety, memory, false);
        return true;
    }
    const auto quote = quote_escape_dash(world, pathing, safety, pathing.to_ally_spawn(), dead);
    // A cast tried and failed may have revealed a hidden blocker, and a dash moved us: either way
    // vision is read again and the quote, which vouches only for its first landing, is dropped.
    bool reusable = true, casted = false;
    if (quote.clears && !safety.touched(quote.tiles[0])) {
        bool attempted = false;
        casted = cast_at_enemies(world, escape_step_value, true, &attempted);
        if (!casted) {
            if (!attempted) casted = cast_escape_dash(world, pathing, quote);
            see_again(world, pathing, safety);
            reusable = false;
        }
    }
    if (!casted) {
        bool looked = false;
        // Walked (the quote is from the old tile), cast, or read vision again.
        if (escape_walk(world, pathing, safety, &looked)) casted = !my_can_cast(), reusable = false;
        if (looked) reusable = false;
    }
    if (!casted) {
        bool attempted = false;
        casted = cast_at_enemies(world, escape_step_value, false, &attempted);
        if (attempted && !casted) {
            see_again(world, pathing, safety);
            reusable = false;
        }
    }
    if (!cambc::self().is_alive()) return true;
    if (!my_can_attack() || !my_can_cast()) see_kills(world, pathing, safety);
    if (can_tribute_safely(world, pathing, safety, memory)) {
        bank_gems(world, pathing, safety, memory, false);
        return true;
    }
    if (my_can_cast()) {
        if (reusable) {
            const bool escaped = cast_escape_dash(world, pathing, quote);
            if (quote.count > 0) see_again(world, pathing, safety);
            if (!escaped && quote.count > 0 && dash_away(world, pathing, safety, pathing.to_ally_spawn(), dead))
                see_again(world, pathing, safety);
        } else if (dash_away(world, pathing, safety, pathing.to_ally_spawn(), dead)) {
            see_again(world, pathing, safety);
        }
    }
    return false;
}

void retreat(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    world.throw_if_stale();
    auto& me = cambc::self();
    decision = Branch::retreat;
    const int mono = mono_trapped(world, pathing, safety, memory, my_health());
    memory.claim = -1;
    if (!memory.siege && (mono >= 0 ? mono == 1 : camp_trapped(world, pathing, safety, my_position(), my_health(), false)))
        memory.camp_fled = my_health();
    memory.banking = banks_bag(world, pathing);
    const bool melee = world.me().facts().walk_and_attack_independent();
    const int range = world.me().facts().attack_range();
    const vec2 here = my_position();
    vec2 dead{-1, -1};
    // A sure kill first. A ranged attack spends the walk, so only where standing is no worse:
    // nothing else reaches us here, or the dash still lands out of every reach.
    if (const auto* kill = my_can_attack() ? sure_kill(world, here, range) : nullptr;
        kill && (melee || only_threat(safety, here, kill->index) || dash_clears(world, pathing, safety, kill->pos))) {
        try {
            attack_champion(kill->handle);
            dead = kill->pos;
        } catch (const cambc::error&) {
        }
    }
    // A kill a step or a dash off, where only the victim reaches us; else the homeward step may still land beside it.
    if (dead.x < 0 && my_can_attack()) dead = step_to_kill(world, pathing, safety, range, melee);
    // A melee kill one step off waits for the step, which may land beside it.
    const bool held = melee && my_can_attack() && sure_kill(world, here, range + 1);
    if (melee && !held) attack_enemy(world);
    if (!my_can_attack()) reset_and_attack_enemy(world, true);
    const auto& f = world.me().facts();
    const int escape_slot = f.slot_of(AbilityKind::dash);
    const bool contested = escape_slot >= 0 && (f.abilities[escape_slot].lands() || f.abilities[1 - escape_slot].hits_enemies());
    const bool keep_dash = contested && my_health() < params::recall_health_fraction * my_max_health()
                           && my_can_cast() && my_cooldown(escape_slot) == 0;
    if (keep_dash) {
        if (dash_retreat_casts(world, pathing, safety, memory, dead)) return;
    } else {
        // After the walk, a cast that allows walking may still follow (Cassi's stun).
        if (!escape_walk(world, pathing, safety) || my_can_cast()) cast_at_enemies(world, escape_step_value);
        if (!me.is_alive()) return;
        if (!my_can_attack() || !my_can_cast()) see_kills(world, pathing, safety);
        // A tribute survives damage; a recall does not.
        if (can_tribute_safely(world, pathing, safety, memory)) {
            bank_gems(world, pathing, safety, memory, false);
            return;
        }
        dash_away(world, pathing, safety, pathing.to_ally_spawn(), dead);
    }
    // The escape dash shares the one cast: the reset only after it, from a melee attack or a ranged walk.
    if (reset_and_attack_enemy(world)) see_kills(world, pathing, safety);
    else see_stuns(world, safety); // Heart of Ruin's landing
    if (!flee_camps(world, pathing, safety, pathing.to_ally_spawn())) retreat_step(world, pathing, safety, pathing.to_ally_spawn());
    // A walk to a hole line's edge can bring a dash out of the camps' reach in reach.
    if (my_can_cast() && safety.camp_damage(my_position()) > 0 && dash_away(world, pathing, safety, pathing.to_ally_spawn(), dead))
        see_again(world, pathing, safety);
    // A ranged walk spent the attack; one that failed did not.
    if (attack_enemy(world) && melee) reset_and_attack_enemy(world, true);
    reset_and_attack_enemy(world);
}

} // namespace

} // namespace aph
