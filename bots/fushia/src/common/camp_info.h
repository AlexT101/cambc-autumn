#pragma once
#include "bb.h"
#include "channel.h"
#include "globals.h"
#include "map_info.h"
#include "types.h"
#include <algorithm>
#include <cambc.h>
#include <span>
#include <vector>

// fixed facts (init), what we last saw (start_turn)
namespace camp_info {
    // numbered as the engine numbers it
    enum class group_state : u8 { unknown, alive, reward, respawning };

    // golem is the last camp_type
    inline constexpr i32 kind_count = i32(cambc::camp_type::golem) + 1;

    // Monsters never move.
    struct monster {
        vec2 pos;
        u16 cell;  // pos's index in a distance field
        u16 group; // index in groups
        u32 id;    // engine id
        cambc::camp_type kind;
    };

    struct group {
        // fixed for the game
        u32 id;                // engine id
        u16 first, count;      // monsters[first, first + count)
        u16 kinds[kind_count]; // monsters per camp_type
        u16 gold, gems;        // a capture's pay
        u32 max_hp;            // summed
        u16 strength;          // hits a round, summed
        u8 range;              // longest
        u16 respawn;           // rounds from payout to alive

        // as last seen
        group_state state = group_state::unknown;
        i32 back = 0;  // respawning: the round it's back
        i32 read = -1; // round last read
    };

    inline cambc::camp_stats stats[kind_count]; // by camp_type; camps don't grow
    inline i32 paid_group = -1, paid_round = 0; // a payout new to us, for the team (comms)
    inline std::vector<group> groups;
    inline std::vector<monster> monsters; // each group's together
    inline cambc::bitboard tiles;         // every monster's tile
    inline cambc::bitboard off_camps;     // every other tile

    // this turn, from our team's sight:
    inline cambc::bitboard in_sight;
    inline cambc::bitboard alive;
    inline cambc::bitboard maybe_alive; // alive, or out of sight
    inline u16 group_at[100 * 100];     // tile (y * width + x) -> index in groups
    inline cambc::camp_type kind_at[100 * 100]; // tile (y * width + x) -> its monster's kind
    inline std::vector<vec2> in_view;   // room for every monster tile
    inline std::vector<group*> groups_in_view;

    inline const group* group_on(vec2 t) {
        return tiles.is_set(t) ? &groups[group_at[t.y * g::W + t.x]] : nullptr;
    }

    inline std::span<const monster> members(const group& g) {
        return {monsters.data() + g.first, g.count};
    }

    // every tile of g in sight: no unseen enemy on one holds its payout back
    inline bool all_in_sight(const group& g) {
        for (const monster& m : members(g))
            if (!in_sight.is_set(m.pos))
                return false;
        return true;
    }

    inline const group* capturing = nullptr; // the reward group we stand on
    inline i32 stepped_on = 0;               // the round we stepped on it, or later
    inline const group* heading = nullptr;   // the reward group we walked to last turn
    inline i32 heading_round = -1;

    // Rounds until the group we stand on pays us (0: none): one stepped on in round s pays at
    // the start of s + capture_time + 1, a recall landing then included (mechanics.md).
    inline i32 payout_in() {
        return capturing ? std::max(stepped_on + cambc::constants::capture_time + 1 - g::round, 0)
                         : 0;
    }

    inline const group& group_of(const monster& m) {
        return groups[m.group];
    }

    inline const cambc::camp_stats& stats_of(const monster& m) {
        return stats[i32(m.kind)];
    }

    // in sight, no monster on its tile
    inline bool seen_dead(const monster& m) {
        return in_sight.is_set(m.pos) && !alive.is_set(m.pos);
    }

    // Rounds until g can be farmed. A reward waits for a capture, not a timer: never.
    inline u32 wait(const group& g) {
        switch (g.state) {
            case group_state::reward:
                return UINT32_MAX;
            case group_state::respawning:
                return u32(std::max(g.back - g::round, 0));
            default:
                return 0;
        }
    }

    // false unless m is alive in our own sight
    inline bool health(const monster& m, f32& hp) {
        using namespace cambc;
        if (!alive.is_set(m.pos))
            return false;
        detail::camp_state s;
        // in team sight but not ours
        const i32 rc = detail::sdk_camp(m.id, &s);
        if (rc == i32(error_code::api_not_in_vision))
            return false;
        detail::check(rc);
        hp = s.health;
        return true;
    }

    inline void attack(const monster& m) {
        using namespace cambc::detail;
        channel::drop();
        check(sdk_attack(u32(entity_kind::camp), m.id));
    }

    // Tiles that monsters in `area` may hit: those we see awake, and those we can't see
    // that may be alive (a monster needs no sight to hit, so unseen ones count as
    // awake). Each hits its attack range around it.
    inline void aggro_into(const cambc::bitboard& area, cambc::bitboard& out) {
        static cambc::bitboard sources, unseen;
        static std::vector<vec2> at(monsters.size());
        cambc::vision::awake_camp_tiles_into(sources);
        bb::xor_into(tiles, in_sight, unseen), sources |= unseen, sources &= area;
        const u32 n = sources.positions_into(at);
        out.clear();
        for (u32 i = 0; i < n; ++i)
            if (const cambc::camp_stats& s = stats[i32(kind_at[at[i].y * g::W + at[i].x])];
                s.base_strength > 0)
                out.draw_chebyshev(at[i], f32(s.base_attack_range));
    }

    inline void init() {
        using namespace cambc;
        const i32 width = map::width();
        for (i32 t = 0; t < kind_count; ++t) {
            detail::camp_design d{};
            detail::check(detail::sdk_camp_design(t, &d));
            stats[t] = d.base_stats;
        }
        // per group: id, gold, gems, respawn, size, then per camp: id, kind, x, y.
        // That's at most 9 words per camp (a group of one: 5 + 4), with at most one
        // camp per tile on maps of at most 100x100.
        static u32 words[9 * 100 * 100];
        u32 count;
        detail::check(
            detail::sdk_map_camp_layout(words, u32(std::size(words)), &count));
        groups.reserve(count / 9), monsters.reserve(count / 4);
        for (u32 i = 0; i + 5 <= count;) {
            const u16 g = u16(groups.size());
            const u32 size = words[i + 4];
            group& grp = groups.emplace_back(group{words[i],
                                                   u16(monsters.size()),
                                                   u16(size),
                                                   {},
                                                   u16(words[i + 1]),
                                                   u16(words[i + 2]),
                                                   0,
                                                   0,
                                                   0,
                                                   u16(words[i + 3])});
            i += 5;
            for (u32 m = 0; m < size; ++m, i += 4) {
                const i32 kind = i32(words[i + 1]);
                const camp_stats& s = stats[kind];
                ++grp.kinds[kind];
                grp.max_hp += u32(s.base_health), grp.strength += u16(s.base_strength);
                grp.range = std::max(grp.range, u8(s.base_attack_range));
                const vec2 t{i32(words[i + 2]), i32(words[i + 3])};
                tiles.set(t), group_at[t.y * width + t.x] = g;
                kind_at[t.y * width + t.x] = camp_type(kind);
                monsters.push_back(
                    {t, u16(map_info::cell(t)), g, words[i], camp_type(kind)});
            }
        }
        bb::not_into(tiles, off_camps);
        in_view.resize(monsters.size());
        groups_in_view.reserve(groups.size());
    }

    // This turn's sight boards, and the state of every group in view.
    inline void start_turn() {
        using namespace cambc;
        if (!g::alive)
            return;
        const i32 now = g::round, width = map::width();
        vision::visible_tiles_into(in_sight);
        in_sight &= tiles;
        vision::camp_tiles_into(alive);
        bb::xor_into(tiles, in_sight, maybe_alive), maybe_alive |= alive;
        const u32 count = in_sight.positions_into(in_view);
        groups_in_view.clear();
        for (u32 i = 0; i < count; ++i) {
            group& grp = groups[group_at[in_view[i].y * width + in_view[i].x]];
            if (grp.read == now)
                continue;
            grp.read = now;
            groups_in_view.push_back(&grp);
            u32 raw;
            detail::check(detail::sdk_camp_group_state(grp.id, &raw));
            const bool knew = grp.state == group_state::respawning;
            const i32 knew_back = grp.back;
            grp.state = group_state(raw);
            if (grp.state == group_state::respawning) {
                i32 timer;
                detail::check(detail::sdk_camp_group_cooldown(grp.id, &timer));
                grp.back = now + timer;
                // the timer reads `respawn` on the payout round
                if (const i32 paid = grp.back - grp.respawn;
                    (!knew || knew_back != grp.back) && paid > now - 4)
                    paid_group = i32(&grp - groups.data()), paid_round = paid;
            }
        }
        const group* on = group_on(g::my_pos);
        if (on && on->state != group_state::reward)
            on = nullptr;
        // Walked onto it in our last turn: that round. Else it died while we stood there, in
        // our last round or before our turn in this one: this round, so a recall lands late
        // rather than early.
        if (on != capturing)
            capturing = on,
            stepped_on = on == heading && heading_round == now - 1 ? now - 1 : now;
        if (capturing) { // an enemy on its tiles at a round start wipes the count
            static cambc::bitboard enemies;
            vision::champion_tiles_into(team::enemy, enemies);
            for (const monster& m : members(*capturing))
                if (enemies.is_set(m.pos))
                    stepped_on = now;
        }
    }
} // namespace camp_info
