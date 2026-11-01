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
        income.spent += shard_price * count;
        return true;
    } catch (const cambc::error&) {
        return false;
    }
}

void buy_consumable(cambc::consumable_type type) {
    auto& me = cambc::self();
    try {
        if (me.can_buy(type)) throw_if_stale(), me.buy(type), income.spent += type.cost();
    } catch (const cambc::error&) {
    }
}

// Locks on our own and middle altars keep the enemy's bags from scoring there until broken.
void buy_lock() { buy_consumable(cambc::consumable_type::altar_lock); }

bool carries_crystal() { return cambc::self().consumables()[cambc::consumable_type::tp_crystal].count() > 0; }
bool can_buy_crystal() { return my_gold() >= cambc::consumable_type::tp_crystal.cost(); }

// Once a hop to an altar only a crystal reaches (StaticMap::hops) would have beaten walking to bank.
void buy_crystal(const Memory& memory) {
    if (memory.wants_crystal) buy_consumable(cambc::consumable_type::tp_crystal);
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
        upkeep.camp_taken += camp;
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
// Set in buy_shards: only its best_emblem calls start a learned emblem, so prices and quotes follow the
// current logic until the emblem's first shard is bought.
bool shopping = false;

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

// Our build with `bought` added to our stats, owning `owned`.
Build build_of(const World& world, const cambc::enum_map<cambc::item_type>& owned, const Build& bought) {
    const auto& self = world.me();
    return Build{self.strength + bought.strength, self.focus + bought.focus, self.max_health + bought.max_health,
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
// stat, Greed ten more.
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
// meanwhile; health lost comes back by a recall and the walk out, a trip per usable health (above
// the recall line).
float upkeep_cost(const World& world, const Upkeep& upkeep, float others, const Build& now, const Build& b) {
    const auto out = [&](const Build& x) { return std::max(1.0f, world.me().facts().raw_output(x.strength, x.focus)); };
    const float turns = static_cast<float>(std::max(1, upkeep.turns));
    const float steps = mean_spawn_steps(upkeep);
    const float clear = (others + out(now) * now.camp_dealt) / (others + out(b) * b.camp_dealt);
    const float camp = upkeep.camp_taken / turns * clear * b.camp_taken / now.camp_taken;
    const float taken = (camp + upkeep.champ_taken / turns) * b.taken / now.taken;
    const float usable = b.max_health * (1.0f - params::recall_health_fraction);
    // Counted from one clearing turn in one: before our first camp hit, gold (priced by this
    // saving) is still worth farming.
    const float clearing = static_cast<float>(upkeep.camp_turns + 1) / static_cast<float>(upkeep.turns + 1);
    return clearing * clear + taken * (static_cast<float>(b.recall) + steps) / usable;
}

// Our mean steps from spawn while alive: the walk back out after a heal.
float spawn_steps(const World& world) {
    fold_upkeep(world.map());
    return mean_spawn_steps(upkeep);
}

// Rounds `damage` costs, priced as upkeep_cost prices it: a heal trip (a recall and the walk `out`
// back out) per usable health.
float heal_rounds(const World& world, float damage, float out) {
    const float usable = my_max_health() * (1.0f - params::recall_health_fraction);
    return damage / usable * (static_cast<float>(recall_turns(world)) + out);
}
// heal_rounds for the damage we carry, back out by our mean steps from spawn (made only when hurt).
float heal_rounds_now(const World& world) {
    const float damage = my_max_health() - my_health();
    return heal_rounds(world, damage, damage > 0 ? spawn_steps(world) : 0.0f);
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
    case tribute: return per_turn(income.tribute_cut, prior_tribute_cut);
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
    const float base = upkeep_cost(world, u, others, now, now);
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
        return {family, stat, base - upkeep_cost(world, u, others, now, b), left * shard_price};
    };
    const bool three = economy_three(world);
    // The best stat emblem: a Power, Jungle, Durability or Bruiser one (Vendetta's Monster too).
    const auto best_stat = [&](int main) {
        Emblem best = value(power, main);
        if (const auto e = value(jungle, main); e.saved > best.saved) best = e;
        if (const auto e = value(durability, health_stat); e.saved > best.saved) best = e;
        if (const auto e = value(bruiser, main); e.saved > best.saved) best = e;
        if (const auto e = value(bruiser, health_stat); e.saved > best.saved) best = e;
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
        for (const int family : {prospector, capture, treasure, hunter, tribute})
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

// The current logic's emblem, except that a new emblem buy_shards starts is the learned one (tools/emblab) for our
// pick count, type and count of emblems owned, unless its passive is already ours.
Emblem best_emblem(const World& world, const Build& bought = {}, const cambc::enum_map<cambc::item_type>* items = nullptr) {
    const int picks = economy_pick_count(world), type = static_cast<int>(world.me().type);
    if (!shopping || items || picks < 3 || picks > 5) return current_emblem(world, bought, items);
    const auto& owned = my_items();
    if (begun_emblem(world, owned)) return current_emblem(world, bought, items);
    unsigned ordinal = 0;
    for (int family = monster; family <= collectors; ++family)
        for (int stat = strength_stat; stat <= health_stat; ++stat) ordinal += owned[emblem_of(family, stat)];
    if (ordinal >= std::size(learned_arm[0][0])) return current_emblem(world, bought, items);
    const int arm = learned_arm[picks - 3][type][ordinal], family = arm / 3;
    if (arm == 255 || (family != power && family != bruiser && has_family(owned, family))) return current_emblem(world, bought, items);
    pin_family = family, pin_stat = arm % 3;
    const Emblem e = current_emblem(world, bought, nullptr);
    pin_family = -1;
    return e;
}

// True if any shard was bought.
bool buy_shards(const World& world) {
    shopping = true;
    struct Done {
        ~Done() { shopping = false; }
    } done;
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

const Prices& prices(const World& world) {
    struct Key {
        float share, strength, focus, max_health;
        int main;
        bool home, monster;
        bool operator==(const Key&) const = default;
    };
    static Key last{-1};
    static Prices kept;
    const auto& self = world.me();
    if (const Key now{gems_share(world), self.strength, self.focus, self.max_health, main_stat(world),
                      self.facts().passive == Passive::gem_focus && has_family(my_items(), home),
                      self.facts().passive == Passive::gem_focus && has_family(my_items(), monster)}; !(now == last)) {
        last = now;
        kept.next = best_emblem(world);
        kept.gain = now.share * kept.next.saved * rounds_per_gem;
        kept.per_gold = params::gold_price_scale * now.share * kept.next.saved / static_cast<float>(std::max(1u, kept.next.cost));
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
        int main;
        bool operator==(const Key&) const = default;
    };
    static Key last{~0u};
    static PurchaseQuote kept;
    const Key key{budget / shard_price, self.strength, self.focus, self.max_health, main_stat(world)};
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
        const float value = affordable_prefix(world).gain + heal_rounds_now(world);
        if (!std::isfinite(value) || !(value > static_cast<float>(std::min(back, recall_turns(world) + hurt) + back))) return false;
    } else {
        const auto stop = home_trip(world, pathing, recall_turns(world), winning_bag(world));
        if (stop.short_gold > 0) return false;
        const int back = pathing.to_ally_spawn().at(here);
        if (back != unreachable && stop.heal + affordable_prefix(world).gain < static_cast<float>(std::min(back, stop.channel + stop.hurt) + back)) return false;
    }
    bool awake = false;
    world.each_stirring([&](int g) { awake = awake || awake_over(world, g, here); });
    return !awake;
}

} // namespace

} // namespace aph
