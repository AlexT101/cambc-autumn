#include <cambc.h>
#include "draft.h"
#include <iterator>

// A top team's composition, one pick per draft round. Our picks so far give the round, so a pick never repeats.
void play_draft() {
    constexpr cambc::champion_draft picks[] = {cambc::champion_draft::heart_of_ruin, cambc::champion_draft::marcella,
        cambc::champion_draft::vendetta, cambc::champion_draft::vesper_vale, cambc::champion_draft::ryth};
    const auto round = cambc::draft::current_draft(cambc::team::ally).size();
    if (round < std::size(picks))
        cambc::draft::pick(picks[round]);
}
