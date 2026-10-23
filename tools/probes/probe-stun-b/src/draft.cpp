// probe-stun-b draft: fixed pick list per scenario (one pick per draft round).
#include <cambc.h>
#include "draft.h"
#include "scenario.h"
#include <vector>

void play_draft() {
    using d = cambc::champion_draft;
#if SCENARIO == 1
    const std::vector<d> picks{d::varg, d::marcella, d::tavi, d::ryth, d::willow};
#elif SCENARIO == 2
    const std::vector<d> picks{d::tavi, d::varg, d::willow, d::ryth, d::marcella};
#else
    const std::vector<d> picks{d::varg, d::marcella, d::willow, d::ryth, d::stellar};
#endif
    const auto n = cambc::draft::current_draft(cambc::team::ally).size();
    cambc::draft::pick(picks.at(n));
}
