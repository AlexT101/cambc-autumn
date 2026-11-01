// Draft: survey once, then pick the scenario's champions in order (fallback: first unpicked).
#include <cambc.h>
#include <algorithm>
#include "bot.h"
#include "draft.h"
#include "survey.h"

void play_draft() {
    static bool surveyed = false;
    if (!surveyed) { survey(); surveyed = true; }
    const auto chosen = cambc::draft::current_draft(cambc::team::ally);
    for (auto p : scenario_draft())
        if (std::find(chosen.begin(), chosen.end(), p) == chosen.end()) { cambc::draft::pick(p); return; }
    for (int i = 0; i < 11; ++i) {
        auto pick = static_cast<cambc::champion_draft>(i);
        if (std::find(chosen.begin(), chosen.end(), pick) == chosen.end()) { cambc::draft::pick(pick); return; }
    }
}
