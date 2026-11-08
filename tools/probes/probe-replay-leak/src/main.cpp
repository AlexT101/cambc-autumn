// probe-replay-leak: what a replay records of a team's shared memory, draft memory and priority.
// Run:
//   cambc run tools/probes/probe-replay-leak tools/probes/probe-replay-leak --map 00corners --rounds 40 --fuel 50000000 -o <dir>
// The draft bot writes 1024 bytes of a marker pattern ("DRFTLEAK" then byte i ^ 0x5a). Every
// champion turn writes the shared bytes "SHRDLK" + round (16 bits) and sets priority
// 0x13570000 + round. Search the replay (and its decompressed sections) for the markers; the
// priorities are also read back in play from the other team to confirm they are visible.
#include <cambc.h>
#include <cstdint>
#include <cstdio>
#include <cstring>

namespace {
void draft_turn() {
    static bool wrote = false;
    if (!wrote) {
        std::uint8_t buf[1024];
        std::memcpy(buf, "DRFTLEAK", 8);
        for (int i = 8; i < 1024; ++i) buf[i] = static_cast<std::uint8_t>(i ^ 0x5a);
        cambc::detail::check(cambc::detail::sdk_bc_submit_draft_memory(buf, sizeof buf));
        wrote = true;
    }
    const auto ally = cambc::draft::current_draft(cambc::team::ally);
    for (int i = 0; i < 11; ++i) {
        const auto pick = static_cast<cambc::champion_draft>(i);
        bool taken = false;
        for (auto a : ally) taken |= a == pick;
        if (!taken) {
            cambc::draft::pick(pick);
            return;
        }
    }
}

void play_turn() {
    const auto r = cambc::round_number();
    std::uint8_t b[8] = {'S', 'H', 'R', 'D', 'L', 'K', static_cast<std::uint8_t>(r >> 8), static_cast<std::uint8_t>(r)};
    cambc::detail::check(cambc::detail::sdk_write_shared_memory(0, b, sizeof b));
    cambc::self().set_priority(static_cast<std::int32_t>(0x13570000u + r));
    for (const auto& c : cambc::champions(cambc::team::enemy))
        if (c.is_visible()) std::printf("PROBE %u enemy %u prio %d\n", r, 0u, c.priority());
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) draft_turn();
            else play_turn();
        } catch (const std::exception& e) {
            std::printf("PROBE err %s\n", e.what());
        }
        cambc::end_turn();
    }
}
