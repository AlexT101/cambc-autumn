#pragma once
#include "../common/common.h"

inline void draft_turn() {
    using namespace cambc;

    static constexpr champion_draft prio[] = {
        champion_draft::heart_of_ruin,
        champion_draft::vendetta,
        champion_draft::vesper_vale,
        champion_draft::cassi_and_issac,
        champion_draft::marcella,
    };

    draft::pick(prio[draft::current_draft(team::ally).size()]);
}
