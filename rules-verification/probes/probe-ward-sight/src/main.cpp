// probe-ward-sight: does a ward's sight count on the turn it is placed?
// Self-play. Both sides compute the same bush tile T (in a cluster of 2+ tiles, nearest both spawns).
//   B's Ryth walks onto T and stays; inside the bush it is unseen from outside the cluster.
//   A's Stellar walks to a non-bush tile S within 3 of T and within 2 of another tile W of T's cluster, then waits.
//   On round TEST (no walk that turn) it logs whether it sees T and the Ryth, wards W, logs again, then basic attacks
//   the Ryth and casts Stellar's unit spell at it. B logs its health every turn. TEST+1 logs sight again.
//   cambc run rules-verification/probes/probe-ward-sight rules-verification/probes/probe-ward-sight \
//     --map 00ambush --rounds 220 --fuel 50000000 -o <dir>
// Result (00ambush, 01the-farm): before the ward T and the Ryth are unseen (reading it throws api_not_in_vision); right
// after place_ward both are visible, and the attack and cast both land (1200 -> 1030 = 30 + 2 x 70).
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <string>
#include <vector>

using cambc::team;
using cambc::vec2;
namespace m = cambc::map;
namespace v = cambc::vision;
using D = cambc::champion_draft;

namespace {

constexpr int TEST = 200;

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

vec2 centre(const cambc::bitboard& b) {
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

std::vector<vec2> cluster_of(vec2 t) {
    std::vector<vec2> out{ t };
    std::deque<vec2> q{ t };
    const vec2 dirs[] = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } };
    while (!q.empty()) {
        const vec2 c = q.front();
        q.pop_front();
        for (auto d : dirs) {
            const vec2 n{ c.x + d.x, c.y + d.y };
            if (!on_map(n) || !m::bushes().is_set(n) || std::find(out.begin(), out.end(), n) != out.end()) continue;
            out.push_back(n);
            q.push_back(n);
        }
    }
    return out;
}

vec2 T{ -1, -1 }, W{ -1, -1 }, S{ -1, -1 };

// T, W and S from map data only, so both sides agree on T.
void choose() {
    vec2 sa = centre(m::spawn_region(team::ally)), sb = centre(m::spawn_region(team::enemy));
    if (side == 'B') std::swap(sa, sb);
    int best = 1 << 30;
    for (auto t : m::bushes().positions()) {
        if (!standable(t)) continue;
        const auto c = cluster_of(t);
        if (c.size() < 2) continue;
        // S: non-bush, within 3 of T and 2 of some W != T in the cluster.
        vec2 s{ -1, -1 }, w{ -1, -1 };
        for (int dy = -3; dy <= 3 && s.x < 0; ++dy)
            for (int dx = -3; dx <= 3 && s.x < 0; ++dx) {
                const vec2 cand{ t.x + dx, t.y + dy };
                if (!standable(cand) || m::bushes().is_set(cand)) continue;
                for (auto x : c)
                    if (x != t && cheb(x, cand) <= 2 && (w.x < 0 || cheb(x, t) < cheb(w, t))) w = x;
                if (w.x >= 0) s = cand;
            }
        if (s.x < 0) continue;
        const int score = std::max(cheb(t, sa), cheb(t, sb)) * 10000 + t.x * 100 + t.y;
        if (score < best) best = score, T = t, W = w, S = s;
    }
}

std::string attempt(const char* what, auto&& f) {
    try { return std::string(what) + "=" + (f() ? "true" : "false"); }
    catch (const cambc::error& e) { return std::string(what) + "=throw:" + cambc::to_string(e.code()); }
}

const cambc::champion* enemy_ryth(std::vector<cambc::champion>& es) {
    for (auto& e : es)
        if (e.champion_name() == cambc::champion_type::ryth) return &e;
    return nullptr;
}

std::string sight() {
    auto es = cambc::champions(team::enemy);
    const auto* e = enemy_ryth(es);
    std::string s = "pos=" + P(cambc::self().position()) + " in_vision(T)=" + std::to_string(v::in_vision(T)) +
                    " visible_tiles(T)=" + std::to_string(v::visible_tiles().is_set(T)) +
                    " self_vis(T)=" + std::to_string(cambc::self().visible_tiles().is_set(T)) + " wards=[";
    for (auto p : cambc::self().ward_positions()) s += P(p);
    s += "]";
    if (!e) return s + " no_enemy_ryth";
    s += " ryth.is_visible=" + std::to_string(e->is_visible());
    try { s += " ryth.pos=" + P(e->position()) + " ryth.hp=" + std::to_string(e->health()); }
    catch (const cambc::error& x) { s += std::string(" ryth.read=throw:") + cambc::to_string(x.code()); }
    return s;
}

bool acted = false;

void play() {
    auto& me = cambc::self();
    const int r = R();
    if (role.empty()) {
        side = find_side();
        choose();
        const bool first = cambc::champions(team::ally).front() == me;
        role = side == 'A' ? (me.champion_name() == cambc::champion_type::stellar ? "watcher" : "idle")
                           : (me.champion_name() == cambc::champion_type::ryth ? "hider" : "idle");
        if (first || role != "idle")
            L("init pos=" + P(me.position()) + " T=" + P(T) + " W=" + P(W) + " S=" + P(S) + " bush(W)=" +
              std::to_string(m::bushes().is_set(W)) + " d(S,T)=" + std::to_string(cheb(S, T)) + " d(S,W)=" + std::to_string(cheb(S, W)));
    }
    if (!me.is_alive() || role == "idle" || T.x < 0) return;

    if (role == "hider") {
        if (me.position() != T && me.can_move()) {
            try { me.move_towards(T); } catch (const cambc::error&) {}
            if (me.position() == T) L("arrived T");
        }
        if (r >= TEST - 2 && r <= TEST + 3) L("hp=" + std::to_string(me.health()) + " pos=" + P(me.position()));
    } else {
        if (r < TEST - 5 && me.position() != S && me.can_move()) {
            try { me.move_towards(S); } catch (const cambc::error&) {}
        }
        if (r == TEST - 1) L("pre-test " + sight() + " at_S=" + std::to_string(me.position() == S));
        if (r == TEST && !acted) {
            acted = true;
            L("before_ward " + sight() + " ward_cd=" + std::to_string(me.ward_cooldown()));
            L(attempt("place_ward(W)", [&] { return me.place_ward(W); }));
            L("after_ward " + sight());
            auto es = cambc::champions(team::enemy);
            const auto* e = enemy_ryth(es);
            if (e) {
                L(attempt("attack", [&] { me.attack(*e); return true; }));
                L(attempt("cast0", [&] { return me.abilities()[0].use(*e); }));
                L("after_actions " + sight());
            }
        }
        if (r == TEST + 1 || r == TEST + 2) L("next " + sight());
    }
}

void play_draft() {
    side = find_side();
    const auto mine = cambc::draft::current_draft(team::ally);
    auto have = [&](D d) { return std::find(mine.begin(), mine.end(), d) != mine.end(); };
    std::vector<D> pref = side == 'A' ? std::vector<D>{ D::stellar, D::willow, D::prism, D::tavi, D::marcella }
                                      : std::vector<D>{ D::ryth, D::varg, D::ren, D::marcella, D::willow };
    for (auto d : pref)
        if (!have(d)) { cambc::draft::pick(d); return; }
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
