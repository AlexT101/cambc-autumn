"""Create isolated ward experiments from the full frozen ocean498; never patch an existing arm."""
from pathlib import Path
import subprocess
R = Path(__file__).resolve().parents[3]
BASE = 'variants/oc-campsh-498'

def arm(name, old, new):
    dest = 'variants/' + name
    subprocess.run([str(R/'copybot'), BASE, dest], check=True, cwd=R)
    p = R/'bots'/dest/'src/bot.cc'
    s = p.read_text()
    assert s.count(old) == 1, (name, s.count(old))
    p.write_text(s.replace(old, new))

arm('oc-wtile-498', '''    // A teammate's ward unseen in the bush blocks its tile, and allies pick the same tile first.
    for (auto p : Tiles<3>{best})
        if (try_ward(p, memory)) return true;''', '''    // Keep the chosen cluster and placement trigger; rank its tiles by actual ward sight.
    static bitboard sight{cambc::uninitialized};
    const auto& cluster = map.bush_cluster(first_tile(best)).tiles;
    vec2 chosen = first_tile(best);
    int most = -1;
    for (auto p : Tiles<25>{best}) {
        if (!fuel_ok(floor + 2000)) break;
        cambc::ward::visible_tiles_from_into(p, sight);
        sight &= cluster;
        const int value = score(sight);
        if (value > most) chosen = p, most = value;
    }
    if (most >= 0 && try_ward(chosen, memory)) return true;
    // Hidden allied wards can block the preferred tile.
    for (auto p : Tiles<3>{best})
        if ((most < 0 || p != chosen) && try_ward(p, memory)) return true;''')

arm('oc-wbush-498', '''    if (p.x < 0) return std::nullopt;
    if (memory.ward == p) return false;''', '''    if (p.x < 0 || !test(map.bushes, p)) return std::nullopt;
    if (memory.ward == p) return false;''')

arm('oc-wcamp-498', '''// The draft's ward tile for our work (claimed group, else waited-at altar): placed once in range,''', '''// A cleared camp near our feet can retain information after we leave; avoid a map-wide scan.
bool ward_camp(const World& world, Memory& memory) {
    const auto& map = world.map();
    const vec2 here = my_position();
    if (!in_bounds(here) || !fuel_ok(end_reserve / 2 + 2000)) return false;
    if (in_bounds(memory.ward) && dist(here, memory.ward) < 8) return false;
    static bitboard tiles{cambc::uninitialized}, allied{cambc::uninitialized};
    tiles.clear();
    tiles.draw_chebyshev(here, cambc::constants::ward_placement_radius);
    tiles &= map.camp_tiles;
    drop(tiles, map.blocked_for_us);
    cambc::vision::ward_tiles_into(team::ally, allied);
    drop(tiles, allied);
    for (auto p : Tiles<25>{tiles}) {
        if (!fuel_ok(end_reserve / 2 + 2000)) break;
        const int group = map.group_at(p);
        if (group >= 0 && world.camps[group].state != CampState::alive && try_ward(p, memory)) return true;
    }
    return false;
}

// The draft's ward tile for our work (claimed group, else waited-at altar): placed once in range,''')
p = R/'bots/variants/oc-wcamp-498/src/bot.cc'
s = p.read_text();old='const bool placed = planned ? *planned : bushes && ward_bushes(world, memory);'
assert s.count(old)==1
p.write_text(s.replace(old,'const bool placed = planned ? *planned : bushes && (ward_bushes(world, memory) || ward_camp(world, memory));'))

# Alive-camp ablation keeps the bounded scan and replacement policy identical.
subprocess.run([str(R/'copybot'), 'variants/oc-wcamp-498', 'variants/oc-wcampall-498'], check=True, cwd=R)
p = R/'bots/variants/oc-wcampall-498/src/bot.cc'
s = p.read_text().replace('// A cleared camp near our feet can retain information after we leave; avoid a map-wide scan.', '// A camp near our feet can retain information after we leave; avoid a map-wide scan.')
old = 'group >= 0 && world.camps[group].state != CampState::alive && try_ward(p, memory)'
assert s.count(old) == 1
p.write_text(s.replace(old, 'group >= 0 && try_ward(p, memory)'))
