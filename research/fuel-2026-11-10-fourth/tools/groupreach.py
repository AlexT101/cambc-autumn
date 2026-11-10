from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/model'
h=(p/'safety.h').read_text().replace('    std::uint32_t sets_camps_version_ = 0;', '''    std::uint32_t sets_camps_version_ = 0;
    std::array<std::int16_t, 8> sets_groups_;
    std::array<std::uint32_t, 8> sets_group_versions_;
    int sets_group_count_ = 0;''');(p/'safety.h').write_text(h)
s=(p/'safety.cc').read_text();a=s.index('    if ((sets_reusable_ ||');b=s.index('    sets_built_ = true;',a)
s=s[:a]+'''    if (sets_built_ && sets_origin_ == origin_ && sets_kind_ == kind
        && sets_occupied_.lo == occupied.lo && sets_occupied_.hi == occupied.hi
        && sets_fixed_.lo == fixed.lo && sets_fixed_.hi == fixed.hi) {
        bool reusable = sets_reusable_;
        if (!reusable && !splash_) {
            reusable = sets_camps_version_ == world.camp_geometry_version;
            if (!reusable && sets_group_count_ <= static_cast<int>(sets_groups_.size())) {
                reusable = true;
                for (int i = 0; i < sets_group_count_; ++i)
                    reusable &= sets_group_versions_[i] == world.camps[sets_groups_[i]].geometry_version;
            }
        }
        if (reusable) {
            sets_camps_version_ = world.camp_geometry_version;
            set_bounds();
            return;
        }
    }
'''+s[b:]
s=s.replace('    sets_camps_version_ = world.camp_geometry_version;\n    sets_origin_', '    sets_camps_version_ = world.camp_geometry_version;\n    sets_group_count_ = 0;\n    sets_origin_')
s=s.replace('''                const int group = world.map().group_at(p), member = world.map().camp_member_at(p);
                if (group < 0''','''                const int group = world.map().group_at(p), member = world.map().camp_member_at(p);
                if (!splash_ && group >= 0 && sets_group_count_ <= static_cast<int>(sets_groups_.size())) {
                    int k = 0;
                    while (k < sets_group_count_ && sets_groups_[k] != group) ++k;
                    if (k == sets_group_count_) {
                        if (k < static_cast<int>(sets_groups_.size())) {
                            sets_groups_[k] = static_cast<std::int16_t>(group);
                            sets_group_versions_[k] = world.camps[group].geometry_version;
                        }
                        ++sets_group_count_;
                    }
                }
                if (group < 0''')
# Avoid reading the overflow sentinel as an array index on subsequent members.
s=s.replace('group >= 0 && sets_group_count_ <=', 'group >= 0 && sets_group_count_ <')
# A full list can still contain a new group. Mark overflow conservatively once full.
s=s.replace('''                if (group < 0 || member < 0''','''                if (sets_group_count_ == static_cast<int>(sets_groups_.size())) ++sets_group_count_;
                if (group < 0 || member < 0''')
(p/'safety.cc').write_text(s)
