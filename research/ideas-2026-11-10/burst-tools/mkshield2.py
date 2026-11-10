"""mkshield2.py DIR MODE: mkshield.py's camp-aggro shield at no fuel when it cannot fire. MODE: gen | genrev.
The extra work runs only for a group within reach of an ally done acting whose health the group's whole strength
could take (else the original loops run); genrev's doubt only where a group could fell us. Doom lives outside the
Hazard struct (no bigger copies)."""
import sys
d, mode = sys.argv[1], sys.argv[2]
assert mode in ('gen', 'genrev')
S = d + '/src/'
def sub(path, old, new):
    s = open(S + path).read(); assert s.count(old) == 1, (path, old[:70]); open(S + path, 'w').write(s.replace(old, new))
rev = mode == 'genrev'

sub('model/safety.h', "float partner_bound(const World& world, const ChampionBelief& e);\n",
"""float partner_bound(const World& world, const ChampionBelief& e);
// A camp hit we could take instead of `o`, an ally done acting that it would fell: its death in our health
// (all of it, and more, for our linked partner).
float ally_fall_value(const World& world, const ChampionBelief& o);
// Not counting on the shelter of an ally yet to act from a camp hit that would fell us: it may leave.
inline constexpr bool shield_doubt_later = """ + ('true' if rev else 'false') + """;
// The most any group deals in a camp phase: an ally with more health and shield no group can fell.
float max_group_strength(const World& world);
""")
sub('model/safety.h', "    int tie_only_count_ = 0;\n",
"""    int tie_only_count_ = 0;
    // camp_damage reads members_ to here: after the members, each shield (a member whose hit falls on an ally done
    // acting that it fells, where our taking it would spare the ally) as two hits that cancel within the radius
    // where we would take that hit instead and leave ally_fall_value beyond it.
    int camp_total_ = 0;
""")
sub('model/safety.cc', "float partner_bound(const World& world, const ChampionBelief& e) {",
"""float ally_fall_value(const World& world, const ChampionBelief& o) {
    const auto& me = world.me();
    const float ours = my_health() + (me.shield_slot >= 0 ? shield_value(me.handle) : 0.0f);
    if (o.facts().passive == Passive::linked_pair && me.facts().passive == Passive::linked_pair) return my_max_health() + ours + 1;
    // Its life against ours: each full health, life and bag (params value units).
    const float theirs = o.max_health + params::life_value + params::gem_value * static_cast<float>(o.gems);
    const float own = my_max_health() + params::life_value + params::gem_value * static_cast<float>(me.gems);
    return ours * std::min(1.0f, theirs / own);
}

float max_group_strength(const World& world) {
    static float most = -1;
    if (most < 0) {
        most = 0;
        for (const auto& g : world.map().groups) most = std::max(most, g.strength);
    }
    return most;
}

float partner_bound(const World& world, const ChampionBelief& e) {""")
sub('model/safety.cc', """    const bool reread = refresh_;
    const auto& groups = world_.map().groups;
    world_.each_stirring([&](int g) {""",
"""    const bool reread = refresh_;
    const auto& groups = world_.map().groups;
    // Allies done acting that some group could fell (into others), and whether an ally is yet to act.
    std::array<std::int8_t, 4> fallers;
    int n_fallers = 0;
    bool later = false;
    float ours = -1; // our health and shield, read where a group could fell us
    // Members whose hit falls on a faller: shields (camp_total_) once every hit on it is summed.
    struct Onto {
        vec2 pos;
        int radius;
        bool stunned;
        std::int8_t ally; // into others
        float hit;
    };
    std::array<Onto, 8> onto;
    int n_onto = 0;
    world_.each_stirring([&](int g) {""")
sub('model/safety.cc', """                if (n < static_cast<int>(others.at.size()) && o.alive && o.visible && !o.is_self && !gone(o))
                    others.at[n++] = {o.pos, &o, -1, -2};""", """                if (n < static_cast<int>(others.at.size()) && o.alive && o.visible && !o.is_self && !gone(o)) {
                    if (!o.acted) later = true;
                    else if (n_fallers < static_cast<int>(fallers.size()) && o.health + o.shield <= max_group_strength(world_) * o.taken)
                        fallers[static_cast<std::size_t>(n_fallers++)] = static_cast<std::int8_t>(n);
                    others.at[n++] = {o.pos, &o, -1, -2};
                }""")
sub('model/safety.cc', """        for (std::size_t i = 0; i < size; ++i) {
            const auto& m = groups[g].members[i];
            if (c.health[i] <= 0 || m.strength <= 0 || (reread && seen_empty(m.pos))) continue;
            if (!stirred && c.member_asleep(i)) continue;""", """        bool track = false, doubt = false;
        for (int i = 0; i < n_fallers && !track && c.awake == Awake::awake; ++i) {
            const auto& o = others.at[fallers[static_cast<std::size_t>(i)]];
            track = box_out(o) <= groups[g].reach && o.belief->health + o.belief->shield <= groups[g].strength * o.belief->taken;
        }
        if (shield_doubt_later && later) {
            if (ours < 0) ours = my_health() + (world_.me().shield_slot >= 0 ? shield_value(world_.me().handle) : 0.0f);
            doubt = groups[g].strength * camp_factor_ >= ours;
        }
        if (track || doubt) {
        for (std::size_t i = 0; i < size; ++i) {
            const auto& m = groups[g].members[i];
            if (c.health[i] <= 0 || m.strength <= 0 || (reread && seen_empty(m.pos))) continue;
            if (!stirred && c.member_asleep(i)) continue;
            {
                int reach = m.reach, tie = m.reach;
                // The other that takes the hit: the strictly nearest within range, or -1 if tied.
                int target = -1, target_d = m.reach + 1;
                const bool doubts = doubt && m.strength * camp_factor_ >= ours;
                for (int k = 0; k < k_near; ++k) {
                    auto& o = others.at[near[k]];
                    const int d = dist(o.pos, m.pos);
                    if (d < target_d) target = near[k], target_d = d;
                    else if (d == target_d) target = -1;
                    if (d - 1 >= reach || (doubts && o.belief->side == team::ally && !o.belief->acted)) continue;
                    reach = std::min(reach, d - first(o)), tie = std::min(tie, d);
                }
                if (track && target >= 0 && n_onto < static_cast<int>(onto.size()))
                    if (const auto& o = *others.at[target].belief; o.side == team::ally && o.acted)
                        onto[static_cast<std::size_t>(n_onto++)] = {m.pos, target_d - first(others.at[target]), camp_stunned(m.handle) && test(world_.visible, m.pos),
                                                                    static_cast<std::int8_t>(target), m.strength * o.taken};
                emit(m, reach, tie);
            }
        }
        return;
        }
        for (std::size_t i = 0; i < size; ++i) {
            const auto& m = groups[g].members[i];
            if (c.health[i] <= 0 || m.strength <= 0 || (reread && seen_empty(m.pos))) continue;
            if (!stirred && c.member_asleep(i)) continue;""")
sub('model/safety.cc', """    });
    member_count_ = count;
}""", """    });
    member_count_ = count;
    camp_total_ = count;
    // An ally felled by the hits on it, which our taking one of them would spare.
    for (int i = 0; i < n_onto; ++i) {
        const auto& x = onto[static_cast<std::size_t>(i)];
        const auto& o = *others.at[x.ally].belief;
        float sum = 0;
        for (int j = 0; j < n_onto; ++j)
            if (onto[static_cast<std::size_t>(j)].ally == x.ally) sum += onto[static_cast<std::size_t>(j)].hit;
        if (const float health = o.health + o.shield; sum < health || sum - x.hit >= health) continue;
        if (static_cast<std::size_t>(camp_total_) + 2 > members_.size()) members_.resize(static_cast<std::size_t>(camp_total_) + 2);
        const float value = ally_fall_value(world_, o);
        members_[static_cast<std::size_t>(camp_total_++)] = {x.pos, value, 1, 1 << 12, 0, x.stunned, 0};
        members_[static_cast<std::size_t>(camp_total_++)] = {x.pos, -value, 1, x.radius, 0, x.stunned, 0};
    }
}""")
sub('model/safety.cc', """float Safety::camp_damage(vec2 p, bool worst, bool next) {
    const auto& members = awake_members();""", """float Safety::camp_damage(vec2 p, bool worst, bool next) {
    if (!members_known_) find_members();
    const std::span<const CampHit> members{members_.data(), static_cast<std::size_t>(camp_total_)};""")

# The dash landings' hazards (combat/self_abilities.cc): doom kept beside the hazards, not in them.
sub('combat/self_abilities.cc', """// Enemies and awake monsters that could reach a tile within a dash of `here` before our next turn.""",
"""// threats_near's camp hazards (by index) that pick an ally done acting and fell it: where they do not pick us, its
// death (ally_fall_value), listed after the hazards as two that cancel where the member picks us.
struct Doom {
    int hazard;
    float value;
    const ChampionBelief* ally;
    float hit;
};
std::array<Doom, 8> dooms;
int n_dooms = 0;

// Enemies and awake monsters that could reach a tile within a dash of `here` before our next turn.""")
sub('combat/self_abilities.cc', """    static std::vector<Hazard> out;
    out.clear();""", """    static std::vector<Hazard> out;
    out.clear();
    n_dooms = 0;""")
sub('combat/self_abilities.cc', """    struct Other {
        vec2 pos;
        bool first;
    };""", """    struct Other {
        vec2 pos;
        bool first;
        const ChampionBelief* belief;
    };
    bool fallers = false, later = false;
    float ours = -1;""")
sub('combat/self_abilities.cc', """                        if (!o.is_self && o.alive && o.visible && o.pos != dead && n_others < static_cast<int>(others.size()))
                            others[static_cast<std::size_t>(n_others++)] = {o.pos, world.slot(o, round) < mine};""",
"""                        if (!o.is_self && o.alive && o.visible && o.pos != dead && n_others < static_cast<int>(others.size())) {
                            if (o.side == team::ally) {
                                if (!o.acted) later = true;
                                else if (o.health + o.shield <= max_group_strength(world) * o.taken) fallers = true;
                            }
                            others[static_cast<std::size_t>(n_others++)] = {o.pos, world.slot(o, round) < mine, &o};
                        }""")
sub('combat/self_abilities.cc', """            auto& h = out.emplace_back(Hazard{m.pos, m.reach, true, m.strength * hit_factor});
            // Rules camps.attack: the nearest champion in its reach, a tie to who acts first.
            for (int k = 0; k < n_others; ++k) {
                const auto& o = others[static_cast<std::size_t>(k)];
                const int d = dist(m.pos, o.pos);
                if (d > m.reach || d > h.rival) continue;
                h.rival_first = d < h.rival ? o.first : h.rival_first || o.first;
                h.rival = d;
            }""", """            auto& h = out.emplace_back(Hazard{m.pos, m.reach, true, m.strength * hit_factor});
            bool doubts = false;
            if (shield_doubt_later && later) {
                if (ours < 0) ours = max_group_strength(world) * hit_factor >= my_health_and_shield(world) ? my_health_and_shield(world) : 1e9f;
                doubts = h.hit >= ours;
            }
            if (fallers || doubts) {
                const ChampionBelief* onto = nullptr;
                int near_d = m.reach + 1;
                for (int k = 0; k < n_others; ++k) {
                    const auto& o = others[static_cast<std::size_t>(k)];
                    const int d = dist(m.pos, o.pos);
                    if (d > m.reach) continue;
                    if (d < near_d) near_d = d, onto = o.belief->side == team::ally && o.belief->acted ? o.belief : nullptr;
                    else if (d == near_d) onto = nullptr;
                    if (d > h.rival || (doubts && o.belief->side == team::ally && !o.belief->acted)) continue;
                    h.rival_first = d < h.rival ? o.first : h.rival_first || o.first;
                    h.rival = d;
                }
                if (fallers && onto && n_dooms < static_cast<int>(dooms.size()))
                    dooms[static_cast<std::size_t>(n_dooms++)] = {static_cast<int>(out.size()) - 1, 0, onto, m.strength * onto->taken};
                continue;
            }
            // Rules camps.attack: the nearest champion in its reach, a tie to who acts first.
            for (int k = 0; k < n_others; ++k) {
                const auto& o = others[static_cast<std::size_t>(k)];
                const int d = dist(m.pos, o.pos);
                if (d > m.reach || d > h.rival) continue;
                h.rival_first = d < h.rival ? o.first : h.rival_first || o.first;
                h.rival = d;
            }""")
sub('combat/self_abilities.cc', """    return out;
}

// The damage a tile takes from the threats before our next turn""", """    // Only the hits that fell their ally and whose taking would spare it.
    for (int i = 0; i < n_dooms; ++i) {
        auto& x = dooms[static_cast<std::size_t>(i)];
        float sum = 0;
        for (int j = 0; j < n_dooms; ++j)
            if (dooms[static_cast<std::size_t>(j)].ally == x.ally) sum += dooms[static_cast<std::size_t>(j)].hit;
        const float health = x.ally->health + x.ally->shield;
        x.value = sum >= health && sum - x.hit < health ? ally_fall_value(world, *x.ally) : 0;
    }
    for (int i = 0; i < n_dooms; ++i) {
        const auto& x = dooms[static_cast<std::size_t>(i)];
        if (x.value <= 0) continue;
        Hazard minus = out[static_cast<std::size_t>(x.hazard)];
        minus.hit = -x.value;
        out.push_back(Hazard{x.ally->pos, 1 << 12, true, x.value});
        out.push_back(minus);
    }
    return out;
}

// The damage a tile takes from the threats before our next turn""")
print('ok', d, mode)
