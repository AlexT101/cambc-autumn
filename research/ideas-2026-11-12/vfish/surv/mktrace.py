"""mktrace.py SRC DST: bots/variants/SRC copied to bots/variants/DST with decision trace lines (debug builds only).
Lines (rounds <= LIM): WH r h x y hp code | ST r h x y lost self_falls tku tkt allies enemies falls pursued unseen hit key
 CT r h target tx ty lost self_falls tku tkt i key delayed late | EB r h e vis x y hp maxhp str foc gems | TT r h sx sy ex ey hp maxhp gems"""
import subprocess, sys
from pathlib import Path
R = Path('/home/ubuntu/cambc-autumn'); src, dst = sys.argv[1], sys.argv[2]
subprocess.run([str(R / 'copybot'), '-f', f'variants/{src}', f'variants/{dst}'], check=True, cwd=R)
s = R / 'bots/variants' / dst / 'src'
import os
LIM = int(os.environ.get('TRACE_LIM', '400'))
LITE = os.environ.get('TRACE_LITE') == '1'
def sub(rel, old, new, count=1):
    p = s / rel; t = p.read_text(); n = t.count(old)
    if n != count: sys.exit(f"{rel}: {n} matches for {old[:70]!r}, want {count}")
    p.write_text(t.replace(old, new))
B = 'debug_block'
G = f'if (world.round <= {LIM}) '
GH = 'if (false) ' if LITE else G
sub('combat/fight.cc', "    const auto t = safety.stand_trade(roster, falls);\n",
    "    const auto t = safety.stand_trade(roster, falls);\n"
    "    " + B + '({ ' + GH + 'std::printf("ST %d %u %d %d %d %d %d %d %d %d %d %d %d %d %u\\n", world.round, my_handle(), p.x, p.y, static_cast<int>(t.lost), static_cast<int>(t.self_falls), '
    "t.turns_to_kill_us, t.turns_to_kill_them, t.allies, t.enemies, static_cast<int>(falls), static_cast<int>(pursued), static_cast<int>(unseen), reach.hit ? 1 : 0, roster.key); });\n")
sub('combat/fight.cc', "            t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late);\n",
    "            t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late);\n"
    "            " + B + '({ ' + GH + 'std::printf("CT %d %u %u %d %d %d %d %d %d %d %u %u %u\\n", world.round, my_handle(), static_cast<std::uint32_t>(target.handle), target.pos.x, target.pos.y, '
    "static_cast<int>(t.lost), static_cast<int>(t.self_falls), t.turns_to_kill_us, t.turns_to_kill_them, i, key, delayed, late); });\n")
wh = lambda code: B + '({ ' + G + 'std::printf("WH %d %u %d %d %d ' + str(code) + '\\n", world.round, my_handle(), here.x, here.y, static_cast<int>(my_health())); });'
sub('combat/fight.cc',
    "    HoldAt hold(world, pathing, here, memory.damage);\n    if (drawn_home(world, safety, hold)) return true;\n",
    "    HoldAt hold(world, pathing, here, memory.damage);\n"
    "    if (drawn_home(world, safety, hold)) {\n"
    "        " + B + '({ ' + G + 'std::printf("WH %d %u %d %d %d %d\\n", world.round, my_handle(), here.x, here.y, static_cast<int>(my_health()), fc_drawn); });\n'
    "        return true;\n    }\n")
sub('combat/fight.cc',
    "    if (mono >= 0 ? mono == 1 : camp_trapped(world, pathing, safety, here, health, memory.siege)) return true;\n",
    "    if (mono >= 0 ? mono == 1 : camp_trapped(world, pathing, safety, here, health, memory.siege)) {\n        " + wh(3) + "\n        return true;\n    }\n")
sub('combat/fight.cc',
    "    if (memory.camp_fled >= 0 && !memory.siege) return true;\n    // Willow holds no fight: an enemy likely",
    "    if (memory.camp_fled >= 0 && !memory.siege) {\n        " + wh(4) + "\n        return true;\n    }\n    // Willow holds no fight: an enemy likely")
sub('combat/fight.cc',
    "        && !willow_stands(world))\n        return true;\n    return finish_heal(world, pathing, safety) || stand_lost_at(world, safety, hold);\n",
    "        && !willow_stands(world)) {\n        " + wh(5) + "\n        return true;\n    }\n"
    "    const bool fc_home = finish_heal(world, pathing, safety) || stand_lost_at(world, safety, hold);\n"
    "    " + B + '({ ' + G + 'std::printf("WH %d %u %d %d %d %d\\n", world.round, my_handle(), here.x, here.y, static_cast<int>(my_health()), fc_home ? 6 : 0); });\n'
    "    return fc_home;\n")
sub('combat/fight.cc',
    "        && !finishing_camp(world, hold.p) && !hold.keeps_us(safety))\n        return true;\n    return outmatched(world, safety, hold) && !hold.keeps_us(safety);\n",
    "        && !finishing_camp(world, hold.p) && !hold.keeps_us(safety)) {\n        " + B + "({ fc_drawn = 1; });\n        return true;\n    }\n"
    "    " + B + "({ fc_drawn = 2; });\n"
    "    return outmatched(world, safety, hold) && !hold.keeps_us(safety);\n")
sub('combat/fight.cc', "namespace {\n\n// The hold we would keep at p (hold_rounds)", "namespace {\n\nint fc_drawn = 0;\n\n// The hold we would keep at p (hold_rounds)")
D_OLD = 'debug_block({ std::printf("D %d %u %c %d %d\\n", world.round, static_cast<std::uint32_t>(world.me().handle), static_cast<char>(decision), memory.farm_group, memory.claim); });\n'
TT = ("    " + B + "({\n"
    f"        if (world.round <= {LIM} && world.me().alive) {{\n"
    "            const auto& me = world.me();\n"
    "            const vec2 p = my_position();\n"
    "            std::printf(\"TT %d %u %d %d %d %d %d %d %d\\n\", world.round, static_cast<std::uint32_t>(me.handle),\n"
    "                                world.turn_start.x, world.turn_start.y, p.x, p.y, static_cast<int>(my_health()),\n"
    "                                static_cast<int>(my_max_health()), static_cast<int>(my_gems()));\n"
    "            for (const auto& e : world.enemies) {\n"
    "                if (!e.alive || !e.visible) continue;\n"
    "                std::printf(\"EB %d %u %u %d %d %d %d %d %d %d\\n\", world.round, static_cast<std::uint32_t>(me.handle),\n"
    "                                     static_cast<std::uint32_t>(e.handle), e.pos.x, e.pos.y,\n"
    "                                     static_cast<int>(e.health), static_cast<int>(e.max_health), static_cast<int>(e.strength),\n"
    "                                     static_cast<int>(e.focus), e.gems);\n"
    "            }\n"
    "        }\n"
    "    });\n")
sub('bot.cc', "    " + D_OLD, "    " + D_OLD + TT)
ft = (s / 'combat/fight.cc').read_text()
if "    if (safety.stun_kill(here)) return true;\n" in ft:
    sub('combat/fight.cc', "    if (safety.stun_kill(here)) return true;\n", "    if (safety.stun_kill(here)) {\n        " + wh(7) + "\n        return true;\n    }\n")
sh = (s / 'model/safety.h').read_text()
if "    bool stun_kill(vec2 p);\n" in sh:
    sub('model/safety.h', "    bool stun_kill(vec2 p);\n", "    bool stun_kill(vec2 p);\n"
        "    void trace_stun(vec2 p) {\n"
        "        const bool k = stun_kill(p);\n"
        "        for (auto left = live_enemies(); left; left &= left - 1) {\n"
        "            const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];\n"
        "            if (!e.visible && !credible_unseen(e)) continue;\n"
        "            const auto& c = stun_chain(e);\n"
        "            if (c.reach < 0) continue;\n"
        "            const int d = std::max(std::abs(p.x - e.pos.x), std::abs(p.y - e.pos.y));\n"
        "            std::printf(\"SC %d %u %u %d %d %d %d %d %d %d %d\\n\", world_.round, static_cast<std::uint32_t>(world_.me().handle), static_cast<std::uint32_t>(e.handle), foes_[static_cast<std::size_t>(e.index)].turns, c.reach, d,\n"
        "                        static_cast<int>(c.damage[static_cast<std::size_t>(std::min(d, Strike::max_reach))]), static_cast<int>(own_health_), static_cast<int>(k), static_cast<int>(e.visible), stun_kill_reach(e));\n"
        "        }\n"
        "    }\n")
    sub('bot.cc', "            const vec2 p = my_position();\n            std::printf(\"TT", "            const vec2 p = my_position();\n            safety.trace_stun(world.turn_start);\n            std::printf(\"TT")
    sub('model/pathing.cc', "bool Pathing::move_to(vec2 tile, bool* refused) {\n    if (refused) *refused = true;\n    throw_if_stale();\n",
        "bool Pathing::move_to(vec2 tile, bool* refused) {\n    if (refused) *refused = true;\n    throw_if_stale();\n"
        "    debug_block({ if (world_.round <= " + str(LIM) + " && safety_ && safety_->stun_kill_within(tile, 0)) std::printf(\"MZ %d %u %d %d %d %d %d\\n\", world_.round, static_cast<std::uint32_t>(world_.me().handle), tile.x, tile.y, guard_ != nullptr ? 1 : 0, guard_fn_ != nullptr ? 1 : 0, guard_ && test(*guard_, tile) ? 1 : 0); });\n")
if LITE:
    bt = (s / 'bot.cc').read_text()
    old = "                if (!e.alive || !e.visible) continue;\n                std::printf(\"EB"
    assert bt.count(old) == 1
    (s / 'bot.cc').write_text(bt.replace(old, "                if (true) continue;\n                std::printf(\"EB"))
print('ok', dst)
