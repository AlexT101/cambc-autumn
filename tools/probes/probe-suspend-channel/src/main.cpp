// probe-suspend-channel: does a bot that runs out of fuel while channelling a recall resume next round?
// Run at the default fuel:
//   cambc run tools/probes/probe-suspend-channel tools/probes/probe-suspend-channel --map 00ambush --rounds 16 -o DIR
// The ally with the lowest id (S) walks one step off spawn in rounds 2-3, starts a recall in round 5 and
// burns fuel until the round changes; the next ally (C, control) does the same in round 5 without a
// recall. Each logs "PROBE <engine round> <S|C> ..." (team-a.stdout); every turn logs "start".
#include <cambc.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <utility>
#include <vector>

static void burn() {
    const auto r0 = cambc::round_number();
    volatile std::uint64_t x = 0;
    for (std::uint64_t i = 0;; ++i) {
        x = x * 6364136223846793005ULL + 1;
        if (i % 256 == 0 && cambc::round_number() != r0) return;
    }
}

static void play() {
    auto& me = cambc::self();
    std::vector<unsigned> ids;
    for (auto& c : cambc::champions(cambc::team::ally)) ids.push_back(static_cast<unsigned>(static_cast<cambc::handle_champion_t>(c)));
    std::sort(ids.begin(), ids.end());
    const unsigned id = static_cast<unsigned>(static_cast<cambc::handle_champion_t>(me));
    const int k = static_cast<int>(std::find(ids.begin(), ids.end(), id) - ids.begin());
    if (k > 1) return;
    const char* who = k == 0 ? "S" : "C";
    const auto r = cambc::round_number();
    std::printf("PROBE %u %s start recalling=%d\n", r, who, int(me.is_recalling()));
    if (r == 2 || r == 3) {
        const auto p = me.position();
        for (auto [dx, dy] : {std::pair{0, 1}, {0, -1}, {1, 0}, {-1, 0}, {1, 1}, {-1, -1}, {1, -1}, {-1, 1}})
            try {
                if (me.move_absolute({p.x + dx, p.y + dy})) break;
            } catch (const cambc::error&) {}
    }
    if (r == 5) {
        if (k == 0) {
            try {
                me.recall();
                std::printf("PROBE %u S recall_started recalling=%d\n", cambc::round_number(), int(me.is_recalling()));
            } catch (const cambc::error& e) {
                std::printf("PROBE %u S recall_error %d\n", cambc::round_number(), int(e.code()));
            }
        }
        burn();
        std::printf("PROBE %u %s resumed recalling=%d\n", cambc::round_number(), who, int(me.is_recalling()));
    }
}

int main() {
    while (true) {
        if (!cambc::is_draft()) {
            try {
                play();
            } catch (const cambc::error&) {
                std::printf("PROBE error\n");
            }
        }
        cambc::end_turn();
    }
}
