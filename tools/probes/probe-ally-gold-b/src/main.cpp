// probe-ally-gold-b: probe-ally-gold's raw gold reads on enemies in vision. Both teams draft the first legal
// champions and walk at the enemy spawn, so they meet; each turn start every champion prints, for every other
// champion, sdk_champion's code (97 = out of vision), sdk_champion_gold's code and value (12345 = untouched).
// Run: cambc run tools/probes/probe-ally-gold-b tools/probes/probe-ally-gold-b --map maps/gen/gen-tiny-120101200.map26a --rounds 30 --fuel 50000000 -o <dir>
//      then unzip the .repl26a: tr -d '\000' < team-a.stdout | grep goldread
#include <cambc.h>
#include <cstdio>

using namespace cambc::detail;

int main() {
    while (true) {
        if (cambc::is_draft()) {
            for (int c = 0; c < 12; ++c)
                if (sdk_draft_champion(c) == 0) break;
        } else {
            const std::uint32_t me = static_cast<std::uint32_t>(sdk_my_champion());
            for (const bool enemies : {false, true}) {
                std::uint32_t handles[16]{}, n = 0;
                check(enemies ? sdk_enemies(handles, 16, &n) : sdk_allies(handles, 16, &n));
                for (std::uint32_t i = 0; i < n; ++i) {
                    if (handles[i] == me) continue;
                    champion_info info{};
                    std::uint32_t gold = 12345;
                    const int seen = sdk_champion(handles[i], &info);
                    const int code = sdk_champion_gold(handles[i], &gold);
                    std::printf("PROBE %u me %u goldread %s %u champion=%d gold_code=%d gold=%u\n",
                                static_cast<unsigned>(cambc::round_number()), me, enemies ? "enemy" : "ally", handles[i],
                                seen, code, gold);
                }
            }
            try {
                cambc::self().move_towards(cambc::map::spawn_region(cambc::team::enemy).positions()[0]);
            } catch (...) {
            }
        }
        cambc::end_turn();
    }
}
