#include "linefight.h"
#include <algorithm>
#include <array>
#include <cmath>
#include "bands.h"
#include "kit.h"
#include "safety.h"
#include "sim_core.h"
#include "world.h"

namespace aph::line {

namespace {
using simcore::FP;
using simcore::i64;
using AK = cambc::ability_kind;

i64 fx(double v) { return static_cast<i64>(std::llround(v * static_cast<double>(FP))); }

struct Live {
    float shield = 0;
    int shield_left = 0, stun = 0;
};

// Shields and stuns of a champion in sight (one raw read; nothing for one out of sight).
Live live_buffs(const ChampionBelief& b) {
    Live out;
    if (!b.visible && !b.is_self) return out;
    std::array<cambc::detail::buff_data, 8> raw{};
    std::uint32_t n = 0;
    if (cambc::detail::sdk_champion_buff_data(static_cast<std::uint32_t>(b.handle), raw.data(), static_cast<std::uint32_t>(raw.size()), &n) != 0)
        return out;
    for (std::uint32_t i = 0; i < n && i < raw.size(); ++i) {
        if (raw[i].type == static_cast<std::uint32_t>(cambc::detail::buff_kind::shield)) {
            out.shield += raw[i].data.shield.value;
            out.shield_left = std::max(out.shield_left, static_cast<int>(raw[i].data.shield.duration));
        } else if (raw[i].type == static_cast<std::uint32_t>(cambc::detail::buff_kind::stun)) {
            out.stun = std::max(out.stun, static_cast<int>(raw[i].data.stun.duration));
        }
    }
    return out;
}

void make_unit(simcore::BUnit& u, const ChampionBelief& b, int side, vec2 at, bool extra, int round) {
    const hyp::Kit& k = hyp::facts::kit(b.type);
    const Live bf = live_buffs(b);
    u.side = side;
    u.x = at.x, u.y = at.y;
    u.rng = std::max(1, k.attack_range);
    u.hp = fx(b.health);
    u.maxhp = fx(std::max(b.max_health, b.health));
    u.shield = fx(bf.shield);
    u.shield_left = bf.shield > 0 ? std::max(1, bf.shield_left) : 0;
    u.basic = fx(b.strength);
    u.retal = fx(b.retaliation());
    u.splash = k.passive == cambc::passive_type::splash_attack;
    u.reset_on_kill = k.passive == cambc::passive_type::reset_cooldowns_on_kill;
    u.stun_immune = k.passive == cambc::passive_type::stun_immunity;
    u.stun = std::clamp(bf.stun, 0, 7);
    u.focus = -1;
    u.kite = k.ranged() ? 2 : 0;
    u.extra = extra;
    const bool uncertain = b.cooldowns_uncertain();
    for (std::size_t s = 0; s < 2; ++s) {
        const hyp::Ability& a = k.ab[s];
        simcore::Abil& o = u.ab[s];
        o = {};
        if (!a.present) continue;
        o.kind = static_cast<unsigned char>(a.kind);
        o.cd = static_cast<signed char>(uncertain ? 0 : std::clamp(b.ready_round[s] - round, 0, 7));
        o.dur = static_cast<signed char>(std::clamp(a.duration, 0, 7));
        o.radius = static_cast<signed char>(std::clamp(static_cast<int>(a.radius), 0, 7));
        o.excl = a.excludes_walking;
        o.enhanced = a.enhanced;
        o.amt = fx(a.modifier * b.focus);
    }
}
} // namespace

float shield_of(const ChampionBelief& b) { return live_buffs(b).shield; }

const Outcome& at(const World& world, Safety& safety, vec2 p) {
    static int round = -1;
    static vec2 where{-1, -1};
    static Outcome cached;
    if (round != world.round || where != p) {
        round = world.round, where = p;
        cached = evaluate(world, safety, p, bands::saved(), 10);
    }
    return cached;
}

Outcome evaluate(const World& world, Safety& safety, vec2 at, bool double_turn, int horizon) {
    Outcome o;
    struct Cand {
        const ChampionBelief* b;
        vec2 pos;
        int d;
    };
    std::array<Cand, 8> allies{}, foes{};
    int na = 0, nf = 0;
    for (const auto& a : world.allies)
        if (a.alive && !a.is_self && a.visible && dist(a.pos, at) <= 5 && na < 8) allies[static_cast<std::size_t>(na++)] = {&a, a.pos, dist(a.pos, at)};
    for (const auto& t : safety.threats()) {
        if (!t.credible()) continue;
        const auto& e = world.enemies[static_cast<std::size_t>(t.enemy)];
        vec2 pos = t.pos;
        int d = 0;
        if (t.visible) {
            d = dist(pos, at);
            if (d > 7) continue;
        } else {
            d = t.distance(at);
            if (d > t.strike.reach + 1) continue;
            int bd = 1 << 20;   // its possible tile nearest us
            for (auto q : positions_within(e.possible, at, std::min(16, t.strike.reach + 1)))
                if (dist(q, at) < bd) bd = dist(q, at), pos = q;
            if (bd == 1 << 20) continue;
        }
        if (nf < 8) foes[static_cast<std::size_t>(nf++)] = {&e, pos, d};
    }
    if (nf == 0) return o;
    auto nearest = [](const Cand& x, const Cand& y) { return x.d < y.d || (x.d == y.d && x.b->index < y.b->index); };
    std::sort(allies.begin(), allies.begin() + na, nearest);
    std::sort(foes.begin(), foes.begin() + nf, nearest);

    static simcore::Battle B;
    B.n = 0, B.first_death = -1, B.rounds = 0;
    double us0 = 0, them0 = 0;
    const auto add = [&](const ChampionBelief& b, int side, vec2 pos, bool extra) {
        if (B.n >= simcore::BMAX) return -1;
        B.dead[B.n] = false;
        make_unit(B.u[B.n], b, side, pos, extra, world.round);
        return B.n++;
    };
    const int me_slot = add(world.me(), 0, at, double_turn);
    us0 += world.me().health;
    for (int i = 0; i < std::min(na, 4); ++i) {
        add(*allies[static_cast<std::size_t>(i)].b, 0, allies[static_cast<std::size_t>(i)].pos, false);
        us0 += allies[static_cast<std::size_t>(i)].b->health;
    }
    for (int i = 0; i < std::min(nf, 5); ++i)
        if (add(*foes[static_cast<std::size_t>(i)].b, 1, foes[static_cast<std::size_t>(i)].pos, false) >= 0)
            them0 += foes[static_cast<std::size_t>(i)].b->health, o.any_enemy = true;
    if (!o.any_enemy) return o;
    B.run_line(horizon);
    o.rounds = B.rounds;
    double us_left = 0, them_left = 0;
    bool us_alive = false, them_alive = false;
    for (int i = 0; i < B.n; ++i) {
        const double h = B.dead[i] ? 0.0 : static_cast<double>(B.u[i].hp + B.u[i].shield) / static_cast<double>(FP);
        if (B.u[i].side == 0) us_left += h, us_alive |= !B.dead[i];
        else them_left += h, them_alive |= !B.dead[i];
    }
    o.i_die = me_slot >= 0 && B.dead[me_slot];
    o.wiped = !us_alive;
    const double our = std::min(1.0, us_left / std::max(1.0, us0)), their = std::min(1.0, them_left / std::max(1.0, them0));
    o.margin = our - their;
    o.we_win = (!them_alive && us_alive) || (us_alive && o.margin > 0);
    return o;
}

} // namespace aph::line
