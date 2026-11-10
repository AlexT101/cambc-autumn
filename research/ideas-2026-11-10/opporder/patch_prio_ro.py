"""Mite body whose turn ORDER follows Mite's real priority formula (research/mite-2026-11-08 README, 11-09 12:00
version), not ocean's order mapped onto Mite's values (fishfid/patch_prio.py). Apply to Mt3p (unpatched priorities).
  dead 1050; channel ending this turn 18965; ocean's kill wish 21262 (Mite's kill flag);
  contact (an enemy seen at turn start within 4, or 6 if either side is ranged): 100 - d, +2000 when an enemy is
  within 5 and it carries 10+ gems or is at <= 40% health; alert (an enemy within 8 at this or the previous turn
  start): 0; quiet 1000 + floor(20 h), Heart of Ruin / Marcella 1025 + floor(24 h) unless under 50% beside a healthy ally.
Usage: patch_prio_ro.py BOT_DIR"""
import sys, pathlib
d = pathlib.Path(sys.argv[1]) / 'src'
def sub(f, old, new):
    p = d / f; s = p.read_text(); assert s.count(old) == 1, (f, old); p.write_text(s.replace(old, new))
sub('model/turn_order.h', 'inline constexpr int priority_payload_bits = 16;', 'inline constexpr int priority_payload_bits = 0; // body: no payload')
sub('model/comms.cc', '    if (a.priority_round != world.round || a.next_priority == 0) return -1;\n',
    '    if (a.priority_round != world.round || a.next_priority == 0 || priority_payload_bits == 0) return -1;\n')
old_pp = '''std::int32_t packed_priority(int raw, int index, std::uint32_t payload) {
    const int rank = (rank_code(raw) - rank_code(0)) * 8 + (7 - index);
    return rank * (1 << priority_payload_bits) + static_cast<std::int32_t>(payload);
}'''
new_pp = '''namespace body_prio {
int value = 1020;
bool alert_prev = false;
} // namespace body_prio
std::int32_t packed_priority(int raw, int, std::uint32_t) {
    if (raw >= 2 * band_width) return 21262; // kill flag
    return body_prio::value;
}'''
sub('model/turn_order.cc', old_pp, new_pp)
p = d / 'model/turn_order.cc'; s = p.read_text()
s = s.replace('static_assert(((rank_code(3 * band_width - 1) - rank_code(0)) * 8 + 7) < 1 << (31 - priority_payload_bits));\n', '')
p.write_text(s)
setup = '''    {
        const auto& me = world.me();
        const float h = me.max_health > 0 ? std::clamp(my_health() / me.max_health, 0.0f, 1.0f) : 1.0f;
        int nearest = 99, near_ranged = 99;
        bool alert = false;
        for (const auto& e : world.enemies) {
            if (!e.alive || !e.visible) continue;
            const int g = dist(e.pos, me.pos);
            alert |= g <= 8;
            nearest = std::min(nearest, g);
            if (me.facts().ranged || e.facts().ranged) near_ranged = std::min(near_ranged, g);
        }
        const bool big = me.type == cambc::champion_type::heart_of_ruin || me.type == cambc::champion_type::marcella;
        bool beside = false;
        for (const auto& a : world.allies)
            beside |= !a.is_self && a.alive && a.visible && a.max_health > 0 && dist(a.pos, me.pos) <= 2 && a.health >= 0.65f * a.max_health;
        int v;
        if (!me.alive) v = 1050;
        else if (me.channel != Channel::none && my_channel_time() <= 1) v = 18965;
        else if (nearest <= 4 || near_ranged <= 6) v = 100 - nearest + (nearest <= 5 && (me.gems >= 10 || h <= 0.4f) ? 2000 : 0);
        else if (alert || body_prio::alert_prev) v = 0;
        else if (big && !(h < 0.5f && beside)) v = 1025 + static_cast<int>(std::floor(24 * h));
        else v = 1000 + static_cast<int>(std::floor(20 * h));
        body_prio::value = v;
        body_prio::alert_prev = alert;
    }
    follow::posting = {};
'''
sub('model/turn_order.cc', '    follow::posting = {};\n', setup)
