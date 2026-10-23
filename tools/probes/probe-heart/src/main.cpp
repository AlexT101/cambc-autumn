// probe-heart: can a bot draft the engine's unlisted champion (draft id 11, "Heart of Ruin"), and what does it get in play?
//   cambc run tools/probes/probe-heart tools/probes/probe-capture-b --map packs --rounds 3 --fuel 50000000
#include <cambc.h>
#include <iostream>

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) {
                for (int id : {11, 0, 1}) {
                    try { cambc::draft::pick(static_cast<cambc::champion_draft>(id)); std::cout << "PROBE draft " << cambc::round_number() << " pick " << id << " ok\n"; break; }
                    catch (const std::exception& e) { std::cout << "PROBE draft " << cambc::round_number() << " pick " << id << " err " << e.what() << '\n'; }
                }
            } else {
                auto& me = cambc::self();
                std::cout << "PROBE " << cambc::round_number() << " type=" << static_cast<int>(me.champion_name()) << " hp=" << me.max_health()
                          << " str=" << me.strength() << " focus=" << me.focus() << " range=" << me.attack_range() << '\n';
            }
        } catch (const std::exception& e) {
            std::cout << "PROBE err " << e.what() << '\n';
        }
        cambc::end_turn();
    }
}
