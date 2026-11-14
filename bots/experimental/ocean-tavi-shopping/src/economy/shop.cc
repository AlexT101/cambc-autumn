// Shopping and its economics: shards and emblems, builds, upkeep, gold rates and the trips home
// to buy.
#include "../bot_parts.h"
#include "emblem_table.h"

namespace aph {

namespace {

// cambc::item_family's order, which the item enum's layout follows.
enum Family { monster, power, durability, treasure, jungle, home, bruiser, tribute, capture, prospector, hunter, skirmish, greed, collectors };
enum StatKind { strength_stat, focus_stat, health_stat };
static_assert(collectors == static_cast<int>(cambc::item_family::collectors));
static_assert(health_stat == static_cast<int>(cambc::item_stat::health));

unsigned shards_needed(int family) { return family == greed ? greed_shards : shards_per_emblem; }

cambc::item_type shard_of(int family, int stat) {
    return cambc::item_type{static_cast<std::uint32_t>(family * 6 + stat * 2)};
}
cambc::item_type emblem_of(int family, int stat) {
    return cambc::item_type{static_cast<std::uint32_t>(family * 6 + stat * 2 + 1)};
}

unsigned emblems_owned(const cambc::enum_map<cambc::item_type>& owned) {
    unsigned n = 0;
    for (int family = monster; family <= collectors; ++family)
        for (int stat = strength_stat; stat <= health_stat; ++stat) n += owned[emblem_of(family, stat)];
    return n;
}

// The Health emblem Tavi holds its gold for (holds_health), with no shard of it bought yet: best_emblem finishes it
// first, as it would have finished it begun. Kept while we own held_ordinal emblems.
int held_family = -1, held_stat = 0;
unsigned held_ordinal = 0;

constexpr std::uint32_t kill_base_gold = 100;  // combat.kill, before gold bonuses
constexpr std::uint32_t hunter_kill_gold = 50; // a Hunter emblem's extra

// The stat whose shard adds more damage: Focus times our damaging casts so far (landings too, as
// raw_output counts them) against Strength times our basic attacks. Until both have happened, one
// cooldown's worth: the damage spells' multipliers against a basic attack a round plus the reset's.
// Always Focus for Ren (its retaliation scales with it) and for spell kiters on shared-gem maps.
int main_stat(const World& world) {
    const auto& f = world.me().facts();
    float spells = 0, cast = 0;
    for (int s = 0; s < 2; ++s) {
        const auto& a = f.abilities[s];
        if (a.kind == AbilityKind::damage) spells += a.multiplier;
        if (a.kind == AbilityKind::damage || a.lands()) cast += a.multiplier * static_cast<float>(use.casts[s]);
    }
    if ((world.map().shared_gems && spells > 0 && kites_with_spells(world.me())) || f.passive == Passive::retaliation) return focus_stat;
    float attacks = static_cast<float>(use.attacks);
    if (use.attacks == 0 || cast <= 0) cast = spells, attacks = static_cast<float>(ability_cooldown + (f.has_attack_reset() ? 1 : 0));
    return f.focus.growth * cast > attacks * f.strength.growth ? focus_stat : strength_stat;
}

bool buy(cambc::item_type shard, unsigned count) {
    auto& me = cambc::self();
    if (!count || !me.can_buy(shard, count)) return false;
    throw_if_stale();
    try {
        ++items_bought;
        me.buy(shard, count);
        if (held_family >= 0 && shard == shard_of(held_family, held_stat)) held_family = -1;
        income.spent += shard_price * count;
        return true;
    } catch (const cambc::error&) {
        return false;
    }
}

unsigned kept_gold(bool crystal);
void spent_beside_plan(unsigned cost);

// Tavi's plan keeps the gold of its steps (kept_gold).
void buy_consumable(cambc::consumable_type type, bool crystal) {
    auto& me = cambc::self();
    if (my_gold() < kept_gold(crystal) + type.cost()) return;
    try {
        if (me.can_buy(type)) throw_if_stale(), me.buy(type), income.spent += type.cost(), spent_beside_plan(type.cost());
    } catch (const cambc::error&) {
    }
}

// Locks on our own and middle altars keep the enemy's bags from scoring there until broken.
void buy_lock() { buy_consumable(cambc::consumable_type::altar_lock, false); }

bool carries_crystal() { return cambc::self().consumables()[cambc::consumable_type::tp_crystal].count() > 0; }
bool can_buy_crystal() { return my_gold() >= kept_gold(true) + cambc::consumable_type::tp_crystal.cost(); }

// Once a hop to an altar only a crystal reaches (StaticMap::hops) would have beaten walking to bank.
void buy_crystal(const Memory& memory) {
    if (memory.wants_crystal) buy_consumable(cambc::consumable_type::tp_crystal, true);
}

// Tavi shops anywhere: no trip home for it.
bool shops_at_home(const World& world) { return world.me().facts().passive != Passive::remote_shop; }
std::vector<vec2> upkeep_tiles; // noted, their steps not yet in `upkeep`

// At the turn's start: camps hit in the camp phase, from where we ended last turn.
void note_upkeep(const World& world, Safety& safety, float damage) {
    const vec2 here = world.me().pos;
    ++upkeep.turns;
    if (damage > 0) {
        const float camp = std::min(damage, safety.camp_damage(here));
        // On our spawn the turn end heals camp fire for free: no upkeep.
        if (!test(world.map().ally_spawn, here)) upkeep.camp_taken += camp;
        upkeep.champ_taken += damage - camp;
    }
    // Not the first turn: on spawn, its 0 steps were never in the mean.
    if (world.round != world.first_round) upkeep_tiles.push_back(here);
}

// The spawn steps of the tiles noted so far, added in turn order. Only a mean multiplied by
// damage taken needs them, so the spawn field is first made when some was taken.
void fold_upkeep(const StaticMap& map) {
    for (const vec2 p : upkeep_tiles)
        if (const int s = test(map.ally_spawn, p) ? 0 : map.from_ally_spawn().at(p); s != unreachable)
            upkeep.spawn_steps += static_cast<float>(s), ++upkeep.spawn_turns;
    upkeep_tiles.clear();
}

// An emblem with shards owned short of it, which best_emblem finishes before any other.
struct Begun {
    int family, stat;
    bool passive = false; // priced with its passive
};

bool priced_passive(int family) {
    return family == treasure || family == tribute || family == capture || family == prospector || family == hunter || family == skirmish ||
           family == greed || family == collectors;
}

// A learned emblem (learned_arm) current_emblem prices as if begun while pin_family is set.
int pin_family = -1, pin_stat = 0;
struct Pin {
    Pin(int family, int stat) { pin_family = family, pin_stat = stat; }
    ~Pin() { pin_family = -1; }
};

bool holding(const cambc::enum_map<cambc::item_type>& owned) {
    return held_family >= 0 && owned[shard_of(held_family, held_stat)] == 0 && emblems_owned(owned) == held_ordinal;
}

// The begun emblem best_emblem finishes, in the stat it was begun in (the main stat follows our use
// and can change), or none. Only the shards best_emblem would buy count.
std::optional<Begun> begun_emblem(const World& world, const cambc::enum_map<cambc::item_type>& owned) {
    if (pin_family >= 0) return Begun{pin_family, pin_stat, priced_passive(pin_family)};
    const auto& f = world.me().facts();
    const auto has = [&](int family, int stat) { return owned[shard_of(family, stat)] > 0; };
    if (f.passive == Passive::gem_focus && has(monster, health_stat)) return Begun{monster, health_stat};
    if (f.passive == Passive::gem_focus && has(monster, focus_stat)) return Begun{monster, focus_stat};
    if (f.passive == Passive::reset_on_kill && has(monster, strength_stat)) return Begun{monster, strength_stat};
    // On 3 picks everyone may take Monster (best_stat), and finishes one begun.
    if (economy_three(world))
        for (int stat = strength_stat; stat <= health_stat; ++stat)
            if (has(monster, stat)) return Begun{monster, stat};
    constexpr Begun stats[] = {{jungle, strength_stat}, {jungle, focus_stat}, {power, strength_stat}, {power, focus_stat}, {durability, health_stat},
                               {bruiser, strength_stat}, {bruiser, focus_stat}, {bruiser, health_stat}};
    for (const auto& b : stats)
        if (has(b.family, b.stat)) return b;
    for (const int family : {treasure, tribute, capture, prospector, hunter, skirmish, greed, collectors})
        for (int stat = strength_stat; stat <= health_stat; ++stat)
            if (has(family, stat)) return Begun{family, stat, true};
    if (f.heals() && has(jungle, health_stat)) return Begun{jungle, health_stat};
    if (f.passive == Passive::gem_focus)
        for (const int family : {power, jungle, home})
            if (has(family, health_stat)) return Begun{family, health_stat};
    // A learned emblem, which the lists above need not name.
    for (int family = monster; family <= collectors; ++family)
        for (int stat = strength_stat; family != greed && stat <= health_stat; ++stat)
            if (has(family, stat)) return Begun{family, stat, priced_passive(family)};
    return std::nullopt;
}

// Our stats, damage taken (Jungle and Durability), and camp damage dealt (Monster, Collectors).
struct Build {
    float strength = 0, focus = 0, max_health = 0, camp_taken = 1, taken = 1, camp_dealt = 1;
    int recall = static_cast<int>(cambc::constants::recall_time);
};

// Our build with `bought` added to our stats as bought (without Tavi's planned shards), owning `owned`.
Build build_of(const World& world, const cambc::enum_map<cambc::item_type>& owned, const Build& bought) {
    const auto& self = world.me();
    return Build{self.strength - tavi_planned.strength + bought.strength, self.focus - tavi_planned.focus + bought.focus,
                 self.max_health - tavi_planned.max_health + bought.max_health,
                 has_family(owned, jungle) ? jungle_camp_taken : 1.0f, has_family(owned, durability) ? durability_taken : 1.0f,
                 dealt_with(owned).camp, has_family(owned, home) ? home_recall_time : recall_turns(world)};
}

void add_shards(Build& b, const ChampionFacts& f, int stat, float shards) {
    if (stat == strength_stat) b.strength += shards * f.strength.growth;
    if (stat == focus_stat) b.focus += shards * f.focus.growth;
    if (stat == health_stat) {
        b.max_health += shards * f.health.growth;
        if (f.passive == Passive::health_strength)
            b.strength += cambc::constants::passive_abilities::ryth_health_strength_ratio * shards * f.health.growth;
    }
}

// What completing an emblem adds beyond its shards: Power a sixth shard, Bruiser one of each other
// stat, Greed fifteen more.
void add_completion(Build& b, const ChampionFacts& f, int family, int stat) {
    if (family == power) add_shards(b, f, stat, 1);
    if (family == greed) add_shards(b, f, stat, static_cast<float>(greed_stats - greed_shards));
    if (family == bruiser)
        for (int s = strength_stat; s <= health_stat; ++s)
            if (s != stat) add_shards(b, f, s, 1);
}

// Where every gem is behind a siege, our upkeep before a camp has hit us: every turn on the nearest
// Monolith, alongside the others' output (`others`), its hits on the nearest of us (the melee while
// any lives) split by max health, the walk out its distance from spawn.
Upkeep siege_upkeep(const World& world, float& others) {
    const auto& map = world.map();
    Upkeep u;
    others = 0;
    int g = -1, steps = unreachable;
    for (int h = 0; h < static_cast<int>(map.groups.size()); ++h)
        if (map.groups[h].has_monolith && map.ally_steps(h) < steps) g = h, steps = map.ally_steps(h);
    if (g < 0) return upkeep;
    bool melee = false;
    for (const auto& a : world.allies) melee |= (a.alive || a.is_self) && !a.facts().ranged;
    float pool = 0;
    for (const auto& a : world.allies) {
        if (!a.alive && !a.is_self) continue;
        if (!a.is_self) others += camp_output(a);
        if (!melee || !a.facts().ranged) pool += a.max_health;
    }
    const auto& self = world.me();
    u.turns = u.camp_turns = u.spawn_turns = std::max(1, upkeep.turns);
    u.spawn_steps = static_cast<float>(steps * u.turns);
    u.champ_taken = upkeep.champ_taken;
    if (!melee || !self.facts().ranged)
        u.camp_taken = map.groups[g].strength * params::siege_hit_share * camp_hit_factor() * self.max_health / pool * static_cast<float>(u.turns);
    return u;
}

// The upkeep emblems are priced at, with the others' output beside ours on the same camps.
Upkeep priced_upkeep(const World& world, float& others) {
    others = 0;
    if (upkeep.camp_taken > 0 || upkeep.champ_taken > 0) fold_upkeep(world.map()); // upkeep_cost reads the steps only then
    return world.map().monolith_only && upkeep.camp_taken <= 0 ? siege_upkeep(world, others) : upkeep;
}

float mean_spawn_steps(const Upkeep& u) { return u.spawn_turns > 0 ? u.spawn_steps / static_cast<float>(u.spawn_turns) : 0.0f; }

// Rounds a turn of ours costs in clearing and heal trips at upkeep u, with build b: the clearing
// share shrinks with our output (beside the others' on the same camps), as do the camps' hits taken
// meanwhile; health lost comes back by a heal trip from our mean steps from spawn (heal_trip), one
// per usable health (above the recall line).
// upkeep_cost's terms that hold for every candidate build of one pricing, each its own sub-expression.
struct UpkeepBasis {
    const ChampionFacts* facts;
    float others, now_dealt, steps, camp_turn, champ_turn, now_camp_taken, now_taken, clearing;
};
UpkeepBasis upkeep_basis(const World& world, const Upkeep& upkeep, float others, const Build& now) {
    const auto& f = world.me().facts();
    const float turns = static_cast<float>(std::max(1, upkeep.turns));
    // Counted from one clearing turn in one: before our first camp hit, gold (priced by this
    // saving) is still worth farming.
    return {&f, others, others + std::max(1.0f, f.raw_output(now.strength, now.focus)) * now.camp_dealt, mean_spawn_steps(upkeep),
            upkeep.camp_taken / turns, upkeep.champ_taken / turns, now.camp_taken, now.taken,
            static_cast<float>(upkeep.camp_turns + 1) / static_cast<float>(upkeep.turns + 1)};
}
float upkeep_cost(const UpkeepBasis& u, const Build& b) {
    const float clear = u.now_dealt / (u.others + std::max(1.0f, u.facts->raw_output(b.strength, b.focus)) * b.camp_dealt);
    const float camp = u.camp_turn * clear * b.camp_taken / u.now_camp_taken;
    const float taken = (camp + u.champ_turn) * b.taken / u.now_taken;
    const float usable = b.max_health * (1.0f - params::recall_health_fraction);
    return u.clearing * clear + taken * heal_trip(b.recall, u.steps, u.steps) / usable;
}
float upkeep_cost(const World& world, const Upkeep& upkeep, float others, const Build& now, const Build& b) {
    return upkeep_cost(upkeep_basis(world, upkeep, others, now), b);
}

// Our mean steps from spawn while alive: the walk back out after a heal.
float spawn_steps(const World& world) {
    fold_upkeep(world.map());
    return mean_spawn_steps(upkeep);
}

// Rounds `damage` costs, priced as upkeep_cost prices it: a heal trip (heal_trip: from a stand `gap`
// steps from our spawn, back out `out` steps from the recall's landing) per usable health.
float heal_rounds(const World& world, float damage, float gap, float out) {
    const float usable = my_max_health() * (1.0f - params::recall_health_fraction);
    return damage / usable * heal_trip(world, gap, out);
}
// heal_rounds for the damage we carry, from and back out by our mean steps from spawn (made only when hurt).
float heal_rounds_now(const World& world) {
    const float damage = my_max_health() - my_health();
    const float steps = damage > 0 ? spawn_steps(world) : 0.0f;
    return heal_rounds(world, damage, steps, steps);
}

// Income's prior, worth income_prior_gems gems of our own: this map's capture income per gem (every
// group but Monoliths, all where only Monoliths pay, each captured alone), and measured rates
// (rounds alive per gem collected, kills per gem, Tribute's cut turn ends per gem).
constexpr float income_prior_gems = 30;
constexpr float prior_rounds_per_gem = 4.5f;
constexpr float prior_kills_per_gem = 0.005f;
constexpr float prior_tribute_cut = 0.015f;
struct IncomePrior {
    float holds = 0, prospected_gems = 0, prospected_gold = 0, gold = 0;
};
const IncomePrior& income_prior(const StaticMap& map) {
    static const IncomePrior prior = [&] {
        IncomePrior p;
        float gems = 0;
        for (const auto& G : map.groups) {
            if (G.has_monolith && !map.monolith_only) continue;
            gems += static_cast<float>(G.gems);
            p.holds += 1;
            p.prospected_gems += static_cast<float>(prospected(G.cluster_gems, 1));
            p.prospected_gold += static_cast<float>(prospected(G.cluster_gold, 1));
            p.gold += static_cast<float>(G.gold);
        }
        if (gems > 0) p = {p.holds / gems, p.prospected_gems / gems, p.prospected_gold / gems, p.gold / gems};
        return p;
    }();
    return prior;
}

// Our gems and turns alive, with the prior's, and the rounds our gold has left: the same for every
// candidate of a best_emblem call.
struct IncomeRates {
    float gems, turns, horizon;
};
IncomeRates income_rates(const World& world) {
    const float gems = income.gems + income_prior_gems;
    const float turns = static_cast<float>(upkeep.turns) + prior_rounds_per_gem * income_prior_gems;
    return {gems, turns, std::min(static_cast<float>(bag_rounds_left(world)), gems_share(world) * turns / gems)};
}

float fight_share() { return upkeep.champ_taken / (upkeep.camp_taken + upkeep.champ_taken + params::fight_camp_prior); }

// The reactive Tribute price: the cut on the bag we carry, from trib_min_bag gems, spread over the rounds our
// gold has left.
float reactive_tribute(const IncomeRates& rates) {
    const int bag = static_cast<int>(my_gems());
    if (bag < params::trib_min_bag) return 0;
    const float cut = static_cast<float>(tribute_turns(bag, false) - tribute_turns(bag, true));
    if (cut <= 0) return 0;
    return cut / std::max(rates.horizon, 20.0f);
}

// The share of a turn (best_emblem's unit) a passive emblem's passive saves, from our income per turn
// alive (income, prior-weighted): Capture's hold rounds per payout and Tribute's cut turn ends;
// Prospector's extra gems per gem as the farming they save; gold (Prospector's, Treasure's,
// Hunter's) at `per_gold` saved per gold, earned evenly until our share of the gems still to farm is
// done at our pace (or the game ends) and so spent on average halfway there.
float passive_saved(const World& world, const IncomeRates& rates, const cambc::enum_map<cambc::item_type>& owned, int family, float per_gold) {
    if (has_family(owned, family)) return 0;
    const auto& prior = income_prior(world.map());
    const auto& f = world.me().facts();
    const float gems = rates.gems, turns = rates.turns;
    const auto per_turn = [&](float counted, float prior_per_gem) { return (counted + prior_per_gem * income_prior_gems) / turns; };
    const float gold = 0.5f * per_gold * rates.horizon;
    const float paid = gold_rate(f, owned);
    const float kill_gold = per_turn(income.kill_gold, f.heals() ? 0.0f : prior_kills_per_gem * static_cast<float>(kill_base_gold));
    switch (family) {
    case capture: return static_cast<float>(capture_rounds(false) - capture_rounds(true)) * per_turn(income.holds, prior.holds);
    case tribute: return per_turn(income.tribute_cut, prior_tribute_cut) + reactive_tribute(rates);
    case prospector: {
        const float extra = (income.prospected_gems + prior.prospected_gems * income_prior_gems) / gems;
        return extra / (1 + extra) + gold * paid * per_turn(income.prospected_gold, prior.prospected_gold);
    }
    case treasure: {
        float base = per_turn(income.capture_gold, prior.gold) + kill_gold;
        if (f.passive == Passive::stun_immune)
            base += static_cast<float>(cambc::constants::passive_abilities::marcella_tribute_gold_per_gem) * gems / turns;
        return gold * treasure_gold * base;
    }
    case hunter: return gold * paid * static_cast<float>(hunter_kill_gold) / static_cast<float>(kill_base_gold) * kill_gold;
    case skirmish: return params::fight_weight * fight_share() * (1.0f - 1.0f / skirmish_dealt);
    default: return 0;
    }
}

// `bought`: the stats of shards bought since the turn's start; `items`: what we would then own.
Emblem current_emblem(const World& world, const Build& bought, const cambc::enum_map<cambc::item_type>* items) {
    const auto& f = world.me().facts();
    const auto& owned = items ? *items : my_items();
    const Build now = build_of(world, owned, bought);
    float others;
    const Upkeep u = priced_upkeep(world, others);
    const UpkeepBasis basis = upkeep_basis(world, u, others, now);
    const float base = upkeep_cost(basis, now);
    // The fight value's shared terms stay outside the candidate loop.
    const float fight_scale = params::fight_weight * fight_share();
    const float p_now = std::max(1.0f, f.raw_output(now.strength, now.focus)) * now.max_health / now.taken;
    const bool collecting = has_family(owned, collectors); // every new family adds to its camp damage
    const auto value = [&](int family, int stat) __attribute__((always_inline)) -> Emblem {
        const unsigned left = shards_needed(family) - owned[shard_of(family, stat)];
        Build b = now;
        add_shards(b, f, stat, static_cast<float>(left));
        add_completion(b, f, family, stat);
        if (family == jungle) b.camp_taken = jungle_camp_taken;
        if (family == durability) b.taken = durability_taken;
        if (family == monster || family == collectors || collecting) b.camp_dealt = dealt_with(owned, family).camp;
        if (family == home) b.recall = home_recall_time;
        const float p_b = std::max(1.0f, f.raw_output(b.strength, b.focus)) * b.max_health / b.taken;
        return {family, stat, base - upkeep_cost(basis, b) + fight_scale * std::max(0.0f, 1.0f - p_now / p_b), left * shard_price};
    };
    const bool three = economy_three(world);
    // The best stat emblem: a Power, Jungle, Durability or Bruiser one (Vendetta's Monster too).
    const auto best_stat = [&](int main) {
        Emblem best = value(power, main);
        if (const auto e = value(jungle, main); e.saved > best.saved) best = e;
        if (const auto e = value(durability, health_stat); e.saved > best.saved) best = e;
        if (const auto e = value(bruiser, main); e.saved > best.saved) best = e;
        if (const auto e = value(bruiser, health_stat); e.saved > best.saved) best = e;
        // Durability's -10% taken outweighs a sixth Health shard for all but Ryth, whose Health adds Strength.
        if (f.passive == Passive::health_strength)
            if (const auto e = value(power, health_stat); e.saved > best.saved) best = e;
        if (f.heals() && !has_family(owned, jungle))
            if (const auto e = value(jungle, health_stat); e.saved > best.saved) best = e;
        if (three) {
            if (!has_family(owned, monster))
                if (const auto e = value(monster, main); e.saved > best.saved) best = e;
        } else if (f.passive == Passive::reset_on_kill && !has_family(owned, monster)) {
            // Vendetta's high base Strength makes +15% on camps worth more than a sixth shard.
            if (const auto e = value(monster, strength_stat); e.saved > best.saved) best = e;
        }
        return best;
    };
    // A passive's gold is priced at what the best stat emblem saves a gold.
    const auto per_gold = [](const Emblem& e) { return std::max(0.0f, e.saved) / static_cast<float>(emblem_price); };
    // The best of `best` and a passive emblem: five shards in stat `a` or `b`, and its passive.
    const auto or_passive = [&](Emblem best, int a, int b) {
        Emblem shards = value(prospector, a);
        if (const auto e = value(prospector, b); e.saved > shards.saved) shards = e;
        const IncomeRates rates = income_rates(world);
        const float gold_saves = per_gold(best);
        for (const int family : {prospector, capture, treasure, hunter, tribute, skirmish})
            if (const float saved = shards.saved + passive_saved(world, rates, owned, family, gold_saves); saved > best.saved)
                best = {family, shards.stat, saved, emblem_price, saved - shards.saved};
        return best;
    };
    if (const auto b = begun_emblem(world, owned)) {
        Emblem e = value(b->family, b->stat);
        if (b->passive) {
            e.passive = passive_saved(world, income_rates(world), owned, b->family, per_gold(best_stat(main_stat(world))));
            e.saved += e.passive;
        }
        return e;
    }
    if (f.passive == Passive::gem_focus) {
        Emblem best = value(power, health_stat);
        if (const auto e = value(bruiser, health_stat); e.saved > best.saved) best = e;
        if (const auto e = value(bruiser, focus_stat); e.saved > best.saved) best = e;
        if (const auto e = value(jungle, health_stat); e.saved > best.saved) best = e;
        if (const auto e = value(durability, health_stat); e.saved > best.saved) best = e;
        if (!has_family(owned, monster))
            if (const auto e = value(monster, health_stat); e.saved > best.saved) best = e;
        if (!has_family(owned, home))
            if (const auto e = value(home, health_stat); e.saved > best.saved) best = e;
        if (const auto e = value(power, focus_stat); e.saved > best.saved) best = e;
        if (!has_family(owned, monster))
            if (const auto e = value(monster, focus_stat); e.saved > best.saved) best = e;
        return or_passive(best, health_stat, focus_stat);
    }
    const int main = main_stat(world);
    Emblem best = best_stat(main);
    return or_passive(best, main, health_stat);
}

// With a bag that a Tribute emblem would cut, the Tribute emblem in its best stat in place of `e` when it
// saves more; never over a begun emblem (best_emblem finishes those first).
Emblem reactive_over(const World& world, const Build& bought, const Emblem& e, const cambc::enum_map<cambc::item_type>* items) {
    const auto& owned = items ? *items : my_items();
    const int bag = static_cast<int>(my_gems());
    if (has_family(owned, tribute) || bag < params::trib_min_bag || tribute_turns(bag, true) == tribute_turns(bag, false)) return e;
    Emblem best = e;
    for (int stat = strength_stat; stat <= health_stat; ++stat) {
        pin_family = tribute, pin_stat = stat;
        const Emblem t = current_emblem(world, bought, items);
        pin_family = -1;
        if (t.saved > best.saved) best = t;
    }
    debug_block({
        if (best.family == tribute && e.family != tribute)
            std::printf("KTRIB %d %d bag=%u over=%d saved=%.3f/%.3f\n", world.round, static_cast<int>(world.me().type), my_gems(), e.family,
                        best.saved, e.saved);
    });
    return best;
}

// The current logic's emblem, except that a new one is the learned one (tools/emblab) for our pick count, type and
// count of emblems owned (`items`, what we would own, else ours), unless its passive is already ours: what
// buy_shards buys, so prices() and affordable_prefix() forecast the same.
Emblem best_emblem(const World& world, const Build& bought = {}, const cambc::enum_map<cambc::item_type>* items = nullptr) {
    const auto& owned = items ? *items : my_items();
    if (holding(owned)) {
        Pin pin{held_family, held_stat};
        return current_emblem(world, bought, items);
    }
    const int picks = economy_pick_count(world), type = static_cast<int>(world.me().type);
    if (picks < 3 || picks > 5) return current_emblem(world, bought, items);
    if (begun_emblem(world, owned)) return current_emblem(world, bought, items);
    unsigned ordinal = 0;
    for (int family = monster; family <= collectors; ++family)
        for (int stat = strength_stat; stat <= health_stat; ++stat) ordinal += owned[emblem_of(family, stat)];
    if (ordinal >= std::size(learned_arm[0][0])) return reactive_over(world, bought, current_emblem(world, bought, items), items);
    const int arm = learned_arm[picks - 3][type][ordinal], family = arm / 3;
    if (arm == 255 || (family != power && family != bruiser && has_family(owned, family)))
        return reactive_over(world, bought, current_emblem(world, bought, items), items);
    Emblem e;
    {
        Pin pin{family, arm % 3};
        e = current_emblem(world, bought, items);
    }
    return reactive_over(world, bought, e, items);
}

// Health bought off our spawn raises max health only (cambc-rules economy.health_purchase), so Tavi alive off it
// buys Health shards only in the purchase that completes their emblem, on the turn it would have completed anyway;
// the rest wait for our spawn or death, which give that Health at once.
// Not beside a healer, whose heals stop at our max health.
bool holds_health(const World& world) {
    if (!world.me().alive || shops_at_home(world) || test(world.map().ally_spawn, my_position())) return false;
    for (const auto& a : world.allies)
        if (!a.is_self && a.facts().heals()) return false;
    return true;
}

unsigned reactive_bag();

// Families whose worth comes only from damage we deal: Tavi buys them at its next damaging act
// (before_damage), unseen by the enemy until then, rather than on the turn its gold allows. The others work between
// our turns (capture payouts, hits taken) or at a channel's start, and are bought as before.
bool deferrable(int family) {
    return family == monster || family == power || family == bruiser || family == hunter || family == skirmish || family == greed
           || family == collectors;
}

// buy_shards' purchases for Tavi, in buy_shards' order after the sold items bought back, each bought when its time
// comes: a `now` step at the turn's start, the rest at before_damage. Every reader of our stats sees the whole plan
// as bought (util.h tavi_planned); the shop prices from our stats as bought.
struct PlanStep {
    cambc::item_type shard;
    unsigned count;
    bool now, bought;
    int round;                  // planned in
    cambc::item_type restores;  // the sold item it buys back, with restores_count of it (0: none)
    unsigned restores_count;
    float strength, focus, max_health; // what it adds
};
struct TaviPlan {
    std::array<PlanStep, 24> steps;
    int n = 0;
    cambc::enum_map<cambc::item_type> owned; // ours once every step is bought
    cambc::enum_map<cambc::item_type> sold;  // sold on our spawn, not yet bought back
    float held_health = 0;                   // the max health of the Health shards our spawn buys (holds_health)
    unsigned held_gold = 0;                  // their price
    unsigned left = 0;                       // gold past the steps
    // Our gold, purchase count and holds_health as of the plan's last change.
    unsigned gold = ~0u, bought = ~0u;
    bool hold = false;
};
TaviPlan tavi;
World* tavi_world = nullptr; // this turn's, while Tavi plans
constexpr int most_sold_steps = 16; // the rest of the steps for new gold

// The plan's steps not yet bought, as best_emblem's `bought` (the held Health is not bought).
Build unbought(const TaviPlan& p) {
    Build b;
    for (int k = 0; k < p.n; ++k)
        if (const auto& s = p.steps[static_cast<std::size_t>(k)]; !s.bought) b.strength += s.strength, b.focus += s.focus, b.max_health += s.max_health;
    return b;
}

// `extend`: new gold continues the plan from its last step, as buy_shards' next purchase continued from the shards
// already bought (a begun emblem is finished first); else it is made from what we own and what we sold, then the
// steps chosen before and not yet bought (as buy_shards would have bought them then), as far as our gold goes.
void make_plan(const World& world, bool extend, bool hold) {
    auto& p = tavi;
    p.hold = hold;
    const auto& f = world.me().facts();
    Build total;
    unsigned gold = my_gold();
    const auto step = [&](cambc::item_type shard, unsigned count, bool now, cambc::item_type restores, unsigned restores_count, const Build& before,
                          int round) {
        p.steps[static_cast<std::size_t>(p.n++)] = {shard, count, now, false, round, restores, restores_count,
                                                   total.strength - before.strength, total.focus - before.focus, total.max_health - before.max_health};
    };
    if (extend) {
        total = unbought(p);
        gold = p.left + (gold - p.gold);
    } else {
        struct Chosen {
            cambc::item_type shard;
            unsigned count;
            int round;
        };
        std::array<Chosen, std::tuple_size_v<decltype(p.steps)>> chosen;
        int n_chosen = 0;
        for (int k = 0; k < p.n; ++k)
            if (const auto& s = p.steps[static_cast<std::size_t>(k)]; !s.bought && !s.restores_count) chosen[static_cast<std::size_t>(n_chosen++)] = {s.shard, s.count, s.round};
        p.n = 0;
        p.owned = my_items();
        for (int family = monster; family <= collectors; ++family)
            for (int stat = strength_stat; stat <= health_stat; ++stat) {
                const auto emblem = emblem_of(family, stat), shard = shard_of(family, stat);
                for (unsigned i = 0; i < p.sold[emblem]; ++i) {
                    const unsigned count = shards_needed(family);
                    if (gold < shard_price * count || p.n == most_sold_steps) {
                        p.sold[emblem] = i;
                        break;
                    }
                    const Build before = total;
                    gold -= shard_price * count;
                    add_shards(total, f, stat, static_cast<float>(count));
                    add_completion(total, f, family, stat);
                    p.owned[emblem] += 1;
                    step(shard, count, false, emblem, 1, before, world.round);
                }
                if (const unsigned count = p.sold[shard]) {
                    if (gold < shard_price * count || p.n == most_sold_steps) {
                        p.sold[shard] = 0;
                        continue;
                    }
                    const Build before = total;
                    gold -= shard_price * count;
                    add_shards(total, f, stat, static_cast<float>(count));
                    p.owned[shard] += count;
                    step(shard, count, false, shard, count, before, world.round);
                }
            }
        for (int k = 0; k < n_chosen; ++k) {
            const auto [shard, count, round] = chosen[static_cast<std::size_t>(k)];
            const int family = static_cast<int>(static_cast<std::uint32_t>(shard)) / 6, stat = static_cast<int>(static_cast<std::uint32_t>(shard)) % 6 / 2;
            const unsigned have = p.owned[shard];
            const bool completes = have + count == shards_needed(family);
            if (gold < shard_price * count || have + count > shards_needed(family) || p.n == static_cast<int>(p.steps.size())) break;
            if (hold && stat == health_stat && !completes) continue; // held by the loop below
            const Build before = total;
            gold -= shard_price * count;
            add_shards(total, f, stat, static_cast<float>(count));
            if (completes) {
                add_completion(total, f, family, stat);
                p.owned[shard] = 0;
                p.owned[emblem_of(family, stat)] += 1;
            } else {
                p.owned[shard] += count;
            }
            step(shard, count, !deferrable(family) || ((stat == health_stat || family == bruiser) && !hold), shard, 0, before, round);
        }
    }
    p.held_health = 0, p.held_gold = 0;
    while (gold >= shard_price && p.n < static_cast<int>(p.steps.size())) {
        const auto e = best_emblem(world, total, &p.owned);
        const auto shard = shard_of(e.family, e.stat);
        const unsigned have = p.owned[shard];
        const unsigned count = std::min<unsigned>(shards_needed(e.family) - have, gold / shard_price);
        const bool completes = have + count == shards_needed(e.family);
        if (hold && e.stat == health_stat && !completes) {
            if (have == 0) held_family = e.family, held_stat = e.stat, held_ordinal = emblems_owned(p.owned);
            p.held_health = static_cast<float>(count) * f.health.growth, p.held_gold = shard_price * count;
            break;
        }
        const Build before = total;
        gold -= shard_price * count;
        add_shards(total, f, e.stat, static_cast<float>(count));
        if (completes) {
            add_completion(total, f, e.family, e.stat);
            p.owned[shard] = 0;
            p.owned[emblem_of(e.family, e.stat)] += 1;
        } else {
            p.owned[shard] += count;
        }
        // Health (Bruiser's too) counts at once on our spawn, dead, or beside a healer, whose heals stop at max health.
        step(shard, count, !deferrable(e.family) || ((e.stat == health_stat || e.family == bruiser) && !hold), shard, 0, before, world.round);
    }
    p.left = gold, p.gold = my_gold(), p.bought = items_bought;
}

// The plan's steps not yet bought, as best_emblem's `bought`.
Build planned_build() { return unbought(tavi); }

// What the plan's steps not yet bought add, and its held Health.
TaviPlanned planned_of(const TaviPlan& p) {
    TaviPlanned out;
    for (int k = 0; k < p.n; ++k)
        if (const auto& s = p.steps[static_cast<std::size_t>(k)]; !s.bought)
            out.strength += s.strength, out.focus += s.focus, out.max_health += s.max_health, out.pending = true;
    out.max_health += p.held_health;
    if (out.pending) {
        const auto d = dealt_with(p.owned);
        out.dealt = d.champion, out.camp_dealt = d.camp;
    }
    out.on = out.pending || p.held_health > 0;
    return out;
}

// Our own record follows every change of the plan, so it always reads as the plan bought. `bought`: the change is
// steps bought, whose stats our record, read before, already has.
void set_planned(World& world, TaviPlanned next, bool bought = false) {
    next.active = true;
    if (next.strength == tavi_planned.strength && next.focus == tavi_planned.focus && next.max_health == tavi_planned.max_health
        && next.pending == tavi_planned.pending && next.on == tavi_planned.on && next.dealt == tavi_planned.dealt
        && next.camp_dealt == tavi_planned.camp_dealt) {
        tavi_planned.active = true;
        return;
    }
    auto& me = world.me_mut();
    if (!bought) {
        me.strength += next.strength - tavi_planned.strength;
        me.focus += next.focus - tavi_planned.focus;
        me.max_health += next.max_health - tavi_planned.max_health;
    }
    if (next.pending) {
        me.dealt = next.dealt, me.camp_dealt = next.camp_dealt;
    } else if (tavi_planned.pending) {
        const auto d = dealt_with(my_items());
        me.dealt = d.champion, me.camp_dealt = d.camp;
    }
    me.scale = damage_scale(me.facts().passive, me.health, me.max_health) * me.dealt;
    next.version = tavi_planned.version + 1;
    tavi_planned = next;
}

bool any_unbought(const TaviPlan& p) {
    for (int k = 0; k < p.n; ++k)
        if (!p.steps[static_cast<std::size_t>(k)].bought) return true;
    return false;
}

// The plan follows our gold (a payout, a kill's gold mid-turn) and is read as bought. Made afresh from what we own
// and sold after purchases outside it or a sale, or once all its steps are bought.
void plan_fresh(World& world) {
    const auto& p = tavi;
    const unsigned gold = my_gold();
    const bool hold = holds_health(world);
    if (p.gold == gold && p.bought == items_bought && p.hold == hold) return;
    make_plan(world, p.bought == items_bought && p.hold == hold && gold > p.gold && any_unbought(p), hold);
    set_planned(world, planned_of(tavi));
}

// Buys the plan's steps not yet bought (with `only_now`, those that must be bought now), stopping at a refusal. A
// step's shard is never another's of a different time, so buying out of order completes the same emblems. True if
// any was bought.
bool execute_plan(World& world, bool only_now) {
    auto& p = tavi;
    bool any = false;
    for (int k = 0; k < p.n; ++k) {
        auto& s = p.steps[static_cast<std::size_t>(k)];
        if (s.bought || (only_now && !s.now)) continue;
        if (!buy(s.shard, s.count)) break;
        s.bought = any = true;
        p.sold[s.restores] -= std::min(p.sold[s.restores], s.restores_count);
    }
    if (!any) return false;
    p.gold = my_gold(), p.bought = items_bought;
    set_planned(world, planned_of(p), true);
    return true;
}

// Alive on our spawn: the sellable items go for their full price (cambc-rules champions.tavi), bought back by the
// plan. Our record read them before the sale, so they stay on it as planned. Noted unit by unit: a turn cut short
// mid-sale keeps what it sold.
void sell_on_spawn(World& world) {
    auto& p = tavi;
    const auto& items = my_items();
    int steps = 0;
    for (int family = monster; family <= collectors; ++family)
        for (int stat = strength_stat; stat <= health_stat; ++stat)
            steps += static_cast<int>(p.sold[emblem_of(family, stat)]) + (p.sold[shard_of(family, stat)] > 0);
    bool checked = false;
    const auto& f = world.me().facts();
    for (int family = monster; family <= collectors; ++family)
        for (int stat = strength_stat; stat <= health_stat; ++stat) {
            if (!tavi_sells(family, stat)) continue;
            for (const bool emblem : {true, false}) {
                const auto item = emblem ? emblem_of(family, stat) : shard_of(family, stat);
                const unsigned have = items[item];
                if (!have || steps + (emblem ? static_cast<int>(have) : p.sold[item] > 0 ? 0 : 1) > most_sold_steps) continue;
                if (!checked && !cambc::self().can_sell()) return;
                checked = true;
                throw_if_stale();
                for (unsigned i = 0; i < have; ++i) {
                    if (cambc::detail::sdk_sell(static_cast<std::uint32_t>(item)) != 0) break;
                    steps += emblem || p.sold[item] == 0;
                    p.sold[item] += 1;
                    ++items_bought;
                    const unsigned shards = emblem ? shards_needed(family) : 1;
                    income.spent -= shard_price * shards; // not a kill's gold (note_income_end); wraps as the sums it enters do
                    Build sold;
                    add_shards(sold, f, stat, static_cast<float>(shards));
                    if (emblem) add_completion(sold, f, family, stat);
                    auto& t = tavi_planned;
                    if (!t.pending) t.dealt = world.me().dealt, t.camp_dealt = world.me().camp_dealt;
                    t.strength += sold.strength, t.focus += sold.focus, t.max_health += sold.max_health;
                    t.on = t.pending = true;
                    ++t.version;
                }
            }
        }
}

// At the turn's start, before anything reads our stats: Tavi plans its gold, alive or dead.
void plan_tavi(World& world) {
    tavi_world = nullptr;
    if (shops_at_home(world)) return;
    tavi_world = &world;
    // Kept from an earlier turn while its key holds: chosen when the gold came, as buy_shards chose before.
    plan_fresh(world);
    set_planned(world, planned_of(tavi));
}

// Before the next turn's world update, which does not read a dead champion's stats again: our record back to what
// we own.
void clear_planned(World& world) {
    set_planned(world, TaviPlanned{});
    tavi_planned.active = false;
}

// A plan that failed while made: none this turn, our record as owned, made afresh next turn (the sold items kept).
void abandon_plan(World& world) {
    tavi.n = 0;
    tavi.gold = ~0u;
    tavi_world = nullptr;
    clear_planned(world);
}

// A consumable from the gold past the steps keeps the plan; one from theirs (a crystal) has it made again.
void spent_beside_plan(unsigned cost) {
    if (!tavi_world || tavi.gold != my_gold() + cost) return;
    if (tavi.left >= cost) tavi.left -= cost, tavi.gold -= cost;
}

// The turn's start purchases: on our spawn the sale first, then the steps that must be bought now.
bool buy_planned_now() {
    auto& world = *tavi_world;
    if (world.me().alive && test(world.map().ally_spawn, my_position())) sell_on_spawn(world);
    plan_fresh(world);
    return execute_plan(world, true);
}

// The gold Tavi's plan keeps for its steps not yet bought. For a crystal (bought before shards), only for the sold
// items and the steps of earlier turns: buy_shards had spent the rest of that gold already.
unsigned kept_gold(bool crystal) {
    if (!tavi_world) return 0;
    // Off our spawn alive, a crystal waits for a later turn's purchase, after buy_shards'.
    crystal = crystal && (!tavi_world->me().alive || test(tavi_world->map().ally_spawn, my_position()));
    unsigned g = crystal ? 0 : tavi.held_gold;
    for (int k = 0; k < tavi.n; ++k)
        if (const auto& s = tavi.steps[static_cast<std::size_t>(k)]; !s.bought && (!crystal || s.restores_count || s.round < tavi_world->round))
            g += shard_price * s.count;
    return g;
}

// True if any shard was bought. Tavi buys by its plan.
bool buy_shards(const World& world) {
    if (tavi_world) return buy_planned_now();
    // Tavi without a plan this turn (abandon_plan): its gold, which may be a sale's, waits for the next.
    if (!shops_at_home(world)) return false;
    unsigned gold = my_gold();
    if (gold < shard_price) return false;
    const unsigned start = gold;
    Build bought;
    while (gold >= shard_price) {
        const auto [family, stat, saved, cost, passive] = best_emblem(world, bought);
        const unsigned have = my_items()[shard_of(family, stat)];
        const unsigned count = std::min<unsigned>(shards_needed(family) - have, gold / shard_price);
        if (!buy(shard_of(family, stat), count)) break;
        gold -= shard_price * count;
        add_shards(bought, world.me().facts(), stat, static_cast<float>(count));
        if (have + count == shards_needed(family)) add_completion(bought, world.me().facts(), family, stat);
    }
    return gold < start;
}

// Gold paid per base gold of a capture to a champion owning `owned`: the Treasure and Vesper Vale bonuses add.
float gold_rate(const ChampionFacts& f, const cambc::enum_map<cambc::item_type>& owned) {
    float rate = has_family(owned, treasure) ? 1.0f + treasure_gold : 1.0f;
    if (f.passive == Passive::bonus_gold)
        rate += static_cast<float>(cambc::constants::passive_abilities::vesper_vale_bonus_gold_percent) / 100.0f;
    return rate;
}

float gold_paid(const World& world) { return gold_rate(world.me().facts(), my_items()); }

// A visible ally's, read from its items.
float gold_paid(const ChampionBelief& a) {
    static cambc::enum_map<cambc::item_type> owned; // overwritten whole
    ok(cambc::detail::sdk_champion_items(static_cast<std::uint32_t>(a.handle), owned.ptr()));
    return gold_rate(a.facts(), owned);
}

// The bag reactive_tribute and reactive_over price, 0 below the size they need.
unsigned reactive_bag() {
    const unsigned bag = my_gems();
    return bag >= static_cast<unsigned>(params::trib_min_bag) ? bag : 0;
}

const Prices& prices(const World& world) {
    struct Key {
        float strength, focus, max_health;
        unsigned bag;
        int main;
        bool home, monster;
        bool operator==(const Key&) const = default;
    };
    static Key last{-1};
    static float chosen_at = -1, priced_at = -1;
    static Prices kept;
    const auto& self = world.me();
    const float share = gems_share(world);
    // The share moves a little most rounds (any score): the choice is kept until it moves by a
    // tenth (as affordable_prefix keeps its own), the prices follow it.
    if (const Key now{self.strength, self.focus, self.max_health, reactive_bag(), main_stat(world),
                      self.facts().passive == Passive::gem_focus && has_family(my_items(), home),
                      self.facts().passive == Passive::gem_focus && has_family(my_items(), monster)};
        !(now == last) || !(std::abs(share - chosen_at) <= 0.1f * chosen_at)) {
        last = now;
        chosen_at = share;
        // Tavi's planned shards bought, the next gold buys what follows them.
        kept.next = tavi_planned.pending ? best_emblem(world, planned_build(), &tavi.owned) : best_emblem(world);
        priced_at = -1;
    }
    if (share != priced_at) {
        priced_at = share;
        kept.gain = share * kept.next.saved * rounds_per_gem;
        kept.per_gold = params::gold_price_scale * share * kept.next.saved / static_cast<float>(std::max(1u, kept.next.cost));
        const float a = static_cast<float>(params::mid_gold_rise), b = static_cast<float>(params::mid_gold_hold),
                    c = static_cast<float>(params::mid_gold_end), t = static_cast<float>(std::max(world.score.ally, world.score.enemy));
        const float h = t < a ? t / a : t <= b ? 1.0f : std::max(0.0f, (c - t) / (c - b));
        kept.per_gold *= 1.0f + (params::mid_gold - 1.0f) * h;
    }
    return kept;
}

// Everything `gold_in` more gold buys, as buy_shards buys it, and the rounds it saves us over our
// share of the gems still to farm: the stats, and the passives of the emblems it completes. The
// saving is kept while our gold, stats and main stat hold.
PurchaseQuote affordable_prefix(const World& world, unsigned gold_in) {
    const unsigned budget = my_gold() + gold_in;
    if (budget < shard_price) return {};
    const auto& self = world.me();
    struct Key {
        unsigned shards;
        float strength, focus, max_health;
        unsigned bag;
        int main;
        bool operator==(const Key&) const = default;
    };
    static Key last{~0u};
    static PurchaseQuote kept;
    const Key key{budget / shard_price, self.strength, self.focus, self.max_health, reactive_bag(), main_stat(world)};
    const float rounds = gems_share(world) * rounds_per_gem;
    if (key == last) return {kept.next, kept.count, kept.gain * rounds};
    last = key;
    const auto& f = self.facts();
    auto owned = my_items();
    const auto build = [&](const Build& bought) { return build_of(world, owned, bought); };
    const Build now = build({});
    PurchaseQuote quote{best_emblem(world)};
    Build bought;
    float passives = 0;
    for (unsigned gold = budget; gold >= shard_price;) {
        const auto e = quote.count == 0 ? quote.next : best_emblem(world, bought, &owned);
        const unsigned have = owned[shard_of(e.family, e.stat)];
        const unsigned count = std::min<unsigned>(shards_needed(e.family) - have, gold / shard_price);
        gold -= shard_price * count;
        quote.count += count;
        add_shards(bought, f, e.stat, static_cast<float>(count));
        owned[shard_of(e.family, e.stat)] += count;
        if (have + count == shards_needed(e.family)) {
            add_completion(bought, f, e.family, e.stat);
            passives += e.passive;
            owned[shard_of(e.family, e.stat)] = 0;
            owned[emblem_of(e.family, e.stat)] += 1;
        }
    }
    float others;
    const Upkeep u = priced_upkeep(world, others);
    quote.gain = upkeep_cost(world, u, others, now, now) - upkeep_cost(world, u, others, now, build(bought)) + passives;
    kept = quote;
    return {quote.next, quote.count, quote.gain * rounds};
}

HomeTrip home_trip(const World& world, Pathing& pathing, int channel, bool wins) {
    const auto& field = pathing.to_any_altar();
    const vec2 land = recall_landing(world);
    const int out = field.at(land);
    // When hurt, the heal takes a turn unless the first step towards an altar stays on spawn.
    int hurt = 0;
    if (my_health() < my_max_health() && out != unreachable) {
        hurt = 1;
        for (const vec2 t : world.map().landing_tiles)
            if (dist(t, land) == 1 && field.at(t) == out - 1) {
                hurt = 0;
                break;
            }
    }
    HomeTrip t{channel, out, hurt, bag_rounds_left(world) - tribute_turns(world, my_gems())};
    if (wins || closing(world, pathing)) return t;
    t.heal = heal_rounds_now(world);
    if (!shops_at_home(world)) return t;
    const auto& p = prices(world);
    const std::uint32_t gold = my_gold();
    t.short_gold = gold >= p.next.cost ? 0 : p.next.cost - gold;
    t.emblem = p.gain;
    return t;
}

// The stop's value as home_trip prices it for an empty bag: the heal, and the next emblem once our
// gold completes it; nothing once the end is close.
FarmRecall farm_recall(const World& world, Pathing& pathing, int channel) {
    FarmRecall r{channel, my_health() < my_max_health() ? 1 : 0, 0.0f};
    if (closing(world, pathing)) return r;
    r.value = heal_rounds_now(world);
    if (shops_at_home(world))
        if (const auto& p = prices(world); my_gold() >= p.next.cost && std::isfinite(p.gain)) r.value += p.gain;
    return r;
}

// At the turn's start, what came since our last turn's end: a capture payout if we ended it on a
// group (the capture phase pays before any turn, and a recall may since have taken us home; a bag
// emptied by a completed tribute is skipped).
void note_income_start(const World& world) {
    const std::uint32_t gems = my_gems(), gold = my_gold();
    if (income.end_round == world.round - 1 && gems >= income.gems_at && (gems > income.gems_at || gold > income.gold_at))
        if (const int g = world.map().group_at(income.end_pos); g >= 0) {
            const auto& G = world.map().groups[g];
            const float gained = static_cast<float>(gems - income.gems_at), base_gold = static_cast<float>(gold - income.gold_at) / gold_paid(world);
            income.holds += 1;
            income.gems += gained;
            income.capture_gold += base_gold;
            if (!world.me().prospector) {
                // From our share: the sharers may be out of sight by now.
                const float share = gained > 0 ? gained / static_cast<float>(std::max(1, G.gems)) : base_gold / static_cast<float>(std::max(1, G.gold));
                const int sharers = share > 0 ? std::max(1, static_cast<int>(std::lround(1.0f / share))) : 1;
                income.prospected_gems += static_cast<float>(prospected(G.cluster_gems, sharers));
                income.prospected_gold += static_cast<float>(prospected(G.cluster_gold, sharers));
            }
        }
    income.start_round = world.round, income.gems_at = gems, income.gold_at = gold, income.spent = 0;
}

// At the turn's end, what our turn brought: only a kill pays in it (its bag, and its gold beside
// what we spent).
void note_income_end(const World& world) {
    const std::uint32_t gems = my_gems(), gold = my_gold();
    if (income.start_round == world.round) {
        if (gems > income.gems_at) income.gems += static_cast<float>(gems - income.gems_at);
        if (gold + income.spent >= income.gold_at + kill_base_gold)
            income.kill_gold += static_cast<float>(gold + income.spent - income.gold_at) / gold_paid(world);
    }
    income.end_round = world.round, income.gems_at = gems, income.gold_at = gold, income.end_pos = my_position();
}

// With no bag to bank and the gold to complete the next emblem (Prism: any shard), home to shop when
// what it buys and the heal save outweigh the trip: there by recall unless walking is quicker, and
// back out.
[[gnu::flatten]] bool wants_shop(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    if (banks_bag(world, pathing) || memory.damage > 0 || !shops_at_home(world)) return false;
    const auto gold = my_gold();
    const bool prism = world.me().facts().passive == Passive::gem_focus;
    if (gold < shard_price || (!prism && gold < emblem_price && !begun_emblem(world, my_items()))) return false;
    const vec2 here = my_position();
    if (test(world.map().ally_spawn, here) || safety.threatened(here)) return false;
    // The trip costs the recall and the walk back out; arriving by recall, the heal takes the turn.
    if (prism) {
        if (winning_bag(world) || closing(world, pathing)) return false;
        const int back = pathing.to_ally_spawn().at(here);
        if (back == unreachable) return false;
        const int hurt = my_health() < my_max_health() ? 1 : 0;
        const float value = params::shop_gain_scale * affordable_prefix(world).gain + heal_rounds_now(world);
        if (!std::isfinite(value) || !(value > static_cast<float>(std::min(back, recall_turns(world) + hurt) + back))) return false;
    } else {
        const auto stop = home_trip(world, pathing, recall_turns(world), winning_bag(world));
        if (stop.short_gold > 0) return false;
        const int back = pathing.to_ally_spawn().at(here);
        if (back != unreachable && stop.heal + params::shop_gain_scale * affordable_prefix(world).gain < static_cast<float>(std::min(back, stop.channel + stop.hurt) + back)) return false;
    }
    bool awake = false;
    world.each_stirring([&](int g) { awake = awake || awake_over(world, g, here); });
    return !awake;
}

} // namespace

// util.h before_damage: Tavi buys its planned shards, on more gold if a kill brought some since the plan.
void materialize_planned() {
    if (!tavi_world) return;
    plan_fresh(*tavi_world);
    execute_plan(*tavi_world, false);
}

} // namespace aph
