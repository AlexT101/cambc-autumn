"""mkshield.py DIR MODE [SCALE] [MARGIN]: camp-aggro shield on an oc-wdash-494 (or v104) copy. MODE: link | gen | genrev.
SCALE multiplies a non-partner ally's death price (1: ours times min(1, its worth / ours); 'full': all of our health).
MARGIN: an ally counts as felled when its health is within (1 + MARGIN) of the hits on it.
An ally done acting that a camp member's hit would fell (the member's nearest champion) prices every tile where
we would not take that hit instead as its death (Safety::camp_damage and the dash landings' danger); genrev also
stops counting on the shelter of an ally yet to act when the hit would fell us."""
import sys
d, mode = sys.argv[1], sys.argv[2]
scale = sys.argv[3] if len(sys.argv) > 3 else '1'
margin = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
assert mode in ('link', 'gen', 'genrev')
S = d + '/src/'
def sub(path, old, new):
    s = open(S + path).read(); assert s.count(old) == 1, (path, old[:70]); open(S + path, 'w').write(s.replace(old, new))
link, rev = mode == 'link', mode == 'genrev'

sub('model/safety.h', "float partner_bound(const World& world, const ChampionBelief& e);\n",
f"""float partner_bound(const World& world, const ChampionBelief& e);
// A camp hit we could take instead of `o`, an ally done acting that it would fell: its death in our health
// (all of it, and more, for our linked partner), or 0 where not counted.
inline constexpr bool shield_link_only = {'true' if link else 'false'};
// Not counting on the shelter of an ally yet to act from a camp hit that would fell us: it may leave.
inline constexpr bool shield_doubt_later = {'true' if rev else 'false'};
float ally_fall_value(const World& world, const ChampionBelief& o);
""")
sub('model/safety.h', "    int tie_only_count_ = 0;\n",
"""    int tie_only_count_ = 0;
    // A member whose hit falls on an ally done acting (the nearest champion to it) and fells it, where our
    // taking that hit instead would spare it: tiles beyond `radius` of it count `value` (ally_fall_value).
    struct Shield {
        vec2 pos;
        int radius;
        bool stunned;
        float value;
    };
    std::array<Shield, 4> shields_{};
    int shield_count_ = 0;
""")
sub('model/safety.cc', "float partner_bound(const World& world, const ChampionBelief& e) {",
"""float ally_fall_value(const World& world, const ChampionBelief& o) {
    const auto& me = world.me();
    const bool partner = o.facts().passive == Passive::linked_pair && me.facts().passive == Passive::linked_pair;
    if (shield_link_only && !partner) return 0;
    const float ours = my_health() + (me.shield_slot >= 0 ? shield_value(me.handle) : 0.0f);
    if (partner) return my_max_health() + ours + 1;
    // Its life against ours: each full health, life and bag (params value units).
    const float theirs = o.max_health + params::life_value + params::gem_value * static_cast<float>(o.gems);
    const float own = my_max_health() + params::life_value + params::gem_value * static_cast<float>(me.gems);
    return @RET@;
}

float partner_bound(const World& world, const ChampionBelief& e) {""".replace('@RET@', 'ours + 1' if scale == 'full' else f'{float(scale)}f * ours * std::min(1.0f, theirs / own)'))
sub('model/safety.cc', "    tie_only_count_ = 0;\n    camp_memo_",
    "    tie_only_count_ = 0;\n    shield_count_ = 0;\n    camp_memo_")
sub('model/safety.cc', """    const bool reread = refresh_;
    const auto& groups = world_.map().groups;
    world_.each_stirring([&](int g) {""",
"""    const bool reread = refresh_;
    const auto& groups = world_.map().groups;
    // Members whose hit falls on an ally done acting: shields_ once every hit on it is summed.
    struct Onto {
        vec2 pos;
        int radius;
        bool stunned;
        std::int8_t ally; // into others
        float hit;
    };
    std::array<Onto, 8> onto;
    int n_onto = 0;
    float ours = -1; // our health and shield, on first need
    world_.each_stirring([&](int g) {""")
sub('model/safety.cc', """            int reach = m.reach, tie = m.reach;
            for (int k = 0; k < k_near; ++k) {
                auto& o = others.at[near[k]];
                if (const int d = dist(o.pos, m.pos); d - 1 < reach) reach = std::min(reach, d - first(o)), tie = std::min(tie, d);
            }
            emit(m, reach, tie);""", """            int reach = m.reach, tie = m.reach;
            // The other that takes the hit: the strictly nearest within range, or -1 if tied.
            int target = -1, target_d = m.reach + 1;
            for (int k = 0; k < k_near; ++k) {
                auto& o = others.at[near[k]];
                const int d = dist(o.pos, m.pos);
                if (d < target_d) target = near[k], target_d = d;
                else if (d == target_d) target = -1;
                if (d - 1 >= reach) continue;
                if (shield_doubt_later && o.belief->side == team::ally && !o.belief->acted) {
                    if (ours < 0) ours = my_health() + (world_.me().shield_slot >= 0 ? shield_value(world_.me().handle) : 0.0f);
                    if (m.strength * camp_factor_ >= ours) continue;
                }
                reach = std::min(reach, d - first(o)), tie = std::min(tie, d);
            }
            if (target >= 0 && n_onto < static_cast<int>(onto.size()) && c.awake == Awake::awake)
                if (const auto& o = *others.at[target].belief; o.side == team::ally && o.acted)
                    onto[static_cast<std::size_t>(n_onto++)] = {m.pos, target_d - first(others.at[target]), camp_stunned(m.handle) && test(world_.visible, m.pos),
                                                                static_cast<std::int8_t>(target), m.strength * o.taken};
            emit(m, reach, tie);""")
sub('model/safety.cc', """    });
    member_count_ = count;
}""", """    });
    member_count_ = count;
    // An ally felled by the hits on it, which our taking one of them would spare.
    for (int i = 0; i < n_onto && shield_count_ < static_cast<int>(shields_.size()); ++i) {
        const auto& x = onto[static_cast<std::size_t>(i)];
        const auto& o = *others.at[x.ally].belief;
        float sum = 0;
        for (int j = 0; j < n_onto; ++j)
            if (onto[static_cast<std::size_t>(j)].ally == x.ally) sum += onto[static_cast<std::size_t>(j)].hit;
        if (const float health = (o.health + o.shield) / @M@; sum < health || sum - x.hit >= health) continue;
        if (const float value = ally_fall_value(world_, o); value > 0) shields_[static_cast<std::size_t>(shield_count_++)] = {x.pos, x.radius, x.stunned, value};
    }
}""")
sub('model/safety.cc', """    const auto& members = awake_members();
    if (members.empty()) return 0;
    next = next && worst;""", """    const auto& members = awake_members();
    if (members.empty() && shield_count_ == 0) return 0;
    next = next && worst;""")
sub('model/safety.cc', """        if (in_square(p, m.pos, m.reach) && !(next && m.stunned)) total += worst ? m.strength : m.strength * m.weight;
    memo = {p, total, true};""", """        if (in_square(p, m.pos, m.reach) && !(next && m.stunned)) total += worst ? m.strength : m.strength * m.weight;
    for (int i = 0; i < shield_count_; ++i)
        if (const auto& s = shields_[static_cast<std::size_t>(i)]; !in_square(p, s.pos, s.radius) && !s.stunned) total += s.value;
    memo = {p, total, true};""")

# The dash landings' hazards (combat/self_abilities.cc).
sub('combat/self_abilities.cc', """    float hit = 0;
    int rival = unreachable;
    bool rival_first = false;""", """    float hit = 0;
    int rival = unreachable;
    bool rival_first = false;
    // Where it does not pick us: the death of the ally done acting that it picks and fells (ally_fall_value).
    float doom = 0;
    const ChampionBelief* onto = nullptr; // the strictly nearest other, if an ally done acting
    float onto_hit = 0;""")
sub('combat/self_abilities.cc', """    struct Other {
        vec2 pos;
        bool first;
    };""", """    struct Other {
        vec2 pos;
        bool first;
        const ChampionBelief* belief;
    };
    float ours = -1;""")
sub('combat/self_abilities.cc', "others[static_cast<std::size_t>(n_others++)] = {o.pos, world.slot(o, round) < mine};",
    "others[static_cast<std::size_t>(n_others++)] = {o.pos, world.slot(o, round) < mine, &o};")
sub('combat/self_abilities.cc', """            for (int k = 0; k < n_others; ++k) {
                const auto& o = others[static_cast<std::size_t>(k)];
                const int d = dist(m.pos, o.pos);
                if (d > m.reach || d > h.rival) continue;
                h.rival_first = d < h.rival ? o.first : h.rival_first || o.first;
                h.rival = d;
            }""", """            int near_d = m.reach + 1;
            for (int k = 0; k < n_others; ++k) {
                const auto& o = others[static_cast<std::size_t>(k)];
                const int d = dist(m.pos, o.pos);
                if (d > m.reach) continue;
                if (d < near_d) near_d = d, h.onto = o.belief->side == team::ally && o.belief->acted ? o.belief : nullptr;
                else if (d == near_d) h.onto = nullptr;
                if (d > h.rival) continue;
                if (shield_doubt_later && o.belief->side == team::ally && !o.belief->acted) {
                    if (ours < 0) ours = my_health_and_shield(world);
                    if (h.hit >= ours) continue;
                }
                h.rival_first = d < h.rival ? o.first : h.rival_first || o.first;
                h.rival = d;
            }
            if (h.onto) h.onto_hit = m.strength * h.onto->taken;""")
sub('combat/self_abilities.cc', """    return out;
}

// The damage a tile takes from the threats before our next turn""", """    for (auto& h : out) {
        if (!h.onto) continue;
        float sum = 0;
        for (const auto& x : out)
            if (x.onto == h.onto) sum += x.onto_hit;
        if (const float health = (h.onto->health + h.onto->shield) / @M@; sum >= health && sum - h.onto_hit < health) h.doom = ally_fall_value(world, *h.onto);
    }
    return out;
}

// The damage a tile takes from the threats before our next turn""")
sub('combat/self_abilities.cc', """    for (const auto& t : threats) {
        const int d = dist(p, t.pos);
        if (d > t.reach) continue;
        if (!t.camp) total += t.blow[static_cast<std::size_t>(d)];
        else if (d < t.rival || (d == t.rival && !t.rival_first)) total += t.hit;
    }""", """    for (const auto& t : threats) {
        const int d = dist(p, t.pos);
        if (d > t.reach) {
            total += t.doom;
            continue;
        }
        if (!t.camp) total += t.blow[static_cast<std::size_t>(d)];
        else if (d < t.rival || (d == t.rival && !t.rival_first)) total += t.hit;
        else total += t.doom;
    }""")
for f in ('model/safety.cc', 'combat/self_abilities.cc'):
    t = open(S + f).read(); open(S + f, 'w').write(t.replace('@M@', f'{1 + margin}f'))
print('ok', d, mode, scale, margin)
