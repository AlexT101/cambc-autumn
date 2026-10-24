// probe-campstun (elkring, self-play): how long does a camp's stun buff last, and when does the stunned camp attack?
// Side 0's Cassi stands at (5,2) (C4 to the elk at (9,2)) and stuns the elk at rounds STUN1 (wakes it) and STUN2;
// Issac stands at (6,2) (C3), the elk's nearest champion. Both log the elk's buffs (type, timer) and their health at
// each turn: a health drop at Issac's turn in round r is round r's camp attack. Prism at (5,3) (C4) stuns it again
// at PRISM_STUN, while the buff of STUN2's spent stun is still listed (timer 0). Everyone else parks out of range.
//   cambc run tools/probes/probe-campstun tools/probes/probe-campstun --map elkring --rounds 35 --fuel 50000000
#include <cambc.h>
#include <algorithm>
#include <array>
#include <cstdio>

#ifndef STUN1
#define STUN1 10
#endif
#ifndef STUN2
#define STUN2 20
#endif
#ifndef PRISM_STUN
#define PRISM_STUN 21
#endif

using cambc::team;
using cambc::vec2;

namespace {

int side = -1;

int my_side() {
    const auto a = cambc::map::spawn_region(team::ally).positions();
    const auto e = cambc::map::spawn_region(team::enemy).positions();
    return (a.front().y * 1000 + a.front().x) < (e.front().y * 1000 + e.front().x) ? 0 : 1;
}

void play_draft() {
    const auto chosen = cambc::draft::current_draft(team::ally);
    if (std::find(chosen.begin(), chosen.end(), cambc::champion_draft::cassi_and_issac) == chosen.end()) {
        cambc::draft::pick(cambc::champion_draft::cassi_and_issac);
        return;
    }
    if (std::find(chosen.begin(), chosen.end(), cambc::champion_draft::prism) == chosen.end()) {
        cambc::draft::pick(cambc::champion_draft::prism);
        return;
    }
    for (int i = 0; i < 11; ++i) {
        const auto p = static_cast<cambc::champion_draft>(i);
        if (std::find(chosen.begin(), chosen.end(), p) == chosen.end()) { cambc::draft::pick(p); return; }
    }
}

void log_buffs(int r, const char* who, const char* when, std::uint32_t camp) {
    std::array<cambc::detail::camp_buff_data, 8> buffs{};
    std::uint32_t n = 0;
    const auto rc = cambc::detail::sdk_camp_buffs(camp, buffs.data(), static_cast<std::uint32_t>(buffs.size()), &n);
    std::printf("PROBE %d %s %s rc=%d buffs=%u", r, who, when, rc, n);
    for (std::uint32_t i = 0; i < n && i < buffs.size(); ++i)
        std::printf(" [type=%u mag=%.2f timer=%d]", buffs[i].type, buffs[i].magnitude, buffs[i].timer);
    std::printf("\n");
}

void play_turn() {
    auto& me = cambc::self();
    const int r = static_cast<int>(cambc::round_number());
    if (side < 0) side = my_side();
    if (side != 0 || !me.is_alive()) return;
    const auto who = me.champion_name();
    const bool cassi = who == cambc::champion_type::cassi, issac = who == cambc::champion_type::issac,
               prism = who == cambc::champion_type::prism;
    if (!cassi && !issac && !prism) {
        const int t = static_cast<int>(who);
        const vec2 park{ t % 3, 3 + t / 3 };
        if (me.position() != park && me.can_move()) me.move_towards(park);
        return;
    }
    const char* name = cassi ? "cassi" : issac ? "issac" : "prism";
    const vec2 elk{ 9, 2 };
    const vec2 post = cassi ? vec2{ 5, 2 } : issac ? vec2{ 6, 2 } : vec2{ 5, 3 };
    if (me.position() != post && me.can_move() && !me.move_towards(post)) std::printf("PROBE %d %s move_failed\n", r, name);
    for (const auto& c : cambc::vision::camps()) {
        if (c.spawn_position() != elk) continue;
        const auto h = static_cast<std::uint32_t>(static_cast<cambc::handle_camp_t>(c));
        std::printf("PROBE %d %s start pos=%d,%d hp=%.0f elk_awake=%d\n", r, name, me.position().x, me.position().y,
                    me.health(), c.is_awake() ? 1 : 0);
        log_buffs(r, name, "start", h);
        if (cassi && (r == STUN1 || r == STUN2) && me.position() == post) {
            const auto abs = me.abilities();
            const bool ok = abs[1].is_ready() && abs[1].use(c);
            std::printf("PROBE %d cassi stun ok=%d\n", r, ok ? 1 : 0);
            log_buffs(r, name, "after_stun", h);
        }
        if (prism && r == PRISM_STUN && me.position() == post) {
            const auto abs = me.abilities();
            const bool ok = abs[0].is_ready() && abs[0].use(c);
            std::printf("PROBE %d prism stun ok=%d\n", r, ok ? 1 : 0);
            log_buffs(r, name, "after_stun", h);
        }
    }
}

} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else play_turn();
        } catch (const std::exception& error) {
            std::printf("bot error: %s\n", error.what());
        }
        cambc::end_turn();
    }
}
