// Function bodies; src/unity.cpp includes this after every header.

namespace aph {
namespace {
[[gnu::flatten]] void place_lock(const World& world)
{
    auto& me = cambc::self();
    if (stunned_turn || !world.me().alive) return;
    const auto& lock = me.consumables()[cambc::consumable_type::altar_lock];
    if (lock.count() == 0 || channelling()) return;
    const auto& map = world.map();
    const vec2 here = my_position();
    // Altars with an enemy tributing first.
    for (int pass = 0; pass < 2; ++pass)
        for (int a = 0; a < static_cast<int>(map.altars.size()); ++a) {
            const vec2 p = map.altars[a].pos;
            if (dist(here, p) > 2 || world.altars[a].ally_lock) continue;
            if (a < static_cast<int>(own_lock_round.size()) && own_lock_round[a] >= 0
                && own_lock_round[a] >= world.altars[a].seen_round)
                continue;
            // Placing one also cancels an enemy's tribute there: its bag stays out of the score.
            bool enemy_tribute = false, winning = false;
            for (const auto& e : world.enemies)
                if (e.alive && e.visible && e.channel == Channel::tribute && dist(e.pos, p) <= 1)
                    enemy_tribute = true, winning |= enemy_tribute_wins(world, e);
            if (enemy_tribute != (pass == 0)) continue;
            if (!enemy_tribute && dist(p, map.ally_spawn_centre) > dist(p, map.enemy_spawn_centre) + 2) continue;
            // Placing one cancels every tribute at the altar, ours included: worth it only against a win.
            bool tributing = false, ours_wins = false;
            for (const auto& ally : world.allies)
                if (!ally.is_self && ally.alive && ally.channel == Channel::tribute && dist(ally.pos, p) <= 1)
                    tributing = true,
                    ours_wins |= world.score.ally + ally.gems >= static_cast<int>(cambc::constants::winning_gems);
            if (tributing && (!winning || ours_wins)) continue;
            const auto known = [&] {
                if (own_lock_round.size() < map.altars.size()) own_lock_round.resize(map.altars.size(), -1);
                own_lock_round[a] = world.round;
            };
            throw_if_stale();
            try {
                if (lock.use(p)) return known();
            } catch (const cambc::error& e) {
                if (e.code() == cambc::error_code::invalid_action_altar_lock_already_locked) known();
            }
        }
}

bool break_lock(const World& world, int altar)
{
    auto& me = cambc::self();
    const vec2 p = world.map().altars[altar].pos;
    if (!my_can_attack() || dist(my_position(), p) > world.me().facts().attack_range()) return false;
    for (const auto& lock : cambc::vision::altar_locks())
        if (lock.is_enemy() && lock.position() == p) {
            throw_if_stale();
            try {
                me.attack(lock);
                return true;
            } catch (const cambc::error&) {
                return false;
            }
        }
    return false;
}

bool enemy_lock_live(vec2 p)
{
    for (const auto& lock : cambc::vision::altar_locks())
        if (lock.is_enemy() && lock.position() == p) return true;
    return false;
}

bool tribute_safe(Safety& safety, const Aims& aims, int turns)
{
    const int window = std::min(turns, params::tribute_window);
    const float health = my_health();
    if (aims.damage * static_cast<float>(window) >= health) return false;
    const int kill = safety.turns_to_kill_idle(my_position(), window + 1);
    return kill == 0 || kill > window;
}

int tribute_turns(int gems)
{ return std::max(1, (gems + 9) / 10); }

int recall_turns(const World& world)
{
    return world.me().fast_recall ? home_recall_time : static_cast<int>(cambc::constants::recall_time);
}

int rounds_left(const World& world)
{ return static_cast<int>(cambc::constants::max_rounds) - world.round; }

bool may_shop(const World& world)
{ return world.me().facts().passive != Passive::remote_shop; }

int gems_short(const World& world)
{
    int pending = 0;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && a.channel == Channel::tribute) pending += a.gems;
    return static_cast<int>(cambc::constants::winning_gems) - world.score.ally - static_cast<int>(my_gems())
           - pending;
}

const ChampionBelief* partner(const World& world)
{ return linked_partner(world, world.me()); }

int bag_at_stake(const World& world)
{
    const auto* p = partner(world);
    const int other = !p || !p->alive ? 0 : p->visible ? p->gems : std::max(p->gems, comms::bag_of(world, p->index));
    return static_cast<int>(my_gems()) + other;
}

void dilate_into(const bitboard& b, bitboard& out)
{
    static bitboard rows{cambc::uninitialized}, shifted{cambc::uninitialized};
    copy_into(b, rows);
    for (const int d : {1, -1}) {
        b.shift_right_into(d, shifted);
        rows |= shifted;
    }
    copy_into(rows, out);
    for (const int d : {1, -1}) {
        rows.shift_up_into(d, shifted);
        out |= shifted;
    }
}

const AltarAccess& altar_access(const World& world, Pathing& pathing)
{
    static AltarAccess a;
    const auto& live = pathing.live_camps();
    if (a.version > 0 && a.live_flips == pathing.live_flips()) return a;
    a.live_flips = pathing.live_flips();
    const auto& map = world.map();
    // `ours` is kept as the walk from our spawn with a.live as walls: most changes update it
    // without a flood from spawn.
    static bitboard walls{cambc::uninitialized}, ours{cambc::uninitialized}, area{cambc::uninitialized},
        seen{cambc::uninitialized}, gone{cambc::uninitialized}, grown{cambc::uninitialized};
    bool walked = false;
    if (a.version > 0 && !map.ally_spawn_tiles.empty()) {
        copy_into(live, area);
        drop(area, a.live);
        copy_into(a.live, gone);
        drop(gone, live);
        const bool back = !board_empty(area), died = !board_empty(gone);
        if (!back && !died) return a;
        if (!back) {
            // Deaths add to the walk what each dead camp beside it reaches without crossing it.
            or_into(pathing.static_walls(), live, walls);
            walls |= ours;
            dilate_into(ours, grown);
            gone &= grown;
            while (!board_empty(gone)) {
                const vec2 t = first_tile(gone);
                walls.reachable_tiles_into(t, unreachable, seen);
                ours |= seen;
                drop(gone, seen);
                set_tile(gone, t, false);
            }
            walked = true;
        } else if (!died) {
            // Respawns whose walkable ring is connected cut no walk: it goes round them.
            dilate_into(area, grown);
            grown &= ours;
            drop(grown, area);
            walked = board_empty(grown);
            if (!walked) {
                not_into(grown, walls);
                walls.reachable_tiles_into(first_tile(grown), static_cast<std::uint16_t>(board_count(grown)), seen);
                walked = seen == grown;
            }
            if (walked) drop(ours, area);
        }
    }
    ++a.version;
    copy_into(live, a.live);
    a.blocks.clear();
    clear_board(a.open);
    clear_board(a.opened);
    a.any_open = false;
    if (map.ally_spawn_tiles.empty()) return a;
    static bitboard tributes{cambc::uninitialized};
    if (a.version == 1) {
        clear_board(tributes);
        for (const auto& t : map.altars) tributes |= t.tribute_tiles();
        // Off our walk, a tribute tile counts below as a crystal's: only if a hop reaches its altar.
        copy_into(tributes, area);
        drop(area, pathing.foot());
        if (!board_empty(area)) {
            for (const auto& h : map.hops()) drop(area, map.altars[h.altar].tribute_tiles());
            drop(tributes, area);
        }
    }
    copy_into(tributes, a.opened);
    if (!walked) {
        or_into(pathing.static_walls(), live, walls);
        walls.reachable_tiles_into(map.ally_spawn_tiles[0], unreachable, ours);
    }
    // open = tributes off live camps, but for those the static walk reaches and this one does not
    copy_into(a.opened, a.open);
    drop(a.open, live);
    // The static walk is a flood as costly as ours (~28k on 100x100, uncached until the warm-up):
    // read it only when a tribute tile is off our walk or none is open.
    copy_into(a.open, area);
    drop(area, ours);
    const bool off_walk = !board_empty(area);
    if (off_walk) {
        copy_into(pathing.foot(), area);
        drop(area, ours);
        drop(a.open, area);
    }
    a.any_open = !a.open.is_empty();
    if (a.any_open) {
        copy_into(a.open, a.opened);
        return a;
    }
    if (!off_walk) {
        copy_into(pathing.foot(), area);
        drop(area, ours);
    }
    a.opened &= area;
    // The live camps beside our walk.
    dilate_into(ours, grown);
    grown &= live;
    or_into(pathing.static_walls(), ours, walls);
    clear_board(seen);
    for (const vec2 t : a.opened.positions()) {
        if (test(seen, t)) continue;
        walls.reachable_tiles_into(t, unreachable, area);
        seen |= area;
        area &= grown;
        for (const vec2 p : area.positions())
            if (const int g = map.group_at(p); g >= 0 && std::find(a.blocks.begin(), a.blocks.end(), g) == a.blocks.end())
                a.blocks.push_back(g);
    }
    return a;
}

float access_fire(const World& world, const AltarAccess& a)
{
    static int round = -1, version = 0;
    static float fire = 0;
    if (round == world.round && version == a.version) return fire;
    round = world.round;
    version = a.version;
    fire = std::numeric_limits<float>::max();
    const auto& map = world.map();
    const auto& groups = map.groups;
    // By group, once read: 1 if a member reaches a tile beside an altar.
    static std::vector<signed char> near;
    if (near.size() != groups.size()) near.assign(groups.size(), -1);
    static std::vector<int> stirring;
    stirring.clear();
    world.each_stirring([&](int g) {
        if (near[g] < 0) {
            near[g] = 0;
            for (const auto& m : groups[g].members)
                for (const auto& altar : map.altars)
                    if (dist(m.pos, altar.pos) <= m.reach + 1) near[g] = 1;
        }
        if (near[g]) stirring.push_back(g);
    });
    // With nothing stirring every open tile is free of fire.
    if (stirring.empty()) return fire = a.any_open ? 0.0f : fire;
    // Room for every tribute tile, which the open ones are among.
    static std::vector<vec2> open;
    if (open.empty()) {
        bitboard tributes;
        for (const auto& t : map.altars) tributes |= t.tribute_tiles();
        open.resize(std::max<std::size_t>(1, board_count(tributes)));
    }
    const auto n = std::min<std::size_t>(positions_into(a.open, open.data(), static_cast<std::uint32_t>(open.size())), open.size());
    for (const vec2 t : std::span{open.data(), n}) {
        float f = 0;
        for (const int g : stirring) {
            if (!test(groups[g].threat(), t)) continue;
            const auto& c = world.camps[g];
            for (std::size_t i = 0; i < groups[g].members.size(); ++i) {
                const auto& m = groups[g].members[i];
                if (c.health[i] > 0 && !c.maybe_asleep(i) && in_square(t, m.pos, m.reach)) f += m.strength;
            }
        }
        if ((fire = std::min(fire, f)) <= 0) break;
    }
    return fire;
}

bool altar_usable(const World& world, Pathing& pathing, int bag, float health)
{
    const auto& a = altar_access(world, pathing);
    return a.any_open && camp_hit_factor() * access_fire(world, a) * static_cast<float>(tribute_turns(bag)) < health;
}

int bankable_bag(const World& world, Pathing& pathing)
{
    const int bag = static_cast<int>(my_gems());
    if (bag == 0 || !altar_usable(world, pathing, bag, my_health())) return 0;
    // Only a crystal reaches an altar and we can neither use nor buy one: farm the gold first.
    if (!world.map().hops().empty() && pathing.to_any_altar().at(my_position()) == unreachable && !carries_crystal()
        && !can_buy_crystal())
        return 0;
    return bag;
}

bool altars_sealed(const World& world, Pathing& pathing)
{
    int bag = static_cast<int>(my_gems());
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive) bag = std::max(bag, a.visible ? a.gems : comms::bag_of(world, a.index));
    return !altar_usable(world, pathing, bag, my_max_health());
}

bool seals(const World& world, const AltarAccess& access, int g)
{
    const auto& c = world.camps[g];
    if (c.state != CampState::alive) return false;
    if (std::find(access.blocks.begin(), access.blocks.end(), g) != access.blocks.end()) return true;
    const auto& members = world.map().groups[g].members;
    for (std::size_t i = 0; i < members.size(); ++i)
        if (c.health[i] > 0 && members[i].strength > 0 && !c.maybe_asleep(i)
            && any_within(access.opened, members[i].pos, members[i].reach))
            return true;
    return false;
}

bool winning_bag(const World& world)
{ return gems_short(world) <= 0; }

int race_left(const World& world)
{
    int short_by = gems_short(world);
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && !(a.visible && a.channel == Channel::tribute))
            short_by -= a.visible ? a.gems : comms::bag_of(world, a.index);
    if (short_by <= 0) return 0;
    const float rate = world.ally_rate();
    return rate > 0 ? static_cast<int>(static_cast<float>(short_by) / rate) : rounds_left(world);
}

int bag_rounds_left(const World& world)
{
    return my_gems() > 0 ? std::min(rounds_left(world), race_left(world)) : rounds_left(world);
}

bool closing(const World& world, Pathing& pathing)
{
    const auto& field = pathing.to_any_altar();
    int walk = field.at(my_position());
    // No walk out of here: recall home and walk from there.
    if (walk == unreachable) {
        const int out = field.at(world.map().ally_spawn_centre);
        walk = out == unreachable ? 0 : recall_turns(world) + out;
    }
    return bag_rounds_left(world) <= walk + tribute_turns(my_gems()) + endgame_margin;
}

bool retaining_gems(const World& world, Pathing& pathing)
{
    return world.me().facts().passive == Passive::gem_focus && my_gems() > 0
           && !winning_bag(world) && !closing(world, pathing);
}

bool any_risk(const World& world, int channel_turns)
{
    return (winning_bag(world) && channel_turns <= params::tribute_window)
           || rounds_left(world) <= channel_turns + endgame_slack;
}

bool tribute_ok(const World& world, Safety& safety, const Aims& aims, int turns)
{
    return turns <= rounds_left(world) && (any_risk(world, turns) || tribute_safe(safety, aims, turns));
}

bool covered(const World& world, vec2 altar)
{
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && dist(e.pos, altar) <= threat_strike(world, e).reach + 1) return true;
    return false;
}

bool submit_here(const World& world, Safety& safety, Aims& aims)
{
    if (stunned_turn) return false; // the engine refuses it, and the thrown error costs ~3.9k fuel
    auto& me = cambc::self();
    const vec2 here = my_position();
    const auto& altars = world.map().altars;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
        if (dist(here, altars[a].pos) > cambc::constants::submit_gems_range) continue;
        if (world.altars[a].enemy_lock && enemy_lock_live(altars[a].pos)) continue;
        if ((covered(world, altars[a].pos) || world.altars[a].enemy_lock || here != world.me().pos)
            && !tribute_ok(world, safety, aims, tribute_turns(my_gems())))
            return false;
        place_lock(world); // first: it cancels every tribute at its altar
        place_ward(world, aims); // first: no ward goes down while channelling
        throw_if_stale();
        try {
            me.submit_gems(altars[a].pos);
            return true;
        } catch (const cambc::error&) {
        }
    }
    return false;
}

HopRoute hop_route(const World& world, Pathing& pathing, Safety& safety, int exclude)
{
    HopRoute best;
    const auto& map = world.map();
    const vec2 here = my_position();
    if (map.hops().empty() || !test(pathing.foot(), here)) return best;
    for (int h = 0; h < static_cast<int>(map.hops().size()); ++h) {
        const int a = map.hops()[h].altar;
        if (a == exclude || world.altars[a].enemy_lock || covered(world, map.altars[a].pos)) continue;
        const int walk = pathing.to_hop(h).at(here), inner = pathing.hop_landing_steps(h);
        if (walk == unreachable || inner == unreachable) continue;
        if (const int steps = walk + cambc::constants::tp_crystal_time + inner + recall_turns(world); steps < best.steps)
            best = {h, steps};
    }
    return best;
}

void take_hop(const World& world, Pathing& pathing, Safety& safety, int h)
{
    const auto& hop = world.map().hops()[h];
    if (test(hop.sources, my_position())) {
        auto targets = pathing.teleport_targets();
        targets &= hop.landings;
        const auto& field = pathing.to_altar(hop.altar);
        vec2 best{-1, -1};
        int best_steps = unreachable;
        for (const vec2 l : targets.positions())
            if (const int s = field.at(l); s < best_steps) best = l, best_steps = s;
        if (best.x >= 0) {
            throw_if_stale();
            try {
                // A teleport is posted as it starts, and holds room for its landing.
                if (!::comms::may_teleport()) return;
                if (cambc::self().consumables()[cambc::consumable_type::tp_crystal].use(best)) {
                    ::comms::teleported();
                    return;
                }
            } catch (const cambc::error&) {
            }
        }
    }
    step_safely(pathing, pathing.to_hop(h), safety);
}

[[gnu::flatten]] void bank_gems(World& world, Pathing& pathing, Safety& safety, Aims& aims, bool heal_step)
{
    if (retaining_gems(world, pathing)) return;
    world.throw_if_stale();
    if (submit_here(world, safety, aims)) return;
    const vec2 here = my_position();
    const auto& altars = world.map().altars;
    // A covered altar counts as altar_switch_steps farther.
    std::array<bool, 16> cover{};
    bool any_locked = false;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
        cover[static_cast<std::size_t>(a & 15)] = covered(world, altars[a].pos);
        any_locked |= world.altars[a].enemy_lock || cover[static_cast<std::size_t>(a & 15)];
    }
    // One cached field covers every altar; per-altar fields are needed only to skip locked ones.
    // Breaking a lock takes a turn per hit left, about a step each.
    int best = -1, best_steps = unreachable;
    if (any_locked) {
        for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
            // A tribute tile is within 1 of its altar: an altar this rules out needs no field.
            const int extra = cover[static_cast<std::size_t>(a & 15)] ? params::altar_switch_steps : 0;
            if (dist(here, altars[a].pos) - 1 + extra >= best_steps) continue;
            const auto& belief = world.altars[a];
            int steps = pathing.to_altar(a).at(here);
            if (steps == unreachable) continue;
            steps += extra;
            if (belief.enemy_lock) steps += belief.enemy_lock_hits > 0 ? belief.enemy_lock_hits : static_cast<int>(cambc::constants::altar_lock_hits);
            if (steps < best_steps) best = a, best_steps = steps;
        }
        any_locked = best >= 0;
    }
    // A pack we would retreat from stands in the way: around it within the usual detour, else
    // wait outside it until it leaves or a recall (recall_to_bank) takes the bag home.
    if (const auto* zone = pack_zone(world)) {
        if (any_locked && world.altars[best].enemy_lock && break_lock(world, best) && !world.me().facts().walk_and_attack_independent())
            return;
        if (pathing.step_towards(any_locked ? pathing.to_altar(best) : pathing.to_any_altar(), zone)) submit_here(world, safety, aims);
        return;
    }
    const int walk_steps = any_locked ? best_steps : pathing.to_any_altar().at(here);
    if (const auto hop = hop_route(world, pathing, safety); hop.hop >= 0 && hop.steps < walk_steps) {
        if (carries_crystal()) {
            take_hop(world, pathing, safety, hop.hop);
            return;
        }
    }
    const Field& field = any_locked ? pathing.to_altar(best) : pathing.to_any_altar();
    // A hole or altar line is crossed by the pathfinder's route (step_safely), when the dash saves enough.
    if (dash_towards(world, pathing, field) && submit_here(world, safety, aims)) return;
    if (any_locked && world.altars[best].enemy_lock && break_lock(world, best) && !world.me().facts().walk_and_attack_independent())
        return;
    if (heal_step && willow_bank_heal_step(world, pathing, safety, field)) {
        submit_here(world, safety, aims);
        return;
    }
    step_safely(pathing, field, safety);
    submit_here(world, safety, aims);
}

float HomeTrip::value(std::uint32_t gold_in) const
{ return heal + (gold_in >= short_gold ? emblem : 0.0f); }

float HomeTrip::rounds(int walk, int overlap, std::uint32_t gold_in) const
{
        const int arrive = std::max(0, channel - overlap) + hurt + from_spawn;
        if (from_spawn == unreachable || arrive > deadline) return static_cast<float>(walk);
        return std::min(static_cast<float>(walk), std::max(0.0f, static_cast<float>(arrive) - value(gold_in)));
    }

HomeTrip home_trip(const World& world, Pathing& pathing, int channel, bool wins)
{
    HomeTrip t{channel, pathing.to_any_altar().at(world.map().ally_spawn_centre), my_health() < my_max_health() ? 1 : 0,
               bag_rounds_left(world) - tribute_turns(my_gems())};
    if (wins || closing(world, pathing)) return t;
    t.heal = heal_rounds(world, my_max_health() - my_health(), spawn_steps());
    if (!may_shop(world)) return t;
    const auto& p = prices(world);
    const std::uint32_t gold = my_gold();
    t.short_gold = gold >= p.next.cost ? 0 : p.next.cost - gold;
    t.emblem = p.gain;
    return t;
}

int altar_here(const World& world, vec2 p)
{
    const auto& altars = world.map().altars;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a)
        if (!world.altars[a].enemy_lock && dist(p, altars[a].pos) <= cambc::constants::submit_gems_range) return a;
    return -1;
}

bool can_tribute_here(const World& world)
{ return my_gems() > 0 && altar_here(world, my_position()) >= 0; }

int carried_locks()
{ return static_cast<int>(cambc::self().consumables()[cambc::consumable_type::altar_lock].count()); }

int tribute_altar(const World& world, vec2 p)
{
    const auto& altars = world.map().altars;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a)
        if (dist(p, altars[a].pos) <= static_cast<int>(cambc::constants::submit_gems_range)) return a;
    return -1;
}

bool can_tribute_safely(const World& world, Pathing& pathing, Safety& safety, const Aims& aims)
{
    if (retaining_gems(world, pathing)) return false;
    if (!can_tribute_here(world)) return false;
    return tribute_ok(world, safety, aims, tribute_turns(my_gems()));
}

bool bag_bound_for_altar(const World& world, Pathing& pathing, Safety& safety)
{
    if (bankable_bag(world, pathing) == 0 || retaining_gems(world, pathing)) return false;
    return closing(world, pathing) || winning_bag(world) || !may_chain(world, safety);
}

bool may_chain(const World& world, Safety& safety)
{
    if (bag_at_stake(world) >= params::chain_bag_limit || winning_bag(world)) return false;
    return !safety.credible_enemy_may_hit_within(my_position(), params::pursuit_steps);
}

bool recall_to_bank(const World& world, Pathing& pathing, Safety& safety, const Aims& aims)
{
    if (!aims.banking) return false;
    const vec2 here = my_position();
    if (safety.threatened(here)) return false;
    // With no walk out (a crystal's pocket), the trip by way of spawn is the only one.
    const int walk = pathing.to_any_altar().at(here);
    if (home_trip(world, pathing, my_channel_time(), winning_bag(world)).rounds(walk, 0, 0) < static_cast<float>(walk)) return true;
    // Nor from home on foot: the stop buys the crystal a hop needs.
    return walk == unreachable && !carries_crystal() && can_buy_crystal() && hop_route(world, pathing, safety).hop >= 0;
}

void carry_bag(World& world, Pathing& pathing, Safety& safety, Aims& aims, bool attacked)
{
    const bool safe = can_tribute_safely(world, pathing, safety, aims);
    const bool close = closing(world, pathing);
    if (!safe && !close && !winning_bag(world) && chase(world, pathing, safety)) return;
    if (safe) {
        decision = 'B';
        aims.banking = true;
        bank_gems(world, pathing, safety, aims);
        return;
    }
    if (can_tribute_here(world)) {
        // Hit with nothing to hit back: waiting here only takes more.
        if (aims.damage > 0 && !attack_target(world)) {
            decision = 'R';
            pathing.set_guard(nullptr);
            dash_away(world, pathing, pathing.to_ally_spawn());
            retreat_step(world, pathing, safety, pathing.to_ally_spawn());
            return;
        }
        const vec2 here = cambc::self().position();
        const auto& altars = world.map().altars;
        const int at = altar_here(world, here);
        // How long they stay is unknown: wait unless another unlocked altar is nearer than
        // altar_switch_steps (bank_gems then walks there, this one counting as that much farther).
        int other_steps = carries_crystal() ? hop_route(world, pathing, safety, at).steps : unreachable;
        for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
            if (a == at || world.altars[a].enemy_lock || dist(here, altars[a].pos) - 1 >= other_steps) continue;
            other_steps = std::min<int>(other_steps, pathing.to_altar(a).at(here));
        }
        if (other_steps >= params::altar_switch_steps) {
            decision = 'W';
            return;
        }
    }
    decision = 'B';
    const bool walked = attacked && !world.me().facts().walk_and_attack_independent();
    aims.banking = close || walked || !may_chain(world, safety) || !farm(world, pathing, safety, aims);
    if (aims.banking) bank_gems(world, pathing, safety, aims); // a tribute can still start after a ranged attack
}

}
}
