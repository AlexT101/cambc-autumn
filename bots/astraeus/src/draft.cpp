#include "draft.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cstring>
#include <span>
#include <vector>
#include "params.h"
#include "util.h"
#include "world.h"

namespace aph {

namespace {

int draft_round() { return static_cast<int>(cambc::round_number()); }

constexpr auto all_champions() {
    std::array<cambc::champion_draft, static_cast<std::size_t>(cambc::champion_draft::heart_of_ruin) + 1> all{};
    for (std::size_t i = 0; i < all.size(); ++i) all[i] = static_cast<cambc::champion_draft>(i);
    return all;
}

// A rejected pick does not spend the turn, so trying the next candidate is always safe.
bool pick_first_available(DraftState& state, std::span<const cambc::champion_draft> order) {
    const auto ours = cambc::draft::current_draft(team::ally);
    for (const auto pick : order) {
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

// The static map analysis every champion would repeat, carried over draft turns while fuel lasts.
// A draft turn keeps `draft_reserve` for the plan's write and the pick.
constexpr std::uint64_t draft_reserve = 40000;

constexpr int champion_types = static_cast<int>(cambc::champion_type::heart_of_ruin) + 1;

// Farm's round-1 view of a champion of one type (rank_body): full health, base stats, every camp
// asleep at full health, gold at a typical price. Per group: its worth (negative if farm never
// picks it), and the rounds and camp damage of clearing it alone, spells kiting where farm would.
struct TypeFacts {
    bool ready = false;
    float output = 0, spare = 0;
    std::vector<float> worth, clear, damage;
};

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
};

int lead_bits(const StaticMap& map) {
    return DraftPlan::lead_bodies * DraftPlan::leads * lead_width(static_cast<int>(map.groups.size()));
}

// The ward section follows the leads, if they fit.
int wards_from(const StaticMap& map, const Analysis& a) { return a.leads_at > 0 ? a.leads_at + lead_bits(map) + a.dash_bits : a.attack_at; }

// Our body i's spawn tile, as the engine places them: team A's row by row from the bottom left,
// team B's on the mirror tiles of A's.
vec2 body_tile(const StaticMap& map, int i) {
    auto tiles = map.team_a ? map.ally_spawn_tiles : map.enemy_spawn.positions();
    std::sort(tiles.begin(), tiles.end(), [](vec2 a, vec2 b) { return a.y != b.y ? a.y < b.y : a.x < b.x; });
    const vec2 t = tiles[std::min<std::size_t>(static_cast<std::size_t>(i), tiles.size() - 1)];
    return map.team_a ? t : map.mirror(t);
}

float base_output(cambc::champion_type type) {
    const auto& f = facts(type);
    return std::max(1.0f, raw_output(f, f.strength.base, f.focus.base));
}

// The members as (health, strength), deadliest first.
void sorted_members(const CampGroup& group, std::vector<std::pair<float, float>>& left) {
    left.clear();
    for (const auto& m : group.members) left.push_back({m.max_health, m.strength});
    std::sort(left.begin(), left.end(), [](const auto& x, const auto& y) { return x.second * y.first > y.second * x.first; });
}

// Camp damage taken clearing `left` in order at `strength` a round; `rounds`, the rounds taken.
float clear_damage(const std::vector<std::pair<float, float>>& left, float strength, float& rounds) {
    float damage = 0;
    rounds = 0;
    for (const auto& [hp, hits] : left) {
        rounds += std::ceil(hp / strength);
        damage += hits * (rounds - 1);
    }
    return damage;
}

void type_facts(const StaticMap& map, cambc::champion_type type, TypeFacts& out) {
    const auto& f = facts(type);
    const float s = base_output(type);
    float spells = 0;
    if (f.ranged)
        for (const auto& ab : f.abilities)
            if (ab.kind == AbilityKind::damage) spells += ab.multiplier * f.focus.base / static_cast<float>(ability_cooldown);
    const float basic = std::max(1.0f, f.strength.base * (f.has_attack_reset() ? 1.0f + 1.0f / static_cast<float>(ability_cooldown) : 1.0f));
    const float usable = f.health.base * (1.0f - params::recall_health_fraction);
    const float paid = f.passive == Passive::bonus_gold ? 1.0f + static_cast<float>(cambc::constants::passive_abilities::vesper_vale_bonus_gold_percent) / 100.0f : 1.0f;
    const float per_gold = 0.2f * paid * (type == cambc::champion_type::cassi ? params::gold_farmer_weight : 1.0f);
    const float per_gem = 1.0f + per_gold * f.tribute_gold_per_gem();
    out.output = s;
    out.spare = usable / params::camp_risk;
    const auto n = map.groups.size();
    out.worth.assign(n, -1), out.clear.assign(n, 0), out.damage.assign(n, 0);
    static std::vector<std::pair<float, float>> left;
    for (std::size_t g = 0; g < n; ++g) {
        const auto& group = map.groups[g];
        if (group.has_monolith || group.gems + group.gold == 0) continue;
        sorted_members(group, left);
        float attackers = 0, rest = 0;
        bool kites = spells > 0 && group.strength > 0;
        for (const auto& m : group.members) {
            if (m.strength > 0) attackers += m.max_health, kites = kites && m.reach < ability_range;
            else rest += m.max_health;
        }
        float alone = 0;
        float damage = clear_damage(left, s, alone), clear = alone;
        if (kites) {
            const float kite = attackers / spells + rest / (basic + spells);
            const float heal = damage / usable * (static_cast<float>(cambc::constants::recall_time) + static_cast<float>(dist(map.landing_tiles[0], group.centre)));
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
    const vec2 tile = body_tile(map, b);
    const int i = static_cast<int>(std::find(map.ally_spawn_tiles.begin(), map.ally_spawn_tiles.end(), tile) - map.ally_spawn_tiles.begin());
    const bool by_tile = !a.spawn_steps.empty() && i < static_cast<int>(map.ally_spawn_tiles.size());
    std::array<std::pair<float, int>, DraftPlan::leads> top;
    top.fill({0.0f, -1});
    static std::vector<std::pair<float, float>> left;
    for (int g = 0; g < static_cast<int>(map.groups.size()); ++g) {
        float worth = T.worth[g], clear = T.clear[g];
        const int steps = by_tile ? a.spawn_steps[g][i] : a.steps[g][0];
        if (worth < 0 || steps == unreachable) continue;
        bool claimed = false;
        for (int j = 0; j < b; ++j) claimed |= a.leads[j][0] == g + 1;
        if (claimed) continue;
        if (T.damage[g] > T.spare) {
            if (partner <= 0) continue;
            sorted_members(map.groups[g], left);
            const float part = T.output / (T.output + partner);
            if (clear_damage(left, T.output + partner, clear) * part > T.spare) continue;
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

std::vector<cambc::champion_type> expected_bodies(const DraftState& state);

// Leads for the team we now expect, as far as fuel above `reserve` allows; a changed guess
// starts them again.
void make_leads(const StaticMap& map, Analysis& a, const DraftState& state, std::uint64_t reserve) {
    if (auto expected = expected_bodies(state); expected != a.lead_for) a.lead_for = std::move(expected), a.leads_made = 0;
    const auto n = map.groups.size();
    for (; a.leads_made < static_cast<int>(std::min<std::size_t>(a.lead_for.size(), DraftPlan::lead_bodies)); ++a.leads_made) {
        auto& T = a.types[static_cast<std::size_t>(a.lead_for[a.leads_made])];
        if (!T.ready) {
            if (!fuel_ok(reserve + 5000 + 600 * n)) return;
            type_facts(map, a.lead_for[a.leads_made], T);
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
int unzigzag(std::uint32_t z) { return z & 1 ? -static_cast<int>((z + 1) / 2) : static_cast<int>(z / 2); }

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
        int best = 1 << 30;
        for (int k = 0; k <= PlanHeader::max_rice; ++k) {
            int bits = 0;
            for (const auto c : codes[which]) bits += PlanWriter::rice_bits(c, k);
            if (bits < best) best = bits, header.rice[which] = static_cast<std::uint8_t>(k);
        }
    }
    PlanWriter w{plan, PlanHeader::bits};
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
    bitboard tributes, walls{cambc::uninitialized}, walk{cambc::uninitialized};
    for (const auto& altar : map.altars) tributes |= altar.tribute_tiles();
    or_into(map.blocked_for_us, map.camp_tiles, walls);
    walls.reachable_tiles_into(map.ally_spawn_tiles[0], unreachable, walk);
    and_into(tributes, map.camp_tiles, walls);
    if (board_empty(tributes) || !board_empty(walls)) return false;
    drop(tributes, walk);
    return board_empty(tributes);
}

// PlanHeader::dash_spawn_steps and dash_altar_steps, field `i` of a dash's walls: from ally spawn
// tile i, or after them from the tribute tiles.
void check_dash_steps(const StaticMap& map, Analysis& a, int i, int spawn_fields) {
    bitboard goals;
    if (i < spawn_fields) set_tile(goals, map.ally_spawn_tiles[i]);
    else
        for (const auto& altar : map.altars) goals |= altar.tribute_tiles();
    // Champions use these steps instead of such a field: the layers the plan reports leave it out.
    const int layers = max_field_layers();
    const auto costliest = costliest_field();
    const auto field = make_field(map.dash_walls, goals);
    max_field_layers() = layers, costliest_field() = costliest;
    for (std::size_t g = 0; g < map.groups.size(); ++g) {
        const int steps = field.at(map.groups[g].centre);
        if (i < spawn_fields) a.dash_spawn = a.dash_spawn && steps == a.spawn_steps[g][i];
        else a.dash_altar = a.dash_altar && steps == a.steps[g][2];
    }
}

// Body b's entry in the dash steps, for a dash of `kind` from its spawn tile.
void dash_entry(const StaticMap& map, Analysis& a, int b, int kind) {
    const vec2 tile = body_tile(map, b);
    const int i = static_cast<int>(std::find(map.ally_spawn_tiles.begin(), map.ally_spawn_tiles.end(), tile) - map.ally_spawn_tiles.begin());
    if (i >= static_cast<int>(map.ally_spawn_tiles.size()) || i >= 1 << dash_tile_bits) return;
    // As check_dash_steps: the layers the plan reports leave the field out.
    const int layers = max_field_layers();
    const auto costliest = costliest_field();
    const auto field = make_field(kind == 1 ? map.dash_walls : map.landing_dash_walls, single(tile));
    max_field_layers() = layers, costliest_field() = costliest;
    auto& codes = a.dash_codes[b];
    codes.clear();
    for (const auto& group : map.groups) {
        const int steps = field.at(group.centre), bound = dist(tile, group.centre);
        if (steps != unreachable && steps < bound) return;
        codes.push_back(steps == unreachable ? 0u : static_cast<std::uint32_t>(steps - bound) + 1);
    }
    int best = 1 << 30;
    for (int k = 0; k <= PlanHeader::max_rice; ++k) {
        int bits = 0;
        for (const auto c : codes) bits += PlanWriter::rice_bits(c, k);
        if (bits < best) best = bits, a.dash_rice[b] = k;
    }
    a.dash_kind[b] = kind, a.dash_tile[b] = i;
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

// One member's attack tiles; false, writing nothing, if they do not fit or champions could not
// decode them.
bool write_attack_tiles(const StaticMap& map, vec2 p, Analysis& a, DraftPlan& plan) {
    static std::array<bitboard, DraftPlan::attack_ranges.size()> tiles{};
    static bitboard off{cambc::uninitialized};
    for (std::size_t k = 0; k < tiles.size(); ++k) {
        const int r = DraftPlan::attack_ranges[k];
        tiles[k] = map.viewers(p, r);
        tiles[k] &= map.open_for_us;
        copy_into(tiles[k], off);
        drop(off, map.open_bushes());
        if (!boards_equal(off, map.sight_off_bushes(p, r))) return false;
    }
    // Bits go only over bush_range's square; each range's bush tiles must be those within it.
    const auto& sent = tiles[0];
    bool any = false, exact = true;
    int bits = 0;
    each_in_square(map.open_bushes(), p, DraftPlan::bush_range, [&](vec2 t) {
        ++bits;
        const bool in = test(sent, t);
        any = any || in;
        for (std::size_t k = 1; k < tiles.size(); ++k)
            if (dist(t, p) <= DraftPlan::attack_ranges[k]) exact = exact && test(tiles[k], t) == in;
    });
    if (!exact) return false;
    PlanWriter w{plan, a.attack_at};
    if (!w.fits(any ? bits : 0)) return false;
    if (any) {
        PlanWriter{plan, a.attack_start + a.attack_index}.put(1, 1);
        each_in_square(map.open_bushes(), p, DraftPlan::bush_range, [&](vec2 t) { w.put(test(sent, t), 1); });
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

// The ward tile in placement range of the site's stand tiles that sees the most of what a champion
// at its centre cannot: tiles an enemy can stand on, counted once within 8 of the stand tiles
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
    sight_from(map, centre, vision_radius, own);
    draw_site(map, site, ability_range, near);
    near &= map.open_for_them;
    drop(near, own);
    draw_site(map, site, ward_sight, far);
    far &= map.open_for_them;
    drop(far, own);
    and_into(reach, map.open_for_us, candidates); // never a wall, hole, altar or their spawn (wards.placement)
    const auto n = std::min<std::uint32_t>(positions_into(candidates, tiles.data(), static_cast<std::uint32_t>(tiles.size())), tiles.size());
    const auto stride = cambc::detail::layout().chunk_stride;
    const int r = static_cast<int>(cambc::constants::ward_vision_radius);
    int best = 0, best_dist = 0;
    vec2 best_tile{-1, -1};
    for (std::uint32_t i = 0; i < n; ++i) {
        const vec2 c = tiles[i];
        sight_from(map, c, r, sight);
        int score = 0;
        each_word_in_square(sight, c, r, [&](int cx, int cy, std::uint64_t w) {
            const auto at = static_cast<std::size_t>(cy) * stride + static_cast<std::size_t>(cx);
            score += 2 * __builtin_popcountll(w & near.ptr()[at]) + __builtin_popcountll(w & far.ptr()[at]);
        });
        if (score > best || (score == best && score > 0 && dist(c, centre) < best_dist))
            best = score, best_dist = dist(c, centre), best_tile = c;
    }
    if (best_tile.x < 0) return 0;
    const auto b = ward_box(map, site);
    return static_cast<std::uint16_t>(1 + (best_tile.y - b.y0) * (b.x1 - b.x0 + 1) + (best_tile.x - b.x0));
}

// The ward section after the attack tiles, with the sites searched so far; false, with no section,
// if its width does not fit or it would not decode to these tiles.
bool write_wards(const StaticMap& map, const Analysis& a, DraftPlan& plan, PlanHeader& header) {
    header.wards_at = 0;
    const int at = wards_from(map, a);
    if (a.ward_bits == 0 || at >= 1 << PlanHeader::at_bits) return false;
    PlanWriter w{plan, at};
    if (!w.put(static_cast<std::uint32_t>(a.ward_bits), ward_width_bits)) return false;
    int written = 0;
    for (const auto code : a.ward_codes) {
        if (!w.put(code, a.ward_bits)) break; // the rest read past the end, as none
        ++written;
    }
    // Codes, not tiles: a tile check per site costs ~300 fuel, past draft_reserve on a big map whose
    // search runs into the 100k draft turns.
    PlanReader check{plan, at};
    bool same = static_cast<int>(check.get(ward_width_bits)) == a.ward_bits;
    for (int site = 0; site < ward_sites(map) && same; ++site)
        same = check.get(a.ward_bits) == (site < written ? a.ward_codes[site] : 0u);
    if (same) header.wards_at = static_cast<std::uint16_t>(at);
    return same;
}

// Each part checks its fuel first; a part not done is retried next draft turn.
void analyse(DraftState& state) {
    auto& plan = state.plan;
    auto& header = state.header;
    auto& a = analysis();
    const auto afford = [](std::uint64_t cost) { return fuel_ok(draft_reserve + cost); };
    if (a.done) return;
    if (!a.map) {
        if (!afford(150000)) return;
        a.map = StaticMap::build();
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
    for (; a.fields < 3 + spawn_fields; ++a.fields) {
        if (!afford(2 * field_cost_estimate())) return;
        if (a.fields == 0) set_steps(map, map.from_ally_spawn(), 0, a);
        else if (a.fields == 1)
            for (std::size_t g = 0; g < map.groups.size(); ++g)
                a.steps[g][1] = static_cast<std::uint16_t>(map.enemy_spawn_steps(map.groups[g].centre));
        else if (a.fields == 2) {
            bitboard goals;
            for (const auto& altar : map.altars) goals |= altar.tribute_tiles();
            set_steps(map, make_field(map.blocked_for_us, goals), 2, a);
        } else {
            set_steps(map, make_field(map.blocked_for_us, single(map.ally_spawn_tiles[a.fields - 3])), a.fields, a);
        }
    }
    if (!header.steps) {
        if (!write_steps(map, a, spawn_fields, plan, header)) {
            a.done = true;
            return;
        }
        a.attack_at = a.attack_start;
        for (const auto& group : map.groups) a.attack_at += static_cast<int>(group.members.size()); // the flags
        header.tributes_walked = tributes_walked(map);
        header.steps = true;
    }
    a.dash_spawn = a.dash_spawn && header.spawn_offsets;
    for (; a.dash_fields <= spawn_fields; ++a.dash_fields) {
        if (a.dash_fields < spawn_fields && !a.dash_spawn) continue;
        if (!afford(2 * field_cost_estimate())) return;
        check_dash_steps(map, a, a.dash_fields, spawn_fields);
    }
    header.dash_spawn_steps = a.dash_spawn, header.dash_altar_steps = a.dash_altar;
    make_leads(map, a, state, draft_reserve);
    // Dashers otherwise build a field from their spawn tile for their round-1 steps (farm).
    if (!header.dash_spawn_steps && !map.crossable.is_empty())
        for (; a.dash_bodies < static_cast<int>(std::min<std::size_t>(a.lead_for.size(), DraftPlan::lead_bodies)); ++a.dash_bodies) {
            const int kind = facts(a.lead_for[a.dash_bodies]).dash_kind();
            if (kind == 0) continue;
            if (!afford(2 * field_cost_estimate())) return;
            dash_entry(map, a, a.dash_bodies, kind);
        }
    for (; !a.attacks_done && a.attack_group < static_cast<int>(map.groups.size()); ++a.attack_group, a.attack_member = 0) {
        const auto& members = map.groups[a.attack_group].members;
        for (; a.attack_member < static_cast<int>(members.size()); ++a.attack_member) {
            const vec2 p = members[a.attack_member].pos;
            if (!afford(20000) || !map.find_bush_clusters(p, DraftPlan::attack_ranges[0], draft_reserve + 20000)) return;
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
    for (; a.ward_site < static_cast<int>(a.ward_codes.size()); ++a.ward_site) {
        static bitboard reach{cambc::uninitialized};
        const std::uint64_t cost = 5000 + 2000 * static_cast<std::uint64_t>(ward_box(map, a.ward_site).area());
        if (!afford(cost)) return;
        draw_site(map, a.ward_site, ward_range(), reach);
        // Under a floor: best_ward's bush_cluster() grows a missing cluster with no limit, and
        // the attack tiles found only those near the groups they reached.
        if (!map.find_bush_clusters(reach, draft_reserve + cost)) return;
        a.ward_codes[a.ward_site] = best_ward(map, a.ward_site, reach);
    }
    a.done = true;
}

} // namespace

TileBox ward_box(const StaticMap& map, int site) {
    const int groups = static_cast<int>(map.groups.size()), r = ward_range();
    TileBox b;
    if (site < groups) {
        b = {1 << 20, 1 << 20, -(1 << 20), -(1 << 20)};
        for (const auto& m : map.groups[site].members)
            b.x0 = std::min(b.x0, m.pos.x), b.y0 = std::min(b.y0, m.pos.y), b.x1 = std::max(b.x1, m.pos.x), b.y1 = std::max(b.y1, m.pos.y);
    } else {
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
    PlanReader bits{plan, PlanHeader::bits};
    const auto read = [&](std::vector<std::uint16_t>& steps, int which) __attribute__((always_inline)) {
        steps.resize(n);
        for (int g = 0; g < n; ++g) {
            const auto c = bits.get_rice(header.rice[which]);
            steps[g] = static_cast<std::uint16_t>(c == 0 ? unreachable : c - 1 + steps_bound(ally, enemy, map.groups[g].centre, which));
        }
    };
    read(out.ally, 0);
    out.enemy_at = bits.at();
    if (!with_enemy) bits.skip_rice(n, header.rice[1]);
    else if (!header.mirrored) read(out.enemy, 1);
    else if (!decode_mirrored(bits, header, map, out)) return false;
    read(out.altar, 2);
    out.offsets.assign(n, 0);
    out.predicted.assign(n, 0);
    if (header.spawn_offsets)
        for (int g = 0; g < n; ++g) {
            if (out.ally[g] == unreachable) continue;
            if (bits.get(1)) out.predicted[g] = 1;
            else out.offsets[g] = bits.get(2 * static_cast<int>(map.ally_spawn_tiles.size()));
        }
    out.end = bits.at();
    return bits.ok();
}

void decode_enemy_steps(const DraftPlan& plan, const PlanHeader& header, const StaticMap& map, DraftSteps& out) {
    PlanReader bits{plan, out.enemy_at};
    if (!header.mirrored) {
        const auto enemy = TileBox::of(map.enemy_spawn.positions());
        out.enemy.resize(map.groups.size());
        for (std::size_t g = 0; g < map.groups.size(); ++g) {
            const auto c = bits.get_rice(header.rice[1]);
            out.enemy[g] = static_cast<std::uint16_t>(c == 0 ? unreachable : c - 1 + steps_bound(out.spawn, enemy, map.groups[g].centre, 1));
        }
    } else if (!decode_mirrored(bits, header, map, out)) {
        out.enemy.assign(map.groups.size(), unreachable);
    }
}

int mirrored_enemy_steps(const DraftPlan& plan, const PlanHeader& header, const StaticMap& map, const DraftSteps& steps, int group) {
    if (!header.mirrored || header.rice[1] != 0) return -1;
    static int next = 0, next_at = 0; // the last group asked + 1, and its code's bit
    const bool ahead = group >= next && next > 0;
    PlanReader bits{plan, ahead ? next_at : steps.enemy_at};
    bits.skip_rice(ahead ? group - next : group, 0);
    const auto code = bits.get_rice(0);
    next = group + 1, next_at = bits.at();
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
    w.put(dash_spawn_steps, 1), w.put(dash_altar_steps, 1), w.put(dash_steps, 1);
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
    h.dash_spawn_steps = get(1), h.dash_altar_steps = get(1), h.dash_steps = get(1);
    for (auto& k : h.rice) k = static_cast<std::uint8_t>(get(rice_bits));
    h.attack_groups = static_cast<std::uint8_t>(get(group_bits));
    h.wards_at = static_cast<std::uint16_t>(get(at_bits));
    h.leads_at = static_cast<std::uint16_t>(get(at_bits));
    return h;
}

namespace {

// params::test_draft: the 10 most common compositions per pick count among the ladder's top 10
// teams (research/hyperion/DRAFT.md), each in its most common pick order.
namespace test_compositions {
using C = cambc::champion_draft;
constexpr C three[][3] = {
    {C::stellar, C::heart_of_ruin, C::ren},
    {C::heart_of_ruin, C::ren, C::ryth},
    {C::marcella, C::heart_of_ruin, C::stellar},
    {C::heart_of_ruin, C::vendetta, C::ren},
    {C::heart_of_ruin, C::marcella, C::vesper_vale},
    {C::heart_of_ruin, C::varg, C::stellar},
    {C::heart_of_ruin, C::marcella, C::ren},
    {C::heart_of_ruin, C::ryth, C::vesper_vale},
    {C::stellar, C::heart_of_ruin, C::cassi_and_issac},
    {C::heart_of_ruin, C::varg, C::cassi_and_issac},
};
constexpr C four[][4] = {
    {C::heart_of_ruin, C::ren, C::stellar, C::ryth},
    {C::heart_of_ruin, C::vendetta, C::ren, C::vesper_vale},
    {C::marcella, C::heart_of_ruin, C::stellar, C::ren},
    {C::stellar, C::heart_of_ruin, C::ren, C::cassi_and_issac},
    {C::heart_of_ruin, C::marcella, C::vesper_vale, C::ryth},
    {C::heart_of_ruin, C::varg, C::cassi_and_issac, C::ryth},
    {C::vesper_vale, C::cassi_and_issac, C::varg, C::stellar},
    {C::marcella, C::ryth, C::stellar, C::heart_of_ruin},
    {C::heart_of_ruin, C::ren, C::ryth, C::tavi},
    {C::marcella, C::ren, C::stellar, C::ryth},
};
constexpr C five[][5] = {
    {C::heart_of_ruin, C::ren, C::stellar, C::ryth, C::varg},
    {C::marcella, C::heart_of_ruin, C::stellar, C::ren, C::ryth},
    {C::heart_of_ruin, C::ren, C::ryth, C::stellar, C::tavi},
    {C::stellar, C::heart_of_ruin, C::ren, C::cassi_and_issac, C::ryth},
    {C::heart_of_ruin, C::marcella, C::vesper_vale, C::ryth, C::stellar},
    {C::heart_of_ruin, C::vendetta, C::ren, C::vesper_vale, C::varg},
    {C::heart_of_ruin, C::varg, C::cassi_and_issac, C::ryth, C::stellar},
    {C::stellar, C::heart_of_ruin, C::prism, C::marcella, C::ren},
    {C::stellar, C::heart_of_ruin, C::cassi_and_issac, C::marcella, C::willow},
    {C::vesper_vale, C::cassi_and_issac, C::varg, C::vendetta, C::stellar},
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

// Both sides see the same map, so the side-swapped game repeats each side's draft.
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
    const auto pick = [&](const auto& table) -> std::span<const C> { return table[map_hash() % std::size(table)]; };
    if (picks == 3) return pick(three);
    if (picks == 4) return pick(four);
    if (picks == 5) return pick(five);
    return params::draft_preference;
}
} // namespace test_compositions

std::span<const cambc::champion_draft> table_draft() {
    switch (cambc::draft::team_size()) {
    case 3: return params::draft_three;
    case 4: return params::draft_four;
    case 5: return params::draft_five;
    }
    return params::draft_preference;
}

std::vector<cambc::champion_draft> draft_order() {
    if constexpr (params::test_draft) {
        static const auto chosen = test_compositions::choose();
        return {chosen.begin(), chosen.end()};
    }
    const auto table = table_draft();
    return {table.begin(), table.end()};
}

// The team we expect, in id order (Cassi before Issac): our picks so far, this round's, then the
// rest of the order.
std::vector<cambc::champion_type> expected_bodies(const DraftState& state) {
    auto picks = cambc::draft::current_draft(team::ally);
    const auto add = [&](const auto& order) {
        for (const auto pick : order)
            if (std::find(picks.begin(), picks.end(), pick) == picks.end()) {
                picks.push_back(pick);
                return;
            }
    };
    const std::size_t team = cambc::draft::team_size();
    // draft_order() keeps test_draft's composition.
    const auto order = draft_order();
    if (state.picked_round != draft_round() && picks.size() < team) add(order);
    for (std::size_t had = 0; picks.size() < team && picks.size() != had;) {
        had = picks.size();
        add(params::test_draft ? std::span<const cambc::champion_draft>{order} : table_draft());
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
    make_leads(*a.map, a, state, draft_reserve / 2);
    const int w = lead_width(static_cast<int>(a.map->groups.size()));
    PlanWriter out{state.plan, a.leads_at};
    for (int b = 0; b < DraftPlan::lead_bodies; ++b)
        for (const int code : a.leads[b]) out.put(b < static_cast<int>(a.lead_for.size()) ? static_cast<std::uint32_t>(code) : 0u, w);
    state.header.leads_at = static_cast<std::uint16_t>(a.leads_at);
}

void write_plan(DraftState& state) {
    // The section stays in state.plan, so it is rewritten only when more sites are searched.
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
    cambc::draft_memory = std::span<const std::byte>{reinterpret_cast<const std::byte*>(&state.plan), sizeof(DraftPlan)};
}

} // namespace

const DraftPlan* read_draft_plan() {
    const auto* bytes = cambc::draft_memory.data();
    if (cambc::draft_memory.size() < sizeof(DraftPlan) || reinterpret_cast<std::uintptr_t>(bytes) % alignof(DraftPlan) != 0)
        return nullptr;
    return reinterpret_cast<const DraftPlan*>(bytes);
}

void play_draft(DraftState& state) {
    // Write before picking: a pick ends the draft turn's actions (later writes fail with error 18),
    // and the draft bot may not run again after its last pick.
    draft_order(); // caches test_draft's selection before the first turn's expensive analysis
    try {
        analyse(state);
    } catch (const std::exception&) {
        analysis().done = true; // a member's tiles may be half written: only finished groups count
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

} // namespace aph
