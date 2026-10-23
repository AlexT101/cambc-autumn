// Draft: dump all static engine data on the first draft turn, then the draft
// state every draft turn. Team abs 0 picks cassi_and_issac first then ascending;
// team abs 1 picks descending from tavi, so picks are distinguishable.
// Needs a big fuel budget: run with  cambc run probe-introspect probe-introspect --map <m> --rounds 2 --fuel 20000000
// (default ~100k/turn runs out mid-dump and the draft then gets random picks).
#include <cambc.h>
#include "draft.h"
#include "dump.h"
#include <algorithm>
#include <vector>

static int draft_calls = 0; // local counter, used only to decide when to dump

void play_draft() {
    const std::string w = "draft";
    ++draft_calls;
    std::cout << probe::P(w) << "draft_turn is_draft=" << cambc::is_draft() << " my_champion=" << cambc::detail::sdk_my_champion()
              << " my_team_abs=" << cambc::detail::sdk_my_team() << " local_call=" << draft_calls << '\n';
    probe::dump_draft_state(w);
    if (draft_calls == 1) {
        probe::dump_settings(w);
        probe::dump_items(w);
        probe::dump_champion_designs(w);
        probe::dump_camp_designs(w);
        probe::dump_passives(w);
        probe::dump_map(w);
        probe::dump_layout(w, true);
        // What does the draft perspective see beyond static map data?
        try { std::cout << probe::P(w) << "draft_vision visible_tiles=" << cambc::vision::visible_tiles().count() << '\n'; }
        catch (const std::exception& e) { std::cout << probe::P(w) << "draft_vision visible_tiles_err=" << e.what() << '\n'; }
        try { std::cout << probe::P(w) << "draft_vision camp_tiles=" << cambc::vision::camp_tiles().count() << '\n'; }
        catch (const std::exception& e) { std::cout << probe::P(w) << "draft_vision camp_tiles_err=" << e.what() << '\n'; }
        try { std::cout << probe::P(w) << "draft_vision vision_camp_groups=" << cambc::vision::camp_groups().size() << '\n'; }
        catch (const std::exception& e) { std::cout << probe::P(w) << "draft_vision camp_groups_err=" << e.what() << '\n'; }
        try { std::cout << probe::P(w) << "draft_vision champions_ally=" << cambc::champions(cambc::team::ally).size()
                        << " champions_enemy=" << cambc::champions(cambc::team::enemy).size() << '\n'; }
        catch (const std::exception& e) { std::cout << probe::P(w) << "draft_vision champions_err=" << e.what() << '\n'; }
    }

    const auto chosen = cambc::draft::current_draft(cambc::team::ally);
    std::vector<int> order;
    if (cambc::detail::sdk_my_team() == 0) order = {3, 0, 1, 2, 4, 5, 6, 7, 8, 9, 10};
    else order = {10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0};
    for (int i : order) {
        auto p = static_cast<cambc::champion_draft>(i);
        if (std::find(chosen.begin(), chosen.end(), p) != chosen.end()) continue;
        cambc::draft::pick(p);
        std::cout << probe::P(w) << "picked=" << i << '\n';
        break;
    }
    // Picks become visible to the next query?
    probe::dump_draft_state(w + "-after-pick");
}
