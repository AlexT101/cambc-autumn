#pragma once
// Pure-arithmetic combat simulation core, carried over intact from Helios (its DESIGN §6; verified exact against its
// round-by-round reference: bots/_simbench, tools/simtest). No engine calls, no allocation: plain integer math on
// fixed arrays, cheap and testable natively. Hyperion uses Battle::run_line -- the user's line model.
//
// Verified engine facts encoded here (cambc 2.1.6, probes 2026-10-14 / 2026-10-16):
//  * every ability cooldown is 8 rounds; every cast range is 4; basic range is 1 (melee) / 3 (ranged)
//  * effect amount = modifier * focus; a stun (cc, Ryth's stun-aoe, Marcella's enhanced attack) makes
//    the target lose its ENTIRE next turn
//  * Varg's shield = 2.5*focus absorbing for 5 rounds; Willow's heal = 3*focus on an ally, never self
//  * an awake camp fighter hits the NEAREST champion within range 3 every round for its strength
//    (wolf 20, elk 60, monolith 200); clusters never attack; camps never move; camps never grow
//
// Hit points and damage are fixed-point integers (FP units per hp). That makes every analytic shortcut
// BIT-EXACT with the round-by-round reference: jumping k rounds subtracts exactly what k rounds would.
#include <algorithm>
#include <cstdint>
#include <cstdlib>

namespace simcore {

using i64 = long long;
inline constexpr i64 FP = 1000;
inline constexpr int CD = 8;           // every ability's cooldown
inline constexpr int CAST_RANGE = 4;   // every ability's cast range
inline constexpr int CAMP_AGGRO = 3;
inline constexpr i64 NEVER = (i64)1 << 60;

enum : unsigned char { K_NONE = 0, K_RESET = 1, K_DAMAGE = 2, K_AOE = 3, K_CC = 4, K_HEAL = 5, K_DASH = 6, K_SHIELD = 7 };


// A zero the optimiser cannot see through. Clearing whole 8-slot tables over a run-time count would otherwise
// become memset (memory.fill, one fuel per byte: 64 per table); 8 explicit stores are cheaper. (Small arrays
// are left to memset: there the fill is the cheaper one.)
inline i64 g_zero64 = 0;

// x * milli / 1000, rounded half-up; x >= 0. The single rounding rule shared by every path.
inline i64 scale_milli(i64 x, i64 milli) { return (x * milli + 500) / 1000; }
inline int cheb(int ax, int ay, int bx, int by) {
    const int dx = std::abs(ax - bx), dy = std::abs(ay - by);
    return dx > dy ? dx : dy;
}

struct Abil {
    unsigned char kind = K_NONE;
    signed char cd = 0;        // rounds until castable (0 = castable this round); always 0..7 at a round start
    signed char dur = 0;       // stun / shield duration in rounds
    signed char radius = 0;    // aoe radius (chebyshev)
    bool excl = false;         // casting it forbids moving in the same round
    bool enhanced = false;     // reset grants an enhanced attack, which stuns for 1 round
    i64 amt = 0;               // effect amount, FP (modifier * focus); before any camp multiplier
};

inline bool periodic_kind(unsigned char k) {   // casts every 8 rounds whenever a camp target exists
    return k == K_DAMAGE || k == K_AOE || k == K_CC || k == K_RESET || k == K_SHIELD;
}

// =====================================================================================================
// Camp clear — engaged abstraction of a farm fight.
//
// Champions stand at their attack positions around the group. Every champion focuses the alive camp that can attack
// (a fighter) with the lowest hp, and only when no fighter is left the lowest-hp cluster (tie: lowest index) -- the farm
// core's pick_camp rule (user, 2026-10-18: of what I can hit, what can attack first) -- so the focus is shared.
// A champion is EXPOSED unless it has safe tiles for its range bucket and the focus is a cluster.
// Every awake fighter hits the TANK = the nearest exposed champion: an exposed melee before an exposed
// ranged, lowest index first. Rules shared by camp_round (reference) and camp_clear_fast:
//  * a ready ability fires the first round it can: DAMAGE/CC hit the focus, AOE hits every camp within
//    its radius of the focus, CC / stun-AOE / enhanced RESET stun the fighters they hit for `dur`
//    rounds after the cast round, RESET adds a second basic attack, SHIELD shields self, HEAL heals the
//    tank (never self; waits until there is a tank below max hp), DASH is never needed (engaged).
//  * simultaneous resolution: all damage of a round accrues and applies at its end, shields first.
//  * a camp kill in a round refreshes every cooldown of a reset_on_kill champion (Vendetta).
// =====================================================================================================

inline constexpr int CMAXC = 6, CMAXM = 12;

struct CChamp {
    i64 hp = 0, maxhp = 0;
    i64 shield = 0;
    int shield_left = 0;       // rounds the active shield still covers (including the current one)
    i64 basic = 0;             // basic damage vs camps, FP (strength x camp multiplier)
    int camp_mult = 1000;      // milli-multiplier on ability damage vs camps
    int taken = 1000;          // milli-multiplier on incoming camp damage
    i64 retal = 0;             // damage returned to each fighter that hits me, FP (Ren)
    bool melee = true, safe = false, splash = false, reset_on_kill = false;
    Abil ab[2];
};

struct CCamp {
    i64 hp = 0, str = 0;       // FP
    bool fighter = false;
    int x = 0, y = 0;
    int stun = 0;              // upcoming rounds it will skip
};

struct CampState {
    int nc = 0, nm = 0;
    CChamp c[CMAXC];
    CCamp m[CMAXM];
    bool cdead[CMAXC] = {};
    bool mdead[CMAXM] = {};
    int r = 1;                 // next round to play
};

// Camp a is focused before camp b: a fighter before a cluster, then lower hp (ties: the scan keeps the lower index).
inline bool camp_first(const CCamp& a, const CCamp& b) {
    return a.fighter != b.fighter ? a.fighter : a.hp < b.hp;
}
inline int camp_focus(const CampState& S) {
    int best = -1;
    for (int j = 0; j < S.nm; ++j)
        if (!S.mdead[j] && (best < 0 || camp_first(S.m[j], S.m[best]))) best = j;
    return best;
}
inline bool camp_exposed(const CampState& S, int i, int T) {
    return !S.cdead[i] && (S.m[T].fighter || !S.c[i].safe);   // a safe tile only protects while on clusters
}
inline int camp_tank(const CampState& S, int T) {
    int ranged = -1;
    for (int i = 0; i < S.nc; ++i) {
        if (!camp_exposed(S, i, T)) continue;
        if (S.c[i].melee) return i;
        if (ranged < 0) ranged = i;
    }
    return ranged;
}
inline bool all_camps_dead(const CampState& S) {
    for (int j = 0; j < S.nm; ++j) if (!S.mdead[j]) return false;
    return true;
}
inline bool any_champ_dead(const CampState& S) {
    for (int i = 0; i < S.nc; ++i) if (S.cdead[i]) return true;
    return false;
}
inline bool all_champs_dead(const CampState& S) {
    for (int i = 0; i < S.nc; ++i) if (!S.cdead[i]) return false;
    return true;
}

// Plays exactly one round (S.r) by the rules above. The reference; also the fast path's fallback.
inline void camp_round(CampState& S) {
    const int T = camp_focus(S);
    const int K = camp_tank(S, T);
    // Only the used prefixes are cleared: zeroing whole arrays is a per-byte memset in wasm fuel.
    i64 incc[CMAXC], incm[CMAXM];
    int newstun[CMAXM];
    for (int i = 0; i < S.nc; ++i) incc[i] = 0;
    for (int j = 0; j < S.nm; ++j) incm[j] = 0, newstun[j] = 0;
    for (int i = 0; i < S.nc; ++i) {
        if (S.cdead[i]) continue;
        CChamp& c = S.c[i];
        int hits = 1;
        for (int s = 0; s < 2; ++s) {
            Abil& a = c.ab[s];
            if (a.kind == K_NONE || a.cd != 0) continue;
            bool cast = true;
            switch (a.kind) {
            case K_DAMAGE: incm[T] += scale_milli(a.amt, c.camp_mult); break;
            case K_AOE: {
                const i64 d = scale_milli(a.amt, c.camp_mult);
                for (int j = 0; j < S.nm; ++j)
                    if (!S.mdead[j] && cheb(S.m[j].x, S.m[j].y, S.m[T].x, S.m[T].y) <= a.radius) {
                        incm[j] += d;
                        if (a.dur > 0 && S.m[j].fighter) newstun[j] = std::max(newstun[j], (int)a.dur);
                    }
                break;
            }
            case K_CC:
                incm[T] += scale_milli(a.amt, c.camp_mult);
                if (S.m[T].fighter) newstun[T] = std::max(newstun[T], (int)a.dur);
                break;
            case K_RESET:
                hits = 2;
                if (a.enhanced && S.m[T].fighter) newstun[T] = std::max(newstun[T], 1);
                break;
            case K_SHIELD: c.shield = a.amt; c.shield_left = a.dur; break;
            case K_HEAL:
                if (K >= 0 && K != i && S.c[K].hp < S.c[K].maxhp) S.c[K].hp = std::min(S.c[K].maxhp, S.c[K].hp + a.amt);
                else cast = false;
                break;
            default: cast = false; break;   // dash: never needed while engaged
            }
            if (cast) a.cd = CD;
        }
        incm[T] += c.basic * hits;
        if (c.splash)
            for (int j = 0; j < S.nm; ++j)
                if (j != T && !S.mdead[j] && cheb(S.m[j].x, S.m[j].y, S.m[T].x, S.m[T].y) <= 1) incm[j] += c.basic * hits;
    }
    if (K >= 0)
        for (int j = 0; j < S.nm; ++j)
            if (!S.mdead[j] && S.m[j].fighter && S.m[j].stun == 0) {
                incc[K] += scale_milli(S.m[j].str, S.c[K].taken);
                incm[j] += S.c[K].retal;
            }
    bool killed = false;
    for (int i = 0; i < S.nc; ++i) {
        if (S.cdead[i]) continue;
        CChamp& c = S.c[i];
        i64 d = incc[i];
        if (c.shield_left > 0) { const i64 a = std::min(c.shield, d); c.shield -= a; d -= a; }
        c.hp -= d;
        if (c.hp <= 0) S.cdead[i] = true;
    }
    for (int j = 0; j < S.nm; ++j) {
        if (S.mdead[j]) continue;
        S.m[j].hp -= incm[j];
        if (S.m[j].hp <= 0) { S.mdead[j] = true; killed = true; }
    }
    for (int i = 0; i < S.nc; ++i) {
        CChamp& c = S.c[i];
        if (c.shield_left > 0 && --c.shield_left == 0) c.shield = 0;
        for (int s = 0; s < 2; ++s) if (c.ab[s].cd > 0) --c.ab[s].cd;
        if (killed && c.reset_on_kill && !S.cdead[i]) c.ab[0].cd = c.ab[1].cd = 0;
    }
    for (int j = 0; j < S.nm; ++j) S.m[j].stun = std::max(S.m[j].stun > 0 ? S.m[j].stun - 1 : 0, newstun[j]);
    ++S.r;
}

struct CampResult {
    bool cleared = false;
    int rounds = 0;            // round at which the last camp died (when cleared)
    bool any_dead = false;
    int phases = 0;            // work counter (fast path): analytic phases + explicit rounds
};

inline CampResult camp_finish(const CampState& S, int phases) {
    CampResult R;
    R.cleared = all_camps_dead(S);
    R.rounds = S.r - 1;
    for (int i = 0; i < S.nc; ++i) R.any_dead |= S.cdead[i];
    R.phases = phases;
    return R;
}

// Reference: plain round loop until cleared, wiped, or `horizon` rounds played. `stop_at_death`: also stop once
// any champion is dead (for callers that only ask "does anyone die?" -- the rest of the fight cannot change it).
inline CampResult camp_clear_ref(CampState& S, int horizon, bool stop_at_death = false) {
    int n = 0;
    while (S.r <= horizon && !all_camps_dead(S) && !all_champs_dead(S) && !(stop_at_death && any_champ_dead(S))) {
        camp_round(S);
        ++n;
    }
    return camp_finish(S, n);
}

// First t >= 0 at which sum_{k=0..t} inc(k) >= h, where inc(k) = a[k] for k < 8 and b[(k-8) % 8]
// afterwards (b is the steady periodic cycle). Increments may be negative. NEVER if it never happens.
inline i64 first_cross(const i64 a[8], const i64 b[8], i64 h) {
    i64 cum = 0;
    for (int j = 0; j < 8; ++j) { cum += a[j]; if (cum >= h) return j; }
    i64 B = 0, maxp = -NEVER;
    for (int j = 0; j < 8; ++j) { B += b[j]; if (B > maxp) maxp = B; }
    i64 k = 0;
    if (B <= 0) {
        if (cum + maxp < h) return NEVER;
    } else {
        const i64 need = h - cum - maxp;
        k = need <= 0 ? 0 : (need + B - 1) / B;
    }
    i64 base = cum + k * B;
    for (int j = 0; j < 8; ++j) { base += b[j]; if (base >= h) return 8 + 8 * k + j; }
    return NEVER;
}
// sum_{k=0..t} inc(k) with the same convention.
inline i64 cum_through(const i64 a[8], const i64 b[8], i64 t) {
    i64 cum = 0;
    const i64 lim = t < 8 ? t : 7;
    for (int j = 0; j <= lim; ++j) cum += a[j];
    if (t < 8) return cum;
    i64 B = 0;
    for (int j = 0; j < 8; ++j) B += b[j];
    const i64 rest = t - 8;
    cum += (rest / 8) * B;
    const int rem = static_cast<int>(rest % 8);
    for (int j = 0; j <= rem; ++j) cum += b[j];
    return cum;
}

// A periodic increment table (first cycle `a`, then `b` repeating) in prefix-sum form, so the queries
// below need no re-summing: cum_through is O(1), first_cross two scans of 8. Same arithmetic as the
// summing versions above (bit-exact).
struct Cyc {
    i64 pa[8], pb[8], B, maxp;
};
inline void cyc_build(const i64 a[8], const i64 b[8], Cyc& c) {
    if (a == b) {   // same table for the first and the steady cycle: one prefix pass
        i64 t = 0, mx = -NEVER;
        for (int j = 0; j < 8; ++j) { t += a[j]; c.pa[j] = c.pb[j] = t; if (t > mx) mx = t; }
        c.B = t;
        c.maxp = mx;
        return;
    }
    i64 s = 0;
    for (int j = 0; j < 8; ++j) { s += a[j]; c.pa[j] = s; }
    i64 t = 0, mx = -NEVER;
    for (int j = 0; j < 8; ++j) { t += b[j]; c.pb[j] = t; if (t > mx) mx = t; }
    c.B = t;
    c.maxp = mx;
}
inline i64 cyc_first_cross(const Cyc& c, i64 h) {
    for (int j = 0; j < 8; ++j) if (c.pa[j] >= h) return j;
    const i64 cum = c.pa[7];
    i64 k = 0;
    if (c.B <= 0) {
        if (cum + c.maxp < h) return NEVER;
    } else {
        const i64 need = h - cum - c.maxp;
        k = need <= 0 ? 0 : (need + c.B - 1) / c.B;
    }
    const i64 base = cum + k * c.B;
    for (int j = 0; j < 8; ++j) if (base + c.pb[j] >= h) return 8 + 8 * k + j;
    return NEVER;
}
inline i64 cyc_cum_through(const Cyc& c, i64 t) {
    if (t < 8) return c.pa[t];
    const i64 rest = t - 8;
    return c.pa[7] + (rest / 8) * c.B + c.pb[rest % 8];
}

// Fast exact camp clear. Between events (a camp or the tank dying, or the focus changing) every
// quantity is periodic with period 8 (all cooldowns are 8), so each event time is solved with
// first_cross() in O(1) cycles. Only the ACTIVE camps are tracked per phase: the focus, camps inside an
// AoE/splash radius of it, and fighters taking retaliation; every other camp takes no damage. Fighters
// that cannot be stunned this phase add one constant to the tank's damage. A phase where a healer
// could fire is played round-by-round instead (heal eligibility depends on the tank's hp, which breaks
// periodicity) — still exact, just slower.
template <int NC, int NM>
inline CampResult camp_clear_fast_n(CampState& S, int horizon, bool stop_at_death) {
    // NC / NM > 0: the champion / camp count known at compile time (the common small shapes: constant trip counts and
    // offsets); 0: read from S. Same arithmetic either way.
    const int nc = NC > 0 ? NC : S.nc;
    const int nm = NM > 0 ? NM : S.nm;
    auto alive_camps = [&] { for (int j = 0; j < nm; ++j) if (!S.mdead[j]) return true; return false; };
    auto any_cdead = [&] { for (int i = 0; i < nc; ++i) if (S.cdead[i]) return true; return false; };
    auto all_cdead = [&] { for (int i = 0; i < nc; ++i) if (!S.cdead[i]) return false; return true; };
    int work = 0;
    struct Sched { int f, o, d; };   // stun casts on fighter f at offset o (+8k), duration d
    // Per champion, fixed for the whole call (kinds, radii, amounts and multipliers never change in a clear):
    // healer, its active-camp radius (splash 1 / AoE radius), each ability's camp damage, its shield slot.
    bool heals[CMAXC];
    int rad[CMAXC], shield_slot[CMAXC];
    i64 camp_dmg[CMAXC][2];
    bool any_heal = false;   // (no healer / no AoE or splash at all: skip those per-phase scans)
    int any_rad = 0;
    for (int i = 0; i < nc; ++i) {
        const CChamp& c = S.c[i];
        heals[i] = c.ab[0].kind == K_HEAL || c.ab[1].kind == K_HEAL;
        any_heal |= heals[i];
        rad[i] = c.splash ? 1 : 0;
        shield_slot[i] = -1;
        for (int s = 0; s < 2; ++s) {
            const Abil& a = c.ab[s];
            if (a.kind == K_AOE) rad[i] = std::max(rad[i], static_cast<int>(a.radius));
            if (a.kind == K_SHIELD) shield_slot[i] = s;   // (the last shield slot, as the scans below found it)
            camp_dmg[i][s] = (a.kind == K_DAMAGE || a.kind == K_AOE || a.kind == K_CC) ? scale_milli(a.amt, c.camp_mult) : 0;
        }
        any_rad |= rad[i];
    }
    while (S.r <= horizon && alive_camps() && !all_cdead() && !(stop_at_death && any_cdead())) {
        ++work;
        int T = -1;   // == camp_focus(S)
        for (int j = 0; j < nm; ++j)
            if (!S.mdead[j] && (T < 0 || camp_first(S.m[j], S.m[T]))) T = j;
        int K = -1;   // == camp_tank(S, T)
        {
            int ranged = -1;
            for (int i = 0; i < nc; ++i) {
                if (!camp_exposed(S, i, T)) continue;
                if (S.c[i].melee) { K = i; break; }
                if (ranged < 0) ranged = i;
            }
            if (K < 0) K = ranged;
        }
        if (K >= 0 && any_heal) {
            bool healer = false;
            for (int i = 0; i < nc; ++i)
                if (!S.cdead[i] && i != K && heals[i]) healer = true;
            if (healer) { camp_round(S); continue; }
        }
        const CCamp& mT = S.m[T];
        const bool retal = K >= 0 && S.c[K].retal > 0;

        // ---- active camps ----
        int R = 0;
        if (any_rad)
            for (int i = 0; i < nc; ++i)
                if (!S.cdead[i]) R = std::max(R, rad[i]);
        int act[CMAXM], na = 0;
        act[na++] = T;
        if (R > 0 || retal)
            for (int m = 0; m < nm; ++m)
                if (m != T && !S.mdead[m] && ((R > 0 && cheb(S.m[m].x, S.m[m].y, mT.x, mT.y) <= R) || (retal && S.m[m].fighter)))
                    act[na++] = m;
        i64 dm[CMAXM][8];   // champion-caused damage per active camp (identical every cycle)
        {   // every round's basic hits first (row 0: every living champion; splash rows: splashers within 1)
            i64 base0 = 0;
            for (int i = 0; i < nc; ++i)
                if (!S.cdead[i]) base0 += S.c[i].basic;
            for (int j = 0; j < 8; ++j) dm[0][j] = base0;
            for (int q = 1; q < na; ++q) {
                i64 bq = 0;
                const CCamp& m = S.m[act[q]];
                if (cheb(m.x, m.y, mT.x, mT.y) <= 1)
                    for (int i = 0; i < nc; ++i)
                        if (!S.cdead[i] && S.c[i].splash) bq += S.c[i].basic;
                for (int j = 0; j < 8; ++j) dm[q][j] = bq;
            }
        }
        Sched sched[4 * CMAXC];
        int nsched = 0;

        // ---- champion contributions ----
        for (int i = 0; i < nc; ++i) {
            if (S.cdead[i]) continue;
            const CChamp& c = S.c[i];
            int extra_at = -1;
            for (int s = 0; s < 2; ++s) {
                const Abil& a = c.ab[s];
                if (!periodic_kind(a.kind)) continue;
                const int o = a.cd;
                switch (a.kind) {
                case K_DAMAGE: dm[0][o] += camp_dmg[i][s]; break;
                case K_AOE: {
                    const i64 d = camp_dmg[i][s];
                    for (int q = 0; q < na; ++q) {
                        const CCamp& m = S.m[act[q]];
                        if (cheb(m.x, m.y, mT.x, mT.y) > a.radius) continue;
                        dm[q][o] += d;
                        if (a.dur > 0 && m.fighter) sched[nsched++] = Sched{act[q], o, a.dur};
                    }
                    break;
                }
                case K_CC:
                    dm[0][o] += camp_dmg[i][s];
                    if (mT.fighter) sched[nsched++] = Sched{T, o, a.dur};
                    break;
                case K_RESET:
                    extra_at = o;
                    if (a.enhanced && mT.fighter) sched[nsched++] = Sched{T, o, 1};
                    break;
                default: break;   // shield: handled with the tank
                }
            }
            if (extra_at >= 0) {   // (the every-round basic hits are already in the rows)
                dm[0][extra_at] += c.basic;
                if (c.splash)
                    for (int q = 1; q < na; ++q) {
                        const CCamp& m = S.m[act[q]];
                        if (cheb(m.x, m.y, mT.x, mT.y) <= 1) dm[q][extra_at] += c.basic;
                    }
            }
        }

        // ---- simple phase: only the focus takes damage (no AoE / splash neighbour, no retaliation) and the tank has
        // no shield. The focus then cannot be overtaken (its death is the next camp event) and the tank's damage is
        // every awake fighter's hit, minus the rounds a fighter skips (its running stun, the focus's scheduled stuns):
        // two 8-round tables at most, no shield state machine, no per-camp tables. Same arithmetic as the general
        // path below (tools/simtest, bots/_simbench: bit-exact).
        if (na == 1 && !retal && (K < 0 || (shield_slot[K] < 0 && S.c[K].shield_left <= 0))) {
            Cyc c0;
            cyc_build(dm[0], dm[0], c0);
            i64 t = cyc_first_cross(c0, mT.hp);
            i64 C = 0;
            i64 dk1[8], dks[8];
            bool masked = false;
            if (K >= 0) {
                const CChamp& k = S.c[K];
                for (int f = 0; f < nm; ++f) {
                    if (S.mdead[f] || !S.m[f].fighter) continue;
                    const i64 hit = scale_milli(S.m[f].str, k.taken);
                    C += hit;
                    const int st = S.m[f].stun;
                    unsigned m1 = st >= 8 ? 0xFFu : ((1u << st) - 1u), ms = 0;
                    for (int q = 0; q < nsched; ++q) {
                        if (sched[q].f != f) continue;
                        for (int w = 1; w <= sched[q].d; ++w) {
                            const int jj = sched[q].o + w;
                            if (jj < 8) m1 |= 1u << jj;
                            ms |= 1u << (jj & 7);
                        }
                    }
                    if ((m1 | ms) == 0) continue;
                    if (!masked) {
                        masked = true;
                        for (int jj = 0; jj < 8; ++jj) dk1[jj] = dks[jj] = 0;
                    }
                    for (unsigned w = m1; w; w &= w - 1) dk1[__builtin_ctz(w)] -= hit;
                    for (unsigned w = ms; w; w &= w - 1) dks[__builtin_ctz(w)] -= hit;
                }
            }
            Cyc ck;
            if (masked) {
                for (int jj = 0; jj < 8; ++jj) dk1[jj] += C, dks[jj] += C;
                cyc_build(dk1, dks, ck);
                const i64 tk = cyc_first_cross(ck, S.c[K].hp);
                if (tk < t) t = tk;
            } else if (K >= 0 && C > 0) {
                const i64 tk = (S.c[K].hp + C - 1) / C - 1;   // first t with C * (t + 1) >= hp
                if (tk < t) t = tk;
            }
            const i64 room = static_cast<i64>(horizon) - S.r;
            if (t > room) t = room;
            bool killed = false;
            {
                CCamp& m = S.m[T];
                m.hp -= cyc_cum_through(c0, t);
                if (m.hp <= 0) { S.mdead[T] = true; killed = true; }
            }
            if (K >= 0) {
                CChamp& k = S.c[K];
                k.hp -= masked ? cyc_cum_through(ck, t) : C * (t + 1);
                if (k.hp <= 0) S.cdead[K] = true;
            }
            for (int i = 0; i < nc; ++i) {   // (as below with no absorbing shield: shields only tick / refresh)
                CChamp& c = S.c[i];
                int so = -1, sdur = 0;
                i64 samt = 0;
                if (const int ss = shield_slot[i]; ss >= 0) so = c.ab[ss].cd, samt = c.ab[ss].amt, sdur = c.ab[ss].dur;
                if (!S.cdead[i] && so >= 0 && t >= so) {
                    const i64 since = (t - so) % 8;
                    const i64 left = sdur - 1 - since;
                    c.shield_left = left > 0 ? static_cast<int>(left) : 0;
                    c.shield = c.shield_left > 0 ? samt : 0;
                } else if (c.shield_left > 0) {
                    const i64 left = static_cast<i64>(c.shield_left) - (t + 1);
                    c.shield_left = left > 0 ? static_cast<int>(left) : 0;
                    if (c.shield_left == 0) c.shield = 0;
                }
                for (int s = 0; s < 2; ++s) {
                    Abil& a = c.ab[s];
                    if (a.kind == K_NONE) continue;
                    if (!S.cdead[i] && periodic_kind(a.kind)) a.cd = static_cast<signed char>((a.cd - (t + 1)) & 7);
                    else a.cd = static_cast<signed char>(std::max<i64>(0, a.cd - (t + 1)));
                }
                if (killed && c.reset_on_kill && !S.cdead[i]) c.ab[0].cd = c.ab[1].cd = 0;
            }
            // stuns left after round t (as below)
            for (int f = 0; f < nm; ++f) {
                if (S.mdead[f]) { S.m[f].stun = 0; continue; }
                if (S.m[f].stun > 0) S.m[f].stun = static_cast<int>(std::max<i64>(0, S.m[f].stun - (t + 1)));
            }
            for (int q = 0; q < nsched; ++q) {
                const Sched& sc = sched[q];
                if (t < sc.o || S.mdead[sc.f]) continue;
                const i64 last = sc.o + 8 * ((t - sc.o) / 8);
                S.m[sc.f].stun = static_cast<int>(std::max<i64>(S.m[sc.f].stun, last + sc.d - t));
            }
            S.r += static_cast<int>(t) + 1;
            continue;
        }

        // ---- tank damage (first cycle / steady) and retaliation on the fighters that hit it ----
        i64 dk1[8], dks[8];
        i64 rf1[CMAXM][8], rfs[CMAXM][8];   // retaliation taken, per active slot (only when retal)
        for (int j = 0; j < 8; ++j) dk1[j] = dks[j] = 0;
        if (retal)
            for (int a = 0; a < na; ++a)
                for (int j = 0; j < 8; ++j) rf1[a][j] = rfs[a][j] = g_zero64;
        if (K >= 0) {
            const CChamp& k = S.c[K];
            i64 constant = 0;
            for (int f = 0; f < nm; ++f) {
                if (S.mdead[f] || !S.m[f].fighter) continue;
                const i64 hit = scale_milli(S.m[f].str, k.taken);
                // Rounds of the first / steady cycle this fighter skips, as 8-bit masks: its running stun
                // (rounds j < stun), then each scheduled cast at offset o stunning rounds o+1 .. o+d.
                const int st = S.m[f].stun;
                unsigned m1 = st >= 8 ? 0xFFu : ((1u << st) - 1u), ms = 0;
                for (int q = 0; q < nsched; ++q) {
                    if (sched[q].f != f) continue;
                    for (int w = 1; w <= sched[q].d; ++w) {
                        const int j = sched[q].o + w;
                        if (j < 8) m1 |= 1u << j;
                        ms |= 1u << (j & 7);
                    }
                }
                int slot = -1;
                if (retal)
                    for (int a = 0; a < na; ++a)
                        if (act[a] == f) slot = a;
                if ((m1 | ms) == 0) {
                    constant += hit;
                    if (slot >= 0)
                        for (int j = 0; j < 8; ++j) rf1[slot][j] += k.retal, rfs[slot][j] += k.retal;
                    continue;
                }
                // == adding `hit` on every unmasked round: all rounds via `constant`, minus the masked ones
                constant += hit;
                for (unsigned w = m1; w; w &= w - 1) dk1[__builtin_ctz(w)] -= hit;
                for (unsigned w = ms; w; w &= w - 1) dks[__builtin_ctz(w)] -= hit;
                if (slot >= 0)
                    for (int j = 0; j < 8; ++j) {
                        if (!((m1 >> j) & 1u)) rf1[slot][j] += k.retal;
                        if (!((ms >> j) & 1u)) rfs[slot][j] += k.retal;
                    }
            }
            for (int j = 0; j < 8; ++j) dk1[j] += constant, dks[j] += constant;
        }

        // ---- the tank's shield (first + one steady cycle through the state machine) ----
        i64 eff1[8], effs[8], sh_after[16];
        int sl_after[16];
        bool shield_sm = false;
        if (K >= 0) {
            const CChamp& k = S.c[K];
            int so = -1, sdur = 0;
            i64 samt = 0;
            if (const int ss = shield_slot[K]; ss >= 0) so = k.ab[ss].cd, samt = k.ab[ss].amt, sdur = k.ab[ss].dur;
            shield_sm = so >= 0 || k.shield_left > 0;
            if (shield_sm) {
                i64 sh = k.shield;
                int sl = k.shield_left;
                for (int j = 0; j < 16; ++j) {
                    if (so >= 0 && (j & 7) == so) sh = samt, sl = sdur;
                    i64 raw = j < 8 ? dk1[j] : dks[j - 8];
                    if (sl > 0) { const i64 a = std::min(sh, raw); sh -= a; raw -= a; }
                    if (j < 8) eff1[j] = raw; else effs[j - 8] = raw;
                    if (sl > 0 && --sl == 0) sh = 0;
                    sh_after[j] = sh;
                    sl_after[j] = sl;
                }
            }
        }
        const i64* k1 = shield_sm ? eff1 : dk1;
        const i64* ks = shield_sm ? effs : dks;

        // per-active-camp first/steady tables (retaliation makes them differ; otherwise shared)
        i64 c1[CMAXM][8], cs[CMAXM][8];
        const i64* t1[CMAXM];
        const i64* ts[CMAXM];
        for (int a = 0; a < na; ++a) {
            if (!retal) { t1[a] = ts[a] = dm[a]; continue; }
            for (int j = 0; j < 8; ++j) c1[a][j] = dm[a][j] + rf1[a][j], cs[a][j] = dm[a][j] + rfs[a][j];
            t1[a] = c1[a];
            ts[a] = cs[a];
        }

        // ---- next event ----
        Cyc cy[CMAXM], cyk;
        for (int a = 0; a < na; ++a) cyc_build(t1[a], ts[a], cy[a]);
        if (K >= 0) cyc_build(k1, ks, cyk);
        i64 t = NEVER;
        for (int a = 0; a < na; ++a) t = std::min(t, cyc_first_cross(cy[a], S.m[act[a]].hp));
        if (K >= 0) t = std::min(t, cyc_first_cross(cyk, S.c[K].hp));
        for (int a = 1; a < na; ++a) {   // an active camp dropping below the focus re-targets everyone
            if (mT.fighter && !S.m[act[a]].fighter) continue;   // (a cluster never takes a fighter's place)
            i64 d1[8], d2[8];
            bool any = false;
            for (int j = 0; j < 8; ++j) {
                d1[j] = t1[a][j] - t1[0][j];
                d2[j] = ts[a][j] - ts[0][j];
                any |= d1[j] > 0 || d2[j] > 0;
            }
            if (!any) continue;   // the focus always takes at least as much: it can't be overtaken
            const int n = act[a];
            const i64 gap = S.m[n].hp - mT.hp;
            Cyc cd;
            cyc_build(d1, d2, cd);
            t = std::min(t, cyc_first_cross(cd, n > T ? gap + 1 : gap));
        }
        const i64 room = static_cast<i64>(horizon) - S.r;
        if (t > room) t = room;

        // ---- jump to the end of round S.r + t ----
        bool killed = false;
        for (int a = 0; a < na; ++a) {
            CCamp& m = S.m[act[a]];
            m.hp -= cyc_cum_through(cy[a], t);
            if (m.hp <= 0) { S.mdead[act[a]] = true; killed = true; }
        }
        if (K >= 0) {
            CChamp& k = S.c[K];
            k.hp -= cyc_cum_through(cyk, t);
            if (k.hp <= 0) S.cdead[K] = true;
            if (shield_sm) {
                const int at = t < 16 ? static_cast<int>(t) : 8 + static_cast<int>((t - 8) % 8);
                k.shield = sh_after[at];
                k.shield_left = sl_after[at];
            }
        }
        for (int i = 0; i < nc; ++i) {
            CChamp& c = S.c[i];
            if (i != K || !shield_sm) {   // no absorption: the shield only ticks and refreshes
                int so = -1, sdur = 0;
                i64 samt = 0;
                if (const int ss = shield_slot[i]; ss >= 0) so = c.ab[ss].cd, samt = c.ab[ss].amt, sdur = c.ab[ss].dur;
                if (!S.cdead[i] && so >= 0 && t >= so) {
                    const i64 since = (t - so) % 8;
                    const i64 left = sdur - 1 - since;
                    c.shield_left = left > 0 ? static_cast<int>(left) : 0;
                    c.shield = c.shield_left > 0 ? samt : 0;
                } else if (c.shield_left > 0) {
                    const i64 left = static_cast<i64>(c.shield_left) - (t + 1);
                    c.shield_left = left > 0 ? static_cast<int>(left) : 0;
                    if (c.shield_left == 0) c.shield = 0;
                }
            }
            for (int s = 0; s < 2; ++s) {
                Abil& a = c.ab[s];
                if (a.kind == K_NONE) continue;
                if (!S.cdead[i] && periodic_kind(a.kind)) a.cd = static_cast<signed char>((a.cd - (t + 1)) & 7);   // == mod 8
                else a.cd = static_cast<signed char>(std::max<i64>(0, a.cd - (t + 1)));
            }
            if (killed && c.reset_on_kill && !S.cdead[i]) c.ab[0].cd = c.ab[1].cd = 0;
        }
        // Stun left after round t: a pre-phase stun still running, or the last cast at or before t of
        // each schedule on this fighter (covering cast+1 .. cast+dur). Casts after t never happen.
        for (int f = 0; f < nm; ++f) {
            if (S.mdead[f]) { S.m[f].stun = 0; continue; }
            if (S.m[f].stun > 0) S.m[f].stun = static_cast<int>(std::max<i64>(0, S.m[f].stun - (t + 1)));
        }
        for (int q = 0; q < nsched; ++q) {
            const Sched& sc = sched[q];
            if (t < sc.o || S.mdead[sc.f]) continue;
            const i64 last = sc.o + 8 * ((t - sc.o) / 8);
            S.m[sc.f].stun = static_cast<int>(std::max<i64>(S.m[sc.f].stun, last + sc.d - t));
        }
        S.r += static_cast<int>(t) + 1;
    }
    return camp_finish(S, work);
}

inline CampResult camp_clear_fast(CampState& S, int horizon, bool stop_at_death = false) {
    // The common shapes (1-4 champions x 1-3 camps; 1-4 champions x more camps) with compile-time counts.
    const int a = S.nc <= 4 ? S.nc : 0, b = S.nm <= 3 ? S.nm : 0;
    switch (a * 4 + b) {
    case 4: return camp_clear_fast_n<1, 0>(S, horizon, stop_at_death);
    case 5: return camp_clear_fast_n<1, 1>(S, horizon, stop_at_death);
    case 6: return camp_clear_fast_n<1, 2>(S, horizon, stop_at_death);
    case 7: return camp_clear_fast_n<1, 3>(S, horizon, stop_at_death);
    case 8: return camp_clear_fast_n<2, 0>(S, horizon, stop_at_death);
    case 9: return camp_clear_fast_n<2, 1>(S, horizon, stop_at_death);
    case 10: return camp_clear_fast_n<2, 2>(S, horizon, stop_at_death);
    case 11: return camp_clear_fast_n<2, 3>(S, horizon, stop_at_death);
    case 12: return camp_clear_fast_n<3, 0>(S, horizon, stop_at_death);
    case 13: return camp_clear_fast_n<3, 1>(S, horizon, stop_at_death);
    case 14: return camp_clear_fast_n<3, 2>(S, horizon, stop_at_death);
    case 15: return camp_clear_fast_n<3, 3>(S, horizon, stop_at_death);
    case 16: return camp_clear_fast_n<4, 0>(S, horizon, stop_at_death);
    case 17: return camp_clear_fast_n<4, 1>(S, horizon, stop_at_death);
    case 18: return camp_clear_fast_n<4, 2>(S, horizon, stop_at_death);
    case 19: return camp_clear_fast_n<4, 3>(S, horizon, stop_at_death);
    default: return camp_clear_fast_n<0, 0>(S, horizon, stop_at_death);
    }
}

// =====================================================================================================
// Champion fight — positional, round-by-round (fights are short; horizon ~10).
// Each round, every unit (in index order, not stunned) picks a focus (sticky: kept while alive; the
// lowest hp+shield enemy within attack range when it has to choose, else the nearest enemy), moves
// (melee closes, dashing when that brings the focus into range; ranged closes to range 3 and kites an
// adjacent melee while its kite budget lasts; a ready movement-exclusive cast pre-empts moving), casts
// every ready ability that has a target, then basic-attacks the focus if in range. Damage, heals and
// shields resolve as in camp_round; a stunned unit loses its whole next turn; Marcella-style
// stun_immune ignores stuns; Ren-style retaliation answers every hit; Varg-style splash hits enemies
// adjacent to the target; Vendetta-style reset_on_kill refreshes cooldowns when its target dies.
// =====================================================================================================

inline constexpr int BMAX = 12;
inline bool they_first = false;   // line model: enemies act before our units each round (experiment; default off)


struct BUnit {
    int side = 0;
    int x = 0, y = 0, rng = 1;
    i64 hp = 0, maxhp = 0, shield = 0;
    int shield_left = 0;
    i64 basic = 0;           // FP
    i64 retal = 0;           // FP per hit taken
    bool splash = false, reset_on_kill = false, stun_immune = false;
    int stun = 0;
    int focus = -1;
    int kite = 0;            // rounds this unit may still back away from an adjacent melee
    bool extra = false;      // a saved double turn (user's priority flip): one action before anyone else's
    Abil ab[2];
};

struct Battle {
    int n = 0;
    BUnit u[BMAX];
    bool dead[BMAX] = {};
    int first_death = -1;    // index of the first unit to die
    int rounds = 0;

    // Wasm fuel is ~1 per operator, so the loop works on bitmasks of living units, per-unit ability masks computed
    // once per call, and set bits instead of zeroed scratch arrays (bots/_simbench: identical final state, field by
    // field, to the straightforward version).
    // lowest hp+shield living enemy of side `sd` within `reach` of (px, py) (ties: lowest index); -1 if none
    int lowest_from(int sd, int px, int py, int reach, bool need_stunnable, unsigned cand) const {
        (void)sd;
        const unsigned live = cand;
        int best = -1;
        i64 bv = 0;
        for (unsigned m = live; m; m &= m - 1) {
            const int j = __builtin_ctz(m);
            const BUnit& v = u[j];
            if (cheb(px, py, v.x, v.y) > reach) continue;   // (cand: enemies of sd only)
            if (need_stunnable && v.stun_immune) continue;
            const i64 val = v.hp + v.shield;
            if (best < 0 || val < bv) best = j, bv = val;
        }
        return best;
    }
    void run(int horizon) {
        unsigned live = 0;                       // bit i: unit i alive
        int alive[2] = {0, 0};
        bool any_extra = false;
        unsigned excl_off[BMAX];                 // slots that are move-exclusive "offensive" casts (not none/heal/shield)
        unsigned dash_slots[BMAX];               // slots holding a dash
        unsigned castable[BMAX];                 // slots the cast step can use (not none / dash: a dash never casts there)
        unsigned melee[2] = {0, 0};              // melee units per side (what a kiting ranged unit backs off from)
        unsigned shielded = 0;                   // units with shield_left > 0 (their shield ticks)
        unsigned side_of[2] = {0, 0};            // units per side
        // Timers in absolute rounds instead of per-round countdowns: ability s of unit i is ready from round
        // ready_at[i][s]; unit i is stunned while r < stun_end[i]. A unit's clock starts with the first round that
        // ticks its timers: round 0 for the unit taking a saved double turn, round 1 for everyone else (round 0
        // only ticks the double-turn unit's timers). Same behaviour as the countdowns, without touching every unit
        // every round (bots/_simbench: identical state).
        int ready_at[BMAX][2], stun_end[BMAX];
        for (int i = 0; i < n; ++i) any_extra |= u[i].extra;
        const int r0 = any_extra ? 0 : 1;        // the first round played
        for (int i = 0; i < n; ++i) {
            const BUnit& me = u[i];
            if (!dead[i]) { live |= 1u << i; ++alive[me.side]; }
            excl_off[i] = dash_slots[i] = castable[i] = 0;
            for (int s = 0; s < 2; ++s) {
                const Abil& a = me.ab[s];
                if (a.excl && a.kind != K_NONE && a.kind != K_HEAL && a.kind != K_SHIELD) excl_off[i] |= 1u << s;
                if (a.kind == K_DASH) dash_slots[i] |= 1u << s;
                if (a.kind != K_NONE && a.kind != K_DASH) castable[i] |= 1u << s;
            }
            if (me.rng <= 1) melee[me.side] |= 1u << i;
            side_of[me.side] |= 1u << i;
            if (me.shield_left > 0) shielded |= 1u << i;
            const int ts = (any_extra && me.extra) ? 0 : 1;
            ready_at[i][0] = ts + me.ab[0].cd;
            ready_at[i][1] = ts + me.ab[1].cd;
            // an immune unit's starting stun is cleared at the end of the first round played
            stun_end[i] = me.stun > 0 ? (me.stun_immune ? r0 + 1 : ts + me.stun) : 0;
        }
        int last = -1;                           // the last round played
        for (int r = r0; r <= horizon; ++r) {
            const bool pre = r == 0;
            if (!alive[0] || !alive[1]) break;
            i64 inc[BMAX];                       // valid where the bit of dmg_set is on
            int nst[BMAX];                       // new stun (valid where the bit of stun_set is on)
            int hit_target[BMAX];                // valid where the bit of hit_set is on
            unsigned stun_set = 0, hit_set = 0, dmg_set = 0;
            bool moved_any = false, cast_any = false;   // (for the fast-forward below)
            auto add_dmg = [&](int t, i64 v) {
                if (dmg_set >> t & 1u) inc[t] += v;
                else { inc[t] = v; dmg_set |= 1u << t; }
            };
            auto add_stun = [&](int t, int v) {
                if (stun_set >> t & 1u) { if (v > nst[t]) nst[t] = v; }
                else { nst[t] = v; stun_set |= 1u << t; }
            };
            for (unsigned m = live; m; m &= m - 1) {
                const int i = __builtin_ctz(m);
                BUnit& me = u[i];
                if (r < stun_end[i] || (pre && !me.extra)) continue;
                const int sd = me.side;
                if (me.focus < 0 || !(live >> me.focus & 1u)) {
                    me.focus = lowest_from(sd, me.x, me.y, me.rng, false, live & side_of[1 - sd]);
                    if (me.focus < 0) {   // nearest living enemy (ties: lowest index)
                        int best = -1, bd = 1 << 20;
                        for (unsigned q = live & side_of[1 - sd]; q; q &= q - 1) {
                            const int j = __builtin_ctz(q);
                            const int dj = cheb(me.x, me.y, u[j].x, u[j].y);
                            if (dj < bd) bd = dj, best = j;
                        }
                        me.focus = best;
                    }
                }
                const int f = me.focus;
                if (f < 0) continue;
                BUnit& tf = u[f];
                int d = cheb(me.x, me.y, tf.x, tf.y);
                const unsigned ready = (r >= ready_at[i][0] ? 1u : 0u) | (r >= ready_at[i][1] ? 2u : 0u);
                const unsigned dr = dash_slots[i] & ready;
                // Engine rules, every unit: ONE successful cast a round (both slots; a dash is a cast); a ranged unit
                // walks OR basic-attacks (a reset restores the attack); a move-exclusive spell cannot share a round
                // with a walk. A step toward the focus (sign step on each axis) lowers the chebyshev distance by exactly
                // 1 (from >= 1): d is tracked instead of recomputed.
                bool walked = false;     // an ordinary step (a dash is a cast, not a walk)
                int cslot = -1;          // the round's one cast
                auto toward = [&]() { me.x += (tf.x > me.x) - (tf.x < me.x); me.y += (tf.y > me.y) - (tf.y < me.y); --d; moved_any = true; };
                if (sd == 0) {
                    // Our side plays the user's combat rules by matchup (states/attack.cpp does the same).
                    if (me.rng <= 1) {
                        if (tf.rng <= 1) {
                            // melee vs melee: move + attack; else dash + move + attack; else hold where they cannot move +
                            // attack us (distance > 2), as close as that allows
                            if (d <= 2) {
                                if (d > 1) toward(), walked = true;
                            } else if (dr && d <= 4) {
                                cslot = __builtin_ctz(dr);
                                toward(), toward();
                                if (d > 1) toward(), walked = true;
                            } else if (d >= 4) {
                                toward(), walked = true;
                            }
                        } else {
                            // melee vs ranged: move + attack; else dash + move + attack; else walk toward them
                            if (d > 2 && dr && d <= 4) cslot = __builtin_ctz(dr), toward(), toward();
                            if (d > 1) toward(), walked = true;
                        }
                    } else if (tf.rng <= 1) {
                        // ranged vs melee: out of our range, walk toward them; in range, stand still (the cast step may
                        // dash away)
                        if (d > me.rng) toward(), walked = true;
                    } else if (d > me.rng) {
                        // ranged vs ranged: dash into range (then attack: a dash is not a walk); else walk toward them but
                        // never into their range
                        if (dr && d - 2 <= me.rng) {
                            cslot = __builtin_ctz(dr);
                            while (d > me.rng) toward();
                        } else if (d - 1 > tf.rng) {
                            toward(), walked = true;
                        }
                    }
                } else {
                    // Theirs: melee closes, dashing when that brings the focus into range; ranged closes to its range and
                    // kites an adjacent melee while its kite budget lasts; a ready movement-exclusive cast pre-empts moving.
                    const bool excl_ready = d <= CAST_RANGE && (excl_off[i] & ready);
                    if (!excl_ready) {
                        if (me.rng <= 1) {
                            if (d > 1) {
                                if (dr && d - 2 <= 1) {
                                    cslot = __builtin_ctz(dr);
                                    toward();
                                    if (d > 1) toward();
                                }
                                if (d > 1) toward(), walked = true;
                            }
                        } else {
                            int threat = -1;
                            if (me.kite > 0)   // the first adjacent enemy melee (index order)
                                for (unsigned q = live & melee[1 - sd]; q; q &= q - 1) {
                                    const int j = __builtin_ctz(q);
                                    if (cheb(me.x, me.y, u[j].x, u[j].y) <= 1) { threat = j; break; }
                                }
                            if (threat >= 0) {
                                me.x -= (u[threat].x > me.x) - (u[threat].x < me.x); me.y -= (u[threat].y > me.y) - (u[threat].y < me.y);
                                --me.kite;
                                d = cheb(me.x, me.y, tf.x, tf.y);
                                walked = true;
                                moved_any = true;
                            } else if (d > me.rng) {
                                toward(), walked = true;
                            }
                        }
                    }
                }
                if (cslot >= 0) ready_at[i][cslot] = r + CD, cast_any = true;   // the dash took the round's cast
                // The round's one cast (when no dash took it): ours in the user's order for the matchup, theirs the first
                // ready slot (slot order) that has a target. A slot with no target is passed over.
                int hits = 1;
                bool enh = false, reset_cast = false;
                auto try_cast = [&](int s) -> bool {
                    Abil& a = me.ab[s];
                    if (!(ready >> s & 1u) || (a.excl && walked)) return false;
                    switch (a.kind) {
                    case K_DAMAGE: {
                        const int tg = d <= CAST_RANGE ? f : lowest_from(sd, me.x, me.y, CAST_RANGE, false, live & side_of[1 - sd]);
                        if (tg < 0) return false;
                        add_dmg(tg, a.amt);
                        if (u[tg].retal > 0) add_dmg(i, u[tg].retal);
                        hit_set |= 1u << i; hit_target[i] = tg;
                        break;
                    }
                    case K_CC: {
                        const int tg = (d <= CAST_RANGE && !tf.stun_immune) ? f : lowest_from(sd, me.x, me.y, CAST_RANGE, true, live & side_of[1 - sd]);
                        if (tg < 0) return false;
                        add_dmg(tg, a.amt);
                        if (a.amt > 0 && u[tg].retal > 0) add_dmg(i, u[tg].retal);
                        add_stun(tg, a.dur);
                        break;
                    }
                    case K_AOE: {
                        if (d > CAST_RANGE) return false;
                        for (unsigned q = live & side_of[1 - sd]; q; q &= q - 1) {
                            const int j = __builtin_ctz(q);
                            if (cheb(u[j].x, u[j].y, tf.x, tf.y) > a.radius) continue;
                            add_dmg(j, a.amt);
                            if (u[j].retal > 0) add_dmg(i, u[j].retal);
                            if (a.dur > 0 && !u[j].stun_immune) add_stun(j, a.dur);
                        }
                        break;
                    }
                    case K_HEAL: {
                        int tg = -1;
                        for (unsigned q = live & side_of[sd] & ~(1u << i); q; q &= q - 1) {
                            const int j = __builtin_ctz(q);
                            if (u[j].hp >= u[j].maxhp || cheb(me.x, me.y, u[j].x, u[j].y) > CAST_RANGE) continue;
                            if (tg < 0 || u[j].hp * u[tg].maxhp < u[tg].hp * u[j].maxhp) tg = j;
                        }
                        if (tg < 0) return false;
                        u[tg].hp = std::min(u[tg].maxhp, u[tg].hp + a.amt);
                        break;
                    }
                    case K_SHIELD:
                        me.shield = a.amt; me.shield_left = a.dur;
                        if (a.dur > 0) shielded |= 1u << i; else shielded &= ~(1u << i);
                        break;
                    case K_RESET: hits = 2; enh = a.enhanced; reset_cast = true; break;
                    default: return false;
                    }
                    ready_at[i][s] = r + CD;
                    cast_any = true;
                    return true;
                };
                // (Only a ready, castable slot can cast: with none, the block has nothing to do -- most rounds, the
                // cooldowns being 8.)
                if (cslot < 0 && (castable[i] & ready)) {
                    if (sd == 0) {
                        // can an enemy hit us next round (move + attack)? -> shield first (user). (Asked only when a
                        // shield is ready: nothing else reads it.)
                        bool threatened = false;
                        bool shield_ready = false;
                        for (int s = 0; s < 2; ++s) shield_ready |= me.ab[s].kind == K_SHIELD && (ready >> s & 1u);
                        if (shield_ready)
                            for (unsigned q = live & side_of[1]; q && !threatened; q &= q - 1) {
                                const int j = __builtin_ctz(q);
                                threatened = cheb(me.x, me.y, u[j].x, u[j].y) <= u[j].rng + 1;
                            }
                        // kinds in priority order: melee vs melee stuns LAST (end of turn); every other matchup stuns first
                        const bool mm = me.rng <= 1 && tf.rng <= 1;
                        static constexpr unsigned char order_mm[5] = {K_SHIELD, K_DAMAGE, K_AOE, K_RESET, K_CC};
                        static constexpr unsigned char order_st[5] = {K_SHIELD, K_CC, K_DAMAGE, K_AOE, K_RESET};
                        const unsigned char* order = mm ? order_mm : order_st;
                        for (int k = 0; k < 5 && cslot < 0; ++k) {
                            const unsigned char want = order[k];
                            if (want == K_SHIELD && !threatened) continue;
                            if (want == K_RESET && d > me.rng) continue;   // only when we hit them this round
                            for (int s = 0; s < 2 && cslot < 0; ++s)
                                if (me.ab[s].kind == want && try_cast(s)) cslot = s;
                        }
                        for (int s = 0; s < 2 && cslot < 0; ++s)   // (a heal: when nothing above applied)
                            if (me.ab[s].kind == K_HEAL && try_cast(s)) cslot = s;
                    } else {
                        for (unsigned rc = castable[i] & ready; rc && cslot < 0; rc &= rc - 1) {
                            const int s = __builtin_ctz(rc);
                            if (try_cast(s)) cslot = s;
                        }
                    }
                }
                // The basic attack: in range; a ranged unit that walked has used its attack unless a reset restored it.
                if (d <= me.rng) {
                    if (me.rng > 1 && walked) hits = reset_cast ? 1 : 0;
                    if (hits > 0) {
                        const i64 dmg = me.basic * hits;
                        add_dmg(f, dmg);
                        if (tf.retal > 0) add_dmg(i, tf.retal * hits);
                        if (enh && !tf.stun_immune) add_stun(f, 1);
                        hit_set |= 1u << i; hit_target[i] = f;
                        if (me.splash)
                            for (unsigned q = live & side_of[1 - sd] & ~(1u << f); q; q &= q - 1) {
                                const int j = __builtin_ctz(q);
                                if (cheb(u[j].x, u[j].y, tf.x, tf.y) <= 1) add_dmg(j, dmg);
                            }
                    }
                }
                // Ours, ranged vs melee: with the cast still free, dash away when they could reach us next round (user:
                // they have to walk to us the furthest).
                if (sd == 0 && cslot < 0 && dr && me.rng > 1 && tf.rng <= 1 && d <= tf.rng + 1) {
                    const int s = __builtin_ctz(dr);
                    for (int k = 0; k < 2; ++k) { me.x -= (tf.x > me.x) - (tf.x < me.x); me.y -= (tf.y > me.y) - (tf.y < me.y); }
                    ready_at[i][s] = r + CD;
                    moved_any = cast_any = true;
                }
            }
            unsigned died = 0;
            for (unsigned m = dmg_set & live; m; m &= m - 1) {   // (an undamaged unit's hp / shield do not change)
                const int i = __builtin_ctz(m);
                BUnit& me = u[i];
                i64 dd = inc[i];
                if (me.shield_left > 0) { const i64 a = std::min(me.shield, dd); me.shield -= a; dd -= a; }
                me.hp -= dd;
                if (me.hp <= 0) { died |= 1u << i; dead[i] = true; --alive[me.side]; if (first_death < 0) first_death = i; }
            }
            live &= ~died;
            // Timers (of the living: callers read nothing of a dead unit but hp and the death). Cooldowns and stuns
            // run on their own (absolute rounds); here only what this round changed, and running shields.
            for (unsigned m = shielded & live; m; m &= m - 1) {
                const int i = __builtin_ctz(m);
                if (pre && !u[i].extra) continue;   // round 0 ticks only the double-turn unit
                if (--u[i].shield_left == 0) { u[i].shield = 0; shielded &= ~(1u << i); }
            }
            for (unsigned m = stun_set & live; m; m &= m - 1) {
                const int i = __builtin_ctz(m);
                if (u[i].stun_immune) continue;
                stun_end[i] = std::max(stun_end[i], r + 1 + nst[i]);
            }
            if (died)   // a kill refreshes the killer's cooldowns (reset_on_kill)
                for (unsigned m = hit_set & live; m; m &= m - 1) {
                    const int i = __builtin_ctz(m);
                    if (!u[i].reset_on_kill || !(died >> hit_target[i] & 1u)) continue;
                    if (pre && !u[i].extra) continue;
                    ready_at[i][0] = std::min(ready_at[i][0], r + 1);
                    ready_at[i][1] = std::min(ready_at[i][1], r + 1);
                }
            rounds = r;
            last = r;
            // Fast-forward (user): a plain round -- nobody moved, cast, was stunned or died -- repeats exactly (same
            // positions, focuses, damage per round, castable set) until the next event: an ability off cooldown, a
            // stunned unit waking, a shield running out or expiring, a death, the horizon. Those rounds are applied at
            // once with the same integer arithmetic, so the state is the one the rounds would leave. (A ready heal
            // blocks it: whether it finds a target depends on hp.)
            if (!pre && !moved_any && !cast_any && !stun_set && !died && r < horizon) {
                i64 k = horizon - r;
                for (unsigned m = live; m && k > 0; m &= m - 1) {
                    const int i = __builtin_ctz(m);
                    const BUnit& me = u[i];
                    if (r < stun_end[i]) k = std::min<i64>(k, stun_end[i] - 1 - r);   // still stunned until then
                    for (int s = 0; s < 2; ++s) {
                        if (me.ab[s].kind == K_NONE) continue;
                        if (ready_at[i][s] > r) k = std::min<i64>(k, ready_at[i][s] - 1 - r);   // off cooldown then
                        else if (me.ab[s].kind == K_HEAL) k = 0;
                    }
                    if (!(dmg_set >> i & 1u) || inc[i] <= 0) continue;
                    if (me.shield_left > 0 && me.shield > 0) k = std::min<i64>(k, std::min<i64>(me.shield_left, me.shield / inc[i]));
                    else k = std::min<i64>(k, (me.hp - 1) / inc[i]);   // alive through the last of them
                }
                if (k > 0) {
                    for (unsigned m = dmg_set & live; m; m &= m - 1) {
                        const int i = __builtin_ctz(m);
                        BUnit& me = u[i];
                        if (me.shield_left > 0 && me.shield > 0) me.shield -= inc[i] * k;   // fully absorbed each round
                        else me.hp -= inc[i] * k;
                    }
                    for (unsigned m = shielded & live; m; m &= m - 1) {
                        const int i = __builtin_ctz(m);
                        u[i].shield_left -= static_cast<int>(k);
                        if (u[i].shield_left <= 0) { u[i].shield_left = 0; u[i].shield = 0; shielded &= ~(1u << i); }
                    }
                    r += static_cast<int>(k);
                    rounds = r;
                    last = r;
                }
            }
        }
        // Back to countdowns as of the next round (the state the per-round version leaves).
        const int rn = last >= 0 ? last + 1 : r0;
        for (unsigned m = live; m; m &= m - 1) {
            const int i = __builtin_ctz(m);
            BUnit& me = u[i];
            const int ri = std::max(rn, (any_extra && me.extra) ? 0 : 1);
            me.ab[0].cd = static_cast<signed char>(std::max(0, ready_at[i][0] - ri));
            me.ab[1].cd = static_cast<signed char>(std::max(0, ready_at[i][1] - ri));
            me.stun = std::max(0, stun_end[i] - ri);
        }
    }

    // FAST_FIGHT (user, 2026-10-17): the fight on a line -- LineSim below. (jumps = false: every round played, for checks)
    void run_line(int horizon, bool jumps = true);

};

// FAST_FIGHT (user, 2026-10-17/18): the fight on a line -- Battle::run_line's state and steps. Every unit fights its
// focus 1v1 at a distance d (from the chebyshev distance at the start); the damage on a unit is summed over everyone
// focusing it. Units act one after another and damage lands at once, so a first strike, a kill and a double turn are real.
//   Turn order (the bot's bands, priority.h): ours act before theirs, except a unit holding our saved double turn
//   (extra), which acts after them -- its first action alone in round 0 (it is our turn: everyone else has acted).
//   The double turn: when its next action kills its focus (a hit plus the best ability ready by then, in reach), or the
//   melee-vs-ranged double move below, it flips to acting before them -- its next action comes right after this one.
// The user's rules by matchup ("engage" = the attack this turn, then the cast):
//   melee vs melee:  d <= 2 engage (a step at 2); a ready dash and d <= 4: dash + step + engage (the dash is the cast);
//                    d 3 with a ready ranged stun (one that allows the step): stun + step, else pass (ours: they close
//                    in); d >= 4 step.
//   melee vs ranged: d <= 2 engage; dash and d <= 4 engage; ranged stun and d 3: stun + step; ranged stun, d 4 and
//                    holding the double move: stun + step (the double move kept); holding the double move and it (with
//                    the dash) reaches them: the double move; else step.
//   ranged vs melee: d > 3 step (no dash); d <= 3 attack; adjacent with the cast still free and a dash: dash out to 3.
//   ranged vs ranged: a ready range-4 damaging ability they cannot answer (they own no range-4 ability): poke -- d > 4
//                    step, d 4 stand and cast; else a dash and d 4-5: dash into range (3) + attack; else d > 3 step
//                    (no dash); d <= 3 attack.
//   Theirs always close in (user): the same rules, never passing.
//   The cast (one a turn): the ready ability scoring most (user, 2026-10-18), as a fraction of a max hp -- damage
//   (a spell, a reset's extra hit): my damage / their max hp; a stun: their damage (a turn each round stunned) / my max
//   hp, plus its damage; a shield: its amount / my max hp; a heal: what it restores / that ally's max hp; a killing hit
//   first. Castable: damage spells within cast range 4 (not engaged too); a pure stun when engaged (ranged: within 3);
//   a reset or shield when attacking; a heal whenever an ally in range is hurt; nothing move-exclusive after a walk.
//   A stun costs the stunned unit its next turns; cooldowns keep ticking (every turn end).
//   Accelerated: while everyone is farther than any rule's reach only the distances change, so those rounds go at
//   once; once a round repeats (nobody moved, cast, was stunned or died) the rounds up to the next event go at once.
// Flat arrays + member functions (one static instance, every used field set per call): wasm fuel is ~1 per
// instruction, and lambdas capturing the state by reference cost a pointer load per access.
struct LineSim {
    static constexpr i64 KILL = (i64)1 << 50;
    static constexpr i64 SC = (i64)1 << 20;   // score scale: 1 max hp
    int n = 0, r = 0, horizon = 0, far_d = 5, first_death = -1, rounds = 0;
    bool pre = false, jumps = true, moved_any = false, cast_any = false, stun_any = false, refocus = false, far_possible = true;
    unsigned live = 0, side_of[2] = {0, 0}, before = 0, after = 0, shielded = 0, acted = 0, died = 0, dmg_set = 0;
    int alive[2] = {0, 0};
    // per unit
    const BUnit* U = nullptr;   // the Battle's units (read-only: what the hot path does not need copied)
    int side[BMAX], rng[BMAX], focus[BMAX], dist[BMAX], ra[BMAX][2], stun_end[BMAX], shl[BMAX];
    i64 hp[BMAX], sh[BMAX], basic[BMAX], retal[BMAX], inc[BMAX];
    bool dead[BMAX];
    // slot masks (bit s: ability slot s): any / dash / heal / move-exclusive / range-4 spells (damage, area, stun) /
    // abilities that count only when attacking (reset, shield) / a stun that allows the step / range-4 spells that
    // deal damage; owns4: the unit has a range-4 spell at all
    unsigned active[BMAX], m_dash[BMAX], m_heal[BMAX], m_excl[BMAX], m_range[BMAX], m_hit[BMAX], m_stun3[BMAX], m_dmg4[BMAX];
    bool owns4[BMAX];

    void load(int nn, const BUnit* u, const bool* dd, int hz, bool jp, int fd, int rds) {
        U = u, n = nn, horizon = hz, jumps = jp, first_death = fd, rounds = rds;
        live = side_of[0] = side_of[1] = before = after = shielded = 0;
        alive[0] = alive[1] = 0;
        moved_any = cast_any = stun_any = refocus = false;
        far_possible = true;
        bool any_extra = false;
        for (int i = 0; i < n; ++i) any_extra |= u[i].extra && u[i].side == 0;
        r = any_extra ? 0 : 1;   // round 0: the double-turn unit alone (as run())
        int maxrng = 1;
        for (int i = 0; i < n; ++i) {
            const BUnit& me = u[i];
            const int sd = me.side;
            side[i] = sd, rng[i] = me.rng;
            hp[i] = me.hp, sh[i] = me.shield, shl[i] = me.shield_left, basic[i] = me.basic, retal[i] = me.retal;
            dead[i] = dd[i];
            if (!dd[i]) { live |= 1u << i; ++alive[sd]; }
            side_of[sd] |= 1u << i;
            unsigned ma = 0, md = 0, mh = 0, mx = 0, mr = 0, mt = 0, ms = 0, m4 = 0;
            for (int s = 0; s < 2; ++s) {
                const Abil& a = me.ab[s];
                const unsigned b = 1u << s;
                if (a.kind == K_NONE) continue;
                ma |= b;
                if (a.excl) mx |= b;
                if (a.kind == K_DASH) md |= b;
                else if (a.kind == K_HEAL) mh |= b;
                else if (a.kind == K_RESET || a.kind == K_SHIELD) mt |= b;
                else if (a.kind == K_DAMAGE || a.kind == K_AOE || a.kind == K_CC) { mr |= b; if (a.amt > 0) m4 |= b; }
                if (!a.excl && (a.kind == K_CC || (a.kind == K_AOE && a.dur > 0))) ms |= b;
            }
            active[i] = ma, m_dash[i] = md, m_heal[i] = mh, m_excl[i] = mx, m_range[i] = mr, m_hit[i] = mt, m_stun3[i] = ms;
            m_dmg4[i] = m4, owns4[i] = mr != 0;
            if (me.shield_left > 0) shielded |= 1u << i;
            const bool x = any_extra && me.extra && sd == 0;
            const int ts = x ? 0 : 1;   // the unit's first round
            ra[i][0] = ts + me.ab[0].cd;
            ra[i][1] = ts + me.ab[1].cd;
            stun_end[i] = me.stun > 0 && !me.stun_immune ? ts + me.stun : 0;
            if (sd == 0) { if (x) after |= 1u << i; else before |= 1u << i; }
            if (me.rng > maxrng) maxrng = me.rng;
            focus[i] = -1;
            dist[i] = 0;
        }
        // Past this distance no rule does anything but step: the melee dash (4), the ranged dash (range + 2), the
        // double move (5), spells (cast range 4).
        far_d = std::max(std::max(5, maxrng + 2), CAST_RANGE + 1);
        for (unsigned q = live; q; q &= q - 1) {   // the first focus: lowest hp + shield in range, else the nearest
            const int i = __builtin_ctz(q);
            int best = -1, near = -1, bd = 1 << 20;
            i64 bv = 0;
            for (unsigned e = live & side_of[1 - side[i]]; e; e &= e - 1) {
                const int j = __builtin_ctz(e);
                const int dj = cheb(u[i].x, u[i].y, u[j].x, u[j].y);
                if (dj < bd) bd = dj, near = j;
                if (dj > rng[i]) continue;
                const i64 v = hp[j] + sh[j];
                if (best < 0 || v < bv) best = j, bv = v;
            }
            if (best < 0) best = near;
            focus[i] = best;
            if (best >= 0) dist[i] = cheb(u[i].x, u[i].y, u[best].x, u[best].y);
        }
    }
    void store(int nn, BUnit* u, bool* dd, int& fd, int& rds) const {
        for (int i = 0; i < nn; ++i) {
            BUnit& me = u[i];
            me.hp = hp[i], me.shield = sh[i], me.shield_left = shl[i], me.focus = focus[i];
            dd[i] = dead[i];
        }
        fd = first_death, rds = rounds;
    }

    int dist_to(int i, int j) const { return focus[j] == i ? dist[j] : cheb(U[i].x, U[i].y, U[j].x, U[j].y); }
    void pick_focus(int i) {   // lowest hp + shield within range, else the nearest (ties: lowest index)
        int best = -1;
        i64 bv = 0;
        const unsigned en = live & side_of[1 - side[i]];
        for (unsigned q = en; q; q &= q - 1) {
            const int j = __builtin_ctz(q);
            if (dist_to(i, j) > rng[i]) continue;
            const i64 v = hp[j] + sh[j];
            if (best < 0 || v < bv) best = j, bv = v;
        }
        if (best < 0) {
            int bd = 1 << 20;
            for (unsigned q = en; q; q &= q - 1) {
                const int j = __builtin_ctz(q);
                const int dj = dist_to(i, j);
                if (dj < bd) bd = dj, best = j;
            }
        }
        focus[i] = best;
        if (best >= 0) dist[i] = dist_to(i, best);
    }
    int heal_target(int i) const {   // the most hurt ally in range (hp fraction; start positions)
        int tg = -1;
        for (unsigned q = live & side_of[side[i]] & ~(1u << i); q; q &= q - 1) {
            const int j = __builtin_ctz(q);
            if (hp[j] >= U[j].maxhp || cheb(U[i].x, U[i].y, U[j].x, U[j].y) > CAST_RANGE) continue;
            if (tg < 0 || hp[j] * U[tg].maxhp < hp[tg] * U[j].maxhp) tg = j;
        }
        return tg;
    }
    void die(int t, int killer) {
        dead[t] = true;
        live &= ~(1u << t);
        --alive[side[t]];
        if (first_death < 0) first_death = t;
        died |= 1u << t;
        refocus = true;
        if (killer >= 0 && U[killer].reset_on_kill && (live >> killer & 1u)) {   // a kill refreshes its cooldowns
            ra[killer][0] = std::min(ra[killer][0], r + 1);
            ra[killer][1] = std::min(ra[killer][1], r + 1);
        }
    }
    __attribute__((always_inline)) void damage(int t, i64 v, int src) {   // lands at once (a running shield first)
        if (v <= 0 || !(live >> t & 1u)) return;
        if (dmg_set >> t & 1u) inc[t] += v; else inc[t] = v, dmg_set |= 1u << t;
        if (shl[t] > 0) { const i64 a = std::min(sh[t], v); sh[t] -= a; v -= a; }
        hp[t] -= v;
        if (hp[t] <= 0) die(t, src);
    }
    __attribute__((always_inline)) void hit(int i, int t, i64 v) {   // with t's retaliation back
        damage(t, v, i);
        if (retal[t] > 0 && (live >> i & 1u)) damage(i, retal[t], t);
    }
    void stun(int t, int dur, bool force) {   // t misses its next `dur` turns
        if (dur <= 0 || !(live >> t & 1u) || (U[t].stun_immune && !force)) return;
        const int from = (pre || (acted >> t & 1u)) ? r + 1 : r;
        stun_end[t] = std::max(stun_end[t], from + dur);
        stun_any = true;
    }
    __attribute__((always_inline)) void use(int i, int s) { ra[i][s] = r + CD; cast_any = true; }
    __attribute__((always_inline)) void flip(int i) { after &= ~(1u << i); before |= 1u << i; cast_any = true; }   // the double turn
    __attribute__((always_inline)) void step(int i, int k) {
        const int f = focus[i];
        dist[i] = std::max(1, dist[i] - k);
        if (focus[f] == i) dist[f] = dist[i];
        moved_any = true;
    }
    i64 frac(i64 x, i64 of) const { return of > 0 ? x * SC / of : 0; }
    // What casting slot s scores now (0: not castable / nothing to gain); see the header.
    i64 score(int i, int s, bool attacking) const {
        const Abil& a = U[i].ab[s];
        const int f = focus[i];
        const int d = dist[i];
        const i64 left = hp[f] + (shl[f] > 0 ? sh[f] : 0);
        const i64 mine = U[i].maxhp, theirs = U[f].maxhp;
        const i64 stun1 = U[f].stun_immune ? 0 : frac(basic[f], mine);   // a turn of theirs prevented
        switch (a.kind) {
        case K_DAMAGE:
            if (d > CAST_RANGE || a.amt <= 0) return 0;
            return a.amt >= left ? KILL : frac(a.amt, theirs);
        case K_AOE:
        case K_CC: {
            if (d > CAST_RANGE) return 0;
            const i64 st = a.dur > 0 ? stun1 * a.dur : 0;
            if (a.amt > 0) return a.amt >= left ? KILL : frac(a.amt, theirs) + st;
            return (rng[i] <= 1 ? attacking : d <= rng[i]) ? st : 0;   // a pure stun
        }
        case K_RESET: return !attacking ? 0 : basic[i] >= left ? KILL : frac(basic[i], theirs) + (a.enhanced ? stun1 : 0);
        case K_SHIELD: return attacking ? frac(a.amt, mine) : 0;
        case K_HEAL: { const int t = heal_target(i); return t < 0 ? 0 : frac(std::min(a.amt, U[t].maxhp - hp[t]), U[t].maxhp); }
        default: return 0;
        }
    }
    void cast(int i, int s) {
        const Abil& a = U[i].ab[s];
        const int f = focus[i];
        use(i, s);
        switch (a.kind) {
        case K_DAMAGE: hit(i, f, a.amt); break;
        case K_AOE: hit(i, f, a.amt); if (a.dur > 0) stun(f, a.dur, false); break;
        case K_CC: if (a.amt > 0) hit(i, f, a.amt); stun(f, a.dur, false); break;
        case K_RESET: hit(i, f, basic[i]); if (a.enhanced) stun(f, 1, false); break;
        case K_SHIELD:
            sh[i] = a.amt, shl[i] = a.dur;
            if (a.dur > 0) shielded |= 1u << i; else shielded &= ~(1u << i);
            break;
        case K_HEAL: { const int t = heal_target(i); if (t >= 0) hp[t] = std::min(U[t].maxhp, hp[t] + a.amt); break; }
        default: break;
        }
    }
    __attribute__((always_inline)) void act(int i) {   // unit i's turn: the user's rules by matchup (header)
        if (r < stun_end[i]) return;
        if (focus[i] < 0 || !(live >> focus[i] & 1u)) pick_focus(i);
        const int f = focus[i];
        if (f < 0) return;
        const bool ours = side[i] == 0, melee = rng[i] <= 1, fmelee = rng[f] <= 1;
        const bool dbl = (after >> i & 1u) != 0;   // holds our saved double turn
        const unsigned rdy = ((r >= ra[i][0] ? 1u : 0u) | (r >= ra[i][1] ? 2u : 0u)) & active[i];
        const unsigned dr = rdy & m_dash[i];
        bool attacking = false, walked = false, cast_used = false;
        const int d = dist[i];
        if (melee) {
            const unsigned st = U[f].stun_immune ? 0u : rdy & m_stun3[i];   // a ready ranged stun allowing the step
            if (d <= 2) {
                if (d == 2) step(i, 1), walked = true;
                attacking = true;
            } else if (dr && d <= 4) {
                use(i, __builtin_ctz(dr)), cast_used = true;
                step(i, 2);
                if (dist[i] > 1) step(i, 1), walked = true;
                attacking = true;
            } else if (st && (d == 3 || (!fmelee && d == 4 && dbl))) {
                cast(i, __builtin_ctz(st)), cast_used = true;   // stun + step (at 4: the double move kept)
                if (live >> f & 1u) step(i, 1), walked = true;
            } else if (!fmelee && dbl && (d == 3 || (dr && d == 5))) {
                // vs ranged: the double move reaches them -- (the dash +) a step now, the next action right after
                if (d == 5) use(i, __builtin_ctz(dr)), cast_used = true, step(i, 2);
                step(i, 1), walked = true;
                flip(i);
            } else if (!(ours && fmelee && d == 3)) {
                step(i, 1), walked = true;   // (ours pass at 3 against a melee: it comes to us)
            }
        } else {
            const bool poke = !fmelee && (rdy & m_dmg4[i]) && !owns4[f];   // vs ranged: a range-4 hit they can't answer
            if (!fmelee && dr && !poke && d > rng[i] && d <= rng[i] + 2) {
                use(i, __builtin_ctz(dr)), cast_used = true;   // dash into range (the cast), then attack
                step(i, d - rng[i]);
            } else if (d > rng[i] && !(poke && d == CAST_RANGE)) {
                step(i, 1), walked = true;   // closer (no dash); poking: stand at 4
            }
            attacking = !walked && dist[i] <= rng[i];
        }
        if (!(live >> f & 1u)) return;
        if (attacking) hit(i, f, basic[i]);
        // The cast: the ready ability scoring most (only slots that can score now are looked at).
        if (!cast_used && (live >> i & 1u) && (live >> f & 1u)) {
            unsigned cand = rdy & (m_heal[i] | (dist[i] <= CAST_RANGE ? m_range[i] : 0u) | (attacking ? m_hit[i] : 0u));
            if (walked) cand &= ~m_excl[i];
            int bs = -1;
            i64 bv = 0;
            for (unsigned c = cand; c; c &= c - 1) {
                const int s = __builtin_ctz(c);
                const i64 v = score(i, s, attacking);
                if (v > bv) bs = s, bv = v;
            }
            if (bs >= 0) cast(i, bs), cast_used = true;
        }
        // Ranged vs melee: adjacent with the cast still free -> dash out to 3.
        if (!melee && fmelee && dr && !cast_used && dist[i] == 1 && (live >> i & 1u) && (live >> f & 1u)) {
            use(i, __builtin_ctz(dr));
            dist[i] = 3;
            if (focus[f] == i) dist[f] = 3;
            moved_any = true;
        }
        // The double turn (user): our next action -- a hit plus the best ability ready by then -- kills the focus.
        if ((after >> i & 1u) && (live >> i & 1u) && (live >> f & 1u) && dist[i] <= (melee ? 2 : rng[i])) {
            i64 bv = 0;
            for (int s = 0; s < 2; ++s) {
                if (r + 1 < ra[i][s]) continue;
                const Abil& a = U[i].ab[s];
                const i64 v = a.kind == K_RESET ? basic[i] : (a.kind == K_DAMAGE || a.kind == K_AOE || a.kind == K_CC) ? a.amt : 0;
                bv = std::max(bv, v);
            }
            if (hp[f] + (shl[f] > 0 ? sh[f] : 0) <= basic[i] + bv) flip(i);
        }
    }
    // Far apart: every unit only steps (each sees more than far_d) -- the rounds until a distance reaches far_d at once
    // (a stun waking, a heal coming ready with someone to heal, the horizon end them earlier). True: jumped.
    bool far_jump() {
        int k = horizon - r + 1;
        for (unsigned q = live; q && k > 0; q &= q - 1) {
            const int i = __builtin_ctz(q);
            const int f = focus[i];
            if (r < stun_end[i]) k = std::min(k, stun_end[i] - r);
            const int rate = (r >= stun_end[i] ? 1 : 0) + (focus[f] == i && r >= stun_end[f] ? 1 : 0);
            if (rate > 0) k = std::min(k, (dist[i] - far_d) / rate);
            for (unsigned hs = m_heal[i]; hs && k > 0; hs &= hs - 1) {
                const int s = __builtin_ctz(hs);
                if (ra[i][s] > r) k = std::min(k, ra[i][s] - r);
                else if (heal_target(i) >= 0) k = 0;
            }
        }
        if (k <= 0) return false;
        for (unsigned q = live; q; q &= q - 1) {
            const int i = __builtin_ctz(q);
            const int f = focus[i];
            const bool mutual = focus[f] == i;
            if (mutual && f < i) continue;   // (a pair's shared distance, once)
            const int rate = (r >= stun_end[i] ? 1 : 0) + (mutual && r >= stun_end[f] ? 1 : 0);
            dist[i] -= rate * k;
            if (mutual) dist[f] = dist[i];
        }
        for (unsigned q = shielded & live; q; q &= q - 1) {
            const int i = __builtin_ctz(q);
            shl[i] -= k;
            if (shl[i] <= 0) { shl[i] = 0; sh[i] = 0; shielded &= ~(1u << i); }
        }
        r += k - 1;
        rounds = r;
        return true;
    }
    // A round that repeated (nobody moved, cast, was stunned or died; the order unchanged): the rounds up to the next
    // event at once -- an ability ready, a stun over, a shield out or expiring, a death, a kill the double turn would
    // confirm, a heal finding someone hurt, the horizon. Same integer arithmetic as the rounds.
    void repeat_jump() {
        i64 k = horizon - r;
        for (unsigned q = live; q && k > 0; q &= q - 1) {
            const int i = __builtin_ctz(q);
            if (r < stun_end[i]) k = std::min<i64>(k, stun_end[i] - 1 - r);
            for (int s = 0; s < 2; ++s) {
                if (U[i].ab[s].kind == K_NONE) continue;
                if (ra[i][s] > r) k = std::min<i64>(k, ra[i][s] - 1 - r);
                else if (U[i].ab[s].kind == K_HEAL && (dmg_set & side_of[side[i]] & ~(1u << i))) k = 0;
            }
            if (!(dmg_set >> i & 1u) || inc[i] <= 0) continue;
            if (shl[i] > 0 && sh[i] > 0) k = std::min<i64>(k, std::min<i64>(shl[i], sh[i] / inc[i]));
            else k = std::min<i64>(k, (hp[i] - 1) / inc[i]);
        }
        for (unsigned q = after & live; q && k > 0; q &= q - 1) {   // the double turn's kill check
            const int i = __builtin_ctz(q);
            const int f = focus[i];
            if (f < 0 || !(dmg_set >> f & 1u) || inc[f] <= 0) continue;
            i64 bv = 0;
            for (int s = 0; s < 2; ++s) {
                const Abil& a = U[i].ab[s];
                bv = std::max(bv, a.kind == K_RESET ? basic[i] : (a.kind == K_DAMAGE || a.kind == K_AOE || a.kind == K_CC) ? a.amt : (i64)0);
            }
            const i64 room = hp[f] + (shl[f] > 0 ? sh[f] : 0) - (basic[i] + bv) - 1;
            k = std::min<i64>(k, room > 0 ? room / inc[f] : 0);
        }
        if (k <= 0) return;
        for (unsigned q = dmg_set & live; q; q &= q - 1) {
            const int i = __builtin_ctz(q);
            if (shl[i] > 0 && sh[i] > 0) sh[i] -= inc[i] * k;   // fully absorbed each round
            else hp[i] -= inc[i] * k;
        }
        for (unsigned q = shielded & live; q; q &= q - 1) {
            const int i = __builtin_ctz(q);
            shl[i] -= static_cast<int>(k);
            if (shl[i] <= 0) { shl[i] = 0; sh[i] = 0; shielded &= ~(1u << i); }
        }
        r += static_cast<int>(k);
        rounds = r;
    }
    void run() {
        for (; r <= horizon; ++r) {
            if (!alive[0] || !alive[1]) break;
            pre = r == 0;
            if (refocus) {
                for (unsigned q = live; q; q &= q - 1) {
                    const int i = __builtin_ctz(q);
                    if (focus[i] < 0 || !(live >> focus[i] & 1u)) pick_focus(i);
                }
                refocus = false;
                far_possible = true;
            }
            if (far_possible && !pre && jumps) {
                for (unsigned q = live; q && far_possible; q &= q - 1) far_possible = dist[__builtin_ctz(q)] > far_d;
                if (far_possible && far_jump()) continue;
            }
            acted = died = dmg_set = 0;
            moved_any = cast_any = stun_any = false;
            // (Experiment switch, off by default -- the user's model has ours acting first: config::FIGHT_THEY_FIRST.)
            const unsigned order[3] = {pre ? 0u : (they_first ? side_of[1] : before), pre ? 0u : (they_first ? before : side_of[1]), after};
            for (int b = 0; b < 3; ++b)
                for (unsigned q = order[b] & live; q; q &= q - 1) {
                    const int i = __builtin_ctz(q);
                    if (!(live >> i & 1u)) continue;
                    acted |= 1u << i;   // (read by stun() for the other units only)
                    act(i);
                    if (!alive[0] || !alive[1]) break;
                }
            for (unsigned q = shielded & live & (pre ? acted : ~0u); q; q &= q - 1) {
                const int i = __builtin_ctz(q);
                if (--shl[i] == 0) { sh[i] = 0; shielded &= ~(1u << i); }
            }
            rounds = r;
            if (jumps && !pre && !moved_any && !cast_any && !stun_any && !died && r < horizon) repeat_jump();
        }
    }
};

inline void Battle::run_line(int horizon, bool jumps) {
    static LineSim L;
    L.load(n, u, dead, horizon, jumps, first_death, rounds);
    L.run();
    L.store(n, u, dead, first_death, rounds);
}

}  // namespace simcore
