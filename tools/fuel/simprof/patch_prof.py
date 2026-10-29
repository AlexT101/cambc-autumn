import sys, pathlib
src = pathlib.Path(sys.argv[1])

def edit(rel, pairs):
    p = src / rel
    t = p.read_bytes().decode()
    crlf = '\r\n' in t
    t = t.replace('\r\n', '\n')
    for old, new, *cnt in pairs:
        n = t.count(old)
        want = cnt[0] if cnt else 1
        if n != want:
            sys.exit(f'{rel}: {n} matches for {old[:60]!r}')
        t = t.replace(old, new)
    if crlf:
        t = t.replace('\n', '\r\n')
    p.write_bytes(t.encode())

edit('model/safety.h', [
    ('class Safety;\n', 'class Safety;\nextern int prof_tag;\nvoid prof_count(int tag, int what);\nvoid prof_flush(unsigned long long decide);\n'),
])

edit('model/safety.cc', [
    # fighter id
    ('    int link;          // Cassi or Issac: the other body, which dies with this one\n};',
     '    int link;          // Cassi or Issac: the other body, which dies with this one\n    int id;\n};'),
    ('constinit Fighters made_fighters;\n',
     '''constinit Fighters made_fighters;
} // namespace
int prof_tag = 0;
namespace {
int prof_acts = 0, prof_quiet = 0;
struct ProfF { signed char id, arr, r0, r1; float hp, sh, str; };
struct ProfSim { int tag, fuel, acts, quiet, we, they; bool falls, tf, plain_u, plain_t; float camp; int nu, nt; std::array<ProfF, 12> f; };
std::array<ProfSim, 48> prof_sims;
int prof_n = 0;
std::array<std::array<int, 4>, 16> prof_counts{}; // per tag: asked-settled, memo, simulated, other
long prof_bytes = 0;
signed char clampc(int v) { return static_cast<signed char>(v > 100 ? 100 : v); }
void prof_snap(ProfSim& r, const Side& us, const Side& them) {
    r.nu = us.count; r.nt = them.count; r.camp = us.camp; r.plain_u = us.plain; r.plain_t = them.plain;
    int k = 0;
    for (const Side* s : {&us, &them})
        for (int i = 0; i < s->count && k < 12; ++i, ++k) {
            const auto& f = s->fighters[i];
            r.f[k] = {static_cast<signed char>(f.id), clampc(f.arrives_at), clampc(f.ready_at[0]), clampc(f.ready_at[1]), f.health, f.shield, f.strength};
        }
}
} // namespace
void prof_count(int tag, int what) { ++prof_counts[tag & 15][what & 3]; }
void prof_flush(unsigned long long decide) {
    debug_block({
        long simfuel = 0;
        for (int i = 0; i < std::min(prof_n, 48); ++i) simfuel += prof_sims[i].fuel;
        bool any = prof_n > 0;
        for (auto& c : prof_counts) for (int v : c) any |= v != 0;
        if (any && prof_bytes < 950000) {
            prof_bytes += std::printf("PT %d %u %llu %d %ld C", cambc::round_number(), static_cast<unsigned>(cambc::self()), decide, prof_n, simfuel);
            for (int t = 0; t < 16; ++t)
                if (prof_counts[t][0] | prof_counts[t][1] | prof_counts[t][2] | prof_counts[t][3])
                    prof_bytes += std::printf(" %d:%d/%d/%d/%d", t, prof_counts[t][0], prof_counts[t][1], prof_counts[t][2], prof_counts[t][3]);
            prof_bytes += std::printf("\\n");
            if (simfuel >= 8000)
                for (int i = 0; i < std::min(prof_n, 48) && prof_bytes < 950000; ++i) {
                    const auto& r = prof_sims[i];
                    prof_bytes += std::printf("PS %d %d %d %d %d %d %d %d %d%d %g |", r.tag, r.fuel, r.acts, r.quiet, r.we, r.they, r.falls, r.tf, r.plain_u, r.plain_t, r.camp);
                    for (int k = 0; k < r.nu + r.nt && k < 12; ++k) {
                        if (k == r.nu) prof_bytes += std::printf(" |");
                        const auto& f = r.f[k];
                        prof_bytes += std::printf(" %d:%d:%d:%d:%g:%g:%g", f.id, f.arr, f.r0, f.r1, f.hp, f.sh, f.str);
                    }
                    prof_bytes += std::printf("\\n");
                }
        }
    });
    prof_n = 0;
    prof_counts = {};
}
namespace {
'''),
    ('float act(Side& self, Side& other) {\n    const int turn = self.turn++;',
     'float act(Side& self, Side& other) {\n    ++prof_acts;\n    const int turn = self.turn++;'),
    ('int play_quiet(Side& us, Side& them, int t, int end, bool they_first, int& ours, int& theirs) {\n',
     'int play_quiet_(Side& us, Side& them, int t, int end, bool they_first, int& ours, int& theirs);\nint play_quiet(Side& us, Side& them, int t, int end, bool they_first, int& ours, int& theirs) {\n    const int r = play_quiet_(us, them, t, end, they_first, ours, theirs);\n    prof_quiet += r - t;\n    return r;\n}\nint play_quiet_(Side& us, Side& them, int t, int end, bool they_first, int& ours, int& theirs) {\n'),
    ('''    bool unknown = false, lost_unknown = false;
    const auto [we_kill, they_kill] =''', '''    bool unknown = false, lost_unknown = false;
    ProfSim* pr = nullptr;
    debug_block({ if (prof_n < 48) { pr = &prof_sims[prof_n]; prof_snap(*pr, us, them); pr->tag = prof_tag; pr->tf = they_first; } ++prof_n; prof_acts = prof_quiet = 0; });
    const auto pf0 = fuel();
    const auto [we_kill, they_kill] ='''),
    ('''    t.falls_known = !unknown;
    t.lost_known = !lost_unknown;
''', '''    const auto pf1 = fuel();
    t.falls_known = !unknown;
    t.lost_known = !lost_unknown;
    debug_block({ if (pr) { pr->fuel = static_cast<int>(pf0 - pf1); pr->acts = prof_acts; pr->quiet = prof_quiet; pr->we = we_kill; pr->they = they_kill; pr->falls = t.self_falls; } });
'''),
    ('Trade Safety::fight(vec2 p, bool falls) {\n', 'Trade Safety::fight(vec2 p, bool falls) {\n    prof_tag = 8;\n'),
    ('                          std::uint32_t late) {\n    world_.throw_if_stale();\n',
     '                          std::uint32_t late) {\n    prof_tag = 7;\n    world_.throw_if_stale();\n'),
    ('''    const auto before = fuel();
    const auto t = trade(us, them, end_reserve, true, falls, falls);''', '''    const auto before = fuel();
    prof_tag = 6;
    const auto t = trade(us, them, end_reserve, true, falls, falls);'''),
    ('Trade Safety::stand(vec2 p, int approach, bool falls, bool unseen, int joined) {\n',
     'Trade Safety::stand(vec2 p, int approach, bool falls, bool unseen, int joined) {\n    prof_tag = 2;\n'),
    ('''    us.camp = camp / world_.me().taken;
    // With nobody in reach yet, we strike first: they must still win.
''', '''    us.camp = camp / world_.me().taken;
    prof_tag = 1;
    // With nobody in reach yet, we strike first: they must still win.
'''),
    ('    if (them.count == 0 && us.camp <= 0) return 0;\n', '    if (them.count == 0 && us.camp <= 0) return 0;\n    prof_tag = 9;\n'),
])

# fighter id in make_slot: set after every make_fighter there
edit('model/safety.cc', [
    ('[[gnu::noinline]] void make_slot(const World& world, const ChampionBelief& c, int slot) {\n    auto& m = made_fighters;\n',
     '[[gnu::noinline]] void make_slot_(const World& world, const ChampionBelief& c, int slot);\n[[gnu::noinline]] void make_slot(const World& world, const ChampionBelief& c, int slot) {\n    make_slot_(world, c, slot);\n    made_fighters.fighter[slot].id = slot;\n}\n[[gnu::noinline]] void make_slot_(const World& world, const ChampionBelief& c, int slot) {\n    auto& m = made_fighters;\n'),
])

# guard tags and counts: 3 U1, 4 U2, 5 tile. counts: 0 settled by cover, 1 memo, 2 simulated
edit('combat/guard.cc', [
    ('''        if (known) {
            lost = known->lost;''', '''        prof_count(prof_tag, known ? 1 : 2);
        if (known) {
            lost = known->lost;'''),
    ('''        if (const int k = settle(key); k == 0 || k == 1) {
            lost = falls = k == 1;
            return true;''', '''        if (const int k = settle(key); k == 0 || k == 1) {
            prof_count(prof_tag, 0);
            lost = falls = k == 1;
            return true;'''),
    ('''    if (m > 1) {
        if (!outcome(enemies | allies, lost, falls)) return nullptr;''', '''    prof_tag = 3;
    if (m > 1) {
        if (!outcome(enemies | allies, lost, falls)) return nullptr;'''),
    ('''    note_placing();
    if (m == 0) return nullptr;
    if (m > 1 &&''', '''    note_placing();
    if (m == 0) return nullptr;
    prof_tag = 4;
    if (m > 1 &&'''),
    ('''    bool any = false;
    for (int i = 0; i < m; ++i) {
        const auto [q, key] = exposed[i];
        const int k = settle(key);''', '''    bool any = false;
    prof_tag = 5;
    for (int i = 0; i < m; ++i) {
        const auto [q, key] = exposed[i];
        const int k = settle(key);
        if (k == 0 || k == 1) prof_count(5, 0); else if (k == 2) prof_count(5, 3);'''),
])

edit('main.cc', [
    ('''            aph::play_turn(*world, *pathing, memory);
        });
''', '''            aph::play_turn(*world, *pathing, memory);
        });
        aph::prof_flush(prof_f0 - aph::fuel());
'''),
    ('''        run("decide", [&] {''', '''        const auto prof_f0 = aph::fuel();
        run("decide", [&] {'''),
])
print('ok')
