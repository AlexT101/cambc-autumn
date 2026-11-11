"""Build the dear-fall arms from oc-dfuel-506: usage mkarms.py NAME MODE FIGHTS LINE"""
import sys, subprocess, os
name, mode, fights, line = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
stake = sys.argv[5] if len(sys.argv) > 5 else 'false'
root = '/home/ubuntu/cambc-autumn'
subprocess.run([root + '/copybot', '-f', 'variants/oc-dfuel-506', 'variants/' + name], cwd=root, check=True)
src = root + '/bots/variants/' + name + '/src/'

def sub(path, old, new, count=1):
    t = open(src + path).read()
    assert t.count(old) == count, (path, old, t.count(old))
    open(src + path, 'w').write(t.replace(old, new))

sub('params.h', 'inline constexpr int brake_bag = 19;', '''inline constexpr int brake_bag = 19;
// A carrier whose fall hands over more than a fight wins (bank.cc dear_fall): 1 a brake_bag, 2 a bag worth more
// than its body and life, 3 a brake_bag it keeps (Prism). It takes no fight it falls in (dear_fall_fights), as
// Cassi and Issac do, and its recall line under threat is the hurt line (dear_fall_line).
inline constexpr int dear_fall_mode = %d;
inline constexpr bool dear_fall_fights = %s;
inline constexpr bool dear_fall_line = %s;
// The pack retreat ratio falls by the body's share of what our fall hands over (guard.cc pack_members_of).
inline constexpr bool stake_ratio = %s;''' % (mode, fights, line, stake))
sub('bot_parts.h', 'int bag_at_stake(const World& world);', 'int bag_at_stake(const World& world);\nbool dear_fall(const World& world);\nfloat threat_line(const World& world);')
sub('economy/bank.cc', '''    return static_cast<int>(my_gems()) + other;
}
''', '''    return static_cast<int>(my_gems()) + other;
}

bool dear_fall(const World& world) {
    const int bag = bag_at_stake(world);
    switch (params::dear_fall_mode) {
    case 1: return bag >= params::brake_bag;
    case 2: return params::gem_value * static_cast<float>(bag) >= my_max_health() + params::life_value;
    case 3: return bag >= params::brake_bag && world.me().facts().passive == Passive::gem_focus;
    default: return false;
    }
}

float threat_line(const World& world) {
    return params::dear_fall_line && dear_fall(world) ? std::max(params::recall_health_fraction, params::hurt_health_fraction) : params::recall_health_fraction;
}
''')
f = 'combat/fight.cc'
sub(f, '''                return params::recall_health_fraction;
        if (world.round''', '''                return threat_line(world);
        if (world.round''')
sub(f, 'return safety.may_reach_within(p, params::threat_radius) ? params::recall_health_fraction : params::safe_recall_health_fraction;',
    'return safety.may_reach_within(p, params::threat_radius) ? threat_line(world) : params::safe_recall_health_fraction;')
sub(f, 'if (health < params::recall_health_fraction * my_max_health() && health < recall_line(world, safety, hold.p) * my_max_health()',
    'if (health < threat_line(world) * my_max_health() && health < recall_line(world, safety, hold.p) * my_max_health()')
sub(f, 'const bool falls = partner(world) != nullptr || lethal();', 'const bool falls = partner(world) != nullptr || (params::dear_fall_fights && dear_fall(world)) || lethal();')
sub(f, '    const bool linked = partner(world) != nullptr;\n    // Best first', '    const bool pair = partner(world) != nullptr;\n    const bool linked = pair || (params::dear_fall_fights && dear_fall(world));\n    // Best first')
sub(f, '|| (!linked && comeback::accept_lost(world, t, target))', '|| (!pair && comeback::accept_lost(world, t, target))')
g = 'combat/guard.cc'
sub(g, '    const bool linked = partner(world) != nullptr;\n    // Unless the list', '    const bool linked = partner(world) != nullptr || (params::dear_fall_fights && dear_fall(world));\n    // Unless the list')
sub(g, 'if (my_health() < params::recall_health_fraction * my_max_health()) return true;', 'if (my_health() < threat_line(world) * my_max_health()) return true;')
sub(g, '    pz.ours = (home ? params::home_retreat_ratio : params::hurt_retreat_ratio) * our_health * our_damage;', '''    // A bag raises what our fall hands over: the ratio falls by the body's share of that stake.
    const float body = pz.max_health + params::life_value;
    const float stake = params::stake_ratio ? body / (body + params::gem_value * static_cast<float>(pz.bag)) : 1.0f;
    pz.ours = (home ? params::home_retreat_ratio : params::hurt_retreat_ratio) * stake * our_health * our_damage;''')
r = subprocess.run(['cambc', 'build', 'bots/variants/' + name, '--release'], cwd=root, capture_output=True, text=True)
print(name, 'build', r.returncode, (r.stdout + r.stderr)[-300:] if r.returncode else 'ok')
