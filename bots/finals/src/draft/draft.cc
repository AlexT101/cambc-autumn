#include "draft.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cstdio>
#include <cstring>
#include <string_view>
#include <cmath>
#include <limits>
#include <optional>
#include <span>
#include <vector>
#include <wasm_simd128.h>
#include "draft_model.h"
#include "map_economy.h"
#include "map_features.h"
#include "../params.h"
#include "../util.h"
#include "../model/world.h"
#include "../book/book.h"

namespace aph {

namespace {

int draft_round() { return static_cast<int>(cambc::round_number()); }

constexpr auto all_champions() {
    std::array<cambc::champion_draft, static_cast<std::size_t>(cambc::champion_draft::heart_of_ruin) + 1> all{};
    for (std::size_t i = 0; i < all.size(); ++i) all[i] = static_cast<cambc::champion_draft>(i);
    return all;
}

const std::vector<cambc::champion_draft>* model_draft();
// What the model draft's features cost (model::measure), if it measured them.
mapfeat::Work feature_work;
bool features_measured = false;

// The table drafts and their fallbacks never pick Vesper Vale; test and model drafts may.
bool vesper_allowed() {
    return params::test_draft || model_draft() != nullptr;
}

// The team lock (draft_model.h required and banned; a user decision, 2026-11-03): always Cassi & Issac, never
// Stellar. Off on test drafts (ladder compositions) and in the draft lab's vehicles (tools/draftlab/vehicle.py),
// whose tables draft both sides.
bool team_locked() {
    return !params::test_draft;
}

constexpr unsigned bit(cambc::champion_draft c) { return 1u << static_cast<int>(c); }

// Banned, or not a missing required champion once the picks left only cover those.
bool lock_forbids(cambc::champion_draft pick, const std::vector<cambc::champion_draft>& ours) {
    if (!team_locked()) return false;
    if (draft_model::banned & bit(pick)) return true;
    unsigned missing = draft_model::required;
    for (const auto c : ours) missing &= ~bit(c);
    const int left = static_cast<int>(cambc::draft::team_size()) - static_cast<int>(ours.size());
    return !(missing & bit(pick)) && std::popcount(missing) >= left;
}

// Banned champions out, and a required one missing from the team's picks moved first. The model's teams already obey
// the lock and keep their order; the tables may not.
std::vector<cambc::champion_draft> locked(std::vector<cambc::champion_draft> order) {
    if (!team_locked()) return order;
    std::erase_if(order, [](cambc::champion_draft c) { return (draft_model::banned & bit(c)) != 0; });
    const auto n = static_cast<std::ptrdiff_t>(cambc::draft::team_size());
    for (int c = draft_model::champions - 1; c >= 0; --c) {
        if (!(draft_model::required & (1u << c))) continue;
        const auto pick = static_cast<cambc::champion_draft>(c);
        const auto at = std::find(order.begin(), order.end(), pick);
        if (at - order.begin() < n) continue;
        if (at != order.end()) order.erase(at);
        order.insert(order.begin(), pick);
    }
    return order;
}

// A rejected pick does not spend the turn, so trying the next candidate is always safe.
bool pick_first_available(DraftState& state, std::span<const cambc::champion_draft> order) {
    const auto ours = cambc::draft::current_draft(team::ally);
    for (const auto pick : order) {
        if (!vesper_allowed() && pick == cambc::champion_draft::vesper_vale) continue;
        if (lock_forbids(pick, ours)) continue;
        if (std::find(ours.begin(), ours.end(), pick) != ours.end()) continue;
        try {
            cambc::draft::pick(pick);
            state.picked_round = draft_round();
            return true;
        } catch (const cambc::error&) {
        }
    }
    return false;
}

// A draft turn keeps this for the plan's write and the pick. The first turn (10M) keeps more: the analysis' cost
// estimates (a ward site, the index) run short on the heaviest maps, and a turn that runs out before its pick makes
// the whole draft random (40k lost ~40 of 67k pool maps once the map features left the analysis more fuel).
std::uint64_t draft_reserve() { return draft_round() == 0 ? 500000 : 40000; }

constexpr int champion_types = static_cast<int>(cambc::champion_type::heart_of_ruin) + 1;

// Farm's round-1 view of a champion of one type (rank_body): full health, base stats, every camp
// asleep at full health, gold at a typical price. Per group: its worth (negative if farm never
// picks it), and the rounds and camp damage of clearing it alone, spells kiting where farm would.
struct TypeFacts {
    bool ready = false;
    float output = 0, spare = 0;
    std::vector<float> worth, clear, damage;
};

struct DraftGroupFacts {
    std::size_t begin = 0, size = 0;
    float attackers = 0, rest = 0;
    bool kites = true;
};

// The static map analysis every champion would repeat, carried over draft turns while fuel lasts.
struct Analysis {
    std::unique_ptr<StaticMap> map;
    std::vector<std::array<std::uint16_t, 3>> steps; // per group: from our spawn, theirs, the altars
    std::vector<std::array<std::uint16_t, DraftPlan::max_spawn_tiles>> spawn_steps; // per group, per ally spawn tile
    int fields = 0; // of those 3 and the spawn tiles', done
    int attack_group = 0, attack_member = 0;
    int attack_index = 0, attack_at = 0; // members done; the next bush bit's place in the plan
    int attack_start = 0;                // the attack tiles' first bit
    bool attacks_done = false;           // attack_at is then where the attack tiles end
    std::vector<std::uint16_t> ward_codes; // per ward site whose code fits in the plan, 0 until searched
    int ward_site = 0, ward_bits = -1;     // sites searched; the section's code width, -1 until set
    int wards_written = 0;                 // ward_site at the section's last write
    int dash_fields = 0;                 // of check_dash_steps' fields, done
    bool dash_spawn = true, dash_altar = true; // their steps so far equal the plan's
    std::array<TypeFacts, champion_types> types;
    std::vector<DraftGroupFacts> group_facts;
    std::vector<std::pair<float, float>> sorted;
    // The leads (group + 1, 0 for none) of the first `leads_made` bodies of `lead_for`, the team
    // we expect; later ones may be left from an earlier guess.
    std::vector<cambc::champion_type> lead_for;
    std::array<std::array<int, DraftPlan::leads>, DraftPlan::lead_bodies> leads{};
    int leads_made = 0;
    int leads_at = 0; // the leads' first bit once the attack tiles are done, 0 if they and the whole ward section do not fit
    // Per lead body expected to dash (dash_entry): its kind (0: no entry), spawn tile's index,
    // Rice parameter and codes; the bodies done; the section's length once written (0: none).
    std::array<int, DraftPlan::lead_bodies> dash_kind{}, dash_tile{}, dash_rice{};
    std::array<std::vector<std::uint32_t>, DraftPlan::lead_bodies> dash_codes;
    int dash_bodies = 0, dash_bits = 0;
    bool done = false;
    bool indexed = false; // the index section is settled, written or not
    unsigned capped = 0;  // DraftCap bits: the sections the first turn's cap cut short
    bool budgeted = false; // work_budget has set the two limits below
    bool opened = false;   // the opening plan was tried (first turn only)
    int attack_groups_max = std::numeric_limits<int>::max(), ward_sites_max = std::numeric_limits<int>::max();
};

int lead_bits(const StaticMap& map) {
    return DraftPlan::lead_bodies * DraftPlan::leads * lead_width(static_cast<int>(map.groups.size()));
}

// The ward section follows the leads, if they fit.
int wards_from(const StaticMap& map, const Analysis& a) { return a.leads_at > 0 ? a.leads_at + lead_bits(map) + a.dash_bits : a.attack_at; }

// Our body b's start tile: champions start in landing order (recall.landing).
vec2 body_tile(const StaticMap& map, int b) {
    return map.landing_tiles[std::min<std::size_t>(static_cast<std::size_t>(b), map.landing_tiles.size() - 1)];
}

// Body b's start tile's index in map.ally_spawn_tiles.
int body_spawn_index(const StaticMap& map, int b) {
    const auto& tiles = map.ally_spawn_tiles;
    return static_cast<int>(std::find(tiles.begin(), tiles.end(), body_tile(map, b)) - tiles.begin());
}

// The Rice parameter that codes `codes` shortest.
int best_rice(const std::vector<std::uint32_t>& codes) {
    int best = 1 << 30, best_k = 0;
    for (int k = 0; k <= PlanHeader::max_rice; ++k) {
        int bits = 0;
        for (const auto c : codes) bits += PlanWriter::rice_bits(c, k);
        if (bits < best) best = bits, best_k = k;
    }
    return best_k;
}

// Every altar's tribute tiles.
bitboard tribute_tiles(const StaticMap& map) {
    bitboard tiles;
    for (const auto& altar : map.altars) tiles |= altar.tribute_tiles();
    return tiles;
}

// A field champions take from the plan instead of building, so left out of the layers and cost
// the plan reports.
Field uncounted_field(const bitboard& walls, const bitboard& goals) {
    const int layers = max_field_layers();
    const auto costliest = costliest_field();
    auto field = make_field(walls, goals);
    max_field_layers() = layers, costliest_field() = costliest;
    return field;
}

float base_output(cambc::champion_type type) {
    const auto& f = facts(type);
    return std::max(1.0f, f.raw_output(f.strength.base, f.focus.base));
}

// Every body and the opening planner use the same member order and base camp health.
void group_facts(const StaticMap& map, Analysis& a) {
    a.group_facts.resize(map.groups.size());
    a.sorted.reserve(map.camp_members.size());
    for (std::size_t g = 0; g < map.groups.size(); ++g) {
        const auto& group = map.groups[g];
        auto& f = a.group_facts[g];
        f.begin = a.sorted.size();
        if (group.has_monolith || group.gems + group.gold == 0) continue;
        for (const auto& m : group.members) {
            a.sorted.push_back({m.max_health, m.strength});
            if (m.strength > 0) f.attackers += m.max_health, f.kites = f.kites && m.reach < ability_range;
            else f.rest += m.max_health;
        }
        f.size = a.sorted.size() - f.begin;
        std::sort(a.sorted.begin() + f.begin, a.sorted.end(), [](const auto& x, const auto& y) { return x.second * y.first > y.second * x.first; });
    }
}

std::span<const std::pair<float, float>> sorted_members(const Analysis& a, std::size_t g) {
    const auto& f = a.group_facts[g];
    return std::span{a.sorted}.subspan(f.begin, f.size);
}

// Camp damage taken clearing `left` in order at `strength` a round; `rounds`, the rounds taken.
float clear_damage(std::span<const std::pair<float, float>> left, float strength, float& rounds) {
    float damage = 0;
    rounds = 0;
    for (const auto& [hp, hits] : left) {
        rounds += std::ceil(hp / strength);
        damage += hits * (rounds - 1);
    }
    return damage;
}

// The drafted walk between a recall's landing tile and group g's centre; the straight line where none reaches.
int landing_steps(const StaticMap& map, const Analysis& a, int g) {
    const auto& tiles = map.ally_spawn_tiles;
    const auto i = static_cast<std::size_t>(std::find(tiles.begin(), tiles.end(), map.landing_tiles[0]) - tiles.begin());
    const int steps = !a.spawn_steps.empty() && i < tiles.size() ? a.spawn_steps[g][i] : a.steps[g][0];
    return steps != unreachable ? steps : dist(map.landing_tiles[0], map.groups[g].centre);
}

void type_facts(const StaticMap& map, const Analysis& a, cambc::champion_type type, TypeFacts& out) {
    const auto& f = facts(type);
    const float s = base_output(type);
    float spells = 0;
    if (f.ranged)
        for (const auto& ab : f.abilities)
            if (ab.kind == AbilityKind::damage) spells += ab.multiplier * f.focus.base / static_cast<float>(ability_cooldown);
    const float basic = std::max(1.0f, f.strength.base * (f.has_attack_reset() ? 1.0f + 1.0f / static_cast<float>(ability_cooldown) : 1.0f));
    const float usable = f.health.base * (1.0f - params::draft_recall_health_fraction);
    const float paid = f.passive == Passive::bonus_gold ? 1.0f + static_cast<float>(cambc::constants::passive_abilities::vesper_vale_bonus_gold_percent) / 100.0f : 1.0f;
    // Farm's gold farmers: Cassi, and Tavi on 3-pick maps of pure-gold groups (economy/farm.cc farm).
    const bool gold_farmer = type == cambc::champion_type::cassi
                             || (type == cambc::champion_type::tavi && cambc::draft::team_size() == 3 && map_economy(map).tavi_map());
    const float per_gold = 0.2f * paid * (gold_farmer ? params::gold_farmer_weight : 1.0f);
    const float per_gem = 1.0f + per_gold * f.tribute_gold_per_gem();
    out.output = s;
    out.spare = usable / params::camp_risk;
    const auto n = map.groups.size();
    out.worth.assign(n, -1), out.clear.assign(n, 0), out.damage.assign(n, 0);
    for (std::size_t g = 0; g < n; ++g) {
        const auto& group = map.groups[g];
        if (group.has_monolith || group.gems + group.gold == 0) continue;
        const auto& G = a.group_facts[g];
        float alone = 0;
        float damage = clear_damage(sorted_members(a, g), s, alone), clear = alone;
        if (spells > 0 && group.strength > 0 && G.kites) {
            const float kite = G.attackers / spells + G.rest / (basic + spells);
            // Each trip home walks there and back or recalls and walks back (heal_trip), whichever is quicker.
            const auto steps = static_cast<float>(landing_steps(map, a, static_cast<int>(g)));
            const float heal = damage / usable * std::min(2.0f * steps, static_cast<float>(cambc::constants::recall_time) + steps);
            if (damage > out.spare || kite < alone + heal) clear = kite, damage = 0;
        }
        const int gems = std::min(group.gems, static_cast<int>(cambc::constants::winning_gems));
        out.worth[g] = per_gem * static_cast<float>(gems) + per_gold * static_cast<float>(group.gold);
        out.clear[g] = clear, out.damage[g] = damage;
    }
    out.ready = true;
}

// Body b's leads from its type's facts: the groups it would value most from its spawn tile, past
// each earlier body's first lead (its likely claim, made before b acts). A clear too costly alone
// may be shared with the strongest later body, still unclaimed when b acts. Only a guess:
// champions weigh the leads first, and the choice is theirs either way.
void rank_body(const StaticMap& map, Analysis& a, int b) {
    const auto& T = a.types[static_cast<std::size_t>(a.lead_for[b])];
    float partner = 0;
    for (std::size_t j = static_cast<std::size_t>(b) + 1; j < a.lead_for.size(); ++j) partner = std::max(partner, base_output(a.lead_for[j]));
    const float horizon = 100.0f * std::max(1.0f, static_cast<float>(std::max(map.width, map.height)) / 50.0f);
    const float cap = static_cast<float>(cambc::constants::capture_time + 1);
    const int i = body_spawn_index(map, b);
    const bool by_tile = !a.spawn_steps.empty() && i < static_cast<int>(map.ally_spawn_tiles.size());
    std::array<std::pair<float, int>, DraftPlan::leads> top;
    top.fill({0.0f, -1});
    for (int g = 0; g < static_cast<int>(map.groups.size()); ++g) {
        float worth = T.worth[g], clear = T.clear[g];
        const int steps = by_tile ? a.spawn_steps[g][i] : a.steps[g][0];
        if (worth < 0 || steps == unreachable) continue;
        bool claimed = false;
        for (int j = 0; j < b; ++j) claimed |= a.leads[j][0] == g + 1;
        if (claimed) continue;
        if (T.damage[g] > T.spare) {
            if (partner <= 0) continue;
            const float part = T.output / (T.output + partner);
            if (clear_damage(sorted_members(a, g), T.output + partner, clear) * part > T.spare) continue;
            worth *= part;
        }
        const float rounds = std::max(1.0f, static_cast<float>(steps) + clear + cap);
        const float value = worth / (rounds * (1.0f + rounds / horizon));
        if (value <= top.back().first) continue;
        top.back() = {value, g};
        for (std::size_t j = top.size() - 1; j > 0 && top[j].first > top[j - 1].first; --j) std::swap(top[j], top[j - 1]);
    }
    for (std::size_t j = 0; j < top.size(); ++j) a.leads[b][j] = top[j].second + 1;
}

std::vector<cambc::champion_type> expected_bodies();

// Leads for the team we now expect, as far as fuel above `reserve` allows; a changed guess
// starts them again.
void make_leads(const StaticMap& map, Analysis& a, std::uint64_t reserve) {
    if (auto expected = expected_bodies(); expected != a.lead_for)
        a.lead_for = std::move(expected), a.leads_made = 0, a.dash_bodies = 0, a.dash_kind = {}; // the dash entries are per lead body too
    const auto n = map.groups.size();
    if (a.group_facts.empty()) group_facts(map, a);
    for (; a.leads_made < static_cast<int>(std::min<std::size_t>(a.lead_for.size(), DraftPlan::lead_bodies)); ++a.leads_made) {
        auto& T = a.types[static_cast<std::size_t>(a.lead_for[a.leads_made])];
        if (!T.ready) {
            if (!fuel_ok(reserve + 5000 + 600 * n)) return;
            type_facts(map, a, a.lead_for[a.leads_made], T);
        }
        if (!fuel_ok(reserve + 3000 + 400 * n)) return;
        rank_body(map, a, a.leads_made);
    }
}

Analysis& analysis() {
    static Analysis a;
    return a;
}

void set_steps(const StaticMap& map, const Field& field, int which, Analysis& a) {
    for (std::size_t g = 0; g < map.groups.size(); ++g) {
        const auto steps = static_cast<std::uint16_t>(field.at(map.groups[g].centre));
        if (which < 3) a.steps[g][which] = steps;
        else a.spawn_steps[g][which - 3] = steps;
    }
}

std::uint32_t zigzag(int v) { return v >= 0 ? 2u * static_cast<std::uint32_t>(v) : 2u * static_cast<std::uint32_t>(-v) - 1; }

// The group entries; false if they do not fit or would not decode to these steps.
bool write_steps(const StaticMap& map, Analysis& a, int spawn_fields, DraftPlan& plan, PlanHeader& header) {
    const int n = static_cast<int>(map.groups.size());
    const auto ally = TileBox::of(map.ally_spawn_tiles), enemy = TileBox::of(map.enemy_spawn.positions());
    header.mirrored = true;
    for (int g = 0; g < n && header.mirrored; ++g) header.mirrored = map.group_at(map.mirror(map.groups[g].centre)) >= 0;
    std::array<std::vector<std::uint32_t>, 3> codes;
    for (int which = 0; which < 3; ++which) {
        for (int g = 0; g < n; ++g) {
            if (which == 1 && header.mirrored) {
                const int m = map.group_at(map.mirror(map.groups[g].centre));
                codes[which].push_back(zigzag(a.steps[g][1] - a.steps[m][0]));
                continue;
            }
            const int steps = a.steps[g][which], bound = steps_bound(ally, enemy, map.groups[g].centre, which);
            if (steps != unreachable && steps < bound) return false;
            codes[which].push_back(steps == unreachable ? 0 : static_cast<std::uint32_t>(steps - bound + 1));
        }
        header.rice[which] = static_cast<std::uint8_t>(best_rice(codes[which]));
    }
    PlanWriter w{plan, plan_body_at(plan)};
    for (int which = 0; which < 3; ++which)
        for (const auto c : codes[which])
            if (!w.put_rice(c, header.rice[which])) return false;
    bool offsets_fit = spawn_fields > 0;
    std::vector<std::uint32_t> offsets(n);
    for (int g = 0; g < n && offsets_fit; ++g)
        for (int i = 0; offsets_fit && i < spawn_fields; ++i) {
            const int base = a.steps[g][0], steps = a.spawn_steps[g][i];
            const int over = base == unreachable ? 0 : steps - base;
            offsets_fit = over >= 0 && over <= 3 && (base != unreachable || steps == unreachable);
            offsets[g] |= static_cast<std::uint32_t>(over) << (2 * i);
        }
    header.spawn_offsets = offsets_fit;
    const auto offset = [&](const DraftSteps& d, int g, int i) {
        return d.predicted[g] ? static_cast<std::uint32_t>(spawn_offset(ally, map.ally_spawn_tiles[i], map.groups[g].centre))
                              : d.offsets[g] >> (2 * i) & 3;
    };
    for (int g = 0; g < n && offsets_fit; ++g) {
        if (a.steps[g][0] == unreachable) continue;
        bool predicted = true;
        for (int i = 0; i < spawn_fields; ++i)
            predicted &= (offsets[g] >> (2 * i) & 3) == static_cast<std::uint32_t>(spawn_offset(ally, map.ally_spawn_tiles[i], map.groups[g].centre));
        if (!w.put(predicted, 1) || (!predicted && !w.put(offsets[g], 2 * spawn_fields))) return false;
    }
    DraftSteps check;
    if (!decode_steps(plan, header, map, check) || check.end != w.at()) return false;
    for (int g = 0; g < n; ++g) {
        if (check.ally[g] != a.steps[g][0] || check.enemy[g] != a.steps[g][1] || check.altar[g] != a.steps[g][2]) return false;
        if (!header.spawn_offsets || check.ally[g] == unreachable) continue;
        for (int i = 0; i < spawn_fields; ++i)
            if (check.ally[g] + offset(check, g, i) != a.spawn_steps[g][i]) return false;
    }
    a.attack_start = w.at();
    return true;
}

// PlanHeader::tributes_walked. Live camps are a subset of the camp tiles, so a tile walkable with
// all of them standing is walkable with any.
bool tributes_walked(const StaticMap& map) {
    auto tributes = tribute_tiles(map);
    bitboard walls{cambc::uninitialized}, walk{cambc::uninitialized}, on_camps{cambc::uninitialized};
    or_into(map.blocked_for_us, map.camp_tiles, walls);
    walls.reachable_tiles_into(map.ally_spawn_tiles[0], unreachable, walk);
    and_into(tributes, map.camp_tiles, on_camps);
    if (board_empty(tributes) || !board_empty(on_camps)) return false;
    drop(tributes, walk);
    return board_empty(tributes);
}

// PlanHeader::dash_spawn_steps and dash_altar_steps, field `i` of a dash's walls: from ally spawn
// tile i, or after them from the tribute tiles.
void check_dash_steps(const StaticMap& map, Analysis& a, int i, int spawn_fields) {
    const auto field = uncounted_field(map.dash_walls, i < spawn_fields ? single(map.ally_spawn_tiles[i]) : tribute_tiles(map));
    for (std::size_t g = 0; g < map.groups.size(); ++g) {
        const int steps = field.at(map.groups[g].centre);
        if (i < spawn_fields) a.dash_spawn = a.dash_spawn && steps == a.spawn_steps[g][i];
        else a.dash_altar = a.dash_altar && steps == a.steps[g][2];
    }
}

// Body b's entry in the dash steps, for a dash of `kind` from its spawn tile.
void dash_entry(const StaticMap& map, Analysis& a, int b, int kind) {
    const int i = body_spawn_index(map, b);
    if (i >= static_cast<int>(map.ally_spawn_tiles.size()) || i >= 1 << dash_tile_bits) return;
    const vec2 tile = map.ally_spawn_tiles[i];
    const auto field = uncounted_field(kind == 1 ? map.dash_walls : map.landing_dash_walls, single(tile));
    auto& codes = a.dash_codes[b];
    codes.clear();
    for (const auto& group : map.groups) {
        const int steps = field.at(group.centre), bound = dist(tile, group.centre);
        if (steps != unreachable && steps < bound) return;
        codes.push_back(steps == unreachable ? 0u : static_cast<std::uint32_t>(steps - bound) + 1);
    }
    a.dash_kind[b] = kind, a.dash_tile[b] = i, a.dash_rice[b] = best_rice(codes);
}

// The dash steps after the leads; none if they do not fit or would not decode to these codes.
void write_dash_steps(const StaticMap& map, Analysis& a, DraftPlan& plan, PlanHeader& header) {
    const int at = a.leads_at + lead_bits(map);
    PlanWriter w{plan, at};
    bool fits = true;
    for (int b = 0; b < DraftPlan::lead_bodies && fits; ++b) {
        fits = w.put(static_cast<std::uint32_t>(a.dash_kind[b]), dash_kind_bits);
        if (!a.dash_kind[b] || !fits) continue;
        int length = 0;
        for (const auto c : a.dash_codes[b]) length += PlanWriter::rice_bits(c, a.dash_rice[b]);
        fits = length < 1 << PlanHeader::at_bits && w.put(static_cast<std::uint32_t>(a.dash_tile[b]), dash_tile_bits)
               && w.put(static_cast<std::uint32_t>(a.dash_rice[b]), PlanHeader::rice_bits) && w.put(static_cast<std::uint32_t>(length), PlanHeader::at_bits);
        for (const auto c : a.dash_codes[b])
            if (fits) fits = w.put_rice(c, a.dash_rice[b]);
    }
    PlanHeader check = header;
    check.dash_steps = true, check.leads_at = static_cast<std::uint16_t>(a.leads_at);
    std::array<DashEntry, DraftPlan::lead_bodies> entries;
    bool same = fits && index_dash_steps(plan, check, static_cast<int>(map.groups.size()), entries);
    for (int b = 0; b < DraftPlan::lead_bodies && same; ++b) {
        same = entries[b].kind == a.dash_kind[b] && (!a.dash_kind[b] || (entries[b].tile == a.dash_tile[b] && entries[b].rice == a.dash_rice[b]));
        if (!same || !a.dash_kind[b]) continue;
        PlanReader r{plan, entries[b].at};
        for (const auto c : a.dash_codes[b]) same = same && r.get_rice(entries[b].rice) == c;
    }
    header.dash_steps = same;
    a.dash_bits = same ? w.at() - at : 0;
}

// One member's attack tiles; false, writing nothing, if they do not fit.
bool write_attack_tiles(const StaticMap& map, vec2 p, Analysis& a, DraftPlan& plan) {
    // Only the largest range is cast. A shadowcast from a clear tile at a smaller radius is the larger's within it
    // (rules: vision.shadowcast_radius), and a cluster out of the smaller range has no tile within it, so each
    // smaller range's viewers and sight off bushes are the largest's within that range.
    static_assert(DraftPlan::attack_ranges.size() == 2 && DraftPlan::attack_ranges[1] < DraftPlan::attack_ranges[0]);
    static_assert(DraftPlan::bush_range == DraftPlan::attack_ranges[0]);
    static bitboard sent{cambc::uninitialized}, opaque{cambc::uninitialized}, one{cambc::uninitialized},
        left{cambc::uninitialized}, rest{cambc::uninitialized};
    const auto r = static_cast<std::uint16_t>(DraftPlan::attack_ranges[0]);
    // Bits go only over bush_range's square, a tile's in each_in_square's order: by word, low bit first.
    const std::uint64_t* const seen = sent.ptr();
    const int stride = static_cast<int>(cambc::detail::layout().chunk_stride);
    int bits = 0;
    each_word_in_square(map.open_bushes(), p, DraftPlan::bush_range, [&](int, int, std::uint64_t tiles) { bits += __builtin_popcountll(tiles); });
    // Champions take the tiles off bushes from sight_off_bushes, which is viewers_into's off bushes: a cast from
    // outside a cluster holds no bush (vision.occlusion), and one from inside holds only its cluster. So only the
    // bushes that see p are cast for, as viewers_into finds them: each cluster in reach from inside it, or from a
    // bush its own.
    bool any = false;
    if (bits > 0) {
        bool first = true;
        const auto cast_from_inside = [&](const bitboard& cluster) {
            bitboard& to = first ? sent : one;
            xor_into(map.walls_and_bushes, cluster, opaque); // walls_and_bushes & ~cluster
            opaque.shadow_cast_into(p, r, to);
            to &= cluster;
            if (!first) sent |= one;
            first = false;
        };
        if (test(map.bushes, p)) cast_from_inside(map.bush_cluster(p).tiles);
        else {
            left.clear();
            left.draw_chebyshev(p, static_cast<float>(r));
            left &= map.bushes;
            while (!left.is_empty()) {
                const auto& cluster = map.bush_cluster(first_tile(left)).tiles;
                cast_from_inside(cluster);
                not_into(cluster, rest);
                left &= rest;
            }
        }
        if (!first)
            each_word_in_square(map.open_bushes(), p, DraftPlan::bush_range,
                                [&](int cx, int cy, std::uint64_t tiles) { any = any || (tiles & seen[cy * stride + cx]) != 0; });
    }
    PlanWriter w{plan, a.attack_at};
    if (!w.fits(any ? bits : 0)) return false;
    if (any) {
        PlanWriter{plan, a.attack_start + a.attack_index}.put(1, 1);
        each_word_in_square(map.open_bushes(), p, DraftPlan::bush_range, [&](int cx, int cy, std::uint64_t tiles) {
            const std::uint64_t in = seen[cy * stride + cx];
            for (; tiles; tiles &= tiles - 1) w.put(static_cast<std::uint32_t>(in >> __builtin_ctzll(tiles) & 1), 1);
        });
    }
    a.attack_at = w.at();
    ++a.attack_index;
    return true;
}

int ward_sites(const StaticMap& map) { return static_cast<int>(map.groups.size() + map.altars.size()); }

// The tiles within r of where a champion stands working the site: its camp tiles, or the altar's
// tribute tiles (within 1 of it).
void draw_site(const StaticMap& map, int site, int r, bitboard& out) {
    clear_board(out);
    const int groups = static_cast<int>(map.groups.size());
    if (site < groups)
        for (const auto& m : map.groups[site].members) draw_square(out, m.pos, static_cast<float>(r));
    else
        draw_square(out, map.altars[site - groups].pos, static_cast<float>(r + 1));
}

// What a ward (or a champion, at radius 8) on p sees: from a bush, its own cluster too (vision.occlusion).
void sight_from(const StaticMap& map, vec2 p, int r, bitboard& out) {
    static bitboard opaque{cambc::uninitialized};
    if (!test(map.bushes, p)) return map.walls_and_bushes.shadow_cast_into(p, static_cast<std::uint16_t>(r), out);
    xor_into(map.walls_and_bushes, map.bush_cluster(p).tiles, opaque);
    opaque.shadow_cast_into(p, static_cast<std::uint16_t>(r), out);
}

// What a champion working the site sees from every one of its stand tiles: the camp tiles, or the
// altar's tribute tiles. The altar itself, where none stands, if it has no tribute tile.
void stand_sight(const StaticMap& map, int site, bitboard& out) {
    static bitboard one{cambc::uninitialized};
    const int groups = static_cast<int>(map.groups.size());
    bool first = true;
    const auto add = [&](vec2 p) {
        sight_from(map, p, vision_radius, first ? out : one);
        if (!first) out &= one;
        first = false;
    };
    if (site < groups)
        for (const auto& m : map.groups[site].members) add(m.pos);
    else {
        const vec2 a = map.altars[site - groups].pos;
        for (int dy = -1; dy <= 1; ++dy)
            for (int dx = -1; dx <= 1; ++dx)
                if (const vec2 q{a.x + dx, a.y + dy}; q.x >= 0 && q.y >= 0 && q.x < map.width && q.y < map.height && test(map.open_for_us, q))
                    add(q);
        if (first) add(a);
    }
}

// The ward tile in placement range of the site's stand tiles that sees the most of what a champion
// on one of them may not: tiles an enemy can stand on, counted once within 8 of the stand tiles
// (as far as such a ward sees) and three times within 4 (attack and ability reach, a step off).
// Bushes are unseen from outside, so a ward inside a cluster near the site scores its tiles.
// `reach` is draw_site(site, ward_range()), its bush clusters found.
std::uint16_t best_ward(const StaticMap& map, int site, const bitboard& reach) {
    constexpr int ward_sight = 2 + 6; // the rules' ward placement radius plus its vision radius
    static bitboard own{cambc::uninitialized}, near{cambc::uninitialized}, far{cambc::uninitialized},
        candidates{cambc::uninitialized}, sight{cambc::uninitialized};
    static std::array<vec2, 1024> tiles;
    const int groups = static_cast<int>(map.groups.size());
    const vec2 centre = site < groups ? map.groups[site].centre : map.altars[site - groups].pos;
    stand_sight(map, site, own);
    draw_site(map, site, ability_range, near);
    near &= map.open_for_them;
    drop(near, own);
    draw_site(map, site, ward_sight, far);
    far &= map.open_for_them;
    drop(far, own);
    if (far.is_empty()) return 0;
    and_into(reach, map.open_for_us, candidates); // never a wall, hole, altar or their spawn (wards.placement)
    const auto n = std::min<std::uint32_t>(positions_into(candidates, tiles.data(), static_cast<std::uint32_t>(tiles.size())), tiles.size());
    const auto& layout = cambc::detail::layout();
    const int stride = static_cast<int>(layout.chunk_stride);
    const int r = static_cast<int>(cambc::constants::ward_vision_radius);
    const std::uint64_t *const seen = sight.ptr(), *const near_w = near.ptr(), *const far_w = far.ptr();
    int best = 0, best_dist = 0;
    vec2 best_tile{-1, -1};
    for (std::uint32_t i = 0; i < n; ++i) {
        const vec2 c = tiles[i];
        sight_from(map, c, r, sight);
        // Whole chunks, unmasked: the cast overwrites the board, so it holds nothing beyond r of c.
        int score = 0;
        const int x0 = std::max(0, c.x - r) >> 3, x1 = std::min(layout.width - 1, c.x + r) >> 3;
        const int y0 = std::max(0, c.y - r) >> 3, y1 = std::min(layout.height - 1, c.y + r) >> 3;
        const auto chunk = [&](int at) {
            const std::uint64_t w = seen[at];
            return 2 * __builtin_popcountll(w & near_w[at]) + __builtin_popcountll(w & far_w[at]);
        };
        // At r 6 a row spans at most 3 chunks, read at fixed offsets: as a loop (vectorised or not) it cost ~2x.
        if (x1 - x0 <= 2)
            for (int cy = y0, at = y0 * stride + x0; cy <= y1; ++cy, at += stride) {
                score += chunk(at);
                if (x1 > x0) score += chunk(at + 1);
                if (x1 > x0 + 1) score += chunk(at + 2);
            }
        else
            for (int cy = y0; cy <= y1; ++cy)
                for (int at = cy * stride + x0, end = cy * stride + x1; at <= end; ++at) score += chunk(at);
        if (score > best || (score == best && score > 0 && dist(c, centre) < best_dist))
            best = score, best_dist = dist(c, centre), best_tile = c;
    }
    if (best_tile.x < 0) return 0;
    const auto b = ward_box(map, site);
    return static_cast<std::uint16_t>(1 + (best_tile.y - b.y0) * (b.x1 - b.x0 + 1) + (best_tile.x - b.x0));
}

// Clears the plan's bits [from, to): whole bytes by memset, ~1 fuel each where put costs ~15 a bit.
void clear_bits(DraftPlan& plan, int from, int to) {
    const auto clear = [&](int bit) { plan.bytes[bit >> 3] &= static_cast<std::uint8_t>(~(1u << (bit & 7))); };
    for (; from < to && (from & 7) != 0; ++from) clear(from);
    if (const int bytes = (to - from) >> 3; bytes > 0) {
        std::memset(plan.bytes.data() + (from >> 3), 0, static_cast<std::size_t>(bytes));
        from += bytes * 8;
    }
    for (; from < to; ++from) clear(from);
}

// The ward section after the attack tiles, with the sites searched so far (unsearched ones 0, none);
// false, with no section, if its width does not fit or it would not decode to these tiles.
// After a write that put the section here, only the sites searched since are written and checked:
// rewriting all of them (~320 fuel a site) ran past draft_reserve on a big map whose search runs into
// the 100k draft turns. Nothing else writes the section's bits, so the rest still hold what was checked.
bool write_wards(const StaticMap& map, const Analysis& a, DraftPlan& plan, PlanHeader& header) {
    const int at = wards_from(map, a);
    const int from = header.wards_at == at ? a.wards_written : 0;
    const int codes_at = at + ward_width_bits;
    header.wards_at = 0;
    if (a.ward_bits == 0 || at >= 1 << PlanHeader::at_bits) return false;
    PlanWriter w{plan, from > 0 ? codes_at + from * a.ward_bits : at};
    if (from == 0 && !w.put(static_cast<std::uint32_t>(a.ward_bits), ward_width_bits)) return false;
    // ward_codes holds only the sites that fit, so every put fits.
    for (int site = from; site < a.ward_site; ++site) w.put(a.ward_codes[site], a.ward_bits);
    const int sites = ward_sites(map), held = static_cast<int>(a.ward_codes.size()), end = codes_at + held * a.ward_bits;
    if (from == 0) clear_bits(plan, w.at(), end); // the sites not yet searched, and whatever an earlier section left there
    // Codes, not tiles: a tile check per site costs ~300 fuel.
    PlanReader check{plan, from > 0 ? codes_at + from * a.ward_bits : at};
    bool same = from > 0 || static_cast<int>(check.get(ward_width_bits)) == a.ward_bits;
    for (int site = from; site < a.ward_site && same; ++site) same = check.get(a.ward_bits) == a.ward_codes[site];
    // The sites cut from the plan read as none: the bits short of a code before the end, then zeros past it.
    if (from == 0 && held < sites && same) same = PlanReader{plan, end}.get(a.ward_bits) == 0;
    if (same) header.wards_at = static_cast<std::uint16_t>(at);
    return same;
}

// The index section (DraftPlan, 5.) into the room after the ward section, once nothing else will
// be written there: fixed steps and checkpoints if both fit, else the checkpoints alone. Champions
// read a fixed step or a block's attack tiles without decoding what comes before. False, with no
// index, if neither fits or one would not decode to what the sections before hold.
bool write_index(const StaticMap& map, const Analysis& a, DraftPlan& plan, PlanHeader& header) {
    header.indexed = false;
    const int n = static_cast<int>(map.groups.size()), sites = ward_sites(map);
    // Ward codes past the stream's end read as none, so a cut section leaves no room.
    if (!header.steps || a.ward_bits < 0 || (a.ward_bits > 0 && static_cast<int>(a.ward_codes.size()) != sites)) return false;
    const int used = wards_from(map, a) + (a.ward_bits > 0 ? ward_width_bits + a.ward_bits * sites : 0);
    const auto ally = TileBox::of(map.ally_spawn_tiles), enemy = TileBox::of(map.enemy_spawn.positions());
    DraftSteps coded; // the steps section as champions decode it
    if (!decode_steps(plan, header, map, coded, true) || coded.end != a.attack_start) return false;
    std::array<std::vector<std::uint32_t>, 3> codes;
    std::array<int, 3> width{};
    for (int which = 0; which < 3; ++which) {
        for (int g = 0; g < n; ++g) {
            const int steps = a.steps[g][which];
            std::uint32_t c;
            if (which == 1 && header.mirrored) c = zigzag(steps - a.steps[map.group_at(map.mirror(map.groups[g].centre))][0]);
            else if (steps == unreachable) c = 0;
            else if (const int bound = steps_bound(ally, enemy, map.groups[g].centre, which); steps >= bound) c = static_cast<std::uint32_t>(steps - bound + 1);
            else return false;
            codes[which].push_back(c);
            width[which] = std::max(width[which], std::bit_width(c));
        }
        if (width[which] >= 1 << PlanIndex::width_bits) return false;
    }
    const int spawn = static_cast<int>(map.ally_spawn_tiles.size());
    int exceptions = 0;
    for (int g = 0; g < n && header.spawn_offsets; ++g) exceptions += coded.ally[g] != unreachable && !coded.predicted[g];
    const int steps_bits = 3 * PlanIndex::width_bits + n * (width[0] + width[1] + width[2])
                           + (header.spawn_offsets ? 2 * n + 2 * spawn * exceptions : 0);
    // The checkpoints: where each block's bush bits start past the first group's.
    const int blocks = (header.attack_groups + PlanIndex::block - 1) / PlanIndex::block;
    std::vector<int> table;
    int bush = 0, member = 0;
    for (int g = 0; g < header.attack_groups; ++g) {
        if (g > 0 && g % PlanIndex::block == 0) table.push_back(bush);
        for (const auto& m : map.groups[g].members)
            if (PlanReader{plan, a.attack_start + member++}.get(1)) bush += count_in_small_square<DraftPlan::bush_range>(map.open_bushes(), m.pos);
    }
    // Every group's members carry a flag; a cut-short group's bits may follow the attack groups'.
    int all = 0;
    for (const auto& group : map.groups) all += static_cast<int>(group.members.size());
    if (a.attack_start + all + bush > a.attack_at) return false;
    const int table_bits = blocks > 1 ? (blocks - 1) * PlanHeader::at_bits : 0;
    const int fixed = PlanHeader::at_bits + 2 + PlanHeader::at_bits;
    bool with_steps = used + fixed + steps_bits + table_bits <= PlanWriter::capacity;
    const bool with_table = table_bits > 0;
    if (!with_steps && (!with_table || used + fixed + table_bits > PlanWriter::capacity)) return false;
    const int length = fixed + (with_steps ? steps_bits : 0) + table_bits;
    const int at = PlanWriter::capacity - length;
    if (length >= 1 << PlanHeader::at_bits) return false;
    PlanWriter w{plan, at};
    w.put(static_cast<std::uint32_t>(a.attack_start), PlanHeader::at_bits);
    w.put(with_steps, 1), w.put(with_table, 1);
    if (with_steps) {
        for (const int k : width) w.put(static_cast<std::uint32_t>(k), PlanIndex::width_bits);
        for (int which = 0; which < 3; ++which)
            for (const auto c : codes[which]) w.put(c, width[which]);
        if (header.spawn_offsets) {
            for (int g = 0; g < n; ++g) w.put(coded.ally[g] != unreachable && coded.predicted[g], 1);
            for (int g = 0; g < n; ++g) w.put(coded.ally[g] != unreachable && !coded.predicted[g], 1);
            for (int g = 0; g < n; ++g)
                if (coded.ally[g] != unreachable && !coded.predicted[g]) w.put(coded.offsets[g], 2 * spawn);
        }
    }
    for (const int t : table) w.put(static_cast<std::uint32_t>(t), PlanHeader::at_bits);
    w.put(static_cast<std::uint32_t>(length), PlanHeader::at_bits);
    if (w.at() != PlanWriter::capacity) return false;
    // Read back as champions will.
    header.indexed = true;
    PlanIndex index;
    bool same = read_index(plan, header, n, spawn, index) && index.steps == with_steps && index.checkpoints == with_table
                && index.steps_end == a.attack_start;
    for (int b = 1; b < blocks && same; ++b) same = index_checkpoint(plan, index, b) == table[b - 1];
    if (same && with_steps) {
        for (int which = 0; which < 3 && same; ++which)
            for (int g = 0; g < n && same; ++g) {
                const int m = which == 1 && header.mirrored ? map.group_at(map.mirror(map.groups[g].centre)) : -1;
                same = index_steps(index_code(plan, index, which, g), which, header.mirrored, ally, enemy, map.groups[g].centre,
                                   m >= 0 ? a.steps[m][0] : 0) == a.steps[g][which];
            }
        if (same && header.spawn_offsets) {
            DraftSteps check;
            index_offsets(plan, index, n, spawn, check);
            for (int g = 0; g < n && same; ++g)
                if (coded.ally[g] != unreachable) same = check.predicted[g] == coded.predicted[g] && check.offsets[g] == coded.offsets[g];
        }
    }
    header.indexed = same;
    return same;
}

// The first turn's cap (analyse): Analysis::capped's bits, the fuel kept beyond draft_reserve, and upper bounds for
// it from the 6400-draft sweep (draft-features.md), each over the most measured: an attack member's tiles (14k on
// average at most), the work after the attack tiles and the index (338k at 124 groups, past its estimate below).
enum DraftCap : unsigned { cap_dash = 1, cap_leads = 2, cap_attacks = 4, cap_index = 8, cap_wards = 16, cap_open = 32 };
constexpr std::uint64_t cap_margin = 300000, attack_cost = 20000, attack_bound = 50000;
std::uint64_t index_bound(int groups) { return 250000 + 2500 * static_cast<std::uint64_t>(groups); }

// The structural budget (2026-11-07): every draft precompute must finish in the first turn (draft-features.md), by
// construction rather than by the fuel cap below. An upper envelope of the whole first turn's fuel over the map's
// geometry and the features' work counts (an LP over 61,696 drafts: ladder, ladder-mix and varied suites; coefficients
// non-negative, tightest on drafts of 6-10.5M) bounds it,
// and past work_limit the attack tiles are cut from the last group back (champions find them in play), then the ward
// sites from the last (bush wards), at a low saving a member and a box tile so that more is cut. A function of the
// map, never of measured fuel; the cap stays as the crash guard.
void work_budget(const StaticMap& map, Analysis& a, int spawn_fields) {
    constexpr double work_limit = 8.7e6, member_saving = 6000, box_saving = 900, site_saving = 4000;
    const double area = static_cast<double>(map.width) * map.height;
    const auto& w = feature_work;
    const bool fw = features_measured;
    const double dh = fw ? w.dash[0] : 0, dp = fw ? w.dash[1] : 0, ch = fw ? w.crystal[0] : 0, cp = fw ? w.crystal[1] : 0;
    const double bushes = map.bushes.count(), groups = static_cast<double>(map.groups.size());
    double members = 0;
    for (const auto& g : map.groups) members += static_cast<double>(g.members.size());
    const int sites = ward_sites(map);
    std::vector<double> box(static_cast<std::size_t>(sites));
    for (int site = 0; site < sites; ++site) box[static_cast<std::size_t>(site)] = ward_box(map, site).area();
    const double bound = 20183.3 + 346.2 * area + 47.697 * map.walls.count() + 500.941 * bushes + 819.426 * w.sight_sources * fw
                         + 844.486 * w.sight_steps * fw + 63.0392 * dh + 115.393 * dp + (ch > 0 || cp > 0 ? 173422 : 0) + 12.7617 * ch
                         + 389.059 * cp + 11121 * members + 5803.2 * spawn_fields * area / 1000 + 67.537 * members * bushes / 100
                         + 40263.2 * sites;
    double over = bound - work_limit;
    int g = static_cast<int>(map.groups.size());
    while (over > 0 && g > 0) over -= member_saving * static_cast<double>(map.groups[static_cast<std::size_t>(--g)].members.size());
    if (g < static_cast<int>(map.groups.size())) a.attack_groups_max = g;
    int site = sites;
    while (over > 0 && site > 0) over -= box_saving * box[static_cast<std::size_t>(--site)] + site_saving;
    if (site < sites) a.ward_sites_max = site;
}

// The opening plan (open_plan.h) for the team we expect, into the facts block's slot. Last in the first turn, on the
// fuel the rest leaves: without room for its fields there is no plan (play farms as usual); its search stops at
// `floor`. Candidates: our half's groups (nearer our spawn than theirs: the model has no enemy, and the middle is
// where live openings meet it), nearest first.
void make_open_plan(const StaticMap& map, Analysis& a, DraftPlan& plan, std::uint64_t floor) {
    namespace op = open_plan;
    op::Problem p;
    p.horizon = params::open_plan::horizon, p.per_gold = params::open_plan::per_gold;
    p.bodies = static_cast<int>(std::min<std::size_t>(a.lead_for.size(), op::max_bodies));
    std::array<std::pair<int, int>, 256> order;
    int n = 0;
    for (int g = 0; g < static_cast<int>(map.groups.size()); ++g) {
        const auto& G = map.groups[g];
        const int us = a.steps[g][0], them = a.steps[g][1];
        if (G.has_monolith || G.gems + G.gold == 0 || us == unreachable || us >= them) continue;
        order[n++] = {us, g};
    }
    std::sort(order.begin(), order.begin() + n);
    p.cands = std::min(n, op::max_cands);
    if (p.bodies == 0 || p.cands == 0) return;
    [[maybe_unused]] const auto fuel_start = cambc::fuel_remaining();
    if (!fuel_ok(floor + static_cast<std::uint64_t>(p.cands) * field_cost_estimate() + 60000)) {
        a.capped |= cap_open;
        return;
    }
    // The walks between candidates. A run and the greedy seeds stop at a group farther than the horizon plus the
    // body's attack range, so the floods stop there: past it every step count reads unreachable, to the same effect.
    int reach = 0;
    for (int b = 0; b < p.bodies; ++b) reach = std::max(reach, facts(a.lead_for[b]).attack_range());
    // Walks are symmetric (a step tests only the tile stepped onto), so candidate c's flood fills its row and column
    // for the candidates after it, and stops once they are reached. A blocked centre is no root and no goal.
    static cambc::distance_field walk;
    static bitboard root{cambc::uninitialized}, goals{cambc::uninitialized}, visited{cambc::uninitialized};
    std::array<bool, op::max_cands> open_centre;
    for (int c = 0; c < p.cands; ++c) open_centre[c] = !test(map.blocked_for_us, map.groups[order[c].second].centre);
    for (int c = 0; c < p.cands; ++c) {
        const int g = order[c].second;
        const auto& G = map.groups[g];
        auto& C = p.cand[c];
        C.group = g, C.gems = static_cast<float>(G.gems), C.gold = static_cast<float>(G.gold), C.respawn = G.respawn, C.home = order[c].first;
        C.members = 0;
        for (const auto& [hp, hits] : sorted_members(a, g)) {
            const int m = std::min(C.members, op::max_members - 1);
            C.hp[m] += hp, C.strength[m] += hits, C.total += hp, C.total_strength += hits;
            C.members = std::min(C.members + 1, op::max_members);
        }
        const bool open = open_centre[c];
        p.steps[c][c] = open ? 0 : unreachable;
        clear_board(goals);
        bool any = false;
        for (int d = c + 1; d < p.cands; ++d)
            if (open && open_centre[d]) set_tile(goals, map.groups[order[d].second].centre), any = true;
            else p.steps[c][d] = p.steps[d][c] = unreachable;
        if (!any) continue;
        clear_board(root);
        set_tile(root, G.centre);
        walk.compute_to(map.blocked_for_us, root, goals, visited, static_cast<std::uint16_t>(p.horizon + reach));
        for (int d = c + 1; d < p.cands; ++d)
            if (open_centre[d]) p.steps[c][d] = p.steps[d][c] = static_cast<std::uint16_t>(steps_at(walk, map.groups[order[d].second].centre));
    }
    for (int b = 0; b < p.bodies; ++b) {
        const auto type = a.lead_for[b];
        const auto& f = facts(type);
        auto& B = p.body[b];
        B.dps = base_output(type), B.range = f.attack_range(), B.melee = !f.ranged;
        B.health = f.health.base, B.usable = f.health.base * (1.0f - params::draft_recall_health_fraction);
        B.bonus = f.passive == Passive::bonus_gold ? 1.0f + static_cast<float>(cambc::constants::passive_abilities::vesper_vale_bonus_gold_percent) / 100.0f : 1.0f;
        const int i = body_spawn_index(map, b);
        const bool by_tile = !a.spawn_steps.empty() && i < static_cast<int>(map.ally_spawn_tiles.size());
        for (int c = 0; c < p.cands; ++c) B.from_spawn[c] = by_tile ? a.spawn_steps[order[c].second][i] : a.steps[order[c].second][0];
    }
    float value = 0;
    int iterations = 0;
    [[maybe_unused]] const auto fuel_search = cambc::fuel_remaining();
    const auto best = op::solve(p, floor + 20000, value, iterations);
    op::Lists worked;
    op::simulate_solved(p, best, &worked);
    std::array<std::array<std::uint8_t, op::max_steps>, op::max_bodies> steps{};
    for (int b = 0; b < p.bodies; ++b)
        for (int k = 0; k < op::max_steps; ++k) steps[b][k] = worked[b][k] >= 0 ? static_cast<std::uint8_t>(p.cand[worked[b][k]].group + 1) : 0;
    PlanFacts::write_open(plan, steps);
    debug_block({
        std::printf("OPENPLAN value %.1f iterations %d cands %d bodies %d fuel start %llu search %llu end %llu\n", value, iterations, p.cands, p.bodies,
                    static_cast<unsigned long long>(fuel_start), static_cast<unsigned long long>(fuel_search), static_cast<unsigned long long>(cambc::fuel_remaining()));
        for (int b = 0; b < p.bodies; ++b) {
            std::printf("OPENPLAN body %d", b);
            for (int k = 0; k < op::max_steps && steps[b][k]; ++k) std::printf(" g%d", steps[b][k] - 1);
            std::printf("\n");
        }
    });
}

// Each part checks its fuel first; a part not done is retried next draft turn.
// Every draft precompute must finish in the first turn (draft-features.md), so there the optional parts (after the
// steps) are a last-resort cap instead: one starts only if the fuel left covers its upper bound, the index's and
// cap_margin over the reserve, else its section is cut short where it is (as a plan cut for room reads) and the
// analysis goes on. Only the map, facts, fields and steps can leave it unfinished.
void analyse(DraftState& state) {
    auto& plan = state.plan;
    auto& header = state.header;
    auto& a = analysis();
    const auto afford = [](std::uint64_t cost) { return fuel_ok(draft_reserve() + cost); };
    if (a.done) return;
    const bool first = draft_round() == 0;
    const auto index_cost = [&] { return a.indexed ? 0 : index_bound(static_cast<int>(a.map->groups.size())); };
    const auto floor = [&](std::uint64_t cost) { return draft_reserve() + cap_margin + index_cost() + cost; };
    // In the first turn, whether a part of upper bound `cost` may start; false records section `bit` as capped.
    const auto room = [&](std::uint64_t cost, unsigned bit) {
        if (!first || fuel_ok(floor(cost))) return true;
        a.capped |= bit;
        return false;
    };
    if (!a.map) {
        if (!afford(150000)) return;
        a.map = StaticMap::build();
        // Before anything that may stop the analysis: champions measure them themselves otherwise.
        if (!a.map->ally_spawn_tiles.empty()) measure_facts(*a.map).write(plan);
        const auto groups = a.map->groups.size();
        const auto spawn = a.map->ally_spawn_tiles.size();
        if (groups > 255 || spawn == 0) {
            a.done = true;
            return;
        }
        a.steps.resize(groups);
        a.spawn_steps.resize(spawn <= DraftPlan::max_spawn_tiles ? groups : 0);
        header.check = plan_check(*a.map);
    }
    const auto& map = *a.map;
    const int spawn_fields = a.spawn_steps.empty() ? 0 : static_cast<int>(map.ally_spawn_tiles.size());
    if (!a.budgeted) work_budget(map, a, spawn_fields), a.budgeted = true;
    for (; a.fields < 3 + spawn_fields; ++a.fields) {
        if (!afford(2 * field_cost_estimate())) return;
        if (a.fields == 0) set_steps(map, map.from_ally_spawn(), 0, a);
        else if (a.fields == 1)
            for (std::size_t g = 0; g < map.groups.size(); ++g)
                a.steps[g][1] = static_cast<std::uint16_t>(map.enemy_spawn_steps(map.groups[g].centre));
        else set_steps(map, make_field(map.blocked_for_us, a.fields == 2 ? tribute_tiles(map) : single(map.ally_spawn_tiles[a.fields - 3])), a.fields, a);
    }
    if (!header.steps) {
        if (!write_steps(map, a, spawn_fields, plan, header)) {
            header.mirrored = header.spawn_offsets = false, header.rice = {};
            a.done = true;
            return;
        }
        a.attack_at = a.attack_start;
        for (const auto& group : map.groups) a.attack_at += static_cast<int>(group.members.size()); // the flags
        header.tributes_walked = tributes_walked(map);
        header.camp_sealed = !header.tributes_walked && map.any_camp_hop(); // undrafted, the map makes every hop
        header.steps = true;
    }
    a.dash_spawn = a.dash_spawn && header.spawn_offsets;
    for (; a.dash_fields <= spawn_fields; ++a.dash_fields) {
        if (a.dash_fields < spawn_fields && !a.dash_spawn) continue;
        if (!room(2 * field_cost_estimate(), cap_dash)) {
            a.dash_spawn = a.dash_altar = false;
            break;
        }
        if (!afford(2 * field_cost_estimate())) return;
        check_dash_steps(map, a, a.dash_fields, spawn_fields);
    }
    header.dash_spawn_steps = a.dash_spawn, header.dash_altar_steps = a.dash_altar;
    make_leads(map, a, first ? floor(0) : draft_reserve());
    if (first && a.leads_made < static_cast<int>(std::min<std::size_t>(a.lead_for.size(), DraftPlan::lead_bodies))) a.capped |= cap_leads;
    // Dashers otherwise build a field from their spawn tile for their round-1 steps (farm).
    if (!header.dash_spawn_steps && !map.crossable.is_empty())
        for (; a.dash_bodies < static_cast<int>(std::min<std::size_t>(a.lead_for.size(), DraftPlan::lead_bodies)); ++a.dash_bodies) {
            const int kind = facts(a.lead_for[a.dash_bodies]).dash_kind();
            if (kind == 0) continue;
            if (!room(2 * field_cost_estimate(), cap_dash)) {
                a.dash_bodies = DraftPlan::lead_bodies; // the rest have no entry (dash_kind 0)
                break;
            }
            if (!afford(2 * field_cost_estimate())) return;
            dash_entry(map, a, a.dash_bodies, kind);
        }
    for (; !a.attacks_done && a.attack_group < static_cast<int>(map.groups.size()); ++a.attack_group, a.attack_member = 0) {
        if (a.attack_group >= a.attack_groups_max) {
            a.attacks_done = true;
            break;
        }
        const auto& members = map.groups[a.attack_group].members;
        for (; a.attack_member < static_cast<int>(members.size()); ++a.attack_member) {
            const vec2 p = members[a.attack_member].pos;
            // With no bush in range, finding clusters would do nothing.
            const bool found = room(attack_bound, cap_attacks) && afford(attack_cost)
                               && (count_in_small_square<DraftPlan::attack_ranges[0]>(map.bushes, p) == 0
                                   || map.find_bush_clusters(p, DraftPlan::attack_ranges[0], first ? floor(attack_bound) : draft_reserve() + attack_cost));
            if (!found && !first) return;
            if (!found) {
                a.capped |= cap_attacks;
                a.attacks_done = true;
                break;
            }
            if (!write_attack_tiles(map, p, a, plan)) {
                a.attacks_done = true;
                break;
            }
        }
        if (!a.attacks_done) header.attack_groups = static_cast<std::uint8_t>(a.attack_group + 1);
    }
    a.attacks_done = true;
    if (a.ward_bits < 0) {
        const int sites = ward_sites(map);
        a.ward_bits = 0;
        for (int site = 0; site < sites; ++site) a.ward_bits = std::max(a.ward_bits, std::bit_width(static_cast<unsigned>(ward_box(map, site).area())));
        if (a.ward_bits >= 1 << ward_width_bits) a.ward_bits = 0;
        // The leads and dash steps take only room the whole ward section leaves: a ward site
        // cut from the plan changes play (ward_planned), they change only fuel.
        const int wards = a.ward_bits > 0 ? ward_width_bits + a.ward_bits * sites : 0;
        if (a.attack_at < 1 << PlanHeader::at_bits && PlanWriter{plan, a.attack_at}.fits(lead_bits(map) + wards)) a.leads_at = a.attack_at;
        if (a.leads_at > 0 && std::any_of(a.dash_kind.begin(), a.dash_kind.end(), [](int k) { return k > 0; })) {
            write_dash_steps(map, a, plan, header);
            if (!PlanWriter{plan, wards_from(map, a)}.fits(wards)) header.dash_steps = false, a.dash_bits = 0;
        }
        // Codes past the stream's end are cut, so only the sites that fit are searched.
        if (a.ward_bits > 0)
            a.ward_codes.assign(static_cast<std::size_t>(std::clamp((PlanWriter::capacity - wards_from(map, a) - ward_width_bits) / a.ward_bits, 0, sites)), 0);
    }
    // The index before the ward search: it reads only the sections before the wards and the ward section's size,
    // fixed above, and it is what champions' fuel needs most.
    if (!a.indexed) {
        if (first && !fuel_ok(draft_reserve() + cap_margin + index_cost())) a.capped |= cap_index;
        else {
            if (!afford(60000 + 400 * static_cast<std::uint64_t>(map.groups.size()))) return;
            write_index(map, a, plan, header);
        }
        a.indexed = true;
    }
    for (; a.ward_site < static_cast<int>(a.ward_codes.size()); ++a.ward_site) {
        static bitboard reach{cambc::uninitialized};
        if (a.ward_site >= a.ward_sites_max) break; // work_budget: the sites left read 0
        const std::uint64_t cost = 5000 + 2000 * static_cast<std::uint64_t>(ward_box(map, a.ward_site).area());
        if (!room(cost, cap_wards)) break; // the sites left read 0, no planned ward
        if (!afford(cost)) return;
        draw_site(map, a.ward_site, ward_range(), reach);
        // Under a floor: best_ward's bush_cluster() grows a missing cluster with no limit, and
        // the attack tiles found only those near the groups they reached.
        if (!map.find_bush_clusters(reach, first ? floor(cost) : draft_reserve() + cost)) {
            if (!first) return;
            a.capped |= cap_wards;
            break;
        }
        a.ward_codes[a.ward_site] = best_ward(map, a.ward_site, reach);
    }
    if constexpr (params::open_plan::on)
        if (first && !a.opened) a.opened = true, make_open_plan(map, a, plan, floor(0));
    a.done = true;
}

} // namespace

TileBox ward_box(const StaticMap& map, int site) {
    const int groups = static_cast<int>(map.groups.size()), r = ward_range();
    auto b = TileBox::none();
    if (site < groups)
        for (const auto& m : map.groups[site].members) b.add(m.pos);
    else {
        const vec2 p = map.altars[site - groups].pos;
        b = {p.x - 1, p.y - 1, p.x + 1, p.y + 1};
    }
    return {std::max(0, b.x0 - r), std::max(0, b.y0 - r), std::min(map.width - 1, b.x1 + r), std::min(map.height - 1, b.y1 + r)};
}

vec2 ward_tile(const StaticMap& map, int site, std::uint32_t code) {
    if (code == 0) return {-1, -1};
    const auto b = ward_box(map, site);
    const int w = b.x1 - b.x0 + 1, i = static_cast<int>(code) - 1;
    return {b.x0 + i % w, b.y0 + i / w};
}

vec2 drafted_ward(const DraftPlan& plan, const PlanHeader& header, const StaticMap& map, int site) {
    if (header.wards_at == 0) return {-1, -1};
    PlanReader bits{plan, header.wards_at};
    const int w = static_cast<int>(bits.get(ward_width_bits));
    if (w == 0) return {-1, -1};
    bits.skip(site * w);
    return ward_tile(map, site, bits.get(w));
}

int drafted_leads(const DraftPlan& plan, const PlanHeader& header, int groups, int body, std::array<int, DraftPlan::leads>& out) {
    if (header.leads_at == 0 || body >= DraftPlan::lead_bodies) return 0;
    const int w = lead_width(groups);
    PlanReader bits{plan, header.leads_at + body * DraftPlan::leads * w};
    int n = 0;
    for (int i = 0; i < DraftPlan::leads; ++i) {
        const int g = static_cast<int>(bits.get(w)) - 1;
        if (g < 0 || g >= groups || std::find(out.begin(), out.begin() + n, g) != out.begin() + n) break;
        out[n++] = g;
    }
    return n;
}

bool index_dash_steps(const DraftPlan& plan, const PlanHeader& header, int groups, std::array<DashEntry, DraftPlan::lead_bodies>& out) {
    if (!header.dash_steps || header.leads_at == 0) return false;
    PlanReader bits{plan, header.leads_at + DraftPlan::lead_bodies * DraftPlan::leads * lead_width(groups)};
    for (auto& e : out) {
        e = {};
        e.kind = static_cast<int>(bits.get(dash_kind_bits));
        if (!e.kind) continue;
        e.tile = static_cast<int>(bits.get(dash_tile_bits));
        e.rice = static_cast<int>(bits.get(PlanHeader::rice_bits));
        const int length = static_cast<int>(bits.get(PlanHeader::at_bits));
        e.at = bits.at();
        bits.skip(length);
    }
    return bits.ok();
}

int spawn_offset(const TileBox& spawn, vec2 tile, vec2 centre) { return std::clamp(dist(tile, centre) - spawn.dist(centre), 0, 3); }

namespace {
// Every group's steps coded against steps_bound's `which` bound, from `bits`. The reader, the
// parameter and the boxes are copied into locals: through the references every store to `steps`
// reloaded them (~120 fuel a group on 200-group maps, ~60 so).
[[gnu::always_inline]] inline void decode_bounded(PlanReader& bits, const PlanHeader& header, const StaticMap& map, const TileBox& ally,
                                                  const TileBox& enemy, int which, std::vector<std::uint16_t>& steps) {
    const int n = static_cast<int>(map.groups.size());
    steps.resize(n);
    PlanReader r = bits;
    const int k = header.rice[which];
    const TileBox a = ally, e = enemy;
    std::uint16_t* const out = steps.data();
    const CampGroup* const group = map.groups.data();
    for (int g = 0; g < n; ++g) {
        const auto c = r.get_rice(k);
        out[g] = static_cast<std::uint16_t>(c == 0 ? unreachable : c - 1 + steps_bound(a, e, group[g].centre, which));
    }
    bits = r;
}

// The mirrored enemy steps from `bits`; false if a group has no mirror.
bool decode_mirrored(PlanReader& bits, const PlanHeader& header, const StaticMap& map, DraftSteps& out) {
    const int n = static_cast<int>(map.groups.size());
    out.enemy.resize(n);
    for (int g = 0; g < n; ++g) {
        const int m = map.group_at(map.mirror(map.groups[g].centre));
        if (m < 0) return false;
        out.enemy[g] = static_cast<std::uint16_t>(out.ally[m] + unzigzag(bits.get_rice(header.rice[1])));
    }
    return true;
}
} // namespace

bool decode_steps(const DraftPlan& plan, const PlanHeader& header, const StaticMap& map, DraftSteps& out, bool with_enemy) {
    const int n = static_cast<int>(map.groups.size());
    const auto ally = TileBox::of(map.ally_spawn_tiles);
    const auto enemy = header.mirrored || !with_enemy ? TileBox{} : TileBox::of(map.enemy_spawn.positions());
    out.spawn = ally;
    PlanReader bits{plan, plan_body_at(plan)};
    decode_bounded(bits, header, map, ally, enemy, 0, out.ally);
    out.enemy_at = bits.at();
    if (!with_enemy) bits.skip_rice(n, header.rice[1]);
    else if (!header.mirrored) decode_bounded(bits, header, map, ally, enemy, 1, out.enemy);
    else if (!decode_mirrored(bits, header, map, out)) return false;
    decode_bounded(bits, header, map, ally, enemy, 2, out.altar);
    out.offsets.assign(n, 0);
    out.predicted.assign(n, 0);
    if (header.spawn_offsets) {
        PlanReader r = bits; // in locals, as decode_bounded's
        const int width = 2 * static_cast<int>(map.ally_spawn_tiles.size());
        const std::uint16_t* const ally_steps = out.ally.data();
        std::uint8_t* const predicted = out.predicted.data();
        std::uint32_t* const offsets = out.offsets.data();
        for (int g = 0; g < n; ++g) {
            if (ally_steps[g] == unreachable) continue;
            if (r.get(1)) predicted[g] = 1;
            else offsets[g] = r.get(width);
        }
        bits = r;
    }
    out.end = bits.at();
    return bits.ok();
}

void decode_enemy_steps(const DraftPlan& plan, const PlanHeader& header, const StaticMap& map, DraftSteps& out) {
    PlanReader bits{plan, out.enemy_at};
    if (!header.mirrored) decode_bounded(bits, header, map, out.spawn, TileBox::of(map.enemy_spawn.positions()), 1, out.enemy);
    else if (!decode_mirrored(bits, header, map, out)) out.enemy.assign(map.groups.size(), unreachable);
}

bool read_index(const DraftPlan& plan, const PlanHeader& header, int groups, int spawn_tiles, PlanIndex& out) {
    if (!header.indexed) return false;
    const int length = static_cast<int>(PlanReader{plan, PlanWriter::capacity - PlanHeader::at_bits}.get(PlanHeader::at_bits));
    if (length < 2 * PlanHeader::at_bits + 2 || length > PlanWriter::capacity) return false;
    PlanReader bits{plan, PlanWriter::capacity - length};
    out.steps_end = static_cast<int>(bits.get(PlanHeader::at_bits));
    out.steps = bits.get(1), out.checkpoints = bits.get(1);
    int at = bits.at();
    if (out.steps) {
        for (auto& k : out.width) k = static_cast<int>(bits.get(PlanIndex::width_bits));
        at = bits.at();
        for (int which = 0; which < 3; ++which) out.codes_at[which] = at, at += groups * out.width[which];
        out.predicted_at = at;
        if (header.spawn_offsets) {
            out.offsets_at = at + 2 * groups;
            PlanReader mask{plan, at + groups};
            int entries = 0;
            for (int g = 0; g < groups; g += 32) entries += std::popcount(mask.get(std::min(32, groups - g)));
            at = out.offsets_at + entries * 2 * spawn_tiles;
        }
    }
    out.table_at = at;
    return out.steps_end > 0 && at <= PlanWriter::capacity;
}

void index_offsets(const DraftPlan& plan, const PlanIndex& index, int groups, int spawn_tiles, DraftSteps& out) {
    out.offsets.assign(groups, 0);
    out.predicted.assign(groups, 0);
    PlanReader predicted{plan, index.predicted_at}, listed{plan, index.predicted_at + groups}, offsets{plan, index.offsets_at};
    for (int g = 0; g < groups; g += 32) {
        const int n = std::min(32, groups - g);
        for (auto p = predicted.get(n); p; p &= p - 1) out.predicted[g + std::countr_zero(p)] = 1;
        for (auto l = listed.get(n); l; l &= l - 1) out.offsets[g + std::countr_zero(l)] = offsets.get(2 * spawn_tiles);
    }
}

int mirrored_enemy_steps(const DraftPlan& plan, const PlanHeader& header, const StaticMap& map, const DraftSteps& steps, int group) {
    if (!header.mirrored || header.rice[1] != 0) return -1;
    const bool ahead = group >= steps.next_group && steps.next_group > 0;
    PlanReader bits{plan, ahead ? steps.next_at : steps.enemy_at};
    bits.skip_rice(ahead ? group - steps.next_group : group, 0);
    const auto code = bits.get_rice(0);
    steps.next_group = group + 1, steps.next_at = bits.at();
    // A plan written for the map has every mirror group (decode_enemy_steps would read all unreachable).
    const int m = map.group_at(map.mirror(map.groups[group].centre));
    return m < 0 ? unreachable : static_cast<std::uint16_t>(steps.ally[m] + unzigzag(code));
}

std::uint16_t plan_check(const StaticMap& map) {
    const vec2 spawn = map.ally_spawn_tiles[0];
    std::uint32_t h = DraftPlan::current_version;
    for (const int v : {map.width, map.height, static_cast<int>(map.groups.size()), spawn.x, spawn.y})
        h = (h ^ static_cast<std::uint32_t>(v)) * 0x9E3779B1u;
    h ^= h >> 16;
    return static_cast<std::uint16_t>(h & 0xffffu ? h : 1);
}

void PlanHeader::write(DraftPlan& plan) const {
    PlanWriter w{plan};
    w.put(check, check_bits);
    w.put(field_layers, layer_bits);
    w.put(steps, 1), w.put(mirrored, 1), w.put(spawn_offsets, 1), w.put(tributes_walked, 1);
    w.put(dash_spawn_steps, 1), w.put(dash_altar_steps, 1), w.put(dash_steps, 1), w.put(indexed, 1);
    w.put(camp_sealed, 1);
    for (const auto k : rice) w.put(k, rice_bits);
    w.put(attack_groups, group_bits), w.put(wards_at, at_bits), w.put(leads_at, at_bits);
}

PlanHeader PlanHeader::read(const DraftPlan& plan) {
    static_assert(bits <= 128);
    // Two words and constant shifts: PlanReader's window costs ~15 fuel a field.
    std::array<std::uint64_t, 2> w;
    std::memcpy(w.data(), plan.bytes.data(), sizeof w);
    int at = 0;
    const auto get = [&](int n) __attribute__((always_inline)) {
        const std::uint64_t v = at >= 64 ? w[1] >> (at - 64) : at == 0 ? w[0] : w[0] >> at | w[1] << (64 - at);
        at += n;
        return v & ((std::uint64_t{1} << n) - 1);
    };
    PlanHeader h;
    h.check = static_cast<std::uint16_t>(get(check_bits));
    h.field_layers = static_cast<std::uint16_t>(get(layer_bits));
    h.steps = get(1), h.mirrored = get(1), h.spawn_offsets = get(1), h.tributes_walked = get(1);
    h.dash_spawn_steps = get(1), h.dash_altar_steps = get(1), h.dash_steps = get(1), h.indexed = get(1);
    h.camp_sealed = get(1);
    for (auto& k : h.rice) k = static_cast<std::uint8_t>(get(rice_bits));
    h.attack_groups = static_cast<std::uint8_t>(get(group_bits));
    h.wards_at = static_cast<std::uint16_t>(get(at_bits));
    h.leads_at = static_cast<std::uint16_t>(get(at_bits));
    return h;
}

namespace {

// params::test_draft: the 16 most common compositions per pick count, in pick order, in the ranked games
// of the ladder's top 15 other teams on engine 3.0.0 (patch 4.0.0), 2026-11-04 to 11-05
// (research/ladder-drafts-2026-11-05.md), picked by frequency. Generated by tools/draftlab/test_comps.py
// from replays/draftlab/draft5/prior.json.
namespace test_compositions {
using C = cambc::champion_draft;
template <std::size_t N> struct Weighted {
    std::uint32_t weight;
    C team[N];
};
constexpr Weighted<3> three[] = {
    {135, {C::vesper_vale, C::marcella, C::heart_of_ruin}},
    {119, {C::vesper_vale, C::marcella, C::cassi_and_issac}},
    {106, {C::heart_of_ruin, C::marcella, C::vendetta}},
    {93, {C::marcella, C::vesper_vale, C::heart_of_ruin}},
    {92, {C::vesper_vale, C::heart_of_ruin, C::cassi_and_issac}},
    {85, {C::heart_of_ruin, C::vesper_vale, C::marcella}},
    {64, {C::vesper_vale, C::heart_of_ruin, C::vendetta}},
    {57, {C::marcella, C::vendetta, C::vesper_vale}},
    {56, {C::heart_of_ruin, C::vendetta, C::vesper_vale}},
    {43, {C::marcella, C::varg, C::heart_of_ruin}},
    {35, {C::ryth, C::marcella, C::heart_of_ruin}},
    {28, {C::heart_of_ruin, C::vendetta, C::marcella}},
    {21, {C::heart_of_ruin, C::marcella, C::ren}},
    {21, {C::vesper_vale, C::cassi_and_issac, C::heart_of_ruin}},
    {21, {C::vendetta, C::marcella, C::heart_of_ruin}},
    {21, {C::marcella, C::cassi_and_issac, C::vesper_vale}},
};
constexpr Weighted<4> four[] = {
    {132, {C::marcella, C::vendetta, C::heart_of_ruin, C::cassi_and_issac}},
    {98, {C::willow, C::heart_of_ruin, C::vendetta, C::marcella}},
    {84, {C::heart_of_ruin, C::marcella, C::vesper_vale, C::vendetta}},
    {82, {C::marcella, C::vendetta, C::heart_of_ruin, C::willow}},
    {77, {C::heart_of_ruin, C::marcella, C::willow, C::cassi_and_issac}},
    {77, {C::vesper_vale, C::marcella, C::heart_of_ruin, C::ryth}},
    {69, {C::vesper_vale, C::vendetta, C::heart_of_ruin, C::cassi_and_issac}},
    {56, {C::vesper_vale, C::heart_of_ruin, C::vendetta, C::marcella}},
    {56, {C::tavi, C::vesper_vale, C::marcella, C::cassi_and_issac}},
    {49, {C::marcella, C::vesper_vale, C::heart_of_ruin, C::vendetta}},
    {49, {C::heart_of_ruin, C::vesper_vale, C::ryth, C::marcella}},
    {48, {C::vesper_vale, C::cassi_and_issac, C::heart_of_ruin, C::marcella}},
    {41, {C::ryth, C::vesper_vale, C::varg, C::heart_of_ruin}},
    {35, {C::marcella, C::cassi_and_issac, C::vesper_vale, C::heart_of_ruin}},
    {28, {C::marcella, C::vesper_vale, C::varg, C::heart_of_ruin}},
    {21, {C::marcella, C::heart_of_ruin, C::varg, C::vendetta}},
};
constexpr Weighted<5> five[] = {
    {117, {C::heart_of_ruin, C::marcella, C::vesper_vale, C::cassi_and_issac, C::willow}},
    {111, {C::vesper_vale, C::vendetta, C::heart_of_ruin, C::marcella, C::cassi_and_issac}},
    {90, {C::heart_of_ruin, C::vendetta, C::vesper_vale, C::marcella, C::cassi_and_issac}},
    {87, {C::vesper_vale, C::vendetta, C::heart_of_ruin, C::willow, C::marcella}},
    {79, {C::heart_of_ruin, C::cassi_and_issac, C::vesper_vale, C::ryth, C::marcella}},
    {71, {C::heart_of_ruin, C::vesper_vale, C::marcella, C::vendetta, C::tavi}},
    {64, {C::heart_of_ruin, C::marcella, C::ryth, C::vendetta, C::vesper_vale}},
    {62, {C::willow, C::heart_of_ruin, C::vendetta, C::ryth, C::marcella}},
    {53, {C::vesper_vale, C::heart_of_ruin, C::vendetta, C::cassi_and_issac, C::marcella}},
    {53, {C::ryth, C::cassi_and_issac, C::willow, C::varg, C::heart_of_ruin}},
    {50, {C::marcella, C::vendetta, C::heart_of_ruin, C::cassi_and_issac, C::willow}},
    {42, {C::vesper_vale, C::vendetta, C::heart_of_ruin, C::cassi_and_issac, C::willow}},
    {39, {C::heart_of_ruin, C::ren, C::vesper_vale, C::willow, C::marcella}},
    {28, {C::marcella, C::vesper_vale, C::heart_of_ruin, C::vendetta, C::ryth}},
    {28, {C::heart_of_ruin, C::ren, C::vesper_vale, C::prism, C::marcella}},
    {25, {C::vesper_vale, C::heart_of_ruin, C::vendetta, C::marcella, C::ryth}},
};

std::uint64_t mix(std::uint64_t h, std::uint64_t w) {
    h = (h ^ w) * 0x9E3779B97F4A7C15ull;
    return h ^ (h >> 29);
}

std::uint64_t mix_board(std::uint64_t h, const bitboard& board) {
    const auto words = cambc::detail::layout().board_bytes / 8;
    for (std::uint32_t i = 0; i < words; ++i) h = mix(h, board.ptr()[i]);
    return h;
}

// Keyed on our team as well as the map: the side-swapped game gives each side the same composition again.
std::uint64_t map_hash() {
    std::uint64_t h = mix(0, static_cast<std::uint64_t>(cambc::detail::sdk_my_team()));
    h = mix(h, static_cast<std::uint64_t>(cambc::map::width()) << 32 | static_cast<std::uint32_t>(cambc::map::height()));
    for (const auto* board : {&cambc::map::walls(), &cambc::map::bushes(), &cambc::map::holes(), &cambc::map::altars(),
                              &cambc::map::spawn_region(team::ally), &cambc::map::spawn_region(team::enemy)})
        h = mix_board(h, *board);
    static std::array<std::uint32_t, 4096> camps;
    std::uint32_t count{};
    cambc::detail::check(cambc::detail::sdk_map_camp_layout(camps.data(), static_cast<std::uint32_t>(camps.size()), &count));
    h = mix(h, count);
    for (std::uint32_t i = 0; i < std::min<std::uint32_t>(count, camps.size()); ++i) h = mix(h, camps[i]);
    return mix(h, 0);
}

std::span<const C> choose() {
    const auto picks = cambc::draft::team_size();
    const auto pick = [&](const auto& table) -> std::span<const C> {
        std::uint64_t total = 0;
        for (const auto& e : table) total += e.weight;
        auto r = map_hash() % total;
        for (const auto& e : table) {
            if (r < e.weight) return e.team;
            r -= e.weight;
        }
        return table[0].team;
    };
    if (picks == 3) return pick(three);
    if (picks == 4) return pick(four);
    if (picks == 5) return pick(five);
    return params::draft_preference;
}
} // namespace test_compositions

// On 3 picks, Tavi farms maps whose gold lies in pure-gold groups of our side: with no gems
// anywhere beside Vendetta and Heart of Ruin, else in Heart of Ruin's place.
std::span<const cambc::champion_draft> choose_table_draft() {
    using C = cambc::champion_draft;
    static constexpr C gold_three[] = {C::tavi, C::vendetta, C::heart_of_ruin};
    static constexpr C mixed_three[] = {C::marcella, C::vendetta, C::tavi};
    if (const auto& a = analysis(); cambc::draft::team_size() == 3 && a.map && a.fields >= 2) {
        const auto& profile = map_economy(*a.map);
        if (profile.tavi_map()) return profile.total_gems == 0 ? std::span<const C>{gold_three} : std::span<const C>{mixed_three};
    }
    switch (cambc::draft::team_size()) {
    case 3: return params::draft_three;
    case 4: return params::draft_four;
    case 5: return params::draft_five;
    }
    return params::draft_preference;
}

// Chosen once, so a late analysis cannot splice two rosters together. On 3 picks play_draft first
// asks after the analysis, which the first draft turn's fuel finishes on every competition map.
std::span<const cambc::champion_draft> table_draft() {
    static const auto selected = choose_table_draft();
    return selected;
}

namespace model {

static_assert(static_cast<int>(cambc::champion_draft::ryth) == 0 && static_cast<int>(cambc::champion_draft::vesper_vale) == 1
              && static_cast<int>(cambc::champion_draft::cassi_and_issac) == 3 && static_cast<int>(cambc::champion_draft::heart_of_ruin) == 11,
              "draft_model.h ids are champion_draft values");
static_assert(static_cast<int>(cambc::camp_type::gem_cluster) == 2 && static_cast<int>(cambc::camp_type::golem) == 5,
              "map_features.cc camp types are camp_type values");

// The map as mapgen's Grid holds it: team A is absolute team 0 (the map file's spawn), B its mirror.
mapfeat::Input engine_input() {
    mapfeat::Input in;
    in.W = cambc::map::width(), in.H = cambc::map::height();
    const auto sym = cambc::map::symmetry();
    in.sym = sym == cambc::symmetry::horizontal ? mapfeat::horizontal : sym == cambc::symmetry::vertical ? mapfeat::vertical : mapfeat::rotational;
    // Each board's packed rows (a bit a tile, row-major, low bit first) painted 16 tiles at a time, in this order:
    // positions() cost ~10 fuel a tile.
    const std::size_t tiles = static_cast<std::size_t>(in.W * in.H), size = bitboard::linear_buffer_size();
    in.t.resize(tiles);
    constexpr int kinds = 4;
    const bitboard* const boards[kinds] = {&cambc::map::walls(), &cambc::map::holes(), &cambc::map::bushes(), &cambc::map::altars()};
    constexpr mapfeat::Tile kind[kinds] = {mapfeat::wall, mapfeat::hole, mapfeat::bush, mapfeat::altar};
    std::vector<std::uint8_t> bits(kinds * size);
    for (int b = 0; b < kinds; ++b) boards[b]->export_linear_buffer({bits.data() + b * size, size});
    std::uint8_t* const t = in.t.data();
    std::size_t i = 0;
    const v128_t lanes = wasm_i8x16_make(1, 2, 4, 8, 16, 32, 64, -128, 1, 2, 4, 8, 16, 32, 64, -128);
    const v128_t spread = wasm_i8x16_make(0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1);
    for (; i + 16 <= tiles; i += 16) {
        v128_t out = wasm_i8x16_splat(mapfeat::ground);
        for (int b = 0; b < kinds; ++b) {
            std::uint16_t word;
            std::memcpy(&word, bits.data() + b * size + i / 8, 2);
            const v128_t set = wasm_i8x16_eq(wasm_v128_and(wasm_i8x16_swizzle(wasm_i16x8_splat(static_cast<std::int16_t>(word)), spread), lanes), lanes);
            out = wasm_v128_bitselect(wasm_i8x16_splat(kind[b]), out, set);
        }
        wasm_v128_store(t + i, out);
    }
    for (; i < tiles; ++i) {
        t[i] = mapfeat::ground;
        for (int b = 0; b < kinds; ++b)
            if (bits[b * size + i / 8] >> (i % 8) & 1) t[i] = kind[b];
    }
    cambc::detail::aabb box{};
    cambc::detail::check(cambc::detail::sdk_spawn_region(0, &box));
    in.sx = box.min_x, in.sy = box.min_y, in.sw = box.max_x - box.min_x, in.sh = box.max_y - box.min_y;
    // Every group's members: both teams' camps, so mapgen's allCamps() (a self-mirrored camp once).
    std::vector<std::uint32_t> words(2048);
    std::uint32_t n{};
    cambc::detail::check(cambc::detail::sdk_map_camp_layout(words.data(), static_cast<std::uint32_t>(words.size()), &n));
    if (n > words.size()) {
        words.resize(n);
        cambc::detail::check(cambc::detail::sdk_map_camp_layout(words.data(), n, &n));
    }
    for (std::uint32_t i = 0; i + 5 <= n;) {
        const auto size = words[i + 4];
        i += 5;
        for (std::uint32_t m = 0; m < size && i + 4 <= n; ++m, i += 4)
            in.camps.push_back({static_cast<int>(words[i + 1]), static_cast<int>(words[i + 2]), static_cast<int>(words[i + 3])});
    }
    return in;
}

// mapfeat::WalkField from the engine's distance fields (the same king steps and corner rule as
// grid.mjs bfs), at a host call's flat price instead of our own BFS.
void engine_walk(const mapfeat::Input& in, int side, bool camps_block, mapfeat::Distances& out) {
    bitboard blocked{cambc::map::walls() | cambc::map::holes() | cambc::map::altars()}, roots;
    const auto mirror = [&](int x, int y) {
        return in.sym == mapfeat::horizontal ? vec2{in.W - 1 - x, y}
               : in.sym == mapfeat::vertical ? vec2{x, in.H - 1 - y}
                                             : vec2{in.W - 1 - x, in.H - 1 - y};
    };
    for (int y = in.sy; y < in.sy + in.sh; ++y)
        for (int x = in.sx; x < in.sx + in.sw; ++x) {
            const vec2 a{x, y}, b = mirror(x, y);
            roots.set(side ? b : a);
            blocked.set(side ? a : b);
        }
    if (camps_block)
        for (const auto& c : in.camps) blocked.set({c.x, c.y});
    cambc::distance_field field;
    bitboard visited;
    field.compute(blocked, roots, visited);
    // Exported into the upper half of out's own bytes (no second buffer to zero), then widened in place,
    // front to back: the 32 bytes written for tiles i to i + 7 end before the 16 still to read from i + 8.
    // Unreachable (0xffff) becomes -1 by arithmetic; 8 tiles a few SIMD instructions (the plain loop is ~9 fuel
    // a tile).
    static_assert(cambc::distance_field::unreachable == 0xffff);
    const std::size_t n = static_cast<std::size_t>(in.W * in.H);
    out.resize(n);
    auto* const bytes = reinterpret_cast<std::uint8_t*>(out.data());
    field.export_linear_buffer(std::span<std::uint16_t>{reinterpret_cast<std::uint16_t*>(bytes + 2 * n), n});
    std::size_t i = 0;
    const v128_t one16 = wasm_i16x8_splat(1), one = wasm_i32x4_splat(1);
    for (; i + 8 <= n; i += 8) {
        const v128_t v = wasm_i16x8_add(wasm_v128_load(bytes + 2 * n + 2 * i), one16);
        wasm_v128_store(bytes + 4 * i, wasm_i32x4_sub(wasm_u32x4_extend_low_u16x8(v), one));
        wasm_v128_store(bytes + 4 * i + 16, wasm_i32x4_sub(wasm_u32x4_extend_high_u16x8(v), one));
    }
    for (; i < n; ++i) {
        std::uint16_t v;
        std::memcpy(&v, bytes + 2 * n + 2 * i, 2);
        const int x = ((v + 1) & 0xffff) - 1;
        std::memcpy(bytes + 4 * i, &x, 4);
    }
}

// mapfeat::ClearanceSum by bitboard host calls, equal to Grid::clearance_sum (~40k fuel at 100x100 against its BFS's
// ~1.1-1.7M). The BFS gives each tile its first popper's value + 1, so a tile reads g + (its BFS root is an edge
// tile), g its Chebyshev distance to the nearest source (unwalkable 0, walkable edge tile 1), and FIFO order makes
// the root the lowest-index source at distance g. So min(6, c), c the distance to unwalkable or off the map (erosions),
// plus 1 on each tile with both kinds of source at distance g <= 5 whose lowest-index one is an edge tile.
// `bytes` (0 or 1 a tile, row-major) into `out`: the linear buffer is a bit a tile, despite the SDK's comment.
void import_bytes(const std::uint8_t* bytes, std::size_t n, std::vector<std::uint8_t>& packed, bitboard& out) {
    packed.assign((n + 7) / 8, 0);
    std::size_t i = 0;
    for (; i + 16 <= n; i += 16) {
        const auto m = static_cast<std::uint16_t>(wasm_i8x16_bitmask(wasm_i8x16_ne(wasm_v128_load(bytes + i), wasm_i8x16_splat(0))));
        std::memcpy(packed.data() + i / 8, &m, 2);
    }
    for (; i < n; ++i) packed[i / 8] |= static_cast<std::uint8_t>((bytes[i] != 0) << (i % 8));
    out.import_linear_buffer(packed);
}

int engine_clearance(const mapfeat::Input& in, const std::uint8_t* walked) {
    const int W = in.W, H = in.H;
    const std::size_t n = static_cast<std::size_t>(W * H);
    const std::uint8_t* const t = in.t.data();
    const auto walkable = [&](int x, int y) {
        const std::uint8_t k = t[y * W + x];
        return k == mapfeat::ground || k == mapfeat::bush;
    };
    bitboard reach{cambc::uninitialized}, e{cambc::uninitialized}, rows{cambc::uninitialized}, sh{cambc::uninitialized};
    std::vector<std::uint8_t> packed;
    import_bytes(walked, n, packed, reach);
    {
        std::vector<std::uint8_t> bytes(n);
        std::uint8_t* const b = bytes.data();
        std::size_t i = 0;
        for (; i + 16 <= n; i += 16) {
            const v128_t kind = wasm_v128_load(t + i);
            const v128_t walk = wasm_v128_or(wasm_i8x16_eq(kind, wasm_i8x16_splat(mapfeat::ground)), wasm_i8x16_eq(kind, wasm_i8x16_splat(mapfeat::bush)));
            wasm_v128_store(b + i, wasm_v128_and(walk, wasm_i8x16_splat(1)));
        }
        for (; i < n; ++i) b[i] = t[i] == mapfeat::ground || t[i] == mapfeat::bush;
        import_bytes(b, n, packed, e);
    }
    // c >= k + 1 exactly on the walkable tiles eroded k times (off the map shifts in as unwalkable).
    int sum = 0;
    for (int k = 0;; ++k) {
        and_into(e, reach, sh);
        sum += static_cast<int>(sh.count());
        if (k == 5) break;
        e.shift_right_into(1, sh);
        and_into(e, sh, rows);
        e.shift_right_into(-1, sh);
        and_into(rows, sh, rows);
        rows.shift_up_into(1, sh);
        and_into(rows, sh, e);
        rows.shift_up_into(-1, sh);
        and_into(e, sh, e);
    }
    bitboard du{cambc::map::walls() | cambc::map::holes() | cambc::map::altars()}, edge;
    for (int x = 0; x < W; ++x) {
        if (walkable(x, 0)) edge.set({x, 0});
        if (H > 1 && walkable(x, H - 1)) edge.set({x, H - 1});
    }
    for (int y = 1; y < H - 1; ++y) {
        if (walkable(0, y)) edge.set({0, y});
        if (W > 1 && walkable(W - 1, y)) edge.set({W - 1, y});
    }
    if (edge.is_empty() || du.is_empty()) return sum;
    bitboard nu{cambc::uninitialized}, ne{cambc::uninitialized}, tie{cambc::uninitialized};
    for (int g = 1; g <= 5; ++g) {
        square_dilate(du, 1, nu);
        square_dilate(edge, 1, ne);
        xor_into(nu, du, du);
        xor_into(ne, edge, edge);
        and_into(du, edge, tie);
        tie &= reach;
        if (!tie.is_empty())
            for (const vec2 p : tie.positions()) {
                // The lowest-index source at distance g: rows up, x across.
                const auto first_is_edge = [&] {
                    for (int y = std::max(0, p.y - g); y <= std::min(H - 1, p.y + g); ++y) {
                        const bool full = y == p.y - g || y == p.y + g;
                        for (int x = p.x - g; x <= p.x + g; x += full ? 1 : 2 * g) {
                            if (x < 0 || x >= W) continue;
                            if (!walkable(x, y)) return false;
                            if (x == 0 || y == 0 || x == W - 1 || y == H - 1) return true;
                        }
                    }
                    return false;
                };
                sum += first_is_edge();
            }
        std::swap(du, nu);
        std::swap(edge, ne);
    }
    return sum;
}

// The map's features, measured once (the first draft turn's fuel covers them), and the pick count.
struct Measured {
    int picks;
    std::array<double, mapfeat::count> raw;
    std::vector<int> team; // model_team(raw, picks), with no picks known
};

// recall_health_fraction and gold_price_scale as linear functions of the map: SPSA oc5's slopes of the score gradient
// per SD of a feature (map-conditioned diagnostic), over the curvature 0.19, give the best shift in the tune's [0, 1]
// scale; mapcond_shrink of it is taken, clamped to the tune's range. Features as features.json (mapgen metrics).
void condition(const std::array<double, mapfeat::count>& raw, int sym) {
    static_assert(std::string_view{mapfeat::names[0]} == "area" && std::string_view{mapfeat::names[2]} == "spawn_dist"
                  && std::string_view{mapfeat::names[8]} == "altars" && std::string_view{mapfeat::names[11]} == "gems_side"
                  && std::string_view{mapfeat::names[13]} == "big_share");
    const double area = raw[0], spawn = raw[2], altars = raw[8], gems = raw[11], big = raw[13];
    if (!(area > 0) || !std::isfinite(spawn) || !std::isfinite(altars) || !std::isfinite(gems) || !std::isfinite(big)) return;
    const auto z = [](double v, double mu, double sd) { return (v - mu) / sd; };
    const auto set = [](float& x, double slope, double lo, double hi) {
        const double v = x + params::mapcond_shrink * slope / 0.19 * (hi - lo);
        x = static_cast<float>(std::clamp(v, lo, hi));
    };
    set(params::recall_health_fraction,
        -0.05269065614849656 * z(spawn, 66.1149660543131, 47.62428822005238)
            - 0.03924270607871787 * z(std::log(std::max(1.0, gems)), 5.182193810366967, 0.7775773891951455)
            - 0.04630011361548256 * z(std::log(area), 7.895432588966761, 0.7478987844328654),
        0.1489, 0.5954);
    set(params::gold_price_scale,
        -0.04999140976968308 * z(altars, 2.7698848509052185, 2.5604211404480193)
            + 0.04437415451171142 * z(big, 0.2232195154419592, 0.28208371248475167)
            + 0.040453610700071474 * z(sym == mapfeat::vertical ? 1.0 : 0.0, 0.19547058040468585, 0.39656252041884416),
        0.6826, 2.7304);
}

std::optional<Measured> measure() {
    const int picks = static_cast<int>(cambc::draft::team_size());
    if (picks < 3 || picks > 5) return std::nullopt;
    [[maybe_unused]] const auto start = params::draft_parity ? cambc::fuel_remaining() : 0;
    const auto in = engine_input();
    features_measured = true; // a throw still spent what it filled in
    const auto raw = mapfeat::compute(in, engine_walk, true, params::draft_parity ? mapfeat::every : mapfeat::model_features(),
                                      engine_clearance, &feature_work);
    const auto team = mapfeat::model_team(raw, picks);
    if (static_cast<int>(team.size()) != picks) return std::nullopt;
    if constexpr (params::draft_parity) {
        const auto used = start - cambc::fuel_remaining();
        debug_block({
            const auto key = static_cast<unsigned long long>(mapfeat::map_key(in));
            std::printf("FEAT %016llx", key);
            for (const double v : raw) std::printf(" %.17g", v);
            std::printf("\nTEAM %016llx %d", key, picks);
            for (const int c : team) std::printf("%c%s", c == team.front() ? ' ' : ',', draft_model::champion_names[c]);
            std::printf("\nFEATFUEL %016llx %llu\n", key, static_cast<unsigned long long>(used));
        });
    }
    return Measured{picks, raw, team};
}

std::vector<int> ids(const std::vector<cambc::champion_draft>& picks) {
    std::vector<int> out;
    for (const auto p : picks) out.push_back(static_cast<int>(p));
    return out;
}

} // namespace model

// The draft lab's model draft for this map, in pick order (tools/draftlab/README.md, deployment);
// null (table_draft then) with params::map_model_draft off, on test drafts, for pick counts without
// a model, or a failure. Needs only the map, so it is made on the first draft turn, whose 10M fuel
// covers it before the analysis (tools/draftlab/README.md, cost; spawns joined only by dash or
// crystal take a crystal field, up to ~6M).
// With counter terms (draft_model::counters) the team is re-ranked whenever more picks are known, ours or the
// opponent's revealed ones (a round's picks show once both teams have made them); without, it is chosen once.
const std::vector<cambc::champion_draft>* model_draft() {
    if constexpr (params::test_draft || !params::map_model_draft) return nullptr;
    static const auto measured = []() -> std::optional<model::Measured> {
        try {
            return model::measure();
        } catch (const std::exception& e) {
            if constexpr (params::draft_parity) {
                debug_block({ std::printf("FEATFAIL %s\n", e.what()); });
            }
            return std::nullopt;
        } catch (...) {
            return std::nullopt;
        }
    }();
    if (!measured) return nullptr;
    static std::vector<cambc::champion_draft> chosen;
    static int known = -1;
    const auto ours = model::ids(cambc::draft::current_draft(team::ally));
    const auto theirs = draft_model::counters ? model::ids(cambc::draft::current_draft(team::enemy)) : std::vector<int>{};
    const int now = draft_model::counters ? static_cast<int>(ours.size() * 8 + theirs.size()) : 0;
    if (now != known) {
        const bool none = !draft_model::counters || (ours.empty() && theirs.empty());
        const auto team = none ? measured->team : mapfeat::model_team(measured->raw, measured->picks, ours, theirs);
        if (static_cast<int>(team.size()) != measured->picks) return known < 0 ? nullptr : &chosen;
        // The kept champions stay in their order: the draft analysis's leads are per body in pick order, and a
        // changed order restarts them on draft turns too short to finish (8 points lost on the held-out suites).
        std::vector<cambc::champion_draft> next;
        for (const auto c : chosen)
            if (std::find(team.begin(), team.end(), static_cast<int>(c)) != team.end()) next.push_back(c);
        for (const int c : team)
            if (std::find(next.begin(), next.end(), static_cast<cambc::champion_draft>(c)) == next.end()) next.push_back(static_cast<cambc::champion_draft>(c));
        chosen = std::move(next);
        known = now;
    }
    return &chosen;
}

std::vector<cambc::champion_draft> draft_order() {
    if constexpr (params::test_draft) {
        static const auto chosen = test_compositions::choose();
        return {chosen.begin(), chosen.end()};
    }
    // The model first even under the book: its first call must fall in the 10M first draft turn, and it keeps state
    // across picks, so an opponent that leaves the book after pick 0 meets the same draft as without one.
    const auto* chosen = model_draft();
    if (const auto* recorded = book::draft_order()) return *recorded;
    if (chosen) return locked(*chosen);
    const auto table = table_draft();
    return locked({table.begin(), table.end()});
}

// The team we expect, in id order (Cassi before Issac): our picks so far, then the rest of the order.
std::vector<cambc::champion_type> expected_bodies() {
    auto picks = cambc::draft::current_draft(team::ally);
    const std::size_t team = cambc::draft::team_size();
    for (const auto pick : draft_order()) {
        if (picks.size() >= team) break;
        if (std::find(picks.begin(), picks.end(), pick) == picks.end()) picks.push_back(pick);
    }
    std::vector<cambc::champion_type> bodies;
    for (const auto pick : picks) {
        const int d = static_cast<int>(pick), ci = static_cast<int>(cambc::champion_draft::cassi_and_issac);
        if (d == ci) bodies.push_back(cambc::champion_type::cassi), bodies.push_back(cambc::champion_type::issac);
        else bodies.push_back(static_cast<cambc::champion_type>(d < ci ? d : d + 1));
    }
    return bodies;
}

// Rewritten each round: the expected team changes only with a pick off the order.
void write_leads(Analysis& a, DraftState& state) {
    state.header.leads_at = 0;
    if (!a.map || a.leads_at == 0) return;
    make_leads(*a.map, a, draft_reserve() / 2);
    const int w = lead_width(static_cast<int>(a.map->groups.size()));
    PlanWriter out{state.plan, a.leads_at};
    for (int b = 0; b < DraftPlan::lead_bodies; ++b)
        for (const int code : a.leads[b]) out.put(b < std::min(static_cast<int>(a.lead_for.size()), a.leads_made) ? static_cast<std::uint32_t>(code) : 0u, w);
    state.header.leads_at = static_cast<std::uint16_t>(a.leads_at);
}

void write_plan(DraftState& state) {
    // The section stays in state.plan, so only sites searched since its last write are written.
    if (auto& a = analysis(); a.map && a.ward_site != a.wards_written) {
        write_wards(*a.map, a, state.plan, state.header);
        a.wards_written = a.ward_site;
    }
    // Rewritten each round with the bodies picked so far; draft_order() may throw.
    try {
        write_leads(analysis(), state);
    } catch (const std::exception&) {
        state.header.leads_at = 0;
    }
    state.header.field_layers = static_cast<std::uint16_t>(std::min(max_field_layers(), (1 << PlanHeader::layer_bits) - 1));
    state.header.write(state.plan);
    PlanFacts::write_done(state.plan, state.done);
    cambc::detail::check(cambc::detail::sdk_bc_submit_draft_memory(&state.plan, sizeof(DraftPlan)));
}

} // namespace

namespace {
// cambc::draft_memory's snapshot, without its vector (zeroed before the read overwrites it): the SDK's
// is never constructed (sdk_skip.cpp).
alignas(DraftPlan) std::byte draft_bytes[sizeof(DraftPlan)];
bool draft_read = false;
} // namespace
// sdk_skip.cpp names these globals' guards by their mangled names: an SDK that renames or retypes
// them fails here, not by silently building them again. Nothing may read either (the SDK does not).
static_assert(std::is_same_v<decltype(cambc::champion_designs), const std::array<cambc::champion, 13>>);
static_assert(std::is_same_v<decltype(cambc::draft_memory), cambc::draft_memory_buffer>);

void capture_draft_memory() {
    std::uint32_t size{};
    cambc::detail::check(cambc::detail::sdk_draft_memory_size(&size));
    if (size < sizeof(DraftPlan)) return;
    cambc::detail::check(cambc::detail::sdk_read_draft_memory(0, draft_bytes, sizeof(DraftPlan)));
    draft_read = true;
}

const DraftPlan* read_draft_plan() { return draft_read ? reinterpret_cast<const DraftPlan*>(draft_bytes) : nullptr; }

void play_draft(DraftState& state) {
    // Write before picking: a pick ends the draft turn's actions (later writes fail with error 18),
    // and the draft bot may not run again after its last pick.
    // Fix the order before the analysis spends the first turn's fuel. A 3-pick table draft
    // instead waits for the analysis (choose_table_draft's Tavi maps).
    if (params::test_draft || model_draft() || cambc::draft::team_size() != 3) draft_order();
    try {
        analyse(state);
    } catch (const std::exception&) {
        analysis().done = true; // a member's tiles may be half written: only finished groups count
    }
    if (draft_round() == 0) state.done = analysis().done;
    // Local builds: a first turn that cut sections to fit (analyse's cap), counted by the tools; on the ladder, nothing.
    if constexpr (local_build) {
        if (draft_round() == 0 && analysis().capped) std::printf("DRAFT-CAPPED %u\n", analysis().capped);
    }
    // Whether the model's fuel pushed the analysis past the first draft turn (parity.py reports it).
    if constexpr (params::draft_parity) {
        debug_block({
            std::printf("DRAFTTURN %d analysed %d fuel %llu\n", draft_round(), analysis().done ? 1 : 0,
                        static_cast<unsigned long long>(cambc::fuel_remaining()));
        });
    }
    write_plan(state);
    pick_first_available(state, draft_order());
}

void ensure_picked(DraftState& state) {
    if (state.picked_round == draft_round()) return;
    // draft_order() may be what threw in play_draft.
    try {
        if (pick_first_available(state, draft_order())) return;
    } catch (const std::exception&) {
    }
    if (pick_first_available(state, params::draft_preference)) return;
    pick_first_available(state, all_champions());
}

void PlanFacts::write(DraftPlan& plan) const {
    PlanWriter w{plan, PlanHeader::bits};
    const bool facts = present && fits();
    w.put(done, 1), w.put(facts, 1);
    if (facts) w.put(spawn_dist < 0 ? inf_dist : spawn_dist, dist_bits), w.put(altars, altar_bits), w.put(gems, gem_bits), w.put(big_gems, gem_bits);
    w.put(static_cast<std::uint32_t>(outputs), output_count_bits);
    for (int k = 0; k < outputs; ++k) w.put(output[k], output_bits);
    if constexpr (open_bits > 0) {
        w.put(open_made, 1);
        for (const auto& l : open)
            for (const auto g : l) w.put(g, open_plan::step_bits);
    }
}

void PlanFacts::write_open(DraftPlan& plan, const std::array<std::array<std::uint8_t, open_plan::max_steps>, open_plan::max_bodies>& steps) {
    if constexpr (open_bits > 0) {
        PlanWriter w{plan, plan_body_at(plan) - open_bits};
        w.put(1, 1);
        for (const auto& l : steps)
            for (const auto g : l) w.put(g, open_plan::step_bits);
    }
}

PlanFacts PlanFacts::read(const DraftPlan& plan, int* length) {
    PlanReader r{plan, PlanHeader::bits};
    PlanFacts f;
    f.done = r.get(1), f.present = r.get(1);
    if (f.present) {
        f.spawn_dist = static_cast<int>(r.get(dist_bits)), f.altars = static_cast<int>(r.get(altar_bits));
        f.gems = static_cast<int>(r.get(gem_bits)), f.big_gems = static_cast<int>(r.get(gem_bits));
        if (f.spawn_dist == inf_dist) f.spawn_dist = -1;
    }
    f.outputs = static_cast<int>(r.get(output_count_bits));
    for (int k = 0; k < f.outputs; ++k) f.output[k] = static_cast<std::uint16_t>(r.get(output_bits));
    if constexpr (open_bits > 0) {
        f.open_made = r.get(1);
        for (auto& l : f.open)
            for (auto& g : l) g = static_cast<std::uint8_t>(r.get(open_plan::step_bits));
    }
    if (length) *length = r.at() - PlanHeader::bits;
    return f;
}

void PlanFacts::write_done(DraftPlan& plan, bool done) { PlanWriter{plan, PlanHeader::bits}.put(done, 1); }

int plan_body_at(const DraftPlan& plan) {
    int length = 0;
    PlanFacts::read(plan, &length);
    return PlanHeader::bits + length;
}

// From the static map and only the features condition() reads (~15k fuel at 100x100; mapgen's metrics() otherwise
// cost millions). spawn_dist is symmetric, so from our spawn; through the camps, else around them (spawns joined
// only by dash or crystal leave the values alone). gems_side and big_share by the symmetry: a side holds half of
// every camp.
PlanFacts measure_facts(const StaticMap& map) {
    cambc::distance_field field;
    bitboard visited;
    const auto& box = map.enemy_spawn_box;
    const auto spawn_dist = [&](const bitboard& blocked) {
        field.compute(blocked, map.ally_spawn, visited);
        int best = cambc::distance_field::unreachable;
        for (int y = std::max(0, box.y0 - 1); y <= std::min(map.height - 1, box.y1 + 1); ++y)
            for (int x = std::max(0, box.x0 - 1); x <= std::min(map.width - 1, box.x1 + 1); ++x)
                if (!test(map.enemy_spawn, {x, y})) best = std::min<int>(best, field.get({x, y}));
        return best;
    };
    int S = spawn_dist(map.blocked_for_us | map.camp_tiles);
    if (S == cambc::distance_field::unreachable) S = spawn_dist(map.blocked_for_us);
    constexpr int gems_of[6] = {4, 15, 7, 0, 200, 36}; // map_features.cc camp_gems
    int gems = 0, big = 0;
    for (const auto& c : map.camp_members) {
        const int k = static_cast<int>(c.type);
        gems += gems_of[k], big += k == 4 || k == 5 ? gems_of[k] : 0;
    }
    PlanFacts f;
    f.present = true;
    f.spawn_dist = S == cambc::distance_field::unreachable ? -1 : S;
    f.altars = static_cast<int>(map.altar_tiles.count()), f.gems = gems, f.big_gems = big;
    return f;
}

// Each champion is its own instance, which the draft's globals never reach: the draft's facts come through the
// draft memory, else are measured again on the first turn (a missed draft, or another map's plan).
void condition_on_map(const StaticMap& map) {
    static bool done = false;
    if (done) return;
    done = true;
    PlanFacts f;
    const auto* plan = read_draft_plan();
    if (plan && !map.ally_spawn_tiles.empty() && PlanHeader::read(*plan).check == plan_check(map)) {
        f = PlanFacts::read(*plan);
        // Every draft precompute must finish in the draft's first turn (draft-features.md).
        if constexpr (local_build) {
            if (!f.done) {
                std::printf("DRAFT-UNFINISHED: the draft's first turn left its precompute unfinished\n");
                cambc::resign();
            }
        }
    }
    [[maybe_unused]] const bool drafted = f.present;
    if (!f.present) f = measure_facts(map);
    if constexpr (params::check_draft_facts) {
        debug_block({
            const auto m = measure_facts(map);
            std::printf("FACTCHECK %s %s %d %d %d %d\n", drafted ? "drafted" : "measured",
                        m.present == f.present && m.spawn_dist == f.spawn_dist && m.altars == f.altars && m.gems == f.gems
                                && m.big_gems == f.big_gems
                            ? "same"
                            : "DIFF",
                        m.spawn_dist, m.altars, m.gems, m.big_gems);
        });
    }
    const double S = f.spawn_dist < 0 ? std::numeric_limits<double>::infinity() : f.spawn_dist;
    const double gems = f.gems, big = f.big_gems;
    std::array<double, mapfeat::count> raw;
    raw.fill(std::numeric_limits<double>::quiet_NaN());
    raw[0] = static_cast<double>(map.width) * map.height, raw[2] = S, raw[8] = f.altars, raw[11] = gems / 2;
    raw[13] = std::floor(100 * (big / 2) / std::max(1.0, gems / 2) + 0.5) / 100;
    const int sym = map.symmetry == cambc::symmetry::horizontal ? mapfeat::horizontal
                    : map.symmetry == cambc::symmetry::vertical ? mapfeat::vertical
                                                                 : mapfeat::rotational;
    model::condition(raw, sym);
    debug_block({
        std::printf("MAPFEAT %g %g %g %g %g %d %s recall %a gold %a\n", raw[0], raw[2], raw[8], raw[11], raw[13], sym,
                    drafted ? "drafted" : "measured", params::recall_health_fraction, params::gold_price_scale);
    });
}

} // namespace aph
