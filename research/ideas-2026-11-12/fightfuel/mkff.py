"""Budget-arm knobs on a self-capping copy of charybdis (tools/fuel/cap_variant.py --run-fuel 200000): python3 mkff.py SRC

Measurement only, debug builds under --fuel 200000. params::ff:
  uncap_who   these instances keep the whole 200k (1 the Prism, 2 the others, 3 everyone)
  free_gate   fuel gates that pass, the work they would have cut free (90k credited when the gate would have fired, and
              the fuel set back to that moment's after the work, so the rest of the turn sees what a cut would have left): 1 farm loop, 2 chase verdict (plan and slack), 4 step guard (entry, sim, look), 8 prey,
              16 escape plan (min_fuel, slack), 32 turn order
  free_who    whose gates (as uncap_who)
  overdraft   no turn runs out: after the first turn nobody is charged, and fuel() reads this much below the fuel left
              (0 once overdrawn), so every gate cuts as at the cap and a turn that would have run out plays on
  uncap_rounds  every instance keeps the whole 200k (400k on its first turn) through this round, and is capped after
  credit      fuel credited after the world update (credit_who; credit_when 0 always, 1 an enemy in sight, 2 none); the
              turn-end queue's floor rises by it
"""
import sys
from pathlib import Path

SRC = Path(sys.argv[1])
SUBS = [
    ('params.h', '''} // namespace open_plan
''', '''} // namespace open_plan

namespace ff {
inline constexpr int uncap_who = 0;
inline constexpr int free_gate = 0;
inline constexpr int free_who = 3;
inline constexpr int credit = 0;
inline constexpr int credit_who = 3;
inline constexpr int credit_when = 0;
inline constexpr int overdraft = 0;
inline constexpr int uncap_rounds = 0;
} // namespace ff
'''),
    ('util.h', '''#include <vector>
''', '''#include <vector>
#include "params.h"
'''),
    ('util.h', '''inline bool fuel_ok(std::uint64_t needed) { return fuel() >= needed; }
''', '''inline bool fuel_ok(std::uint64_t needed) { return fuel() >= needed; }

namespace ff {
inline bool is_prism() {
    static const bool p = cambc::self().champion_name() == cambc::champion_type::prism;
    return p;
}
inline bool who(int w) { return w == 3 || (w == 1 && is_prism()) || (w == 2 && !is_prism()); }
inline bool free_gate(int bit) { return (params::ff::free_gate & bit) && who(params::ff::free_who); }
inline std::int64_t& credited() {
    static std::int64_t c = 0;
    return c;
}
// From start() to its end the work is free: credited up front (a capped turn has little left when a gate fires), and
// at the end the fuel is set back to what start() found.
struct Free {
    static constexpr std::int64_t boost = 90000;
    bool on = false;
    std::int64_t at = 0;
    void start() {
        if (on) return;
        on = true, at = static_cast<std::int64_t>(cambc::detail::sdk_fuel_remaining());
        cambc::detail::sdk_fuel_adjust(boost);
    }
    Free() = default;
    ~Free() {
        if (on) cambc::detail::sdk_fuel_adjust(at - static_cast<std::int64_t>(cambc::detail::sdk_fuel_remaining()) + 4);
    }
    Free(const Free&) = delete;
    Free& operator=(const Free&) = delete;
};
} // namespace ff
'''),
    ('util.h', '''inline std::uint64_t fuel() { return static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining()); }''',
     '''namespace ff {
inline bool& overdraft_on() {
    static bool on = false;
    return on;
}
} // namespace ff
inline std::uint64_t fuel() {
    const auto real = static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining());
    if (!params::ff::overdraft || !ff::overdraft_on()) return real;
    return real > static_cast<std::uint64_t>(params::ff::overdraft) ? real - static_cast<std::uint64_t>(params::ff::overdraft) : 0;
}'''),
    # uncapped instances
    ('main.cc', '''inline void charge(std::int64_t turns) { cambc::detail::sdk_fuel_adjust(-(turns * (run - cap)) + 3); }''',
     '''inline bool exempt() {
    if (cambc::is_draft()) return false;
    if (aph::params::ff::uncap_rounds && static_cast<int>(cambc::round_number()) <= aph::params::ff::uncap_rounds) return true;
    return aph::ff::who(aph::params::ff::uncap_who);
}
inline void charge(std::int64_t turns) {
    if (aph::params::ff::overdraft && !cambc::is_draft()) {
        aph::ff::overdraft_on() = true;
        return;
    }
    if (exempt()) return;
    cambc::detail::sdk_fuel_adjust(-(turns * (run - cap)) + 3);
}'''),
    ('main.cc', '''[[gnu::noinline]] void first_turn() {
''', '''[[gnu::noinline]] void first_turn() {
    if (exempt()) return;
'''),
    ('main.cc', '''    cambc::detail::sdk_fuel_adjust(target - left() + 15);
}''', '''    cambc::detail::sdk_fuel_adjust(target - left() + 15);
    aph::ff::overdraft_on() = false; // the first turn keeps its own budget
}'''),
    ('main.cc', '''        if (aph::fuel() < end_turn_fuel) {''', '''        if (static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining()) < end_turn_fuel) {'''),
    # the credit
    ('main.cc', '''        if (!updated || !world->ready() || world->is_stale()) return;
''', '''        if (!updated || !world->ready() || world->is_stale()) return;
        aph::ff::credited() = 0;
        if (aph::params::ff::credit && aph::ff::who(aph::params::ff::credit_who)
            && (aph::params::ff::credit_when == 0 || (aph::params::ff::credit_when == 1) == world->enemy_seen())) {
            cambc::detail::sdk_fuel_adjust(aph::params::ff::credit);
            aph::ff::credited() = aph::params::ff::credit;
        }
'''),
    ('main.cc', '''        const auto floor = aph::end_reserve + (start > budget ? start - budget : 0);''',
     '''        const auto floor = aph::end_reserve + (start > budget ? start - budget : 0) + static_cast<std::uint64_t>(aph::ff::credited());'''),
    # 1: the farm loop
    ('economy/farm.cc', '''        seen = left;
        return left >= ample + decode_bound || left >= loop_reserve();
    };''', '''        seen = left;
        if (left >= ample + decode_bound || left >= loop_reserve()) return true;
        if (!ff::free_gate(1)) return false;
        if (!ff_loop) ff_loop.emplace(), ff_loop->start();
        return true;
    };'''),
    ('economy/farm.cc', '''    std::uint64_t seen = ~std::uint64_t{0};
    const auto room = [&]() __attribute__((always_inline)) {''', '''    std::uint64_t seen = ~std::uint64_t{0};
    std::optional<ff::Free> ff_loop;
    const auto room = [&]() __attribute__((always_inline)) {'''),
    ('economy/farm.cc', '''    read_g = -1;
    if (k < evaluated) note_shortcut("farm-partial-evaluation");''', '''    read_g = -1;
    ff_loop.reset();
    if (k < evaluated) note_shortcut("farm-partial-evaluation");'''),
    # 2: the chase verdict
    ('model/escape.cc', '''    if (!fuel_ok(need)) return nullptr;
    auto& p = plans[next];''', '''    ff::Free fr;
    if (!fuel_ok(need)) {
        if (!ff::free_gate(2)) return nullptr;
        fr.start();
    }
    auto& p = plans[next];'''),
    ('model/escape.cc', '''    if (active_ && !pass_[1].ready && fuel() >= params::escape::slack_fuel) run(slack_goal_, pass_[1]);''',
     '''    if (!active_ || pass_[1].ready) return;
    ff::Free fr;
    if (fuel() < params::escape::slack_fuel) {
        if (!ff::free_gate(chase_ ? 2 : 16)) return;
        fr.start();
    }
    run(slack_goal_, pass_[1]);'''),
    # 16: the escape plan
    ('model/escape.cc', '''    if (!self.alive || fuel() < params::escape::min_fuel || !ready_statics(world)) return;
    const std::uint64_t start_fuel = fuel();''', '''    ff::Free fr;
    if (self.alive && fuel() < params::escape::min_fuel) {
        if (!ff::free_gate(16)) return;
        fr.start();
    }
    if (!self.alive || !ready_statics(world)) return;
    const std::uint64_t start_fuel = fuel();'''),
    # 4: the step guard
    ('combat/guard.cc', '''    const auto floor = safety.fight_cost_estimate() + act_reserve;
    if (!fuel_ok(floor + costliest)) {
        note_shortcut("step-guard-entry");
        // Else one dear placing keeps the guard off for as long as enemies stay near.
        costliest -= costliest / 8;
        return nullptr;
    }''', '''    const auto floor = safety.fight_cost_estimate() + act_reserve;
    ff::Free fr;
    if (!fuel_ok(floor + costliest)) {
        if (ff::free_gate(4)) fr.start();
        else {
        note_shortcut("step-guard-entry");
        // Else one dear placing keeps the guard off for as long as enemies stay near.
        costliest -= costliest / 8;
        return nullptr;
        }
    }'''),
    ('combat/guard.cc', '''        if (!known && !fuel_ok(safety.fight_cost_estimate() + act_reserve)) {
            note_shortcut("step-guard-sim");
            return false;
        }''', '''        if (!known && !fuel_ok(safety.fight_cost_estimate() + act_reserve)) {
            if (ff::free_gate(4)) fr.start();
            else {
            note_shortcut("step-guard-sim");
            return false;
            }
        }'''),
    ('combat/guard.cc', '''        if (!fuel_ok(floor + 1000 * static_cast<std::uint64_t>(n))) {
            note_shortcut("step-guard-look");
            return nullptr;
        }''', '''        if (!fuel_ok(floor + 1000 * static_cast<std::uint64_t>(n))) {
            if (ff::free_gate(4)) fr.start();
            else {
            note_shortcut("step-guard-look");
            return nullptr;
            }
        }'''),
    # 8: prey
    ('combat/fight.cc', '''    for (int i = 0; i < n; ++i) {
        if (!fuel_ok(safety.fight_cost_estimate() + reserve)) {
            note_shortcut("prey-cut-short");
            break;
        }''', '''    ff::Free fr;
    for (int i = 0; i < n; ++i) {
        if (!fuel_ok(safety.fight_cost_estimate() + reserve)) {
            if (ff::free_gate(8)) fr.start();
            else {
            note_shortcut("prey-cut-short");
            break;
            }
        }'''),
    ('combat/fight.cc', '''            if (!fuel_ok(safety.fight_cost_estimate() + reserve)) {
                note_shortcut("prey-cut-short");
                break;
            }
            t = safety.chase_trade''', '''            if (!fuel_ok(safety.fight_cost_estimate() + reserve)) {
                if (ff::free_gate(8)) fr.start();
                else {
                note_shortcut("prey-cut-short");
                break;
                }
            }
            t = safety.chase_trade'''),
    # 32: the turn order
    ('model/turn_order.cc', '''    const bool short_of_fuel = world.me().alive && !fuel_ok(order_reserve) && !(fuel_ok(quiet_reserve) && quiet(world));
    if (short_of_fuel) {''', '''    bool short_of_fuel = world.me().alive && !fuel_ok(order_reserve) && !(fuel_ok(quiet_reserve) && quiet(world));
    ff::Free fr;
    if (short_of_fuel && ff::free_gate(32)) fr.start(), short_of_fuel = false;
    if (short_of_fuel) {'''),
]


def main():
    files = {}
    for name, old, new in SUBS:
        s = files.get(name) or (SRC / name).read_text()
        assert s.count(old) == 1, (name, old[:70], s.count(old))
        files[name] = s.replace(old, new)
    for name, s in files.items(): (SRC / name).write_text(s)
    print('knobs added')


if __name__ == '__main__':
    main()
