// probe-ward-bush: do wards follow the bush sight rules, what does sdk_ward_vision return, and what do sdk_wards'
// fields hold?
// Self-play. Both sides compute the same bush tile T (in a cluster of 2+ tiles, nearest both spawns).
//   Round 1: each side's first champion compares sdk_ward_vision at every tile on or within 2 of a bush with two
//   models: walls alone opaque, and the bush rules (walls and every other cluster opaque, other clusters unseen). It
//   logs mismatches, a checksum of the masks (equal on both sides if the mask ignores the observer) and fuel prices.
//   B's Ryth walks onto T and stays. A's Stellar walks to S (off-bush, within 3 of T) and waits.
//   TEST: A wards W (off-bush, within 2 of S, T in its walls-only sight) and logs the Ryth's visibility and the
//   tiles the ward added against both models. TEST+3: B wards an off-bush tile Bw within 2 of T. TEST+5: A logs
//   sdk_wards. TEST+12: A wards Wb (a bush tile within 2 of S) and logs the same.
//   A's other champions, at spawn, log sdk_wards on TEST+5 and TEST+13.
//   cambc run tools/probes/probe-ward-bush tools/probes/probe-ward-bush \
//     --map 00ambush --rounds 216 --fuel 50000000 -o <dir>
// Result (00ambush, 2026-10-22):
//   - Wards follow the bush rules. The off-bush ward at W added 1 tile, all inside the bush model, and neither T nor
//     the Ryth in it (12 tiles of its walls-only sight stayed unseen); the ward on a bush (Wb) revealed its cluster, T
//     and the Ryth (58 tiles, all inside the bush model).
//   - sdk_ward_vision matches the bush model at all 684 tiles surveyed (552 off bushes, 132 on), and the walls-only
//     model at none; it holds the ward's own tile, no walls, and is the same from both teams (checksums equal). It
//     equals the sight the ward actually added. ~348 fuel a call; sdk_enemy_ward_occupancy ~177.
//   - sdk_wards lists the wards of both teams in the caller's own sight only (its own position and its own ward):
//     A's champions at spawn listed none, not even their teammate's ward. Fields: team (absolute), position,
//     timer -1, disabled 0, owner = the owning champion's handle. ~14 fuel with none, ~20 with two.
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <string>
#include <vector>

using cambc::bitboard;
using cambc::team;
using cambc::vec2;
namespace m = cambc::map;
namespace v = cambc::vision;
namespace d = cambc::detail;
using D = cambc::champion_draft;

namespace {

constexpr int TEST = 200;
constexpr int R6 = 6;

int R() { return (int)cambc::round_number(); }
int cheb(vec2 a, vec2 b) { return std::max(std::abs(a.x - b.x), std::abs(a.y - b.y)); }
std::string P(vec2 p) { return "(" + std::to_string(p.x) + "," + std::to_string(p.y) + ")"; }
bool on_map(vec2 t) { return t.x >= 0 && t.y >= 0 && t.x < m::width() && t.y < m::height(); }

char side = 0;
std::string role;

void L(const std::string& s) {
    std::printf("PROBE %d %c %s %s %s\n", R(), side, cambc::to_string(cambc::self().champion_name()).c_str(), role.c_str(), s.c_str());
}

char find_side() {
    const vec2 a = m::spawn_region(team::ally).positions().front(), e = m::spawn_region(team::enemy).positions().front();
    return (a.x < e.x || (a.x == e.x && a.y < e.y)) ? 'A' : 'B';
}

vec2 centre(const bitboard& b) {
    long sx = 0, sy = 0, n = 0;
    for (auto p : b.positions()) sx += p.x, sy += p.y, ++n;
    return { (int)(sx / n), (int)(sy / n) };
}

bool camp_tile(vec2 t) {
    for (const auto& g : m::camp_groups())
        for (const auto& c : g)
            if (c.spawn_position() == t) return true;
    return false;
}

bool standable(vec2 t) {
    return on_map(t) && !m::walls().is_set(t) && !m::holes().is_set(t) && !m::altars().is_set(t) && !camp_tile(t) &&
           !m::spawn_region(team::ally).is_set(t) && !m::spawn_region(team::enemy).is_set(t);
}

bitboard cluster_of(vec2 t) {
    bitboard out;
    out.set(t);
    std::deque<vec2> q{ t };
    const vec2 dirs[] = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } };
    const auto bushes = m::bushes();
    while (!q.empty()) {
        const vec2 c = q.front();
        q.pop_front();
        for (auto dd : dirs) {
            const vec2 n{ c.x + dd.x, c.y + dd.y };
            if (!on_map(n) || !bushes.is_set(n) || out.is_set(n)) continue;
            out.set(n);
            q.push_back(n);
        }
    }
    return out;
}

bitboard model_walls(vec2 w) { return m::walls().shadow_cast(w, R6) & ~m::walls(); }

// The bush rules: walls and every cluster but the viewer's own opaque; other clusters' tiles unseen.
bitboard model_bush(vec2 w) {
    const auto bushes = m::bushes(), walls = m::walls();
    bitboard others = bushes;
    if (bushes.is_set(w)) others = bushes & ~cluster_of(w);
    return (walls | others).shadow_cast(w, R6) & ~walls & ~others;
}

bitboard engine_mask(vec2 w) {
    bitboard out{ cambc::uninitialized };
    d::check(d::sdk_ward_vision(w.x, w.y, out.ptr()));
    return out;
}

std::string wards_dump() {
    d::ward_info raw[16]{};
    std::uint32_t n = 0;
    const auto f0 = cambc::fuel_remaining();
    const auto code = d::sdk_wards(raw, 16, &n);
    const auto f1 = cambc::fuel_remaining();
    std::string s = "sdk_wards code=" + std::to_string(code) + " n=" + std::to_string(n) + " fuel=" + std::to_string(f0 - f1) +
                    " my_team=" + std::to_string(d::sdk_my_team()) + " [";
    for (std::uint32_t i = 0; i < n && i < 16; ++i)
        s += " {team=" + std::to_string(raw[i].team) + " pos=" + P({ raw[i].x, raw[i].y }) + " timer=" + std::to_string(raw[i].timer) +
             " disabled=" + std::to_string(raw[i].disabled) + " owner=" + std::to_string(raw[i].owner) + "}";
    s += " ] handles ally=";
    for (const auto& c : cambc::champions(team::ally)) s += std::to_string((std::uint32_t)static_cast<cambc::handle_champion_t>(c)) + ",";
    s += " enemy=";
    for (const auto& c : cambc::champions(team::enemy)) s += std::to_string((std::uint32_t)static_cast<cambc::handle_champion_t>(c)) + ",";
    return s;
}

void survey() {
    const auto bushes = m::bushes(), walls = m::walls();
    bitboard near = bushes;
    for (auto b : bushes.positions())
        for (int dy = -2; dy <= 2; ++dy)
            for (int dx = -2; dx <= 2; ++dx)
                if (on_map({ b.x + dx, b.y + dy })) near.set({ b.x + dx, b.y + dy });
    near &= ~walls;
    int n = 0, off_bush = 0, on_bush = 0, mis_bush = 0, mis_walls = 0, has_walls = 0, has_self = 0;
    std::uint64_t sum = 0;
    std::string first_bush, first_walls;
    for (auto p : near.positions()) {
        const auto e = engine_mask(p);
        ++n;
        (bushes.is_set(p) ? on_bush : off_bush)++;
        for (auto q : e.positions()) sum = sum * 1000003u + (std::uint64_t)(q.x * 128 + q.y + 1);
        if (!(e & walls).is_empty()) ++has_walls;
        if (e.is_set(p)) ++has_self;
        const auto eo = e & ~walls;
        const auto db = eo ^ model_bush(p), dw = eo ^ model_walls(p);
        if (!db.is_empty()) {
            ++mis_bush;
            if (first_bush.empty())
                first_bush = P(p) + " bush=" + std::to_string(bushes.is_set(p)) + " engine_only=" + std::to_string((eo & db).count()) +
                             " model_only=" + std::to_string((db & ~eo).count());
        }
        if (!dw.is_empty()) {
            ++mis_walls;
            if (first_walls.empty())
                first_walls = P(p) + " bush=" + std::to_string(bushes.is_set(p)) + " engine_only=" + std::to_string((eo & dw).count()) +
                              " model_only=" + std::to_string((dw & ~eo).count());
        }
    }
    L("survey tiles=" + std::to_string(n) + " off_bush=" + std::to_string(off_bush) + " on_bush=" + std::to_string(on_bush) +
      " mismatch_bush_model=" + std::to_string(mis_bush) + " mismatch_walls_model=" + std::to_string(mis_walls) +
      " masks_with_walls=" + std::to_string(has_walls) + " masks_with_own_tile=" + std::to_string(has_self) + " checksum=" + std::to_string(sum));
    L("first_bush_mismatch " + first_bush);
    L("first_walls_mismatch " + first_walls);
    bitboard out{ cambc::uninitialized };
    const vec2 p = near.positions().front();
    const auto f0 = cambc::fuel_remaining();
    (void)d::sdk_ward_vision(p.x, p.y, out.ptr());
    const auto f1 = cambc::fuel_remaining();
    (void)d::sdk_enemy_ward_occupancy(out.ptr());
    const auto f2 = cambc::fuel_remaining();
    L("fuel sdk_ward_vision=" + std::to_string(f0 - f1) + " sdk_enemy_ward_occupancy=" + std::to_string(f1 - f2));
}

vec2 T{ -1, -1 }, S{ -1, -1 }, W{ -1, -1 }, Wb{ -1, -1 }, Bw{ -1, -1 };

void choose() {
    vec2 sa = centre(m::spawn_region(team::ally)), sb = centre(m::spawn_region(team::enemy));
    if (side == 'B') std::swap(sa, sb);
    const auto bushes = m::bushes();
    int best = 1 << 30;
    for (auto t : bushes.positions()) {
        if (!standable(t) || cluster_of(t).count() < 2) continue;
        vec2 s{ -1, -1 }, w{ -1, -1 }, wb{ -1, -1 };
        for (int dy = -3; dy <= 3 && s.x < 0; ++dy)
            for (int dx = -3; dx <= 3 && s.x < 0; ++dx) {
                const vec2 c{ t.x + dx, t.y + dy };
                if (!standable(c) || bushes.is_set(c)) continue;
                vec2 cw{ -1, -1 }, cb{ -1, -1 };
                for (int ey = -2; ey <= 2; ++ey)
                    for (int ex = -2; ex <= 2; ++ex) {
                        const vec2 q{ c.x + ex, c.y + ey };
                        if (!standable(q) || q == c) continue;
                        if (!bushes.is_set(q) && cw.x < 0 && model_walls(q).is_set(t) && !model_bush(q).is_set(t)) cw = q;
                        if (bushes.is_set(q) && cb.x < 0) cb = q;
                    }
                if (cw.x >= 0 && cb.x >= 0) s = c, w = cw, wb = cb;
            }
        if (s.x < 0) continue;
        const int score = std::max(cheb(t, sa), cheb(t, sb)) * 10000 + t.x * 100 + t.y;
        if (score < best) best = score, T = t, S = s, W = w, Wb = wb;
    }
    int bd = 1 << 30;
    for (int dy = -2; dy <= 2; ++dy)
        for (int dx = -2; dx <= 2; ++dx) {
            const vec2 q{ T.x + dx, T.y + dy };
            if (T.x < 0 || !standable(q) || bushes.is_set(q) || q == S) continue;
            if (cheb(q, S) < bd) bd = cheb(q, S), Bw = q;
        }
}

std::string attempt(const char* what, auto&& f) {
    try { return std::string(what) + "=" + (f() ? "true" : "false"); }
    catch (const cambc::error& e) { return std::string(what) + "=throw:" + cambc::to_string(e.code()); }
}

std::string ryth() {
    for (auto& e : cambc::champions(team::enemy))
        if (e.champion_name() == cambc::champion_type::ryth) {
            std::string s = "ryth.visible=" + std::to_string(e.is_visible());
            try { s += " ryth.pos=" + P(e.position()); }
            catch (const cambc::error& x) { s += std::string(" ryth.read=throw:") + cambc::to_string(x.code()); }
            return s;
        }
    return "no_ryth";
}

void ward_and_check(vec2 at) {
    const auto before = v::visible_tiles();
    L("before " + ryth() + " T_visible=" + std::to_string(before.is_set(T)));
    L(attempt("place_ward", [&] { return cambc::self().place_ward(at); }) + " at=" + P(at) + " bush=" + std::to_string(m::bushes().is_set(at)));
    const auto after = v::visible_tiles();
    const auto mb = model_bush(at), mw = model_walls(at), e = engine_mask(at) & ~m::walls();
    const auto gained = after & ~before;
    L("after " + ryth() + " T_visible=" + std::to_string(after.is_set(T)) + " gained=" + std::to_string(gained.count()) +
      " gained_outside_bush_model=" + std::to_string((gained & ~mb).count()) + " bush_model_unseen=" + std::to_string((mb & ~after).count()) +
      " walls_model_unseen=" + std::to_string((mw & ~after).count()) + " gained_bush_tiles=" + std::to_string((gained & m::bushes()).count()) +
      " engine_mask_unseen=" + std::to_string((e & ~after).count()) + " gained_outside_engine_mask=" + std::to_string((gained & ~e).count()));
}

void play() {
    auto& me = cambc::self();
    const int r = R();
    if (role.empty()) {
        side = find_side();
        choose();
        const bool first = cambc::champions(team::ally).front() == me;
        role = side == 'A' ? (me.champion_name() == cambc::champion_type::stellar ? "watcher" : "idle")
                           : (me.champion_name() == cambc::champion_type::ryth ? "hider" : "idle");
        if (first) survey();
        if (first || role != "idle")
            L("init pos=" + P(me.position()) + " T=" + P(T) + " S=" + P(S) + " W=" + P(W) + " Wb=" + P(Wb) + " Bw=" + P(Bw));
    }
    if (role == "idle" && side == 'A' && (r == TEST + 5 || r == TEST + 13))
        L("far " + wards_dump() + " pos=" + P(me.position()) + " visible(W)=" + std::to_string(v::visible_tiles().is_set(W)) +
          " visible(Bw)=" + std::to_string(v::visible_tiles().is_set(Bw)));
    if (!me.is_alive() || role == "idle" || T.x < 0) return;
    if (role == "hider") {
        if (me.position() != T && me.can_move()) {
            try { me.move_towards(T); } catch (const cambc::error&) {}
        }
        if (r == TEST + 3) {
            L(attempt("place_ward", [&] { return me.place_ward(Bw); }) + " at=" + P(Bw) + " pos=" + P(me.position()));
            L(wards_dump());
        }
    } else {
        if (r < TEST - 5 && me.position() != S && me.can_move()) {
            try { me.move_towards(S); } catch (const cambc::error&) {}
        }
        if (r == TEST) {
            L("at_S=" + std::to_string(me.position() == S));
            ward_and_check(W);
            L(wards_dump());
        }
        if (r == TEST + 5) {
            L(wards_dump() + " Bw_visible=" + std::to_string(v::visible_tiles().is_set(Bw)));
            const auto e = engine_mask(Bw) & ~m::walls();
            L("enemy ward mask at Bw: vs_bush_model=" + std::to_string((e ^ model_bush(Bw)).count()) +
              " vs_walls_model=" + std::to_string((e ^ model_walls(Bw)).count()));
        }
        if (r == TEST + 12) {
            ward_and_check(Wb);
            L(wards_dump());
        }
    }
}

void play_draft() {
    side = find_side();
    const auto mine = cambc::draft::current_draft(team::ally);
    auto have = [&](D dd) { return std::find(mine.begin(), mine.end(), dd) != mine.end(); };
    std::vector<D> pref = side == 'A' ? std::vector<D>{ D::stellar, D::willow, D::prism, D::tavi, D::marcella }
                                      : std::vector<D>{ D::ryth, D::varg, D::ren, D::marcella, D::willow };
    for (auto dd : pref)
        if (!have(dd)) { cambc::draft::pick(dd); return; }
}

} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else play();
        } catch (const cambc::error& e) {
            std::printf("PROBE %d err %s\n", R(), e.message().c_str());
        } catch (const std::exception& e) { std::printf("PROBE %d err %s\n", R(), e.what()); }
        cambc::end_turn();
    }
}
