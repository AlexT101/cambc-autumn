"""mkpp.py DIR ROUNDS: the ping-pong guard on an oc-wdash-494 copy (with or without mkarm.py's deny)."""
import sys
d, n = sys.argv[1], int(sys.argv[2])
S = d + '/src/'
def sub(path, old, new):
    s = open(S + path).read(); assert s.count(old) == 1, (path, old[:60]); open(S + path, 'w').write(s.replace(old, new))
sub('params.h', "inline constexpr int brake_bag = 19;\n",
    "inline constexpr int brake_bag = 19;\n"
    "// A quiet turn that walks us back to last turn's start tile keeps the work's steps off the tile it left for this\n"
    "// many rounds (bot.cc pingpong): a goal step and a pull-back (want_home, yield_capture) otherwise alternate.\n"
    f"inline constexpr int pingpong_rounds = {n};\n")
sub('bot.cc', "bool end_ward = false; // the turn-end ward, seeing more than our last observe\n",
"""bool end_ward = false; // the turn-end ward, seeing more than our last observe
// The tile a quiet turn walked us back from to last turn's start, kept off the work's steps until `until`.
struct {
    vec2 last_start{-1, -1}, tile{-1, -1};
    int last_round = -1, until = -1;
} pingpong;
""")
sub('bot.cc', """        static const bool near = home_monolith_map(world);
        guard_work(world, pathing, safety, memory.damage, near ? home_reach_avoid(world, memory) : nullptr);""",
"""        static const bool near = home_monolith_map(world);
        const bitboard* avoid = near ? home_reach_avoid(world, memory) : nullptr;
        if (pingpong.until >= world.round && pingpong.tile != world.turn_start) {
            static bitboard both{cambc::uninitialized};
            if (avoid) copy_into(*avoid, both);
            else clear_board(both);
            set_tile(both, pingpong.tile);
            avoid = &both;
        }
        guard_work(world, pathing, safety, memory.damage, avoid);""")
sub('bot.cc', """    if (!support_owned) start_recall(world);
    count_use(world, could_attack);
}""", """    if (!support_owned) start_recall(world);
    count_use(world, could_attack);
    if (!world.me().alive) {
        pingpong.last_round = -1;
        return;
    }
    if (const vec2 here = my_position(); pingpong.last_round == world.round - 1 && here == pingpong.last_start && here != start
                                         && !engaged && !engaged_before && memory.damage <= 0)
        pingpong.tile = start, pingpong.until = world.round + params::pingpong_rounds;
    pingpong.last_start = start, pingpong.last_round = world.round;
}""")
print('ok', d)
