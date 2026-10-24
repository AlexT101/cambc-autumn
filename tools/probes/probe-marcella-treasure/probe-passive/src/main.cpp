// probe-capture-b: passive opponent for capture probes.
// Draft: picks the lowest-numbered champion not yet on our team. Gameplay: ends every turn, never moves.
#include <cambc.h>
#include <algorithm>

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) {
                const auto chosen = cambc::draft::current_draft(cambc::team::ally);
                for (int i = 0; i < 11; ++i) {
                    auto pick = static_cast<cambc::champion_draft>(i);
                    if (std::find(chosen.begin(), chosen.end(), pick) == chosen.end()) { cambc::draft::pick(pick); break; }
                }
            }
        } catch (...) {}
        cambc::end_turn();
    }
}
