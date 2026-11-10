from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/economy/camps.cc';s=p.read_text()
s=s.replace('CampLeft* left, int n, int range) {','CampLeft* left, int n, int range, bool incremental = false) {')
a=s.index('    if (n > 1)\n        std::sort(left, left + n,')
b=s.index('    for (int i = 0; i < n; ++i) {',a)
s=s[:a]+'''    const auto before = [](const CampLeft& a, const CampLeft& b) {
        const float x = a.strength * b.health, y = b.strength * a.health;
        return x != y ? x > y : a.fire < b.fire;
    };
    if (incremental) {
        for (int i = 1; i < n; ++i) {
            const auto member = left[i];
            int j = i;
            while (j > 0 && before(member, left[j - 1])) left[j] = left[j - 1], --j;
            left[j] = member;
        }
    } else if (n > 1) std::sort(left, left + n, before);
'''+s[b:]
s=s.replace('        slot->version = belief.version, slot->range = range;', '        const bool incremental = slot->range == range;\n        slot->version = belief.version, slot->range = range;')
a=s.index('            int living = 0;',s.index('CampLeft* const sorted'))
b=s.index('            slot->n = living;',a)
s=s[:a]+'''            int living = 0;
            static std::vector<std::uint8_t> seen;
            if (incremental) {
                seen.assign(group.members.size(), 0);
                for (int j = 0; j < slot->n; ++j) {
                    const int m = sorted[j].member;
                    seen[static_cast<std::size_t>(m)] = 1;
                    const float hp = fresh ? group.members[m].max_health : belief.health[m];
                    if (hp > 0) sorted[living++] = {hp, group.members[m].strength, m, 0.0f, -1.0f};
                }
            }
            for (std::size_t m = 0; m < group.members.size(); ++m) {
                if (incremental && seen[m]) continue;
                const float hp = fresh ? group.members[m].max_health : belief.health[m];
                if (hp > 0) sorted[living++] = {hp, group.members[m].strength, static_cast<int>(m), 0.0f, -1.0f};
            }
'''+s[b:]
s=s.replace('clear_fire(world.map(), g, sorted, living, range);','clear_fire(world.map(), g, sorted, living, range, incremental);')
p.write_text(s)
