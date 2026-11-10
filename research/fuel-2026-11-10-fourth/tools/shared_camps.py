from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/model'
cc=(p/'pathing.cc').read_text()
a=cc.index('// The first build draws every member alive')
b=cc.index('std::unique_ptr<Pathing::Approach>&',a)
chunk=cc[a:b].replace('Pathing::draw_all_camps()', 'World::draw_all_camps() const').replace('Pathing::live_camps()', 'World::live_camps() const').replace('world_.camps_version','camps_version').replace('world_.camps_dirty','camps_dirty').replace('world_.camps[g]','camps[g]')
cc=cc[:a]+'const bitboard& Pathing::live_camps() { return world_.live_camps(); }\n\n'+cc[b:]
cc=cc.replace('live_flips_', 'world_.live_flips()')
(p/'pathing.cc').write_text(cc)
cc=(p/'world.cc').read_text(); idx=cc.rindex('} // namespace aph'); cc=cc[:idx]+chunk+cc[idx:]; (p/'world.cc').write_text(cc)
h=(p/'pathing.h').read_text(); a=h.index('    bitboard live_camps_;'); b=h.index('    bool centres_ready_',a); fields=h[a:b]; h=h[:a]+h[b:]; h=h.replace('return live_flips_;','return world_.live_flips();'); (p/'pathing.h').write_text(h)
h=(p/'world.h').read_text(); h=h.replace('since Pathing::live_camps','since live_camps'); h=h.replace('    std::uint32_t camps_version', '    const bitboard& live_camps() const;\n    std::uint32_t live_flips() const { return live_flips_; }\n    std::uint32_t camps_version'); pos=h.index('private:',h.index('class World'))
fields=fields.replace('    bitboard','    mutable bitboard').replace('    std::','    mutable std::').replace('draw_all_camps();','draw_all_camps() const;'); h=h[:pos]+h[pos:].replace('private:', 'private:\n'+fields,1); (p/'world.h').write_text(h)
s=(p/'safety.cc').read_text(); a=s.index('// By tile, once looked up: its camp group'); b=s.index('// The enemy wards',a); s=s[:a]+s[b:]
a=s.index('        // A camp in a bush is unseen from outside its cluster'); b=s.index('        units_ |= live;',a)
s=s[:a]+'''        const Window live = board_window(world, world.live_camps(), origin_) & camps;
        // A dash may cross a camp hidden in a bush.
        if (dash) pass &= ~(live & ~board_window(world, world.map().bushes, origin_));
        land &= ~live;
'''+s[b:]; (p/'safety.cc').write_text(s)
