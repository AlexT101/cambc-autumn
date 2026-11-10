from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/model';h=(p/'safety.h').read_text().replace('        Blow pointblank;', '        Blow pointblank;\n        int pointblank_range = 0;');(p/'safety.h').write_text(h)
s=(p/'safety.cc').read_text();s=s.replace('        bool stuns = false;\n    };\n    static constexpr auto patterns', '        bool stuns = false;\n        int pointblank_range = win_r;\n    };\n    static constexpr auto patterns')
s=s.replace('        bool stuns = false, stationary = true;\n    };\n    static constexpr auto patterns', '        bool stuns = false, stationary = true;\n        int pointblank_range = win_r;\n    };\n    static constexpr auto patterns')
s=s.replace('                    auto& t = out.terms[j];\n                    t.way.stuns', '                    out.pointblank_range = std::min(out.pointblank_range, range);\n                    auto& t = out.terms[j];\n                    t.way.stuns')
s=s.replace('    ws.stuns = pattern.stuns;', '    ws.stuns = pattern.stuns;\n    ws.pointblank_range = pattern.pointblank_range;')
s=s.replace('        if (d <= 1 && !t.bush(p)) {', '''        if (d <= ws.pointblank_range
            && ((d <= 1 && !t.bush(p)) || (sight(*world_, p, d > 1) & win_bit(win_r - dx, win_r - dy)))) {''')
(p/'safety.cc').write_text(s)
