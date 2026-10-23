// probe-wardcd: try to place a ward every turn and log the result and ward_cooldown() before and after.
//   cambc run tools/probes/probe-wardcd tools/probes/probe-wardcd --map 00elkring --rounds 25 --fuel 50000000
#include <cambc.h>
#include <cstdio>

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) {
                cambc::draft::pick(cambc::champion_draft::ryth);
            } else {
                const auto& me = cambc::self();
                const int before = me.ward_cooldown();
                const auto p = me.position();
                const cambc::vec2 at{p.x + (cambc::round_number() % 2 ? 1 : -1), p.y};
                const char* result = "ok";
                try { me.place_ward(at); } catch (const std::exception& e) { result = e.what(); }
                std::printf("PROBE r=%d id=%u cd_before=%d cd_after=%d place=%s\n", cambc::round_number(),
                            static_cast<unsigned>(static_cast<cambc::handle_champion_t>(me)), before, me.ward_cooldown(), result);
            }
        } catch (const std::exception& e) {
            std::printf("PROBE err %s\n", e.what());
        }
        cambc::end_turn();
    }
}
