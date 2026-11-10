from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/model';h=(p/'safety.h').read_text();h=h.replace('        int basic = -1; // the plain basic attack\'s way','        Blow pointblank;\n        int basic = -1; // the plain basic attack\'s way');(p/'safety.h').write_text(h)
s=(p/'safety.cc').read_text();key='    // Largest damage first: a query stops at the first way that reaches it.'
s=s.replace(key,'''    float single = -1, walked = -1;
    for (int i = 0; i < ws.count; ++i) {
        const auto& w = ws.way[i];
        if (w.walked) walked = std::max(walked, w.damage);
        else single = std::max(single, w.damage);
    }
    ws.pointblank = {std::max({0.0f, walked, single < 0 ? 0.0f : single + (twice ? s : 0.0f)}), true, ws.stuns};
'''+key)
key='    const auto& pattern = patterns[&f - champion_table.data()]'
s=s.replace(key,'''    static_assert([] {
        for (const auto& kit : patterns)
            for (const auto& pattern : kit)
                for (int i = 0; i < pattern.count; ++i)
                    if (pattern.terms[i].way.range < 1) return false;
        return true;
    }());
'''+key)
key='        const auto& ws = *ways_;\n        int ward = -1;'
s=s.replace(key,'''        const auto& ws = *ways_;
        // Every movement set contains the origin; all attacks reach a neighbour that is outside bushes.
        if (d <= 1 && !t.bush(p)) {
            memo = {p, ws.pointblank, stamp_};
            return ws.pointblank;
        }
        int ward = -1;''')
(p/'safety.cc').write_text(s)
