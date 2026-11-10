from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/model'
h=(p/'world.h').read_text();a=h.index('struct CampBelief {');i=h.index('    std::uint32_t version = 0;',a);h=h[:i]+h[i:].replace('    std::uint32_t version = 0;', '    std::uint32_t version = 0;\n    std::uint32_t geometry_version = 0; // living member set, including respawns',1);(p/'world.h').write_text(h)
s=(p/'world.cc').read_text()
s=s.replace('    camp_geometry_version += c.state == CampState::alive;', '    if (c.state == CampState::alive) ++camp_geometry_version, ++c.geometry_version;')
s=s.replace('            ++camp_geometry_version;', '            ++camp_geometry_version, ++c.geometry_version;')
s=s.replace('    camp_geometry_version += (c.state == CampState::alive) != (previous == CampState::alive);', '    if ((c.state == CampState::alive) != (previous == CampState::alive)) ++camp_geometry_version, ++c.geometry_version;')
s=s.replace('                if constexpr (live) camp_geometry_version += (hp > 0) != (health[i] > 0);', '                if constexpr (live)\n                    if ((hp > 0) != (health[i] > 0)) ++camp_geometry_version, ++c.geometry_version;')
(p/'world.cc').write_text(s)
s=(p/'pathing.cc').read_text().replace('if (live_versions_[g] == c.version)', 'if (live_versions_[g] == c.geometry_version)').replace('live_versions_[g] = c.version;', 'live_versions_[g] = c.geometry_version;');(p/'pathing.cc').write_text(s)
s=(p/'safety.cc').read_text();a=s.index('const MemberLanes& member_lanes(');b=s.index('// A tile in our vision',a);s=s[:a]+s[a:b].replace('c.version','c.geometry_version')+s[b:];(p/'safety.cc').write_text(s)
