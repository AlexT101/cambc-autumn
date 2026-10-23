// probe-allowances-b: passive scripted opponent for probe-allowances.
// Draft: Varg, Ryth, Marcella, Tavi, Prism. In play, Varg walks to the bush at (13,22) on interlock and
// parks there (a hidden target); every other champion stays on spawn. Logs its position every 10 rounds.
#include <cambc.h>
#include <algorithm>
#include <array>
#include <iostream>

int main() {
    using namespace cambc;
    constexpr std::array picks{ champion_draft::varg, champion_draft::ryth, champion_draft::marcella, champion_draft::tavi,
        champion_draft::prism };
    while (true) {
        try {
            if (is_draft()) {
                const auto chosen = draft::current_draft(team::ally);
                for (auto p : picks)
                    if (std::find(chosen.begin(), chosen.end(), p) == chosen.end()) { draft::pick(p); break; }
            } else {
                auto& me = self();
                const vec2 park{ 13, 22 };
                if (me.is_alive() && me.champion_name() == champion_type::varg && me.position() != park && me.can_move())
                    me.move_towards(park);
                if (round_number() % 10 == 0)
                    std::cout << "PROBE " << round_number() << ' ' << to_string(me.champion_name()) << " B pos=(" << me.position().x
                              << "," << me.position().y << ") hp=" << me.health() << '\n';
            }
        } catch (const std::exception& e) {
            std::cout << "PROBE B error " << e.what() << '\n';
        }
        end_turn();
    }
}
