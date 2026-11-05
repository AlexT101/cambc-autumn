// Attack resets, dashes, heals and shields. Each casts at most once and returns true if it did;
// only one cast succeeds per turn, so call the most valuable first.
#pragma once
#include <array>
#include <optional>
#include "../util.h"

namespace aph {

class World;
class Pathing;
class Safety;
struct ChampionBelief;

// The enemy a basic attack from here should hit, read live as vision changes when we move: the
// biggest kill, else the weakest, or for Varg the most value counting splash. Never one whose
// retaliation would kill us, nor one on its spawn (it heals at its turn end) unless the hit kills
// it or, with `stunnable_only`, stuns it; with that flag, only enemies a stun affects.
std::optional<cambc::handle_champion_t> attack_target(const World& world, bool stunnable_only = false);

// With the basic attack spent (by attacking, or by a ranged champion's walk), reset it and attack
// again. Enemies: attack_target's, unless Varg's shield wants the cast and the hit does not kill.
// Camps: the member nearest death (a Vendetta kill readies both abilities), held back while an
// enemy is close enough to want the reset for a fight.
// `stunning_only`: only a reset whose attack stuns (Marcella), on an enemy it would stun; call it
// before abilities.cc's casts, which share the one cast per turn, and the plain one after.
// `group`: only that group's camps.
bool reset_and_attack_enemy(const World& world, bool stunning_only = false);
bool reset_and_attack_camp(const World& world, int group);
// A camp tile lies within `range` of p.
bool camp_in_reach(const World& world, vec2 p, int range);

// Tiles within 3 of `from` that a travel dash (Pathing::step_towards) must not land on: Heart of
// Ruin's landing strike would wake a group not fully awake or draw a killing retaliation there. Null
// if none; else a scratch board, valid until the next call.
const bitboard* travel_landing_veto(const World& world, vec2 from);
// Into attack range of `target`, else of a visible enemy we can finish or are beating; attack after it.
bool dash_to_attack(const World& world, Pathing& pathing, Safety* safety, const ChampionBelief* target = nullptr);
// To less damage from visible enemies and awake camps (a camp's only where it would pick us),
// tie-broken towards `home`. `dead`: the tile of an enemy we killed this turn, which the beliefs
// still hold alive.
bool dash_away(const World& world, Pathing& pathing, Safety& safety, const Field& home, vec2 dead = {-1, -1});
// dash_away's choice, quoted without casting: its first landings, best first, from `from`.
// `clears`: the first lands where no threat reaches us (a camp's only where it would pick us).
struct EscapeDashQuote {
    int slot = -1, count = 0;
    vec2 from{-1, -1};
    std::array<vec2, 3> tiles{};
    bool clears = false;
};
EscapeDashQuote quote_escape_dash(const World& world, Pathing& pathing, Safety& safety, const Field& home, vec2 dead);
// The quote's first landing only, if we are still where it was made and its slot is ready.
bool cast_escape_dash(const World& world, Pathing& pathing, const EscapeDashQuote& quote);
// A ready dash could land out of every visible enemy's reach and every awake camp's that would pick
// us, `dead` aside.
bool dash_clears(const World& world, Pathing& pathing, Safety& safety, vec2 dead);
// Onto one of `tiles` (landings the caller accepts), nearest our spawn.
bool dash_onto(const World& world, Pathing& pathing, const bitboard& tiles);

// A heal cast now against the same heal held. Health does not come back off spawn, so a heal cast
// now leaves the rest of the damage for the cast after the cooldown; holding gains only when the
// allies in reach lose health faster than the heal restores it over its cooldown: then a cast that
// restores less than a full heal wastes more of the heal than waiting for a full one wastes of the
// cooldown. A heal that may keep an ally from falling before our next turn is cast at once.
class HealGate {
public:
    // The allies within `radius` of `from` that a heal could serve.
    HealGate(const World& world, Safety& safety, vec2 from, int radius, float amount)
        : world_(world), safety_(safety), from_(from), radius_(radius), amount_(amount) {}
    // A heal restoring `gain` to ally `a` at `pos` with `health`.
    bool worth(const ChampionBelief& a, vec2 pos, float gain, float health);
private:
    // What could hit `a` at p a round: camp hits, and `blow_share` of the enemy blows.
    float damage(const ChampionBelief& a, vec2 p, float blow_share);
    const World& world_;
    Safety& safety_;
    vec2 from_;
    int radius_;
    float amount_;
    float least_ = -1; // the least gain worth casting, worked out on first need
    // damage()'s parts by ally and tile, as worked out.
    struct Hits {
        const ChampionBelief* ally;
        vec2 p;
        float fire, blows;
    };
    std::array<Hits, 8> hits_;
    int n_hits_ = 0;
};
// Willow: the ally the heal restores most, among those HealGate passes.
bool heal_ally(const World& world, Safety& safety);
// A heal restoring `gain` of `amount` to an ally at `fraction` of its health is worth stepping for.
bool worth_healing(float amount, float gain, float fraction);
// A visible healer, us or an ally, could heal now, restoring `amount`: an ally's cooldowns are not
// in its belief, so this reads them live.
bool heal_ready(const World& world, const ChampionBelief& healer, float& amount);
struct HealTarget {
    const ChampionBelief* ally;
    vec2 pos;
    float gain, fraction; // what the heal restores, and the ally's health fraction before it
};
// A visible ally off its spawn that a heal of `amount` is worth casting on (`gate`), or with `step`
// or no gate, also worth stepping for (worth_healing). One keeping a recall going will reach spawn
// and heal there.
std::optional<HealTarget> heal_target(const World& world, const ChampionBelief& a, float amount, HealGate* gate = nullptr, bool step = false);
// Varg or Heart of Ruin: before damage from an awake camp, a camp we are hitting or an enemy in
// reach. `farmed`: the group farm chose, which we hit from attack range; another group's camp in
// attack range is hit only if our attack is spent.
bool shield_if_needed(const World& world, Safety& safety, int farmed);

} // namespace aph
