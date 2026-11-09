"""tickgrid.py SRC: tick<4>() (an amortised checkpoint) at the entry of every top-level function in the
decision's files, except inline/constexpr ones, tiny hot ones and those already checked."""
import re, sys
from pathlib import Path
S = Path(sys.argv[1]); total = 0
FILES = sorted([*S.glob('combat/*.cc'), *S.glob('economy/*.cc'), S/'model/safety.cc', S/'model/turn_order.cc', S/'model/turn_window.cc', S/'model/enemy_reach.cc', S/'bot.cc'])
TINY = ['Safety::struck(', 'Safety::gone(', 'prospected(', 'shard_of(', 'emblem_of(', 'reach_pool(', 'threat_pool(', 'Reach::at(', 'act(Side', 'camp_tile(',
        'live_member(', 'ward_of(', 'next_turn_round(', 'add_shards(', 'add_completion(', 'attack(Fighter', 'cast(Fighter', 'each(int', 'shards_needed(',
        'priced_passive(', 'member_pool(', 'next_threat(', 'mean_spawn_steps(', 'fight_share(', 'shops_at_home(', 'carries_crystal(', 'can_buy_crystal(',
        'gold_rate(', 'gold_paid(', 'reactive_bag(', 'rank_code(', 'packed_priority(', 'camp_hits(', 'my_', 'Safety::Safety(']
pat = re.compile(r'^(\[\[[^\]]*\]\]\s*)?[A-Za-z_][\w:<>,\s\*&]*\s[\*&]?[\w:~]+\([^;]*\)\s*(const\s*)?(noexcept\s*)?\{\s*$')
for f in FILES:
    lines = f.read_text().split('\n'); out = []; n = 0
    for i, l in enumerate(lines):
        out.append(l)
        if not pat.match(l) or 'constexpr' in l or 'inline' in l or l.startswith(('namespace', 'struct', 'class', 'union', 'enum', 'template', 'if ', 'for ', 'while ', 'switch', 'else', 'return')):
            continue
        if any(t in l for t in TINY): continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ''
        if 'tick<' in nxt or 'checkpoint(' in nxt or 'throw_if_stale' in nxt: continue
        out.append('    tick<4>();'); n += 1
    f.write_text('\n'.join(out)); total += n
    print(f.relative_to(S), n)
print('total', total)
