// Deterministic draft: first not-yet-picked champion from a fixed preference list.
#include <cambc.h>
#include "draft.h"
#include <algorithm>

void play_draft() {
    using cd = cambc::champion_draft;
    const cd prefs[] = {cd::vesper_vale, cd::ren, cd::varg, cd::marcella, cd::willow, cd::ryth, cd::stellar};
    const auto chosen = cambc::draft::current_draft(cambc::team::ally);
    for (auto p : prefs)
        if (std::find(chosen.begin(), chosen.end(), p) == chosen.end()) { cambc::draft::pick(p); return; }
}
