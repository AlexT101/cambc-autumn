"""Priority encodings: a body writes Fish's (FISH_MODEL 5) or Mite's (research/mite-2026-11-08, 11-09 12:00 version)
priority values in place of ocean's packed ones, so the opponent classifier reads it as the team it plays.
The body's own order is kept as far as the encoding allows: each of its raw ranks maps monotonically onto that team's
values (Fish's quiet level is its health band, so idle bodies order by health; Mite's quiet value likewise).
The comms payload (16 low bits of ocean's priority) goes: allies read none.
Usage: patch_prio.py BOT_DIR F|M [order|exact|near]
order (default): idle bodies keep the body's idle order (idle_priority.h: who takes a camp's tie hit), spread over
  Fish's early-to-quiet levels -5..3 (late 5..8) or Mite's 1000..1049; exact: Fish's health band, Mite's quiet value.
  Exact cost the bodies ~8 points of win rate on 256 ladder games (Flp3 79.7% against Flp2 71.1%)."""
import sys, pathlib
d = pathlib.Path(sys.argv[1]) / 'src'; who = sys.argv[2]; mode = sys.argv[3] if len(sys.argv) > 3 else 'order'
def sub(f, old, new):
    p = d / f; s = p.read_text(); assert s.count(old) == 1, (f, old); p.write_text(s.replace(old, new))
sub('model/turn_order.h', 'inline constexpr int priority_payload_bits = 16;', 'inline constexpr int priority_payload_bits = 0; // body: no payload')
sub('model/comms.cc', '    if (a.priority_round != world.round || a.next_priority == 0) return -1;\n',
    '    if (a.priority_round != world.round || a.next_priority == 0 || priority_payload_bits == 0) return -1;\n')
FISH = '''std::int32_t packed_priority(int raw, int, std::uint32_t) {
    int L;
    if (raw >= band_width) L = raw >= 2 * band_width ? -117 : -116; // kill, protect: outermost contact+
    else if ((raw = std::clamp(raw, lowest_raw, highest_raw)) >= contact_first) L = -101 - std::min(raw - contact_first, 14);
    else if (raw == dead_priority) L = -1;
    else if (raw >= idle_lowest) L = IDLE_F;
    else if (raw >= idle_lowest - idle_span) L = LATE_F;
    else L = 99 + std::min(contact_last - raw, 16);
    return -body_prio::rank - body_prio::n1 * L;
}'''
MITE = '''std::int32_t packed_priority(int raw, int, std::uint32_t) {
    if (raw >= band_width) return raw >= 2 * band_width ? 3099 : 3095; // kill flag
    raw = std::clamp(raw, lowest_raw, highest_raw);
    if (body_prio::channel) return 18965;
    if (raw >= contact_first) return 2090 + std::min(raw - contact_first, 10); // retreat flag on contact
    if (raw == dead_priority) return 1050;
    if (raw >= idle_lowest) return IDLE_M;
    if (raw >= idle_lowest - idle_span) return 100; // late: after the quiet ones
    return 100 - std::min((contact_last - raw + 1) / 2, 10); // contact 100 - d
}'''
old_pp = '''std::int32_t packed_priority(int raw, int index, std::uint32_t payload) {
    const int rank = (rank_code(raw) - rank_code(0)) * 8 + (7 - index);
    return rank * (1 << priority_payload_bits) + static_cast<std::int32_t>(payload);
}'''
state = '''namespace body_prio {
int rank = 2, n1 = 6, band = 0, quiet = 1020;
bool channel = false, alert = false;
} // namespace body_prio
'''
if mode == 'exact':
    FISH = FISH.replace('IDLE_F', 'body_prio::band').replace('LATE_F', 'body_prio::band + 5')
    MITE = MITE.replace('IDLE_M', 'body_prio::quiet')
elif mode == 'order':
    FISH = FISH.replace('IDLE_F', '-5 + (idle_top - raw) * 9 / idle_span').replace('LATE_F', '5 + (idle_lowest - 1 - raw) * 4 / idle_span')
    MITE = MITE.replace('IDLE_M', '1000 + (raw - idle_lowest) * 50 / idle_span')
else:  # Mite: alert 0 with an enemy within 8; else the quiet value +-2 by the body's idle order
    FISH = FISH.replace('IDLE_F', 'body_prio::band').replace('LATE_F', 'body_prio::band + 5')
    MITE = MITE.replace('IDLE_M', 'body_prio::alert ? 0 : body_prio::quiet - 2 + (raw - idle_lowest) * 5 / idle_span')
sub('model/turn_order.cc', old_pp, state + (FISH if who == 'F' else MITE))
p = d / 'model/turn_order.cc'; s = p.read_text()
s = s.replace('static_assert(((rank_code(3 * band_width - 1) - rank_code(0)) * 8 + 7) < 1 << (31 - priority_payload_bits));\n', '')
p.write_text(s)
# Per-turn state, before any packed_priority call of the turn.
setup = '''    {
        const auto& me = world.me();
        const float h = me.max_health > 0 ? std::clamp(my_health() / me.max_health, 0.0f, 1.0f) : 1.0f;
        body_prio::band = std::max(0, static_cast<int>(std::floor(4 * (1 - h))));
        const bool big = me.type == cambc::champion_type::heart_of_ruin || me.type == cambc::champion_type::marcella;
        body_prio::quiet = big ? 1025 + static_cast<int>(std::floor(24 * h)) : 1000 + static_cast<int>(std::floor(20 * h));
        body_prio::channel = me.alive && me.channel != Channel::none && my_channel_time() <= 1;
        body_prio::alert = false;
        for (const auto& e : world.enemies) body_prio::alert |= e.alive && e.visible && dist(e.pos, me.pos) <= 8;
        // Fish's rank: 2 + place by base max health, ties by type index, Heart of Ruin before Varg.
        const auto key = [](const ChampionBelief& c) {
            const int t = static_cast<int>(c.type);
            return std::pair{-c.facts().health.base, c.type == cambc::champion_type::heart_of_ruin ? 9.5f : static_cast<float>(t)};
        };
        int place = 0;
        for (const auto& a : world.allies) place += !a.is_self && key(a) < key(me);
        body_prio::rank = 2 + place;
        body_prio::n1 = static_cast<int>(world.allies.size()) + 1;
    }
    follow::posting = {};
'''
sub('model/turn_order.cc', '    follow::posting = {};\n', setup)
