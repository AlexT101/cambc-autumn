"""Give an ocean-family body Mite's tribute habit (EXPERIMENTS "Opponent tribute fidelity").   py patch_mite.py BOTDIR

Measured on live r2 replays (one-site maps, rounds <= 600): Mite starts a tribute at the end of every turn it ends
within 1 of an altar with gems, in place of its recall feint. On the channel's first turn it cancels while one of ours
is in contact (59% of first turns with one within 5: 65-80% at 1-4 tiles, ~45% at 5, ~10% at 6), acts, and starts again
at the turn end (63% of cancels restart within 3 rounds). Later turns of a channel are kept as ocean keeps them.
Contact is Mite's priority rule: an enemy within 4, or within 6 when either side is ranged. Idempotent.
    py patch_mite.py BOTDIR [--v3]
v1 (no flag; bodies -Mt, -Mt2) over-feints: 20-22 starts and 10-12 cancels a one-site game against Mite's 11 and 1.7.
--v3 (bodies -Mt3): the habit yields to a recall wanted home (Mite recalls at an altar 20-28% of round ends), and
the first turn cancels in contact only when ocean's own tribute check fails (Mite keeps ~40% of contact turns)."""
import sys
from pathlib import Path
bot = Path(sys.argv[1]); src = bot / 'src'; v3 = '--v3' in sys.argv
bank = src / 'economy/bank.cc'; botc = src / 'bot.cc'; parts = src / 'bot_parts.h'
s = bank.read_text()
if 'mite_tribute_habit' in s: print('already patched'); sys.exit(0)

def sub(text, old, new, path):
    assert text.count(old) == 1, (path, old[:60], text.count(old))
    return text.replace(old, new, 1)

# Shared state and the contact test, before submit_here (anonymous namespace there is fine: all users are in bank.cc).
s = sub(s, '// At an unlocked altar in reach. The caller judged',
        '''// Mite's habit: the round our current tribute was started, and whether an enemy is in Mite's contact.
int tribute_began = -1;
bool mite_contact(const World& world) {
    const bool ranged = world.me().facts().attack_range() > 1;
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && dist(e.pos, my_position()) <= (ranged || e.facts().attack_range() > 1 ? 6 : 4)) return true;
    return false;
}

// At an unlocked altar in reach. The caller judged''', bank)
s = sub(s, '            me.submit_gems(altars[a].pos);\n            const int bag',
        '            me.submit_gems(altars[a].pos);\n            tribute_began = world.round;\n            const int bag', bank)
# The first turn of a channel cancels in contact, so the turn can act; the turn end restarts it.
s = sub(s, '''    if (tribute_ok(world, safety, memory, my_channel_time())) return true;
    // Damage does not interrupt''', '''    if (tribute_began == world.round - 1 && !any_risk(world, static_cast<int>(my_channel_time())) && mite_contact(world)%s) {
        decision = Branch::tribute_cancelled;
        throw_if_stale();
        try {
            me.cancel_submit_gems();
        } catch (const std::exception&) {
            return true;
        }
        return false;
    }
    if (tribute_ok(world, safety, memory, my_channel_time())) return true;
    // Damage does not interrupt''' % (' && !tribute_ok(world, safety, memory, my_channel_time())' if v3 else ''), bank)
# The habit itself, at the end of the non-anonymous part.
s = sub(s, '''bool can_tribute_safely(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {''',
        '''// Mite's turn-end channel: a tribute wherever one can start, else the caller's recall feint.
bool mite_tribute_habit(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    if (stunned_turn || !world.me().alive || channelling() || my_gems() <= 0) return false;
    const vec2 here = my_position();
    if (here.x < 0) return false;
    const int a = altar_here(world, here);
    if (a < 0 || enemy_lock_live(world.map().altars[a].pos) || retaining_gems(world, pathing)) return false;
    if (tribute_turns(world, my_gems()) > rounds_left(world)) return false;%s
    throw_if_stale();
    try {
        cambc::self().submit_gems(world.map().altars[a].pos);
        tribute_began = world.round;
        return true;
    } catch (const cambc::error&) {
    }
    return false;
}

bool can_tribute_safely(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {''' % ('\n    if (want_home(world, pathing, safety, memory)) return false;' if v3 else ''), bank)
bank.write_text(s)
p = parts.read_text()
p = sub(p, 'bool can_tribute_here(const World& world);\n',
        'bool can_tribute_here(const World& world);\nbool mite_tribute_habit(const World& world, Pathing& pathing, Safety& safety, const Memory& memory);\n', parts)
parts.write_text(p)
b = botc.read_text()
b = sub(b, '    if (!support_owned) start_recall(world);\n    count_use',
        '    if (!support_owned) mite_tribute_habit(world, pathing, safety, memory);\n    if (!support_owned) start_recall(world);\n    count_use', botc)
botc.write_text(b)
print('patched', bot)
