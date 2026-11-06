// Where a step may go: the step guard against enemies acting before our next turn, and the pack
// zone to retreat from and keep out of.
#include "../bot_parts.h"

namespace aph {

namespace {

// Around awake camps and credible enemies when a way exists, else straight. Routes are replanned
// every turn, so only danger near us is worth the extra search.
void step_safely(const World& world, Pathing& pathing, const Field& field, Safety& safety) {
    // With the walk spent, a travel dash may still go.
    const bool walks = my_can_move();
    if (!walks && !my_can_cast()) return;
    bool moved;
    const vec2 here = my_position();
    const bool near = safety.avoid_within(here, vision_radius);
    if (!near) {
        moved = pathing.step_towards(field);
    } else {
        const auto& avoid = safety.avoid();
        moved = pathing.step_towards(field, &avoid) || pathing.step_towards(field);
    }
    if (moved || !walks || breach(world, field)) return;
    if (field.at(here) != 0) pathing.leave_respawning(near ? &safety.avoid() : nullptr);
}

// Our ground: no farther from our spawn than from theirs.
bool own_ground(const World& world, vec2 p) {
    const auto& map = world.map();
    const int us = map.from_ally_spawn().at(p), them = map.enemy_spawn_steps(p);
    return us == unreachable || them == unreachable || us <= them;
}

// The pack zone: the tiles within pack_radius of every member of an enemy subset that outmatches us
// and the allies near us, by health times damage a side. Only when we are hurt or carrying, or on our
// own ground. Retreat starts inside it, and every advance (farm, bank, chase) keeps out of it, so what
// made us retreat cannot pull us straight back in. A member in sight stands on its tile; one out of
// sight, while Safety counts it (credible_unseen), on any of its possible tiles off its spawn.
// It is held as one box per minimal outmatching subset, an unseen member's box around its tiles;
// the board is drawn only when asked for.
constexpr int pack_radius = Strike::max_reach - 1;
constexpr int pack_members = 8;

struct PackBox {
    int x0, x1, y0, y1;
};
struct PackMember {
    int x0, x1, y0, y1; // where it may stand
    float health, damage;
    int enemy;
};
// Within r of anywhere m may stand.
[[gnu::always_inline]] inline bool near_member(vec2 p, const PackMember& m, int r) {
    return (static_cast<unsigned>(p.x - m.x0 + r) <= static_cast<unsigned>(m.x1 - m.x0 + 2 * r))
           & (static_cast<unsigned>(p.y - m.y0 + r) <= static_cast<unsigned>(m.y1 - m.y0 + 2 * r));
}
// The box around an unseen enemy's possible tiles off its spawn; false if none. A credible set holds
// at most 2 (2 max_reach + 1)^2 tiles (unseen_weight).
bool possible_box(const World& world, const ChampionBelief& e, PackMember& m) {
    static bitboard off{cambc::uninitialized};
    copy_into(e.possible, off);
    drop(off, world.map().near_enemy_spawn);
    constexpr int side = 2 * Strike::max_reach + 1;
    const Tiles<2 * side * side> tiles{off};
    if (tiles.empty()) return false;
    m.x0 = m.y0 = 1 << 20, m.x1 = m.y1 = -(1 << 20);
    for (const vec2 t : tiles) m.x0 = std::min(m.x0, t.x), m.x1 = std::max(m.x1, t.x), m.y0 = std::min(m.y0, t.y), m.y1 = std::max(m.y1, t.y);
    return true;
}
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

PackZone& pack_members_of(const World& world, Safety& safety) {
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
    for (const auto& e : world.enemies) {
        if (n == pack_members || !e.alive) continue;
        auto& m = pz.members[static_cast<std::size_t>(n)];
        if (e.visible) {
            if (test(map.near_enemy_spawn, e.pos)) continue;
            m.x0 = m.x1 = e.pos.x, m.y0 = m.y1 = e.pos.y;
        } else if (!safety.credible_unseen(e) || !possible_box(world, e, m)) {
            continue;
        }
        m.health = effective_hp(e), m.damage = output(e), m.enemy = e.index;
        ++n;
    }
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

PackZone& pack_boxes(const World& world, Safety& safety) {
    auto& pz = pack_members_of(world, safety);
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
            const auto& b = members[static_cast<std::size_t>(__builtin_ctz(left))];
            x0 = std::max(x0, b.x0 - r), x1 = std::min(x1, b.x1 + r), y0 = std::max(y0, b.y0 - r), y1 = std::min(y1, b.y1 + r);
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

// The live enemies (bits by index) that may stand within r of p: in sight by their tile, out of sight
// by their possible tiles. Before the members, which cost more.
std::uint32_t may_be_near(const World& world, Safety& safety, vec2 p, int r) {
    std::uint32_t out = 0;
    for (auto left = safety.live_enemies(); left; left &= left - 1) {
        const auto& e = world.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (e.visible ? dist(p, e.pos) <= r : possible_within(e, p, r)) out |= 1u << e.index;
    }
    return out;
}

// The members that may stand within r of p, among `near` (may_be_near), outmatch us.
bool outmatch_near(const World& world, const PackZone& pz, std::uint32_t near, vec2 p, int r) {
    float health = 0, damage = 0;
    for (int i = 0; i < pz.n; ++i)
        if (const auto& m = pz.members[static_cast<std::size_t>(i)]; (near >> m.enemy & 1) && (world.enemies[static_cast<std::size_t>(m.enemy)].visible || near_member(p, m, r)))
            health += m.health, damage += m.damage;
    return pz.n > 0 && health * damage > pz.ours;
}

bool in_pack_zone(const World& world, Safety& safety, vec2 p) {
    if (!safety.live_enemies()) return false;
    const std::uint32_t near = may_be_near(world, safety, p, pack_radius);
    if (!near) {
        pack_zone_state(world); // a later query this round reads what we have now
        return false;
    }
    // Within a box when the members within pack_radius of p outmatch us: outmatching only grows with
    // members, in floats too, as the sums add in the boxes' order. An unseen member's box holds more
    // than its tiles, so the zone may too.
    return outmatch_near(world, pack_members_of(world, safety), near, p, pack_radius);
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

const bitboard* pack_zone(const World& world, Safety& safety) {
    static bitboard zone;
    auto& pz = pack_boxes(world, safety);
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
bool pack_covers(const World& world, Safety& safety, vec2 p, int r) {
    const auto& pz = pack_boxes(world, safety);
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

// The cover's first pass, kept for step_guard while GuardInputsHeld: its foes and the tiles past
// no_worse_at, with their nears, in step_guard's order.
struct FirstPass {
    bool held = false, valid = false;
    vec2 here;
    int radius = 0, m = 0;
    std::optional<GuardFoes> g;
    std::array<vec2, 24> tiles;
    std::array<unsigned, 24> nears;
};
FirstPass first_pass;

// The tiles step_guard could guard by its first test alone, null if none: the plan search works
// the guard out only once one of them would count.
const bitboard* step_guard_cover(const World& world, Safety& safety, vec2 here, int radius) {
    world.throw_if_stale();
    if (!enemy_seen(world)) return nullptr;
    auto& fp = first_pass;
    fp.valid = false;
    std::optional<GuardFoes> own;
    GuardFoes& g = fp.held ? fp.g.emplace(world, safety, here, radius) : own.emplace(world, safety, here, radius);
    if (g.reaching == 0) return nullptr;
    static bitboard cover{cambc::uninitialized};
    g.expose_here(here);
    int m = 0;
    const auto& open = world.map().open_for_us;
    const auto* open_packed = open_bits(world);
    const int width = world.map().width;
    const auto w = g.window(here, radius);
    bool any = false;
    for (int dy = -radius, c = 0; dy <= radius; ++dy)
        for (int dx = -radius; dx <= radius; ++dx, ++c) {
            if (!(w.any >> c & 1)) continue;
            const vec2 q{here.x + dx, here.y + dy};
            if ((dx == 0 && dy == 0) || !in_bounds(q)) continue;
            if (const int i = q.x + q.y * width; open_packed ? !(open_packed[i >> 3] >> (i & 7) & 1) : !test(open, q)) continue;
            unsigned near;
            if (g.no_worse_at(w, c, q, near)) continue;
            if (!any) clear_board(cover), any = true;
            set_tile(cover, q);
            fp.tiles[m] = q, fp.nears[m++] = near;
        }
    if (fp.held) fp.valid = true, fp.here = here, fp.radius = radius, fp.m = m;
    return any ? &cover : nullptr;
}

// The tiles a step (or a ready dash) could end on that want_home would leave at once: stopping
// there hands the enemy the first strike. Cassi and Issac also keep off tiles where one would fall.
const bitboard* step_guard(const World& world, Safety& safety, vec2 here, int radius) {
    world.throw_if_stale();
    if (!enemy_seen(world)) return nullptr;
    static bitboard guard{cambc::uninitialized};
    auto& fp = first_pass;
    const bool shared = fp.held && fp.valid && fp.here == here && fp.radius == radius;
    std::optional<GuardFoes> own;
    GuardFoes& g = shared ? *fp.g : own.emplace(world, safety, here, radius);
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
        // Else one dear placing keeps the guard off for as long as enemies stay near.
        costliest -= costliest / 8;
        return nullptr;
    }
    const auto placing = fuel();
    const auto note_placing = [&] {
        if (const auto now = fuel(); now <= placing) costliest = std::max(placing - now, costliest - costliest / 8);
    };
    if (!shared) g.expose_here(here);
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
    unsigned any_near = 0;
    vec2 lo{here.x + radius, here.y + radius}, hi{here.x - radius, here.y - radius}; // the spots' bounding box
    const auto exposed_at = [&](vec2 q, unsigned near) __attribute__((always_inline)) {
        if (all_listed) {
            nears[m] = near;
            spots.a[m] = q;
            exposed[m++] = {q, 0};
            any_near |= near;
            lo = {std::min(lo.x, q.x), std::min(lo.y, q.y)}, hi = {std::max(hi.x, q.x), std::max(hi.y, q.y)};
            return;
        }
        const auto key = safety.fight_key(q);
        if (key == Safety::no_fight) return;
        nears[m] = near;
        exposed[m++] = {q, key};
        enemies |= key & 0xFFFF0000u;
        allies &= key & 0xFFFFu;
    };
    if (shared) {
        for (int i = 0; i < fp.m; ++i) exposed_at(fp.tiles[i], fp.nears[i]);
    } else {
        const auto w = g.window(here, radius);
        for (int dy = -radius, c = 0; dy <= radius; ++dy)
            for (int dx = -radius; dx <= radius; ++dx, ++c) {
                if (!(w.any >> c & 1)) continue;
                const vec2 q{here.x + dx, here.y + dy};
                if ((dx == 0 && dy == 0) || !in_bounds(q)) continue;
                if (const int i = q.x + q.y * width; open_packed ? !(open_packed[i >> 3] >> (i & 7) & 1) : !test(open, q)) continue;
                unsigned near;
                if (g.no_worse_at(w, c, q, near)) continue;
                exposed_at(q, near);
            }
    }
    if (m == 0) {
        note_placing();
        return nullptr;
    }
    // all_listed: the enemies beyond the foes (unseen, or losing a turn) that hit any of the tiles,
    // ~0u if not looked for. With none, fight_key_with() adds only the allies to a tile's foes.
    std::uint32_t others = ~0u;
    if (all_listed) {
        // An ally's fight square holds every spot exactly when it holds their box's two corners.
        enemies = g.visible_of(any_near);
        allies = safety.fight_allies(lo) & safety.fight_allies(hi);
        if (m > 1) enemies |= others = safety.fight_enemies_any(spots.a.data(), m);
    }
    // A fight only gets worse with more enemies or fewer allies: one we win settles those it
    // covers, one we lose those that cover it, and one not lost the `lost` of those it covers with
    // the same enemies (an extra enemy we fell first can keep our own later fall from losing it).
    // By the same token a lost fight can over-settle those with extra enemies: kept, as it only guards more.
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
            if (!settled[i].lost && covers(settled[i].key, key) && ((settled[i].key ^ key) & 0xFFFF0000u) == 0) not_lost = 2;
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
        const auto key = !all_listed ? bound_key
                         : others == 0 ? safety.fight_allies(q) | g.visible_of(mask)
                                       : (safety.fight_key_with(q, g.visible_of(nears[i])) & ~g.visible_of(nears[i])) | g.visible_of(mask);
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
    if constexpr (fish::use_guard) {
        pathing.defer_guard(fishc::step_guard, safety, my_position(), 1);
        return;
    }
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

// The work's steps (bank, shop, contest, siege, farm and its pick-ups) end on no tile beside us that
// want_home would send us back from at once by where it is: beyond the strikes step_guard prices,
// drawn_home there (a pack's zone, a recall line above our health). A hold that outlasts
// what can reach it (hold_outlasts) may be stepped or dashed onto even against the strikes, as
// want_home stays on one. Stands lost only to pursuers are left out: pricing them for every tile
// beside us cost a fight simulation most turns near enemies and ~2.3x the out-of-fuel turns, for no
// gain measured (EXPERIMENTS).
struct WorkGuard {
    Pathing* pathing = nullptr;
    float damage = 0;           // Memory::damage
    int radius = 1;
    bool strikes_known = false; // `strikes` is step_guard's from our tile and radius, worked out already
    const bitboard* strikes = nullptr;
};
WorkGuard work_guard_inputs;

// What the work guard reads alike for every tile beside ours: whether any of them can be drawn home.
// Below recall_health_fraction a recall line may be above us; a pack's zone needs members near.
bool may_draw_home(const World& world, Safety& safety, vec2 here) {
    if (my_health() < params::recall_health_fraction * my_max_health()) return true;
    if (!safety.live_enemies()) return false;
    const std::uint32_t near = may_be_near(world, safety, here, pack_radius + 1);
    // The members within reach of any tile beside us: fewer never outmatch where these do not (in floats too).
    return near && outmatch_near(world, pack_members_of(world, safety), near, here, pack_radius + 1);
}

// The tiles beside us that want_home's drawn_home would send us back from (a hold that outlasts them
// aside), bit i for directions[i]; worked out once a turn and tile, for the guard and its cover.
unsigned keep_out(const World& world, Pathing& pathing, Safety& safety, vec2 here, float damage) {
    static struct {
        int round = -1;
        std::uint32_t observations = 0;
        vec2 here{-1, -1};
        float health = 0;
        unsigned tiles = 0;
    } made;
    const float health = my_health();
    if (made.round == world.round && made.observations == world.observations && made.here == here && made.health == health) return made.tiles;
    made.round = world.round, made.observations = world.observations, made.here = here, made.health = health, made.tiles = 0;
    if (!may_draw_home(world, safety, here)) return 0;
    const auto& open = world.map().open_for_us;
    for (int i = 0; i < 8; ++i) {
        const vec2 q = here + directions[i];
        // want_home never leaves our spawn, which heals us at the turn end.
        if (!in_bounds(q) || !test(open, q) || test(world.map().ally_spawn, q)) continue;
        if (drawn_home_at(world, pathing, safety, q, damage)) made.tiles |= 1u << i;
    }
    return made.tiles;
}

const bitboard* work_guard(const World& world, Safety& safety, vec2 here, int radius) {
    const auto& in = work_guard_inputs;
    auto& pathing = *in.pathing;
    const bitboard* strikes = in.strikes_known ? in.strikes : step_guard(world, safety, here, radius);
    static bitboard out{cambc::uninitialized};
    bool copied = false;
    const auto edit = [&] {
        if (copied) return;
        copied = true;
        if (strikes) copy_into(*strikes, out);
        else clear_board(out);
    };
    if (strikes)
        for (int dy = -radius; dy <= radius; ++dy)
            for (int dx = -radius; dx <= radius; ++dx)
                if (const vec2 q{here.x + dx, here.y + dy}; in_bounds(q) && test(*strikes, q))
                    if (const int rounds = hold_rounds(world, pathing, q); rounds >= 0 && hold_outlasts(safety, in.damage, q, rounds))
                        edit(), set_tile(out, q, false);
    const unsigned kept = keep_out(world, pathing, safety, here, in.damage);
    for (unsigned left = kept; left; left &= left - 1) edit(), set_tile(out, here + directions[std::countr_zero(left)]);
    if (!copied) return strikes;
    return kept || !out.is_empty() ? &out : nullptr;
}

// work_guard's cover: step_guard's, and the tiles keep_out sets.
const bitboard* work_cover(const World& world, Safety& safety, vec2 here, int radius) {
    const auto& in = work_guard_inputs;
    const bitboard* strikes = in.strikes_known ? in.strikes : step_guard_cover(world, safety, here, radius);
    const unsigned kept = keep_out(world, *in.pathing, safety, here, in.damage);
    if (!kept) return strikes;
    static bitboard cover{cambc::uninitialized};
    if (strikes) copy_into(*strikes, cover);
    else clear_board(cover);
    for (unsigned left = kept; left; left &= left - 1) set_tile(cover, here + directions[std::countr_zero(left)]);
    return &cover;
}

// A chase that worked out the step guard from where we still stand: the work guard reads it.
void strike_guard_known(const Pathing& pathing, vec2 here) {
    if (const auto held = pathing.held_guard(); !held.fn && held.here == here && held.radius >= work_guard_inputs.radius)
        work_guard_inputs.strikes_known = true, work_guard_inputs.strikes = held.guard;
}

// After the strike search, the work guard in place of the step guard (guard_steps).
void guard_work(const World& world, Pathing& pathing, Safety& safety, float damage) {
    if constexpr (fish::use_guard) {
        pathing.defer_guard(fishc::step_guard, safety, my_position(), 1);
        return;
    }
    if (world.me().facts().heals()) return; // Willow keeps its stations' guard (support.cc)
    const auto& self = world.me();
    int radius = 1;
    for (int s = 0; s < 2; ++s)
        if (self.facts().abilities[s].kind == AbilityKind::dash && self.ability_ready(s, world.round) && my_can_cast()) radius = dash_range;
    // A step guard held from a smaller radius misses the farther dash landings.
    const auto held = pathing.held_guard();
    const bool known = !held.fn && held.radius >= radius;
    work_guard_inputs = {&pathing, damage, radius, known, known ? held.guard : nullptr};
    pathing.defer_guard(work_guard, safety, my_position(), radius, work_cover);
}

} // namespace

GuardInputsHeld::GuardInputsHeld() { first_pass.held = true, first_pass.valid = false; }
GuardInputsHeld::~GuardInputsHeld() { release(); }
void GuardInputsHeld::release() { first_pass.held = first_pass.valid = false; }

} // namespace aph
