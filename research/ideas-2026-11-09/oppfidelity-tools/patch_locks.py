"""Give an ocean-family body Fish's or Mite's altar-lock policy (EXPERIMENTS "Opponent tribute fidelity").
    py patch_locks.py BOTDIR fish|none
Live r2, one-site maps, rounds < 600: Fish places 2.4 locks a game, Mite 0.1, spar bodies 0.8-0.9; our hits on their
locks are 9.6 against Fish, 0.1 against Mite, 3.2 locally.
fish: FISH_MODEL 8.5, as bots/fish has it: locks are bought only on lock maps (the enemy's walk to beside the altar
      nearest our spawn at most 4 longer than ours) and placed on any altar within 2 that has no lock of either team.
none: Mite buys no locks, so it never places one."""
import sys
from pathlib import Path
bot = Path(sys.argv[1]); mode = sys.argv[2]; src = bot / 'src'
bank = src / 'economy/bank.cc'; botc = src / 'bot.cc'; parts = src / 'bot_parts.h'

def sub(text, old, new, path):
    assert text.count(old) == 1, (path, old[:70], text.count(old))
    return text.replace(old, new, 1)

b = botc.read_text()
if 'lock_map(world.map())' in b or '// no locks (Mite)' in b: print('already patched'); sys.exit(0)
if mode == 'none':
    b = sub(b, '    if (consumables) buy_lock();\n', '    // no locks (Mite)\n', botc)
    botc.write_text(b); print('patched none', bot); sys.exit(0)
assert mode == 'fish'
b = sub(b, '    if (consumables) buy_lock();\n', '    if (consumables && lock_map(world.map())) buy_lock();\n', botc)
botc.write_text(b)
p = parts.read_text()
p = sub(p, 'bool can_tribute_here(const World& world);\n', 'bool can_tribute_here(const World& world);\nbool lock_map(const StaticMap& map);\n', parts)
parts.write_text(p)
s = bank.read_text()
s = sub(s, '            if (!enemy_tribute && !our_side(map, a) && !keep_guard_lock(world, a)) continue;\n',
        '            if (!enemy_tribute && world.altars[a].enemy_lock) continue; // Fish: any altar with no lock of either team\n', bank)
s = s.replace('            if (!enemy_tribute && world.round < params::lock_deny_from && !keep_guard_lock(world, a)) continue;\n', '')
s = sub(s, 'bool can_tribute_safely(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {',
        '''// Fish's lock maps (FISH_MODEL 8.5, 112/115 maps): the enemy's walk to beside the altar nearest our
// spawn is at most 4 longer than ours (walls, holes and altars blocking, camps not).
bool lock_map(const StaticMap& map) {
    static int known = -1;
    if (known >= 0) return known == 1;
    const auto& field = map.from_ally_spawn();
    int best = unreachable, gap = unreachable;
    for (const auto& altar : map.altars) {
        int ours = unreachable, theirs = unreachable;
        for (int dx = -1; dx <= 1; ++dx)
            for (int dy = -1; dy <= 1; ++dy)
                if (const vec2 t{altar.pos.x + dx, altar.pos.y + dy}; (dx || dy) && in_bounds(t))
                    ours = std::min(ours, field.at(t)), theirs = std::min(theirs, map.enemy_spawn_steps(t));
        if (ours < best) best = ours, gap = theirs == unreachable ? unreachable : theirs - ours;
    }
    known = best != unreachable && gap <= 4;
    return known == 1;
}

bool can_tribute_safely(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {''', bank)
bank.write_text(s); print('patched fish', bot)
