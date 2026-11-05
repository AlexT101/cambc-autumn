"""mkprof.py SRC DST: bots/DST = bots/SRC + MK lines: per farm loop, which memo keys moved and by which input,
and per fact block the recomputes, their fuel and whether they gave the same values (debug_block only)."""
import shutil, subprocess, sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
src, dst = root / "bots" / sys.argv[1], root / "bots" / sys.argv[2]
if dst.exists():
    shutil.rmtree(dst)
shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".cambc", "build", "target", ".cache", "compile_commands.json"))
f = dst / "src/economy/farm.cc"
s = f.read_text()


def rep(a, b, count=1):
    global s
    assert s.count(a) == count, (s.count(a), a)
    s = s.replace(a, b)


# Inputs at each fact's last compute, for the reasons.
rep("""    float damage = 0, rounds = 0, kite = -1;
};""", """    float damage = 0, rounds = 0, kite = -1;
    int p_bag = 0, p_short = 0, p_banking = 0, p_emblems = 0, p_sticky = 0;
    float p_per_gold = 0, p_trib = 0, p_str = 0, p_ref = 0, p_spl = 0, p_bas = 0, p_surv = 0;
    int p_range = 0, p_clr_set = 0, p_ctx_set = 0, p_gold_set = 0;
    int p_tt = 0, p_minsb = 0, p_wins = 0;
};
struct MKP {
    int ctx_mask = 0, gold_mask = 0, clr_mask = 0, first = 0;
    int o_bag = 0, n_bag = 0, o_short = 0, n_short = 0;
    float o_str = 0, n_str = 0, o_ref = 0, n_ref = 0, o_spl = 0, n_spl = 0, o_bas = 0, n_bas = 0, o_pg = 0, n_pg = 0, o_tg = 0, n_tg = 0;
    std::uint64_t loop_start = 0, t0 = 0, t1 = 0;
    int n_ctx = 0, same_ctx = 0, n_gold = 0, same_gold = 0, n_fast = 0, same_fast = 0, n_kf = 0, n_clr = 0, same_dmg = 0, same_kite = 0, n_kite = 0;
    std::uint64_t f_ctx = 0, f_gold = 0, f_fast = 0, f_kf = 0, f_clr = 0, f_dmg = 0, f_kite = 0;
    // reasons: input bits moved since the group's last compute, by same (1) or not (0)
    int ctx_r[64][2]{}, gold_r[8][2]{}, clr_r[256][2]{};
    std::uint64_t ctx_rf[64]{}, clr_rf[256]{};
    int ctx_fine = 0; // recomputes whose finer inputs (wins, min(gems,short_by), tribute_turns(bag+gems), banks, emblems, sticky) held
    GroupFacts old{};
    bool hit = false;
};
inline MKP& mkp() {
    static MKP p;
    return p;
}""")

rep("""    auto& last_context = memo.last_context;
    auto& context = memo.context;
""", """    debug_block({
        MKP& P = mkp();
        P = MKP{};
        const auto& L = memo.last_context;
        P.first = memo.context == 0;
        P.ctx_mask = (L.bag != bag) | (L.short_by != short_by) << 1 | (L.banking != banks_bag) << 2 | (L.emblems != emblems) << 3;
        P.o_bag = L.bag, P.n_bag = bag, P.o_short = L.short_by, P.n_short = short_by;
    });
    auto& last_context = memo.last_context;
    auto& context = memo.context;
""")
rep("""    if (gold_context == 0 || per_gold != last_per_gold || tribute_gold != last_tribute_gold)
""", """    debug_block({
        MKP& P = mkp();
        P.gold_mask = (per_gold != last_per_gold) | (tribute_gold != last_tribute_gold) << 1;
        P.o_pg = last_per_gold, P.n_pg = per_gold, P.o_tg = last_tribute_gold, P.n_tg = tribute_gold;
    });
    if (gold_context == 0 || per_gold != last_per_gold || tribute_gold != last_tribute_gold)
""")
rep("""    if (const FarmClearing now{strength, reflect, spells, basic, range}; clearing == 0 || !(now == last_clearing))
""", """    debug_block({
        MKP& P = mkp();
        const auto& L = last_clearing;
        P.clr_mask = (L.strength != strength) | (L.reflect != reflect) << 1 | (L.spells != spells) << 2 | (L.basic != basic) << 3 | (L.range != range) << 4;
        P.o_str = L.strength, P.n_str = strength, P.o_ref = L.reflect, P.n_ref = reflect, P.o_spl = L.spells, P.n_spl = spells, P.o_bas = L.basic, P.n_bas = basic;
    });
    if (const FarmClearing now{strength, reflect, spells, basic, range}; clearing == 0 || !(now == last_clearing))
""")
rep("""    int k = 0;
    for (; k < evaluated && room(); ++k) {
""", """    int k = 0;
    debug_block({ mkp().loop_start = fuel(); mkc() = MKC{}; });
    for (; k < evaluated && room(); ++k) {
""")
# Pre-facts kf fallback and fastest.
rep("""                    float fastest;
                    if (kf.version == belief.version && kf.fastest_strength == strength) fastest = kf.fastest;
                    else if (belief.version == 0) fastest = group.health / strength;
                    else kf.version = belief.version, kf.fastest_strength = strength, fastest = kf.fastest = fastest_clear(world, g, strength);
""", """                    float fastest;
                    debug_block({ mkp().t0 = fuel(); mkp().hit = !(kf.version == belief.version && kf.fastest_strength == strength) && belief.version != 0; mkp().old = kf; });
                    if (kf.version == belief.version && kf.fastest_strength == strength) fastest = kf.fastest;
                    else if (belief.version == 0) fastest = group.health / strength;
                    else kf.version = belief.version, kf.fastest_strength = strength, fastest = kf.fastest = fastest_clear(world, g, strength);
                    debug_block({ MKP& P = mkp(); if (P.hit) { P.n_kf++; P.f_kf += P.t0 - fuel(); } });
""")
rep("""        auto& known = group_facts[g];
        if (known.context != context || known.sticky != (g == farm_group)) {
""", """        auto& known = group_facts[g];
        debug_block({ MKP& P = mkp(); P.t0 = fuel(); P.hit = known.context != context || known.sticky != (g == farm_group); P.old = known; });
        if (known.context != context || known.sticky != (g == farm_group)) {
""")
rep("""            known.context = context;
            known.sticky = g == farm_group;
            known.gold_context = 0;
        }
        if (known.gold_context != gold_context) {
""", """            known.context = context;
            known.sticky = g == farm_group;
            known.gold_context = 0;
        }
        debug_block({
            MKP& P = mkp();
            if (P.hit) {
                const auto& o = P.old;
                const std::uint64_t spent = P.t0 - fuel();
                P.n_ctx++, P.f_ctx += spent;
                const bool same = o.p_ctx_set && o.walk == known.walk && o.chained_tribute == known.chained_tribute && o.tribute == known.tribute
                                  && o.gold_in == known.gold_in && o.weight == known.weight && o.gems == known.gems && o.walked_bank == known.walked_bank
                                  && o.walked_cycle == known.walked_cycle;
                P.same_ctx += same;
                const int m = !o.p_ctx_set ? 32 : (o.p_bag != bag) | (o.p_short != short_by) << 1 | (o.p_banking != banks_bag) << 2 | (o.p_emblems != emblems) << 3 | (o.p_sticky != (g == farm_group)) << 4;
                P.ctx_r[m][same]++;
                P.ctx_rf[m] += spent;
                const int tt = tribute_turns(world, bag + group.gems);
                const int minsb = std::min(group.gems + (prospector ? prospected(group.cluster_gems, 1) : 0), short_by);
                const int wins_now = group.gems >= short_by;
                P.ctx_fine += o.p_ctx_set && o.p_tt == tt && o.p_minsb == minsb && o.p_wins == wins_now && o.p_banking == banks_bag && o.p_emblems == emblems && o.p_sticky == (g == farm_group);
                known.p_bag = bag, known.p_short = short_by, known.p_banking = banks_bag, known.p_emblems = emblems, known.p_sticky = g == farm_group, known.p_ctx_set = 1;
                known.p_tt = tt, known.p_minsb = minsb, known.p_wins = wins_now;
            }
            P.t0 = fuel();
            P.hit = known.gold_context != gold_context;
            P.old = known;
        });
        if (known.gold_context != gold_context) {
""")
rep("""            known.gold_context = gold_context;
        }
        if (known.version != belief.version || known.fastest_strength != strength)
            known.version = belief.version, known.fastest_strength = strength, known.fastest = fastest_clear(world, g, strength);
""", """            known.gold_context = gold_context;
        }
        debug_block({
            MKP& P = mkp();
            if (P.hit) {
                const auto& o = P.old;
                P.n_gold++, P.f_gold += P.t0 - fuel();
                const bool same = o.p_gold_set && o.gold == known.gold;
                P.same_gold += same;
                const int m = !o.p_gold_set ? 4 : (o.p_per_gold != per_gold) | (o.p_trib != tribute_gold) << 1;
                P.gold_r[m][same]++;
                known.p_per_gold = per_gold, known.p_trib = tribute_gold, known.p_gold_set = 1;
            }
            P.t0 = fuel();
            P.hit = known.version != belief.version || known.fastest_strength != strength;
            P.old = known;
        });
        if (known.version != belief.version || known.fastest_strength != strength)
            known.version = belief.version, known.fastest_strength = strength, known.fastest = fastest_clear(world, g, strength);
        debug_block({ MKP& P = mkp(); if (P.hit) { P.n_fast++; P.f_fast += P.t0 - fuel(); P.same_fast += P.old.fastest == known.fastest; } });
""")
rep("""        if (known.clearing != clearing || known.clear_version != belief.version) {
            known.clearing = clearing, known.clear_version = belief.version;
            known.damage = known.rounds = 0, known.kite = -1;
            if (belief.state != CampState::cleared) {
                known.damage = min_camp_damage(world, g, strength, &known.rounds, reflect);
                if (group.strength > 0) known.kite = spell_clear_rounds(world, g, range, spells, basic);
            }
        }
""", """        debug_block({ MKP& P = mkp(); P.t0 = fuel(); P.hit = known.clearing != clearing || known.clear_version != belief.version; P.old = known; });
        if (known.clearing != clearing || known.clear_version != belief.version) {
            known.clearing = clearing, known.clear_version = belief.version;
            known.damage = known.rounds = 0, known.kite = -1;
            if (belief.state != CampState::cleared) {
                debug_block({ mkp().t1 = fuel(); });
                known.damage = min_camp_damage(world, g, strength, &known.rounds, reflect);
                debug_block({ mkp().f_dmg += mkp().t1 - fuel(); mkp().t1 = fuel(); });
                if (group.strength > 0) known.kite = spell_clear_rounds(world, g, range, spells, basic);
                debug_block({ if (group.strength > 0) { mkp().f_kite += mkp().t1 - fuel(); mkp().n_kite++; } });
            }
        }
        debug_block({
            MKP& P = mkp();
            if (P.hit) {
                const auto& o = P.old;
                const std::uint64_t spent = P.t0 - fuel();
                P.n_clr++, P.f_clr += spent;
                const bool sd = o.p_clr_set && o.damage == known.damage && o.rounds == known.rounds;
                const bool sk = o.p_clr_set && o.kite == known.kite;
                P.same_dmg += sd, P.same_kite += sk;
                const float surv = home_survivable(world.me());
                const int m = !o.p_clr_set ? 128
                                           : (o.clear_version != belief.version) | (o.p_str != strength) << 1 | (o.p_ref != reflect) << 2 | (o.p_spl != spells) << 3
                                                 | (o.p_bas != basic) << 4 | (o.p_range != range) << 5 | (o.p_surv != surv) << 6;
                P.clr_r[m][sd && sk]++;
                P.clr_rf[m] += spent;
                known.p_str = strength, known.p_ref = reflect, known.p_spl = spells, known.p_bas = basic, known.p_range = range, known.p_surv = surv, known.p_clr_set = 1;
            }
        });
""")
rep("""    if (k < evaluated) note_shortcut("farm-partial-evaluation");
""", """    debug_block({
        MKP& P = mkp();
        if (P.loop_start && !cambc::is_draft()) {
            std::printf("MK %d %u o%d b%d c%d k%d n%d L%llu cm%d gm%d km%d f%d bag%d>%d sb%d>%d str%g>%g ref%g>%g spl%g>%g bas%g>%g pg%g>%g tg%g>%g"
                        " ctx%d/%d/%llu/%d gold%d/%d/%llu fast%d/%d/%llu kf%d/%llu clr%d/%d/%d/%llu/%llu/%llu/%d",
                        cambc::round_number(), static_cast<unsigned>(static_cast<cambc::handle_champion_t>(cambc::self())), opening ? 1 : 0, banks_bag ? 1 : 0,
                        k < evaluated ? 1 : 0, k, n_groups, (unsigned long long)(P.loop_start - fuel()), P.ctx_mask, P.gold_mask, P.clr_mask, P.first,
                        P.o_bag, P.n_bag, P.o_short, P.n_short, P.o_str, P.n_str, P.o_ref, P.n_ref, P.o_spl, P.n_spl, P.o_bas, P.n_bas, P.o_pg, P.n_pg, P.o_tg, P.n_tg,
                        P.n_ctx, P.same_ctx, (unsigned long long)P.f_ctx, P.ctx_fine, P.n_gold, P.same_gold, (unsigned long long)P.f_gold,
                        P.n_fast, P.same_fast, (unsigned long long)P.f_fast, P.n_kf, (unsigned long long)P.f_kf,
                        P.n_clr, P.same_dmg, P.same_kite, (unsigned long long)P.f_clr, (unsigned long long)P.f_dmg, (unsigned long long)P.f_kite, P.n_kite);
            std::printf(" sr%llu/%d/%llu/%d", (unsigned long long)mkc().sr_f, mkc().sr_n, (unsigned long long)mkc().cf_f, mkc().cf_n);
            mkc() = MKC{};
            std::printf(" CR");
            for (int m = 0; m < 64; ++m)
                for (int q = 0; q < 2; ++q)
                    if (P.ctx_r[m][q]) std::printf(" %d:%d:%d:%llu", m, q, P.ctx_r[m][q], (unsigned long long)(q ? 0 : 0));
            std::printf(" CF");
            for (int m = 0; m < 64; ++m)
                if (P.ctx_rf[m]) std::printf(" %d:%llu", m, (unsigned long long)P.ctx_rf[m]);
            std::printf(" GR");
            for (int m = 0; m < 8; ++m)
                for (int q = 0; q < 2; ++q)
                    if (P.gold_r[m][q]) std::printf(" %d:%d:%d", m, q, P.gold_r[m][q]);
            std::printf(" KR");
            for (int m = 0; m < 256; ++m)
                for (int q = 0; q < 2; ++q)
                    if (P.clr_r[m][q]) std::printf(" %d:%d:%d", m, q, P.clr_r[m][q]);
            std::printf(" KF");
            for (int m = 0; m < 256; ++m)
                if (P.clr_rf[m]) std::printf(" %d:%llu", m, (unsigned long long)P.clr_rf[m]);
            std::printf("\\n");
        }
        P.loop_start = 0;
    });
    if (k < evaluated) note_shortcut("farm-partial-evaluation");
""")
f.write_text(s)
print("patched", f)
# Static first reads inside min_camp_damage: StandReach builds and clear_fire.
h = dst / "src/bot_parts.h"
hs = h.read_text()
hs += """
struct MKC {
    std::uint64_t sr_f = 0, cf_f = 0;
    int sr_n = 0, cf_n = 0;
};
inline MKC& mkc() {
    static MKC c;
    return c;
}
"""
h.write_text(hs)
c = dst / "src/economy/camps.cc"
s = c.read_text()
rep("""        known = stand_reach(world.map(), g, range).homes.empty() ? 1 : 2;
""", """        std::uint64_t t0 = 0;
        debug_block({ t0 = fuel(); });
        known = stand_reach(world.map(), g, range).homes.empty() ? 1 : 2;
        debug_block({ mkc().sr_f += t0 - fuel(); mkc().sr_n++; });
""")
rep("""            clear_fire(world.map(), g, sorted, living, range);
""", """            std::uint64_t t0 = 0;
            debug_block({ t0 = fuel(); });
            clear_fire(world.map(), g, sorted, living, range);
            debug_block({ mkc().cf_f += t0 - fuel(); mkc().cf_n++; });
""")
c.write_text(s)
print("patched", c)
