"""probe5.py SRC: prey and step-guard cost split (after probe2.py and probe3.py, whose LC line prints f7c slots 0-15).
Slots: 10 prey (whole), 11 its preyable calls, 12 its chase_trade calls, 13 step_guard (whole), 14 its new_fight,
15 its exposure calls."""
import sys
from pathlib import Path
root = Path(sys.argv[1])
def edit(rel, pairs):
    p = root / rel; s = p.read_text()
    for old, new in pairs:
        if s.count(old) != 1: sys.exit(f"{rel}: {s.count(old)}x {old[:80]!r}")
        s = s.replace(old, new)
    p.write_text(s)
edit("combat/fight.cc", [
 ("""const ChampionBelief* prey(const World& world, Safety& safety) {
    world.throw_if_stale();""", """const ChampionBelief* prey(const World& world, Safety& safety) {
    F7Time f7t(10);
    world.throw_if_stale();"""),
 ("""        if (!preyable(world, safety, e, here, range, held)) continue;""",
  """        bool f7ok;
        { F7Time f7p(11); f7ok = preyable(world, safety, e, here, range, held); }
        if (!f7ok) continue;"""),
 ("""        const auto t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late);""",
  """        const auto f7a = fuel();
        const auto t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late);
        ++f7c[0][12], f7c[1][12] += f7a - fuel();"""),
])
edit("combat/guard.cc", [
 ("""const bitboard* step_guard(const World& world, Safety& safety, vec2 here, int radius) {
    world.throw_if_stale();""", """const bitboard* step_guard(const World& world, Safety& safety, vec2 here, int radius) {
    F7Time f7t(13);
    world.throw_if_stale();"""),
 ("""            const auto t = safety.new_fight(key);""", """            const auto f7a = fuel();
            const auto t = safety.new_fight(key);
            ++f7c[0][14], f7c[1][14] += f7a - fuel();"""),
 ("""        const unsigned mask = g.exposure(q, nears[i], damage);""", """        const auto f7a = fuel();
        const unsigned mask = g.exposure(q, nears[i], damage);
        ++f7c[0][15], f7c[1][15] += f7a - fuel();"""),
])
print("ok")
