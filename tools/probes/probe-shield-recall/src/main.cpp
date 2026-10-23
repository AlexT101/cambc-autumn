// probe-shield-recall: does damage fully absorbed by a shield cancel a recall?
// Self-play on interlock: the team spawning at (37..39,37..39) drafts Varg, who walks next to the lone wolf (34,31).
// Turn T: hit the wolf (wakes it), recall without a shield (control). Turn T+1: hit, shield, recall. Logs each turn.
//   cambc run tools/probes/probe-shield-recall tools/probes/probe-shield-recall \
//     --map 00interlock --rounds 40 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <optional>
#include <vector>

using cambc::vec2;
using cambc::team;
using D = cambc::champion_draft;

namespace {

bool bottom_left() { return cambc::map::spawn_region(team::ally).positions().front().y > 20; }

const vec2 WOLF{ 34, 31 }, VARG_AT{ 35, 32 };

int g_role = -1;
int g_start = -1;

void log_self(const char* tag) {
    auto& me = cambc::self();
    const auto b = me.buffs();
    const float sh = b.has_shield() ? b.get<cambc::buff_shield>().value : 0.f;
    const int shd = b.has_shield() ? b.get<cambc::buff_shield>().duration : -1;
    const bool rec = me.is_recalling();
    std::printf("PROBE %d %s pos=(%d,%d) hp=%.2f shield=%.2f shield_dur=%d recalling=%d chan=%d\n", (int)cambc::round_number(), tag,
                me.position().x, me.position().y, me.health(), sh, shd, (int)rec, rec ? (int)me.remaining_channel_time() : -1);
}

void play_turn() {
    auto& me = cambc::self();
    const int r = (int)cambc::round_number();
    if (g_role < 0) {
        g_role = me.champion_name() == cambc::champion_type::varg ? 0 : 3;
        if (g_role == 0)
            for (const auto& g : cambc::map::camp_groups())
                for (const auto& c : g)
                    std::printf("PROBE %d mapcamp %s@(%d,%d)\n", r, cambc::to_string(c.kind()).c_str(), c.spawn_position().x, c.spawn_position().y);
    }
    if (!me.is_alive() || g_role != 0) return;
    if (me.is_recalling()) { log_self("chan"); return; }
    if (me.position() != VARG_AT) {
        if (g_start >= 0) { log_self("moved"); return; }
        if (me.can_move()) me.move_towards(VARG_AT);
        return;
    }
    std::optional<cambc::camp> wolf;
    for (const auto& c : cambc::vision::camps()) if (c.position() == WOLF) wolf = c;
    log_self("start");
    if (wolf) std::printf("PROBE %d wolf hp=%.2f awake=%d\n", r, wolf->health(), (int)wolf->is_awake());
    if (g_start < 0) {
        if (!wolf || !me.can_attack()) return;
        me.attack(*wolf);
        me.recall();
        g_start = r;
        log_self("control_recall_started");
        return;
    }
    if (r == g_start + 1) {
        if (wolf && me.can_attack()) me.attack(*wolf);
        me.abilities()[1].use();
        log_self("shield_cast");
        me.recall();
        log_self("shield_recall_started");
    }
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    const auto theirs = cambc::draft::current_draft(team::enemy);
    auto taken = [&](D d) { return std::find(mine.begin(), mine.end(), d) != mine.end() || std::find(theirs.begin(), theirs.end(), d) != theirs.end(); };
    const std::vector<D> a{ D::varg, D::vesper_vale, D::stellar, D::prism, D::marcella, D::vendetta };
    const std::vector<D> b{ D::ryth, D::vendetta, D::stellar, D::prism, D::marcella, D::vesper_vale };
    for (auto d : bottom_left() ? a : b) if (!taken(d)) { cambc::draft::pick(d); return; }
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else play_turn();
        } catch (const cambc::error& e) {
            std::printf("PROBE err %s\n", e.message().c_str());
        } catch (const std::exception& e) { std::printf("PROBE err %s\n", e.what()); }
        cambc::end_turn();
    }
}
