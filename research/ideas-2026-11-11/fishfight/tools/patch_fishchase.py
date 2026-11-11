"""Fish's chase rule on a hunting body (FISH_MODEL 10.3): a visible enemy is prey when our side's health in sight is
over RATIO x the visible enemies' and our own health fraction is over OWN, whatever the simulated fight says.
Apply on a body that already has patch_hunt.py (preyable passes healthy enemies off our ground).
Usage: patch_fishchase.py BOT_DIR [RATIO=1.24] [OWN=0.44]"""
import sys, pathlib
p = pathlib.Path(sys.argv[1]) / 'src/combat/fight.cc'; s = p.read_text()
ratio = float(sys.argv[2]) if len(sys.argv) > 2 else 1.24; own = float(sys.argv[3]) if len(sys.argv) > 3 else 0.44
def sub(old, new):
    global s; assert s.count(old) == 1, old; s = s.replace(old, new)
sub('''const ChampionBelief* prey(const World& world, Safety& safety) {
''', '''// Body: Fish's chase rule (FISH_MODEL 10.3).
bool fish_chase(const World& world, const ChampionBelief& target) {
    if (!target.visible || my_health() <= %ff * my_max_health()) return false;
    const vec2 here = my_position();
    float ours = my_health(), theirs = 0;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && dist(a.pos, here) <= vision_radius) ours += a.health;
    for (const auto& e : world.enemies)
        if (e.alive && e.visible) theirs += e.health;
    return ours > %ff * theirs;
}

const ChampionBelief* prey(const World& world, Safety& safety) {
''' % (own, ratio))
sub('''    for (int i = 0; i < n; ++i) {
        if (!fuel_ok(safety.fight_cost_estimate() + reserve)) {
            note_shortcut("prey-cut-short");
''', '''    for (int i = 0; i < n; ++i) {
        if (fish_chase(world, *order[i].second)) return order[i].second;
        if (!fuel_ok(safety.fight_cost_estimate() + reserve)) {
            note_shortcut("prey-cut-short");
''')
p.write_text(s)
