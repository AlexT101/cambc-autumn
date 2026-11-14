#pragma once

#include "../../../params.h"
#include <algorithm>
#include <array>
#include <optional>
#include <vector>
#include "../../comms.h"

namespace aph {
struct ChampionBelief;
class World;
}
namespace aph {
namespace {
struct Cast;
struct Target;
}
}

namespace aph {
class World;

struct ChampionBelief;

// The best enemy-hitting cast this turn, if worth it. An excludes-walking cast must also be worth
// `walk`, the walk it forgoes, unless it stuns every visible enemy that could reach us next turn.
bool cast_at_enemies(const World& world, float walk = 0);

// A damage or stun cast on the group being farmed, held while enemies are near.
// Call only when not walking this turn. `attackers_only`: target only members with Strength.
// `any_value`: even a cast worth less than usual, as on a group's last hit points.
bool cast_at_camp(const World& world, int group, bool attackers_only = false, bool any_value = false);

// Prism's safe approach: a harmful unit target or at least two harmful ground targets.
bool cast_at_camp_on_approach(const World& world, int group);

// A visible enemy tributing a bag that wins them the game.
bool enemy_tribute_wins(const World& world, const ChampionBelief& e);

// What stunning e is worth, in enemy health points. `damaging`: the hit's worth already counts a
// cancelled recall.
float stun_worth(const World& world, const ChampionBelief& e, bool damaging);

// A dash landing at p would hit a member of a sleeping group that strikes, waking it.
bool landing_wakes(const World& world, vec2 p, int radius);

constexpr int max_unseen_tiles = 9;

// e is tracked, unseen and on few tiles, and its retaliation would kill us at `health`.
bool unseen_suicidal(const ChampionBelief& e, float health);

}
namespace aph {
namespace {
// Values are in enemy health points.
constexpr float stun_value = 80;

constexpr float winning_tribute_value = 5000;

constexpr float min_value = 40;

constexpr float min_landing_value = 250;

constexpr float min_camp_value = 50;

constexpr int hold_range = 6;

bool walked_this_turn(const World& world);

bool castable(const World& world, int slot);

struct Cast {
    int slot = -1;
    float value = 0;
    std::optional<cambc::handle_champion_t> champion;
    std::optional<cambc::camp> camp;
    vec2 tile{-1, -1};
    bool dash = false; // a landing on `tile`
    float rank = -1;   // camp casts: the damage prevented, which picks the cast (value still sets the floors)

    float key() const;
    void offer(const Cast& other);


    bool execute() const;











};

float raw_damage(int slot);

// Health lost after mitigation and shields, capped at health.
float damage_to(int slot, cambc::handle_champion_t target, float raw);

// Timer 0: spent on this round's camp phase; a new stun still skips the next (probe-campstun).
bool camp_stunned_now(std::uint32_t camp);

bool recall_kept(const ChampionBelief& e);

// A kill takes the bag, both bags for Cassi and Issac, who die together. Other damage to an
// enemy on its spawn heals at its turn end, and damage to the healthier of Cassi and Issac only
// counts once it takes that body below the other.
float enemy_hit_worth(const World& world, const ChampionBelief& e, float damage, float health, bool on_spawn);

}
}
namespace aph {
float stun_worth(const World& world, const ChampionBelief& e, bool damaging);

bool landing_wakes(const World& world, vec2 p, int radius);

bool unseen_suicidal(const ChampionBelief& e, float health);

}
namespace aph {
namespace {
struct Target {
    vec2 pos;
    float weight; // chance the enemy is on this tile
    float worth;  // if hit
    float rank = -1; // camps: the damage prevented if hit, which picks the tile (worth sets the floor)
};

void draw_alive_members(const World& world, int g, bitboard& out, int radius = 1);

// Ground centres to skip: their 3x3 would hit a member of a sleeping group, which wakes whole,
// with a monster near us, or of a sleeping Monolith group other than the siege target. In a
// scratch board valid until the next call.
const bitboard& wake_risk(const World& world, vec2 here, int reach);

// Centres within `range` of `here`, off `skip`.
Cast best_ground(int slot, float min_weight_value, const std::vector<Target>& targets, vec2 here, int range,
                 const bitboard& skip, const std::vector<vec2>* harmful = nullptr);

// The landing that `keep` accepts whose `radius` around it hits most, nearest `here` on ties.
template <class Keep>
Cast best_landing(int slot, float min_value, const std::vector<Target>& targets, const bitboard& landings, vec2 here,
                  int radius, Keep keep);

Cast enemy_cast(const World& world, float walk, bool landings);

Cast camp_cast(const World& world, int group, bool attackers_only, bool any_value, bool approach = false);

}
}
namespace aph {
bool enemy_tribute_wins(const World& world, const ChampionBelief& e);

bool cast_at_enemies(const World& world, float walk);

bool cast_at_camp(const World& world, int group, bool attackers_only, bool any_value);

bool cast_at_camp_on_approach(const World& world, int group);

}
