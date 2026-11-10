from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/model';h=(p/'safety.h').read_text()
a=h.index('    std::array<Window, tile_sets> tiles_;');b=h.index('    const World* world_',a)
arrays=h[a:b];h=h[:a]+h[b:]
a=h.index('    vec2 sets_origin_');b=h.index('    // The ways depend',a)
keys=h[a:b];h=h[:a]+'''    struct Sets {
'''+arrays+keys+'''    };
    std::array<Sets, 4> sets_by_;
    Sets* sets_ = nullptr;
'''+h[b:]
for name in ['tiles_','extent_','sets_origin_','sets_occupied_','sets_fixed_','sets_kind_','sets_reusable_','sets_built_','sets_camps_version_']:
    if name in ['tiles_','extent_']:
        # Only the bound accessor sits outside the new Sets structure.
        h=h.replace(f'return {name}[',f'return sets_->{name}[')
(p/'safety.h').write_text(h)
s=(p/'safety.cc').read_text()
a=s.index('void Reach::build(');b=s.index('Blow Threat::at',a);t=s[a:b]
for name in ['tiles_','extent_','sets_origin_','sets_occupied_','sets_fixed_','sets_kind_','sets_reusable_','sets_built_','sets_camps_version_']:
    import re
    t=re.sub(r'\b'+name+r'\b','sets_->'+name,t)
key='    const auto kind = static_cast<std::uint8_t>(twice | dash << 1);'
assert key in t
t=t.replace(key,key+'\n    sets_ = &sets_by_[kind];')
s=s[:a]+t+s[b:];(p/'safety.cc').write_text(s)
