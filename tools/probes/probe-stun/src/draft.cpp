// probe-stun draft: fixed pick list per scenario (one pick per draft round).
#include <cambc.h>
#include "draft.h"
#include "scenario.h"
#include <vector>

void play_draft() {
    using d = cambc::champion_draft;
#if SCENARIO == 1
    const std::vector<d> picks{d::tavi, d::cassi_and_issac, d::prism, d::ren, d::vesper_vale};
#elif SCENARIO == 2
    const std::vector<d> picks{d::vesper_vale, d::tavi, d::cassi_and_issac, d::ren, d::prism};
#else
    const std::vector<d> picks{d::ren, d::vendetta, d::tavi, d::prism, d::vesper_vale};
#endif
    const auto n = cambc::draft::current_draft(cambc::team::ally).size();
    cambc::draft::pick(picks.at(n));
}
