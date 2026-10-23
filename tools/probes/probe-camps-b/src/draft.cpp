// Deterministic draft: first not-yet-picked released champion (lowest enum value).
#include <cambc.h>
#include "draft.h"
#include <algorithm>

void play_draft() {
    const auto chosen = cambc::draft::current_draft(cambc::team::ally);
    for (int i = 0; i < 11; ++i) {
        auto pick = static_cast<cambc::champion_draft>(i);
        if (std::find(chosen.begin(), chosen.end(), pick) == chosen.end()) { cambc::draft::pick(pick); return; }
    }
}
