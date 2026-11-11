"""Compile the actual idle and camp simulators; compare randomized valid states bitwise."""
import subprocess
import sys
import tempfile
from pathlib import Path

base, cand = (Path(p) for p in sys.argv[1:3])


def model(bot, name):
    s = (bot / 'src/model/safety.cc').read_text()
    a = s[s.index('struct CastEffect {'):s.index('// A champion\'s casts, from')]
    b = s[s.index('// A fighter\'s most valuable ready cast'):s.index('constinit std::array<Side, 2> debug_sides')]
    return f'namespace {name} {{\n' + a + b + '\n}\n'


def camps(bot, name):
    s = (bot / 'src/economy/camps.cc').read_text()
    s = s[s.index('struct CampLeft {'):s.index('// Per group and range, built once:')]
    return f'namespace {name} {{\n' + s + '\n}\n'

header = r'''
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <random>
#include <utility>
#include <vector>
#define NO_UNROLL
#define debug_block(...)
constexpr int max_fighters = 6, never = std::numeric_limits<int>::max(), ability_cooldown = 8;
void throw_if_stale() {}
'''
main = r'''
std::mt19937 rng(20261111);
int pick(int n) { return static_cast<int>(rng() % n); }
float number(int n) { return static_cast<float>(1 + pick(n * 16)) / 16; }
template<class F, class K> void make(F& f, K& k) {
    f.strength = number(300);
    for (auto& c : k.cast) {
        c = {};
        const int kind = pick(5);
        c.damage = kind < 2 ? number(500) : 0;
        c.heal = kind == 2 || kind == 3 ? number(500) : 0;
        c.heals_self = kind == 2;
        c.heals_ally = kind == 3;
        c.stuns = pick(4) == 0;
        c.duration = 3;
        c.hits = c.damage > 0 ? 2 : 1;
        c.value = c.damage + c.heal + (c.stuns ? f.strength : 0);
    }
    k.preference = k.cast[1].value > k.cast[0].value ? std::array<int, 2>{1, 0} : std::array<int, 2>{0, 1};
    k.plain = !k.cast[0].heals_self && !k.cast[1].heals_self;
    f.kit = &k;
    for (int i = 0; i < 2; ++i) f.ready_at[i] = k.cast[i].value > 0 ? pick(9) : never;
    f.next_cast = std::min(f.ready_at[0], f.ready_at[1]);
    f.arrives_at = pick(7);
    f.stun_immune = pick(7) == 0;
    f.linked = false;
    f.max_health = 3000;
    f.health = number(3000);
    f.shield = k.plain || pick(2) ? 0 : number(300);
    f.shield_until = f.shield > 0 ? pick(4) : never;
    f.retaliation = pick(3) == 0 ? number(120) : 0;
    f.taken = pick(2) ? 1.0f : 0.8f;
    f.link = -1;
}
template<class D, class S, class K> D convert(const S& f, const K* kit) {
    D d;
    d.kit = kit; d.strength = f.strength; d.ready_at = f.ready_at; d.next_cast = f.next_cast;
    d.arrives_at = f.arrives_at; d.stun_immune = f.stun_immune; d.linked = f.linked;
    d.health = f.health; d.max_health = f.max_health; d.shield = f.shield;
    d.shield_until = f.shield_until; d.retaliation = f.retaliation; d.taken = f.taken; d.link = f.link;
    return d;
}
int main() {
    constexpr int cases = 1000000;
    for (int it = 0; it < cases; ++it) {
        old::Side us, them;
        newer::Side us2, them2;
        std::array<old::Kit, 7> k;
        std::array<newer::Kit, 7> k2;
        const int n = pick(7), horizon = 1 + pick(20);
        const float camp = pick(3) ? 0 : number(300);
        for (int i = 0; i <= n; ++i) {
            old::Fighter f;
            make(f, k[i]);
            if (i == 0) f.arrives_at = never;
            if (i > 0 && i <= 2 && n >= 2) f.linked = pick(2) == 0;
            k2[i].preference = k[i].preference; k2[i].plain = k[i].plain;
            for (int j = 0; j < 2; ++j) {
                auto& d = k2[i].cast[j]; const auto& s = k[i].cast[j];
                d.value=s.value; d.damage=s.damage; d.heal=s.heal; d.heals_self=s.heals_self;
                d.stuns=s.stuns; d.heals_ally=s.heals_ally; d.hits=s.hits; d.duration=s.duration;
            }
            auto f2 = convert<newer::Fighter>(f, &k2[i]);
            (i ? them : us).add(f); (i ? them2 : us2).add(f2);
        }
        us.camp = us2.camp = camp;
        const int expected = old::simulate(us, them, true, nullptr, horizon).second;
        auto cap = newer::their_cap(us2, them2);
        const bool survives = cap.short_of(us2, them2, horizon, 0, horizon, us2.fighters[0].health / us2.fighters[0].taken);
        const int got = survives ? 0 : newer::simulate_idle(us2, them2, horizon);
        if (expected != got) { std::printf("idle mismatch case %d n=%d horizon=%d expected=%d got=%d bound=%d\n", it, n, horizon, expected, got, survives); return 1; }
    }
    for (int it = 0; it < cases; ++it) {
        old::Side us, them;
        newer::Side us2, them2;
        std::array<old::Kit, 12> k;
        std::array<newer::Kit, 12> k2;
        const int nu = 1 + pick(6), ne = 1 + pick(6), horizon = 1 + pick(20);
        const bool first = pick(2);
        for (int i = 0; i < nu + ne; ++i) {
            old::Fighter f;
            make(f, k[i]);
            k2[i].preference = k[i].preference; k2[i].plain = k[i].plain;
            for (int j = 0; j < 2; ++j) {
                auto& d = k2[i].cast[j]; const auto& z = k[i].cast[j];
                d.value=z.value; d.damage=z.damage; d.heal=z.heal; d.heals_self=z.heals_self;
                d.stuns=z.stuns; d.heals_ally=z.heals_ally; d.hits=z.hits; d.duration=z.duration;
            }
            auto f2 = convert<newer::Fighter>(f, &k2[i]);
            (i < nu ? us : them).add(f); (i < nu ? us2 : them2).add(f2);
        }
        us.self = us2.self = 0;
        us.camp = us2.camp = pick(3) ? 0 : number(300);
        auto saved_u = us2, saved_e = them2;
        auto saved_old_u = us, saved_old_e = them;
        const auto expected = old::simulate(us, them, first, nullptr, horizon);
        const auto got = newer::simulate(us2, them2, first, nullptr, horizon);
        if (expected != got) {
            std::printf("fight mismatch case %d n=%d/%d horizon=%d expected=%d/%d got=%d/%d\n", it,nu,ne,horizon,expected.first,expected.second,got.first,got.second); return 1;
        }
        bool falls = false, old_falls = false;
        auto bounded = newer::simulate(saved_u, saved_e, first, &falls, horizon);
        auto old_bounded = old::simulate(saved_old_u, saved_old_e, first, &old_falls, horizon);
        if ((bounded.second > 0) != (old_bounded.second > 0) || falls != old_falls) {
            std::printf("bounded fight mismatch case %d\n",it); return 1;
        }
        if ((bounded.second > 0) != (expected.second > 0)) {
            // The regular trade also ends when our own fighter falls before any enemy.
            // A bound that says we survive must agree with the complete simulation.
            if (bounded.second == 0 && !falls && expected.second > 0) {
                std::printf("survival bound mismatch case %d\n",it); return 1;
            }
        }
    }
    int tails = 0;
    for (int it = 0; it < cases; ++it) {
        const int n = 1 + pick(it % 100 == 0 ? 352 : 32), attackers = pick(n + 1);
        const float strength = 1 + number(1000), reflect = number(300), survivable = number(1000);
        std::vector<old::CampLeft> a(n); std::vector<newer::CampLeft> b(n);
        for (int i = 0; i < n; ++i) {
            const float hp = number(i < attackers ? 3000 : 120), s = i < attackers ? number(500) : 0;
            const float home = pick(4) ? -1.0f : number(500);
            a[i] = {hp, s, i, s, home}; b[i] = {hp, s, i, s, home};
        }
        float ra, rb;
        const float da = old::min_camp_damage(a.data(), n, strength, &ra, reflect, survivable);
        const float db = newer::min_camp_damage(b.data(), n, strength, &rb, reflect, survivable);
        if (std::bit_cast<unsigned>(da) != std::bit_cast<unsigned>(db) || std::bit_cast<unsigned>(ra) != std::bit_cast<unsigned>(rb)) {
            std::printf("camp mismatch case %d n=%d attackers=%d damage=%g/%g rounds=%g/%g\n", it,n,attackers,da,db,ra,rb); return 1;
        }
        tails += attackers < n;
    }
    std::printf("%d idle fights, %d team fights and %d camp clears matched; %d mixed/harmless tails\n", cases,cases,cases,tails);
}
'''
with tempfile.TemporaryDirectory(prefix='chary-fuelC-check-') as tmp:
    tmp = Path(tmp)
    cc, binary = tmp/'check.cc', tmp/'check'
    cc.write_text(header + model(base, 'old') + model(cand, 'newer') + camps(base, 'old') + camps(cand, 'newer') + main)
    subprocess.run(['clang++', '-std=c++20', '-O2', '-ffp-contract=off', '-fsanitize=undefined', str(cc), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
