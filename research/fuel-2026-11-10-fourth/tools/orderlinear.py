from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/economy/camps.cc';s=p.read_text();a=s.index('// Whether `sorted`, a build');b=s.index('// Kept per group, strength and range',a)
s=s[:a]+'''// With the same living set, checking neighbouring keys settles whether the old order still
// sorts. A new tie is rebuilt so its geometry tie-break is applied; an existing tie stays ordered.
[[gnu::noinline]] bool order_holds(const CampGroup& group, const CampBelief& belief, bool fresh, CampLeft* sorted, int n) {
    int living = 0;
    for (std::size_t i = 0; i < group.members.size(); ++i)
        living += (fresh ? group.members[i].max_health : belief.health[i]) > 0;
    if (living != n) return false;
    float previous_old = 0;
    for (int i = 0; i < n; ++i) {
        auto& c = sorted[i];
        const float hp = fresh ? group.members[c.member].max_health : belief.health[c.member];
        if (!(hp > 0)) return false;
        if (i > 0) {
            const auto& p = sorted[i - 1];
            const float x = p.strength * hp, y = c.strength * p.health;
            if (x < y || (x == y && p.strength * c.health != c.strength * previous_old)) return false;
        }
        previous_old = c.health;
        c.health = hp;
    }
    return true;
}

'''+s[b:];p.write_text(s)
