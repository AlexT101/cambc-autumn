#pragma once
#include "../common/common.h"
#include "../path/move_manager.h"

// Where a turn's actions go. The economy (recall, tribute, capture, farm, explore, and the path
// planner under them) takes one of these and acts only through it:
//   act    makes each call as it comes
//   plan   writes the calls down, with g::my_pos following its moves, so the fight can weigh the
//          economy's turn against its own plans and make it only if it is the best
namespace actions {
    using cs = cambc::champion_state;

    struct act {
        bool walk(vec2 t) {
            return move_manager::move_absolute(t);
        }
        bool dash(vec2 t) {
            return move_manager::dash(t);
        }
        void attack_camp(const camp_info::monster& m) {
            camp_info::attack(m);
        }
        // a recall or tribute running from an earlier turn is kept (channel.h)
        void recall() {
            if (!channel::on.contains(cs::recalling))
                channel::drop(), g::me().recall();
        }
        void submit_gems(vec2 altar) {
            if (!channel::on.contains(cs::submitting_gems))
                channel::drop(), g::me().submit_gems(altar);
        }
        bool cast(i8 slot, const camp_info::monster* m, vec2 at) {
            using namespace cambc::detail;
            channel::drop();
            i32 ok;
            if (m)
                check(sdk_cast(u32(slot), u32(entity_kind::camp), m->id, -1, -1, &ok));
            else
                check(sdk_cast(u32(slot), 0, 0, at.x, at.y, &ok));
            return ok != 0;
        }
    };

    struct plan {
        enum class kind : u8 { walk, dash, attack_camp, recall, submit_gems, cast };
        struct call {
            kind k;
            vec2 at; // walk, dash: the tile; submit_gems: the altar; cast: its tile
            const camp_info::monster* m; // attack_camp; cast: its monster, or null
            i8 slot = -1;                // cast
        };

        call calls[8];
        u32 n = 0;
        vec2 from = g::my_pos;
        vec2 to = g::my_pos; // where the calls would leave us, set by close()

        bool walk(vec2 t) {
            add({kind::walk, t, nullptr}), g::my_pos = t;
            return true;
        }
        bool dash(vec2 t) {
            add({kind::dash, t, nullptr}), g::my_pos = t;
            return true;
        }
        void attack_camp(const camp_info::monster& m) {
            add({kind::attack_camp, m.pos, &m});
        }
        void recall() {
            add({kind::recall, {}, nullptr});
        }
        void submit_gems(vec2 altar) {
            add({kind::submit_gems, altar, nullptr});
        }
        bool cast(i8 slot, const camp_info::monster* m, vec2 at) {
            add({kind::cast, at, m, slot});
            return true;
        }

        void add(call c) {
            util::require(n < std::size(calls), "actions::plan: more calls than room");
            calls[n++] = c;
        }

        // done writing: note where we would end, and put g::my_pos back
        void close() {
            to = g::my_pos, g::my_pos = from;
        }

        // a monster an earlier call this turn may have killed
        static bool is_standing(const camp_info::monster& m) {
            f32 hp;
            return camp_info::health(m, hp) && hp > 0;
        }

        // The calls for real, in order. A walk or dash may meet a hidden champion (refused), and a
        // ranged champion's attack this turn used its walk: the rest is then left.
        void make() const {
            act now;
            for (u32 i = 0; i < n; ++i) {
                const call& c = calls[i];
                switch (c.k) {
                    case kind::walk:
                        if (!channel::state().contains(cs::can_move) || !now.walk(c.at))
                            return;
                        break;
                    case kind::dash:
                        if (!now.dash(c.at))
                            return;
                        break;
                    case kind::attack_camp:
                        if (channel::state().contains(cs::can_attack) && is_standing(*c.m))
                            now.attack_camp(*c.m);
                        break;
                    case kind::recall:
                        now.recall();
                        break;
                    case kind::submit_gems:
                        now.submit_gems(c.at);
                        break;
                    case kind::cast:
                        if (channel::state().contains(cs::can_cast) && (!c.m || is_standing(*c.m)))
                            now.cast(c.slot, c.m, c.at);
                        break;
                }
            }
        }
    };
} // namespace actions
