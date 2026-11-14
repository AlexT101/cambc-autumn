#pragma once

#include <algorithm>
#include <array>
#include <cstring>
#include <span>
#include <vector>
#include "comms.h"
#include "log.h"
#include "champions/cassi/states/assess.h"
#include "champions/shared/abilities.h"

namespace aph {
struct State;
struct Turn;
}

namespace aph {
// Debug (debug_state_lines): each state's colour, and the line or dot drawn for the state that ended the
// turn. Its target is the last walk's goal (aim, else the nearest goal tile) unless the state notes one;
// some fall back to their place (an altar, our spawn). A dot: nowhere to go.
inline std::uint32_t state_colour(const char* name);

inline void draw_state_line(Turn& t, const char* name);

void run_states(Turn& t, std::span<const State> states);

}
namespace cassi {
void run(aph::Turn& t);

}
namespace heart_of_ruin {
void run(aph::Turn& t);

}
namespace issac {
void run(aph::Turn& t);

}
namespace marcella {
void run(aph::Turn& t);

}
namespace prism {
void run(aph::Turn& t);

}
namespace ren {
void run(aph::Turn& t);

}
namespace ryth {
void run(aph::Turn& t);

}
namespace stellar {
void run(aph::Turn& t);

}
namespace tavi {
void run(aph::Turn& t);

}
namespace varg {
void run(aph::Turn& t);

}
namespace vendetta {
void run(aph::Turn& t);

}
namespace vesper_vale {
void run(aph::Turn& t);

}
namespace willow {
void run(aph::Turn& t);

}
namespace aph {
struct State {
    const char* name;
    int max_score;
    int (*score)(Turn&);
    bool (*run)(Turn&);
};

}
namespace cassi {
inline constexpr aph::State order[] = {
    {"dead", states::dead::max_score, states::dead::score, states::dead::run},
    {"channel", states::channel::max_score, states::channel::score, states::channel::run},
    {"retreat", states::retreat::max_score, states::retreat::score, states::retreat::run},
    {"prepare", states::prepare::max_score, states::prepare::score, states::prepare::run},
    {"idle", states::idle::max_score, states::idle::score, states::idle::run},
    {"ender", states::ender::max_score, states::ender::score, states::ender::run},
    {"assess", states::assess::max_score, states::assess::score, states::assess::run},
    {"tend", states::tend::max_score, states::tend::score, states::tend::run},
    {"mend", states::mend::max_score, states::mend::score, states::mend::run},
    {"guard", states::guard::max_score, states::guard::score, states::guard::run},
    {"capture", states::capture::max_score, states::capture::score, states::capture::run},
    {"strike", states::strike::max_score, states::strike::score, states::strike::run},
    {"bank", states::bank::max_score, states::bank::score, states::bank::run},
    {"spent", states::spent::max_score, states::spent::score, states::spent::run},
    {"chase", states::chase::max_score, states::chase::score, states::chase::run},
    {"contest", states::contest::max_score, states::contest::score, states::contest::run},
    {"siege", states::siege::max_score, states::siege::score, states::siege::run},
    {"farm", states::farm::max_score, states::farm::score, states::farm::run},
};

}
namespace heart_of_ruin {
inline constexpr aph::State order[] = {
    {"dead", states::dead::max_score, states::dead::score, states::dead::run},
    {"channel", states::channel::max_score, states::channel::score, states::channel::run},
    {"retreat", states::retreat::max_score, states::retreat::score, states::retreat::run},
    {"prepare", states::prepare::max_score, states::prepare::score, states::prepare::run},
    {"idle", states::idle::max_score, states::idle::score, states::idle::run},
    {"ender", states::ender::max_score, states::ender::score, states::ender::run},
    {"assess", states::assess::max_score, states::assess::score, states::assess::run},
    {"tend", states::tend::max_score, states::tend::score, states::tend::run},
    {"mend", states::mend::max_score, states::mend::score, states::mend::run},
    {"guard", states::guard::max_score, states::guard::score, states::guard::run},
    {"capture", states::capture::max_score, states::capture::score, states::capture::run},
    {"strike", states::strike::max_score, states::strike::score, states::strike::run},
    {"bank", states::bank::max_score, states::bank::score, states::bank::run},
    {"spent", states::spent::max_score, states::spent::score, states::spent::run},
    {"chase", states::chase::max_score, states::chase::score, states::chase::run},
    {"contest", states::contest::max_score, states::contest::score, states::contest::run},
    {"siege", states::siege::max_score, states::siege::score, states::siege::run},
    {"farm", states::farm::max_score, states::farm::score, states::farm::run},
};

}
namespace issac {
inline constexpr aph::State order[] = {
    {"dead", states::dead::max_score, states::dead::score, states::dead::run},
    {"channel", states::channel::max_score, states::channel::score, states::channel::run},
    {"retreat", states::retreat::max_score, states::retreat::score, states::retreat::run},
    {"prepare", states::prepare::max_score, states::prepare::score, states::prepare::run},
    {"idle", states::idle::max_score, states::idle::score, states::idle::run},
    {"ender", states::ender::max_score, states::ender::score, states::ender::run},
    {"assess", states::assess::max_score, states::assess::score, states::assess::run},
    {"tend", states::tend::max_score, states::tend::score, states::tend::run},
    {"mend", states::mend::max_score, states::mend::score, states::mend::run},
    {"guard", states::guard::max_score, states::guard::score, states::guard::run},
    {"capture", states::capture::max_score, states::capture::score, states::capture::run},
    {"strike", states::strike::max_score, states::strike::score, states::strike::run},
    {"bank", states::bank::max_score, states::bank::score, states::bank::run},
    {"spent", states::spent::max_score, states::spent::score, states::spent::run},
    {"chase", states::chase::max_score, states::chase::score, states::chase::run},
    {"contest", states::contest::max_score, states::contest::score, states::contest::run},
    {"siege", states::siege::max_score, states::siege::score, states::siege::run},
    {"farm", states::farm::max_score, states::farm::score, states::farm::run},
};

}
namespace marcella {
inline constexpr aph::State order[] = {
    {"dead", states::dead::max_score, states::dead::score, states::dead::run},
    {"channel", states::channel::max_score, states::channel::score, states::channel::run},
    {"retreat", states::retreat::max_score, states::retreat::score, states::retreat::run},
    {"prepare", states::prepare::max_score, states::prepare::score, states::prepare::run},
    {"idle", states::idle::max_score, states::idle::score, states::idle::run},
    {"ender", states::ender::max_score, states::ender::score, states::ender::run},
    {"assess", states::assess::max_score, states::assess::score, states::assess::run},
    {"tend", states::tend::max_score, states::tend::score, states::tend::run},
    {"mend", states::mend::max_score, states::mend::score, states::mend::run},
    {"guard", states::guard::max_score, states::guard::score, states::guard::run},
    {"capture", states::capture::max_score, states::capture::score, states::capture::run},
    {"strike", states::strike::max_score, states::strike::score, states::strike::run},
    {"bank", states::bank::max_score, states::bank::score, states::bank::run},
    {"spent", states::spent::max_score, states::spent::score, states::spent::run},
    {"chase", states::chase::max_score, states::chase::score, states::chase::run},
    {"contest", states::contest::max_score, states::contest::score, states::contest::run},
    {"siege", states::siege::max_score, states::siege::score, states::siege::run},
    {"farm", states::farm::max_score, states::farm::score, states::farm::run},
};

}
namespace prism {
inline constexpr aph::State order[] = {
    {"dead", states::dead::max_score, states::dead::score, states::dead::run},
    {"channel", states::channel::max_score, states::channel::score, states::channel::run},
    {"retreat", states::retreat::max_score, states::retreat::score, states::retreat::run},
    {"prepare", states::prepare::max_score, states::prepare::score, states::prepare::run},
    {"idle", states::idle::max_score, states::idle::score, states::idle::run},
    {"ender", states::ender::max_score, states::ender::score, states::ender::run},
    {"assess", states::assess::max_score, states::assess::score, states::assess::run},
    {"support", states::support::max_score, states::support::score, states::support::run},
    {"tend", states::tend::max_score, states::tend::score, states::tend::run},
    {"mend", states::mend::max_score, states::mend::score, states::mend::run},
    {"guard", states::guard::max_score, states::guard::score, states::guard::run},
    {"capture", states::capture::max_score, states::capture::score, states::capture::run},
    {"strike", states::strike::max_score, states::strike::score, states::strike::run},
    {"bank", states::bank::max_score, states::bank::score, states::bank::run},
    {"spent", states::spent::max_score, states::spent::score, states::spent::run},
    {"chase", states::chase::max_score, states::chase::score, states::chase::run},
    {"contest", states::contest::max_score, states::contest::score, states::contest::run},
    {"siege", states::siege::max_score, states::siege::score, states::siege::run},
    {"farm", states::farm::max_score, states::farm::score, states::farm::run},
};

}
namespace ren {
inline constexpr aph::State order[] = {
    {"dead", states::dead::max_score, states::dead::score, states::dead::run},
    {"channel", states::channel::max_score, states::channel::score, states::channel::run},
    {"retreat", states::retreat::max_score, states::retreat::score, states::retreat::run},
    {"prepare", states::prepare::max_score, states::prepare::score, states::prepare::run},
    {"idle", states::idle::max_score, states::idle::score, states::idle::run},
    {"ender", states::ender::max_score, states::ender::score, states::ender::run},
    {"assess", states::assess::max_score, states::assess::score, states::assess::run},
    {"tend", states::tend::max_score, states::tend::score, states::tend::run},
    {"mend", states::mend::max_score, states::mend::score, states::mend::run},
    {"guard", states::guard::max_score, states::guard::score, states::guard::run},
    {"capture", states::capture::max_score, states::capture::score, states::capture::run},
    {"strike", states::strike::max_score, states::strike::score, states::strike::run},
    {"bank", states::bank::max_score, states::bank::score, states::bank::run},
    {"spent", states::spent::max_score, states::spent::score, states::spent::run},
    {"chase", states::chase::max_score, states::chase::score, states::chase::run},
    {"contest", states::contest::max_score, states::contest::score, states::contest::run},
    {"siege", states::siege::max_score, states::siege::score, states::siege::run},
    {"farm", states::farm::max_score, states::farm::score, states::farm::run},
};

}
namespace ryth {
inline constexpr aph::State order[] = {
    {"dead", states::dead::max_score, states::dead::score, states::dead::run},
    {"channel", states::channel::max_score, states::channel::score, states::channel::run},
    {"retreat", states::retreat::max_score, states::retreat::score, states::retreat::run},
    {"prepare", states::prepare::max_score, states::prepare::score, states::prepare::run},
    {"idle", states::idle::max_score, states::idle::score, states::idle::run},
    {"ender", states::ender::max_score, states::ender::score, states::ender::run},
    {"assess", states::assess::max_score, states::assess::score, states::assess::run},
    {"tend", states::tend::max_score, states::tend::score, states::tend::run},
    {"mend", states::mend::max_score, states::mend::score, states::mend::run},
    {"guard", states::guard::max_score, states::guard::score, states::guard::run},
    {"capture", states::capture::max_score, states::capture::score, states::capture::run},
    {"strike", states::strike::max_score, states::strike::score, states::strike::run},
    {"bank", states::bank::max_score, states::bank::score, states::bank::run},
    {"spent", states::spent::max_score, states::spent::score, states::spent::run},
    {"chase", states::chase::max_score, states::chase::score, states::chase::run},
    {"contest", states::contest::max_score, states::contest::score, states::contest::run},
    {"siege", states::siege::max_score, states::siege::score, states::siege::run},
    {"farm", states::farm::max_score, states::farm::score, states::farm::run},
};

}
namespace stellar {
inline constexpr aph::State order[] = {
    {"dead", states::dead::max_score, states::dead::score, states::dead::run},
    {"channel", states::channel::max_score, states::channel::score, states::channel::run},
    {"retreat", states::retreat::max_score, states::retreat::score, states::retreat::run},
    {"prepare", states::prepare::max_score, states::prepare::score, states::prepare::run},
    {"idle", states::idle::max_score, states::idle::score, states::idle::run},
    {"ender", states::ender::max_score, states::ender::score, states::ender::run},
    {"assess", states::assess::max_score, states::assess::score, states::assess::run},
    {"tend", states::tend::max_score, states::tend::score, states::tend::run},
    {"mend", states::mend::max_score, states::mend::score, states::mend::run},
    {"guard", states::guard::max_score, states::guard::score, states::guard::run},
    {"capture", states::capture::max_score, states::capture::score, states::capture::run},
    {"strike", states::strike::max_score, states::strike::score, states::strike::run},
    {"bank", states::bank::max_score, states::bank::score, states::bank::run},
    {"spent", states::spent::max_score, states::spent::score, states::spent::run},
    {"chase", states::chase::max_score, states::chase::score, states::chase::run},
    {"contest", states::contest::max_score, states::contest::score, states::contest::run},
    {"siege", states::siege::max_score, states::siege::score, states::siege::run},
    {"farm", states::farm::max_score, states::farm::score, states::farm::run},
};

}
namespace tavi {
inline constexpr aph::State order[] = {
    {"dead", states::dead::max_score, states::dead::score, states::dead::run},
    {"channel", states::channel::max_score, states::channel::score, states::channel::run},
    {"retreat", states::retreat::max_score, states::retreat::score, states::retreat::run},
    {"prepare", states::prepare::max_score, states::prepare::score, states::prepare::run},
    {"idle", states::idle::max_score, states::idle::score, states::idle::run},
    {"ender", states::ender::max_score, states::ender::score, states::ender::run},
    {"assess", states::assess::max_score, states::assess::score, states::assess::run},
    {"tend", states::tend::max_score, states::tend::score, states::tend::run},
    {"mend", states::mend::max_score, states::mend::score, states::mend::run},
    {"guard", states::guard::max_score, states::guard::score, states::guard::run},
    {"capture", states::capture::max_score, states::capture::score, states::capture::run},
    {"strike", states::strike::max_score, states::strike::score, states::strike::run},
    {"bank", states::bank::max_score, states::bank::score, states::bank::run},
    {"spent", states::spent::max_score, states::spent::score, states::spent::run},
    {"chase", states::chase::max_score, states::chase::score, states::chase::run},
    {"contest", states::contest::max_score, states::contest::score, states::contest::run},
    {"siege", states::siege::max_score, states::siege::score, states::siege::run},
    {"farm", states::farm::max_score, states::farm::score, states::farm::run},
};

}
namespace varg {
inline constexpr aph::State order[] = {
    {"dead", states::dead::max_score, states::dead::score, states::dead::run},
    {"channel", states::channel::max_score, states::channel::score, states::channel::run},
    {"retreat", states::retreat::max_score, states::retreat::score, states::retreat::run},
    {"prepare", states::prepare::max_score, states::prepare::score, states::prepare::run},
    {"idle", states::idle::max_score, states::idle::score, states::idle::run},
    {"ender", states::ender::max_score, states::ender::score, states::ender::run},
    {"assess", states::assess::max_score, states::assess::score, states::assess::run},
    {"tend", states::tend::max_score, states::tend::score, states::tend::run},
    {"mend", states::mend::max_score, states::mend::score, states::mend::run},
    {"guard", states::guard::max_score, states::guard::score, states::guard::run},
    {"capture", states::capture::max_score, states::capture::score, states::capture::run},
    {"strike", states::strike::max_score, states::strike::score, states::strike::run},
    {"bank", states::bank::max_score, states::bank::score, states::bank::run},
    {"spent", states::spent::max_score, states::spent::score, states::spent::run},
    {"chase", states::chase::max_score, states::chase::score, states::chase::run},
    {"contest", states::contest::max_score, states::contest::score, states::contest::run},
    {"siege", states::siege::max_score, states::siege::score, states::siege::run},
    {"farm", states::farm::max_score, states::farm::score, states::farm::run},
};

}
namespace vendetta {
inline constexpr aph::State order[] = {
    {"dead", states::dead::max_score, states::dead::score, states::dead::run},
    {"channel", states::channel::max_score, states::channel::score, states::channel::run},
    {"retreat", states::retreat::max_score, states::retreat::score, states::retreat::run},
    {"prepare", states::prepare::max_score, states::prepare::score, states::prepare::run},
    {"idle", states::idle::max_score, states::idle::score, states::idle::run},
    {"ender", states::ender::max_score, states::ender::score, states::ender::run},
    {"assess", states::assess::max_score, states::assess::score, states::assess::run},
    {"tend", states::tend::max_score, states::tend::score, states::tend::run},
    {"mend", states::mend::max_score, states::mend::score, states::mend::run},
    {"guard", states::guard::max_score, states::guard::score, states::guard::run},
    {"capture", states::capture::max_score, states::capture::score, states::capture::run},
    {"strike", states::strike::max_score, states::strike::score, states::strike::run},
    {"bank", states::bank::max_score, states::bank::score, states::bank::run},
    {"spent", states::spent::max_score, states::spent::score, states::spent::run},
    {"chase", states::chase::max_score, states::chase::score, states::chase::run},
    {"contest", states::contest::max_score, states::contest::score, states::contest::run},
    {"siege", states::siege::max_score, states::siege::score, states::siege::run},
    {"farm", states::farm::max_score, states::farm::score, states::farm::run},
};

}
namespace vesper_vale {
inline constexpr aph::State order[] = {
    {"dead", states::dead::max_score, states::dead::score, states::dead::run},
    {"channel", states::channel::max_score, states::channel::score, states::channel::run},
    {"retreat", states::retreat::max_score, states::retreat::score, states::retreat::run},
    {"prepare", states::prepare::max_score, states::prepare::score, states::prepare::run},
    {"idle", states::idle::max_score, states::idle::score, states::idle::run},
    {"ender", states::ender::max_score, states::ender::score, states::ender::run},
    {"assess", states::assess::max_score, states::assess::score, states::assess::run},
    {"tend", states::tend::max_score, states::tend::score, states::tend::run},
    {"mend", states::mend::max_score, states::mend::score, states::mend::run},
    {"guard", states::guard::max_score, states::guard::score, states::guard::run},
    {"capture", states::capture::max_score, states::capture::score, states::capture::run},
    {"strike", states::strike::max_score, states::strike::score, states::strike::run},
    {"bank", states::bank::max_score, states::bank::score, states::bank::run},
    {"spent", states::spent::max_score, states::spent::score, states::spent::run},
    {"chase", states::chase::max_score, states::chase::score, states::chase::run},
    {"contest", states::contest::max_score, states::contest::score, states::contest::run},
    {"siege", states::siege::max_score, states::siege::score, states::siege::run},
    {"farm", states::farm::max_score, states::farm::score, states::farm::run},
};

}
namespace willow {
inline constexpr aph::State order[] = {
    {"dead", states::dead::max_score, states::dead::score, states::dead::run},
    {"channel", states::channel::max_score, states::channel::score, states::channel::run},
    {"retreat", states::retreat::max_score, states::retreat::score, states::retreat::run},
    {"prepare", states::prepare::max_score, states::prepare::score, states::prepare::run},
    {"idle", states::idle::max_score, states::idle::score, states::idle::run},
    {"ender", states::ender::max_score, states::ender::score, states::ender::run},
    {"assess", states::assess::max_score, states::assess::score, states::assess::run},
    {"support", states::support::max_score, states::support::score, states::support::run},
    {"tend", states::tend::max_score, states::tend::score, states::tend::run},
    {"mend", states::mend::max_score, states::mend::score, states::mend::run},
    {"guard", states::guard::max_score, states::guard::score, states::guard::run},
    {"capture", states::capture::max_score, states::capture::score, states::capture::run},
    {"strike", states::strike::max_score, states::strike::score, states::strike::run},
    {"bank", states::bank::max_score, states::bank::score, states::bank::run},
    {"spent", states::spent::max_score, states::spent::score, states::spent::run},
    {"chase", states::chase::max_score, states::chase::score, states::chase::run},
    {"contest", states::contest::max_score, states::contest::score, states::contest::run},
    {"siege", states::siege::max_score, states::siege::score, states::siege::run},
    {"farm", states::farm::max_score, states::farm::score, states::farm::run},
};

}
