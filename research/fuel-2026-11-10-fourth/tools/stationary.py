from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/model'
h=(p/'safety.h').read_text();h=h.replace('        bool stuns = false;\n        int basic = -1;', '        bool stuns = false, stationary = false;\n        int basic = -1;');(p/'safety.h').write_text(h)
s=(p/'safety.cc').read_text();a=s.index('void Reach::build(');b=s.index('void Reach::set_bounds()',a);t=s[a:b];t=t.replace('        build_ways(e, ready, ready2, twice);\n','').replace('    build_ways(e, ready, ready2, twice);\n','');key='    // Our champions around it,';i=t.index(key)
t=t[:i]+'''    splash_ = f.passive == Passive::splash_attack;
    build_ways(e, ready, ready2, twice);
    if (ways_->stationary && !splash_) {
        tiles_[here] = win_bit(win_r, win_r);
        extent_[here] = 0;
        set_bounds();
        return;
    }
'''+t[i:];s=s[:a]+t+s[b:]
s=s.replace('        bool stuns = false;\n    };\n    static constexpr auto patterns', '        bool stuns = false, stationary = true;\n    };\n    static constexpr auto patterns')
s=s.replace('                    auto& t = out.terms[j];\n                    t.way.stuns', '                    out.stationary &= from == here;\n                    auto& t = out.terms[j];\n                    t.way.stuns')
s=s.replace('    ws.stuns = pattern.stuns;','    ws.stuns = pattern.stuns;\n    ws.stationary = pattern.stationary;');(p/'safety.cc').write_text(s)
