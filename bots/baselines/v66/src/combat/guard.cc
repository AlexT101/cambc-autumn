// Where a step may go: the step guard against enemies acting before our next turn, and the pack
// zone to retreat from and keep out of.
#include "../bot_parts.h"

namespace aph {

namespace {

// Around awake camps and credible enemies when a way exists, else straight. Routes are replanned
// every turn, so only danger near us is worth the extra search.
void step_safely(const World& world, Pathing& pathing, const Field& field, Safety& safety) {
    if (!my_can_move()) return;
    bool moved;
    if (!safety.avoid_within(my_position(), vision_radius)) {
        moved = pathing.step_towards(field);
    } else {
        const auto& avoid = safety.avoid();
        moved = pathing.step_towards(field, &avoid) || pathing.step_towards(field);
    }
    if (!moved) breach(world, field);
}

// Our ground: no farther from our spawn than from theirs.
bool own_ground(const World& world, vec2 p) {
    const auto& map = world.map();
    const int us = map.from_ally_spawn().at(p), them = map.enemy_spawn_steps(p);
    return us == unreachable || them == unreachable || us <= them;
}

// The pack zone: the tiles within pack_radius of every member of an enemy subset (seen this round
// or last) that outmatches us and the allies near us, by health times damage a side. Only when we
// are hurt or carrying, or on our own ground. Retreat starts inside it, and every advance (farm,
// bank, chase) keeps out of it, so what made us retreat cannot pull us straight back in.
// It is held as one box per minimal outmatching subset; the board is drawn only when asked for.
constexpr int pack_radius = Strike::max_reach - 1;
constexpr int pack_members = 8;

struct PackBox {
    int x0, x1, y0, y1;
};
struct PackMember {
    vec2 pos;
    float health, damage;
};
struct PackZone {
    // What the boxes are worked out from, read by this round's first query that needs them.
    int round = -1;
    int n = 0; // 0: no pack can outmatch us
    std::array<PackMember, pack_members> members;
    float ours = 0;
    int boxed = -1; // the round the boxes were last worked out in
    int boxes = 0;
    std::array<PackBox, (1u << pack_members) - 1> box; // at most one per subset
    bool drawn = false;
    // Our health and bag as this round's first query read them: they can change during the turn
    // (a kill takes a bag).
    int frozen = -1;
    float health = 0, max_health = 0;
    int bag = 0;
};

PackZone& pack_zone_state(const World& world) {
    static PackZone pz;
    if (pz.frozen != world.round) {
        pz.frozen = world.round;
        pz.health = my_health();
        pz.max_health = my_max_health();
        pz.bag = bag_at_stake(world);
    }
    return pz;
}

PackZone& pack_members_of(const World& world) {
    auto& pz = pack_zone_state(world);
    if (pz.round == world.round) return pz;
    pz.round = world.round;
    pz.n = 0;
    const auto& map = world.map();
    const vec2 here = world.me().pos;
    const float health = pz.health;
    const bool hurt = health < params::hurt_health_fraction * pz.max_health || pz.bag >= params::brake_bag;
    // A pack in our half has come to fight there; healthy elsewhere, we came to fight.
    const bool home = own_ground(world, here);
    if (!hurt && !home) return pz;
    int n = 0;
    for (const auto& e : world.enemies)
        if (n < pack_members && e.alive && e.age(world.round) <= 1 && !test(map.near_enemy_spawn, e.pos))
            pz.members[static_cast<std::size_t>(n++)] = {e.pos, effective_hp(e), output(e)};
    if (n == 0) return pz;
    float our_health = 0, our_damage = 0;
    for (const auto& a : world.allies)
        if (a.alive && (a.is_self || (a.visible && dist(here, a.pos) <= params::pack_ally_radius))) {
            our_health += ((a.is_self ? health : a.health) + a.shield) / a.taken;
            our_damage += output(a);
        }
    pz.ours = (home ? params::home_retreat_ratio : params::hurt_retreat_ratio) * our_health * our_damage;
    pz.n = n;
    return pz;
}

PackZone& pack_boxes(const World& world) {
    auto& pz = pack_members_of(world);
    if (pz.boxed == pz.round) return pz;
    pz.boxed = pz.round;
    pz.boxes = 0;
    pz.drawn = false;
    const int n = pz.n;
    const auto& members = pz.members;
    const float ours = pz.ours;
    // Only minimal outmatching subsets: a superset's tiles lie within its subsets'.
    std::array<unsigned, 32> minimal;
    int m = 0;
    constexpr int r = pack_radius;
    // By mask, each subset's sums from those of the mask without its highest member, a smaller mask.
    struct Subset {
        float health, damage;
    };
    static std::array<Subset, 1u << pack_members> subsets;
    subsets[0] = {0, 0};
    for (unsigned mask = 1; mask < (1u << n); ++mask) {
        // A covered mask's supersets are covered too, so its sums are never read.
        bool covered = false;
        for (int k = 0; k < m && !covered; ++k) covered = (minimal[k] & mask) == minimal[k];
        if (covered) continue;
        const int top = 31 - __builtin_clz(mask);
        const auto& e = members[static_cast<std::size_t>(top)];
        const auto& rest = subsets[mask ^ (1u << top)];
        auto& sub = subsets[mask];
        sub = {rest.health + e.health, rest.damage + e.damage};
        if (sub.health * sub.damage <= ours) continue;
        if (m < static_cast<int>(minimal.size())) minimal[m++] = mask;
        // The box within r of every member.
        int x0 = -1 << 20, x1 = 1 << 20, y0 = -1 << 20, y1 = 1 << 20;
        for (unsigned left = mask; left; left &= left - 1) {
            const vec2 p = members[static_cast<std::size_t>(__builtin_ctz(left))].pos;
            x0 = std::max(x0, p.x - r), x1 = std::min(x1, p.x + r), y0 = std::max(y0, p.y - r), y1 = std::min(y1, p.y + r);
        }
        if (x0 > x1 || y0 > y1) continue;
        pz.box[pz.boxes++] = {x0, x1, y0, y1};
    }
    return pz;
}

// After a re-read of vision: the next query builds the boxes from what we see now.
void forget_pack_zone(const World& world) {
    auto& pz = pack_zone_state(world);
    pz.round = pz.boxed = -1;
}

bool in_pack_zone(const World& world, vec2 p) {
    // Each box lies within pack_radius of every member of its subset.
    bool near = false, recent = false;
    for (const auto& e : world.enemies)
        if (e.alive && e.age(world.round) <= 1)
            recent = true, near |= (static_cast<unsigned>(p.x - e.pos.x + pack_radius) <= 2u * pack_radius)
                                   & (static_cast<unsigned>(p.y - e.pos.y + pack_radius) <= 2u * pack_radius);
    if (!near) {
        if (recent) pack_zone_state(world); // a later query this round reads what we have now
        return false;
    }
    // In a box exactly when the members within pack_radius of p outmatch us: outmatching only grows
    // with members, in floats too, as the sums add in the boxes' order.
    const auto& pz = pack_members_of(world);
    float health = 0, damage = 0;
    for (int i = 0; i < pz.n; ++i)
        if (const auto& e = pz.members[static_cast<std::size_t>(i)]; dist(p, e.pos) <= pack_radius) health += e.health, damage += e.damage;
    return health * damage > pz.ours;
}

// Adds the tiles of a box inside the map as a few squares, overlapping at the far edges: a host
// square costs about what a single tile does, a whole-board operation far more.
void draw_box(bitboard& b, int x0, int x1, int y0, int y1) {
    const int side = std::min(x1 - x0, y1 - y0) / 2 * 2 + 1; // the largest odd side that fits
    if (side == 1) {
        for (int y = y0; y <= y1; ++y)
            for (int x = x0; x <= x1; ++x) set_tile(b, {x, y});
        return;
    }
    const int r = side / 2;
    for (int cy = y0 + r;; cy = std::min(cy + side, y1 - r)) {
        for (int cx = x0 + r;; cx = std::min(cx + side, x1 - r)) {
            draw_square(b, {cx, cy}, static_cast<float>(r));
            if (cx == x1 - r) break;
        }
        if (cy == y1 - r) break;
    }
}

const bitboard* pack_zone(const World& world) {
    static bitboard zone;
    auto& pz = pack_boxes(world);
    if (pz.boxes == 0) return nullptr;
    if (!pz.drawn) {
        pz.drawn = true;
        clear_board(zone);
        const int width = world.map().width, height = world.map().height;
        for (int i = 0; i < pz.boxes; ++i) {
            const auto& b = pz.box[i];
            const int x0 = std::max(b.x0, 0), x1 = std::min(b.x1, width - 1), y0 = std::max(b.y0, 0), y1 = std::min(b.y1, height - 1);
            if (x0 <= x1 && y0 <= y1) draw_box(zone, x0, x1, y0, y1);
        }
    }
    return &zone;
}

// pack_zone() holds every tile within r of p, worked out from its boxes.
bool pack_covers(const World& world, vec2 p, int r) {
    const auto& pz = pack_boxes(world);
    if (pz.boxes == 0) return false;
    const int x0 = std::max(0, p.x - r), x1 = std::min(world.map().width - 1, p.x + r);
    const int y0 = std::max(0, p.y - r), y1 = std::min(world.map().height - 1, p.y + r);
    for (int i = 0; i < pz.boxes; ++i)
        if (const auto& b = pz.box[i]; b.x0 <= x0 && x1 <= b.x1 && b.y0 <= y0 && y1 <= b.y1) return true;
    // Row by row, the boxes that hold the row's first tile not yet held.
    for (int y = y0; y <= y1; ++y) {
        int x = x0;
        for (bool grew = true; grew && x <= x1;) {
            grew = false;
            for (int i = 0; i < pz.boxes; ++i)
                if (const auto& b = pz.box[i]; b.y0 <= y && y <= b.y1 && b.x0 <= x && x <= b.x1) x = b.x1 + 1, grew = true;
        }
        if (x <= x1) return false;
    }
    return true;
}

// open_for_us as packed row-major bits, read without host calls; null if the export's layout is
// not the one expected.
const std::uint8_t* open_bits(const World& world) {
    static std::array<std::uint8_t, 100 * 100 / 8 + 8> bits;
    static int state = 0; // 1 packed, 2 not
    if (state == 0) {
        state = 2;
        const auto& map = world.map();
        const std::size_t size = bitboard::linear_buffer_size();
        if (size + 8 > bits.size() || map.open_for_us.is_empty()) return nullptr;
        map.open_for_us.export_linear_buffer({bits.data(), size});
        const vec2 probe = first_tile(map.open_for_us);
        const int i = probe.x + probe.y * map.width;
        if (bits[static_cast<std::size_t>(i >> 3)] >> (i & 7) & 1) state = 1;
    }
    return state == 1 ? bits.data() : nullptr;
}

// step_guard's foes: the seen enemies that may strike within `radius` of us, and how hard. `bound`
// is by distance alone and never below `exposure`, the exact blows, which only the foes in its mask
// can add to; only those `reaching` a step or dash can be in it. A tile no worse than ours is as
// safe as ours.
struct GuardFoes {
    Safety& safety;
    std::array<const ChampionBelief*, 8> foes;
    std::array<const Strike*, 8> strikes;
    Unwritten<vec2, 8> positions;
    Unwritten<const Reach*, 8> reaches; // looked up on first use
    int n = 0;
    unsigned reaching = 0;
    unsigned teleporting = 0; // acting from the teleport's destination, as Safety::blow() has it
    unsigned here_mask = 0;
    float here_damage = 0;

    GuardFoes(const World& world, Safety& safety, vec2 here, int radius) : safety(safety) {
        auto& at = positions.a;
        for (auto left = safety.seen_enemies(); left; left &= left - 1) {
            const auto& e = world.enemies[static_cast<std::size_t>(std::countr_zero(left))];
            const bool lands = e.teleport_pending() && in_bounds(e.tp_dest);
            const vec2 from = lands ? e.tp_dest : e.pos;
            if (n < static_cast<int>(foes.size()) && in_square(here, from, Strike::max_reach + dash_range) && safety.strike_of(e).reach >= 0)
                teleporting |= static_cast<unsigned>(lands) << n, strikes[n] = &safety.strike_of(e), at[n] = from, reaches.a[n] = nullptr, foes[n++] = &e;
        }
        for (int k = 0; k < n; ++k)
            if (in_square(here, at[k], strikes[k]->reach + radius)) reaching |= 1u << k;
    }
    [[gnu::always_inline]] unsigned bound(vec2 p, float& damage) const {
        unsigned mask = 0;
        damage = 0;
        for (unsigned left = reaching; left; left &= left - 1)
            if (const int k = std::countr_zero(left), d = dist(p, positions.a[k]); d <= strikes[k]->reach) mask |= 1u << k, damage += strikes[k]->damage[d];
        return mask;
    }
    // bound() over the square of `radius` around `here`, cell (dx + radius) + (dy + radius) * side:
    // `cells[k]` the cells within foe k's reach, `any` their union.
    struct Window {
        std::array<std::uint32_t, 8> cells;
        std::uint32_t any = 0;
    };
    Window window(vec2 here, int radius) const {
        Window w;
        const int side = 2 * radius + 1;
        for (unsigned left = reaching; left; left &= left - 1) {
            const int k = std::countr_zero(left), r = strikes[k]->reach;
            const vec2 o = positions.a[k] - here;
            const int x0 = std::max(-radius, o.x - r), x1 = std::min(radius, o.x + r), y0 = std::max(-radius, o.y - r), y1 = std::min(radius, o.y + r);
            std::uint32_t cells = 0;
            if (x0 <= x1) {
                const std::uint32_t row = ((1u << (x1 - x0 + 1)) - 1) << (x0 + radius);
                for (int y = y0; y <= y1; ++y) cells |= row << ((y + radius) * side);
            }
            w.cells[static_cast<std::size_t>(k)] = cells;
            w.any |= cells;
        }
        return w;
    }
    // no_worse(bound(p)) for cell c of `w`, damage summed only when it decides.
    [[gnu::always_inline]] bool no_worse_at(const Window& w, int c, vec2 p, unsigned& mask) const {
        mask = 0;
        for (unsigned left = reaching; left; left &= left - 1) {
            const int k = std::countr_zero(left);
            mask |= (w.cells[static_cast<std::size_t>(k)] >> c & 1u) << k;
        }
        if (mask == 0) return true;
        if (mask & ~here_mask) return false;
        float damage = 0;
        for (unsigned left = mask; left; left &= left - 1) {
            const int k = std::countr_zero(left);
            damage += strikes[k]->damage[dist(p, positions.a[k])];
        }
        return damage <= here_damage;
    }
    // Safety::blow() for the foes in `near`: by Strike for a teleporter, as Reach is built at e.pos.
    unsigned exposure(vec2 p, unsigned near, float& damage) {
        unsigned mask = 0;
        damage = 0;
        for (; near; near &= near - 1) {
            const int k = std::countr_zero(near);
            Blow b;
            if (teleporting >> k & 1) {
                b = strikes[k]->blow(dist(p, positions.a[k]));
            } else {
                auto& reach = reaches.a[k];
                if (!reach) reach = &safety.reach_of(*foes[k]);
                b = reach->at(p);
            }
            if (b.hits) mask |= 1u << k, damage += b.damage;
        }
        return mask;
    }
    void expose_here(vec2 here) {
        float damage;
        here_mask = exposure(here, bound(here, damage), here_damage);
    }
    bool no_worse(unsigned mask, float damage) const { return mask == 0 || ((mask & ~here_mask) == 0 && damage <= here_damage); }
    // The fight key bits of the foes in `mask`.
    std::uint32_t visible_of(unsigned mask) const {
        std::uint32_t visible = 0;
        for (; mask; mask &= mask - 1) visible |= 1u << (16 + foes[std::countr_zero(mask)]->index);
        return visible;
    }
};

// The tiles step_guard could guard by its first test alone, null if none: the plan search works
// the guard out only once one of them would count.
const bitboard* step_guard_cover(const World& world, Safety& safety, vec2 here, int radius) {
    world.throw_if_stale();
    if (!enemy_seen(world)) return nullptr;
    GuardFoes g{world, safety, here, radius};
    if (g.reaching == 0) return nullptr;
    static bitboard cover{cambc::uninitialized};
    g.expose_here(here);
    const auto& open = world.map().open_for_us;
    const auto w = g.window(here, radius);
    bool any = false;
    for (int dy = -radius, c = 0; dy <= radius; ++dy)
        for (int dx = -radius; dx <= radius; ++dx, ++c) {
            if (!(w.any >> c & 1)) continue;
            const vec2 q{here.x + dx, here.y + dy};
            if ((dx == 0 && dy == 0) || !in_bounds(q) || !test(open, q)) continue;
            if (unsigned near; g.no_worse_at(w, c, q, near)) continue;
            if (!any) clear_board(cover), any = true;
            set_tile(cover, q);
        }
    return any ? &cover : nullptr;
}

// The tiles a step (or a ready dash) could end on that want_home would leave at once: stopping
// there hands the enemy the first strike. Cassi and Issac also keep off tiles where one would fall.
const bitboard* step_guard(const World& world, Safety& safety, vec2 here, int radius) {
    world.throw_if_stale();
    if (!enemy_seen(world)) return nullptr;
    static bitboard guard{cambc::uninitialized};
    GuardFoes g{world, safety, here, radius};
    const int n = g.n;
    if (n == 0) return nullptr;
    // Placing the tiles costs up to tens of thousands: give up as the fights would, counting the
    // costliest placing lately.
    auto& costliest = step_guard_costliest();
    if (g.reaching == 0) {
        costliest -= costliest / 8;
        return nullptr;
    }
    const auto floor = safety.fight_cost_estimate() + act_reserve;
    if (!fuel_ok(floor + costliest)) {
        note_shortcut("step-guard-entry");
        return nullptr;
    }
    const auto placing = fuel();
    const auto note_placing = [&] {
        if (const auto now = fuel(); now <= placing) costliest = std::max(placing - now, costliest - costliest / 8);
    };
    g.expose_here(here);
    const bool linked = partner(world) != nullptr;
    const auto& open = world.map().open_for_us;
    const auto* open_packed = open_bits(world);
    const int width = world.map().width;
    // Unless the list filled up, the foes hold every visible threat that could hit a tile this near.
    const bool all_listed = n < static_cast<int>(g.foes.size());
    // The tiles more exposed than ours by `bound`, and who would fight on each by it.
    Unwritten<std::pair<vec2, std::uint32_t>, 24> tiles;
    auto& exposed = tiles.a;
    std::array<unsigned, 24> nears;
    Unwritten<vec2, 24> spots; // all_listed: the tiles, whose keys are worked out only past the first union
    int m = 0;
    std::uint32_t enemies = 0, allies = ~0u;
    const auto w = g.window(here, radius);
    for (int dy = -radius, c = 0; dy <= radius; ++dy)
        for (int dx = -radius; dx <= radius; ++dx, ++c) {
            if (!(w.any >> c & 1)) continue;
            const vec2 q{here.x + dx, here.y + dy};
            if ((dx == 0 && dy == 0) || !in_bounds(q)) continue;
            if (const int i = q.x + q.y * width; open_packed ? !(open_packed[i >> 3] >> (i & 7) & 1) : !test(open, q)) continue;
            unsigned near;
            if (g.no_worse_at(w, c, q, near)) continue;
            if (all_listed) {
                nears[m] = near;
                spots.a[m] = q;
                exposed[m++] = {q, 0};
                enemies |= g.visible_of(near);
                allies &= safety.fight_allies(q);
                continue;
            }
            const auto key = safety.fight_key(q);
            if (key == Safety::no_fight) continue;
            nears[m] = near;
            exposed[m++] = {q, key};
            enemies |= key & 0xFFFF0000u;
            allies &= key & 0xFFFFu;
        }
    if (m == 0) {
        note_placing();
        return nullptr;
    }
    if (all_listed && m > 1) enemies |= safety.fight_enemies_any(spots.a.data(), m);
    // A fight only gets worse with more enemies or fewer allies: one we win settles those it
    // covers, one we lose those that cover it, and one not lost the `lost` of those it covers.
    const auto covers = [](std::uint32_t worse, std::uint32_t key) {
        return (key & ~worse & 0xFFFF0000u) == 0 && (worse & ~key & 0xFFFFu) == 0;
    };
    struct Settled {
        std::uint32_t key;
        bool won, lost; // won: neither lost nor do we fall
    };
    std::array<Settled, 26> settled; // one a tile, and the two unions
    int s = 0;
    // 0 won, 1 lost, 2 not lost (self_falls unknown), -1 unsettled.
    const auto settle = [&](std::uint32_t key) {
        int not_lost = -1;
        for (int i = 0; i < s; ++i) {
            if (settled[i].won && covers(settled[i].key, key)) return 0;
            if (settled[i].lost && covers(key, settled[i].key)) return 1;
            if (!settled[i].lost && covers(settled[i].key, key)) not_lost = 2;
        }
        return not_lost;
    };
    // False if fuel ran short.
    const auto simulate = [&](std::uint32_t key, bool& lost, bool& falls) {
        const auto* known = safety.known_fight_of(key);
        if (!known && !fuel_ok(safety.fight_cost_estimate() + act_reserve)) {
            note_shortcut("step-guard-sim");
            return false;
        }
        if (known) {
            lost = known->lost;
            falls = known->self_falls;
        } else {
            const auto t = safety.new_fight(key);
            lost = t.lost;
            falls = t.self_falls;
        }
        if (s < static_cast<int>(settled.size())) settled[s++] = {key, !lost && !falls, lost};
        return true;
    };
    const auto outcome = [&](std::uint32_t key, bool& lost, bool& falls) {
        if (const int k = settle(key); k == 0 || k == 1) {
            lost = falls = k == 1;
            return true;
        }
        return simulate(key, lost, falls);
    };
    bool lost = false, falls = false;
    // Every enemy that could hit any of them against the allies at all of them first: if we win
    // even that, no tile needs guarding. Each bound holds its tile's exact exposure, so a win
    // settles the exact tiles before Reach is asked.
    if (m > 1) {
        if (!outcome(enemies | allies, lost, falls)) return nullptr;
        if (!lost && !falls) {
            note_placing();
            return nullptr;
        }
    }
    // The exact exposures.
    const int bounded = m;
    m = 0;
    enemies = 0, allies = ~0u;
    for (int i = 0; i < bounded; ++i) {
        // An exact look can query Reach on a new tile, ~1000 a foe.
        if (!fuel_ok(floor + 1000 * static_cast<std::uint64_t>(n))) {
            note_shortcut("step-guard-look");
            return nullptr;
        }
        const auto [q, bound_key] = exposed[i];
        float damage = 0;
        const unsigned mask = g.exposure(q, nears[i], damage);
        if (g.no_worse(mask, damage)) continue;
        const auto key = all_listed ? (safety.fight_key_with(q, g.visible_of(nears[i])) & ~g.visible_of(nears[i])) | g.visible_of(mask) : bound_key;
        exposed[m++] = {q, key};
        enemies |= key & 0xFFFF0000u;
        allies &= key & 0xFFFFu;
    }
    note_placing();
    if (m == 0) return nullptr;
    if (m > 1 && (!outcome(enemies | allies, lost, falls) || (!lost && !falls))) return nullptr;
    // Then the fewest enemies first, so that lost fights settle the larger ones.
    std::sort(exposed.begin(), exposed.begin() + m, [](const auto& a, const auto& b) {
        return std::popcount(a.second >> 16) < std::popcount(b.second >> 16);
    });
    bool any = false;
    for (int i = 0; i < m; ++i) {
        const auto [q, key] = exposed[i];
        const int k = settle(key);
        // Not lost settles q unless a fall there counts.
        if (k == 2 && !linked && !safety.lethal(q)) continue;
        if (k == 0 || k == 1) lost = falls = k == 1;
        else if (!simulate(key, lost, falls)) return any ? &guard : nullptr;
        if (lost || (falls && (linked || safety.lethal(q)))) {
            if (!any) clear_board(guard), any = true;
            set_tile(guard, q);
        }
    }
    return any ? &guard : nullptr;
}

// step_guard from where we stand, worked out when a step or dash first needs it.
static_assert([] {
    for (const auto& f : champion_table)
        if (f.heals() && f.has_dash()) return false;
    return true;
}()); // the healer's guard covers single steps only
void guard_steps(const World& world, Pathing& pathing, Safety& safety) {
    // Willow holds no fight: every tile want_home would leave is guarded. With no enemy in reach of
    // a step, an empty board, not null: see_again works out a held guard again.
    if (world.me().facts().heals()) {
        pathing.defer_guard(
            [](const World& w, Safety& s, vec2 here, int) {
                static const bitboard none;
                return s.credible_enemy_may_hit_within(here, 1) ? &stations(w, s, here).guard : &none;
            },
            safety, my_position(), 1);
        return;
    }
    const auto& self = world.me();
    int radius = 1;
    for (int s = 0; s < 2; ++s)
        if (self.facts().abilities[s].kind == AbilityKind::dash && self.ability_ready(s, world.round) && my_can_cast()) radius = dash_range;
    pathing.defer_guard(step_guard, safety, my_position(), radius, step_guard_cover);
}

} // namespace

} // namespace aph
