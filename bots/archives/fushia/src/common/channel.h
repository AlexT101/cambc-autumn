#pragma once
#include "champs.h"
#include "globals.h"
#include <cambc.h>

// A recall or tribute started on an earlier turn is free to cancel (once a turn), and the cancel
// gives back walk, attack and cast (tested on cambc 3.0.5). So the turn is played as if there
// were none: our champs::my_info().state and state() leave it out, the first action cancels it
// (drop()), and a turn that asks for it again, or does nothing, keeps it.
namespace channel {
    using cs = cambc::champion_state;
    inline cs on; // recalling or submitting_gems, from an earlier turn and not yet cancelled

    // after champs::start_turn()
    inline void start_turn() {
        const cs s = g::me().state();
        on = s & (cs::recalling | cs::submitting_gems);
        if (!on.is_empty())
            champs::my_info().state = (s - on) | cs::can_move | cs::can_attack | cs::can_cast;
    }

    // our state now, as if free of the channel while it lasts (nothing has acted yet)
    inline cs state() {
        return on.is_empty() ? g::me().state() : champs::my_info().state;
    }

    // before any action
    inline void drop() {
        if (!on.is_empty())
            on = {}, cambc::detail::check(cambc::detail::sdk_cancel_channel());
    }
} // namespace channel
