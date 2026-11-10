from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/model/safety.cc'
s=p.read_text();a=s.index('    float single = -1, walked = -1;');b=s.index('    // Largest damage first:',a)
s=s[:a]+'''    float single = -1, walked = -1;
    int single_range = 0, walked_range = 0, stun_range = 0;
    for (int i = 0; i < ws.count; ++i) {
        const auto& w = ws.way[i];
        auto& best = w.walked ? walked : single;
        auto& range = w.walked ? walked_range : single_range;
        if (w.damage > best) best = w.damage, range = w.range;
        else if (w.damage == best) range = std::max(range, static_cast<int>(w.range));
        if (w.stuns) stun_range = std::max(stun_range, static_cast<int>(w.range));
    }
    ws.from_here = {std::max({0.0f, walked, single < 0 ? 0.0f : single + (twice ? s : 0.0f)}), true, ws.stuns};
    int settled = 0;
    if (walked == ws.from_here.damage) settled = walked_range;
    if (single == ws.from_here.damage) settled = std::max(settled, single_range);
    if (twice && single >= 0 && single + s == ws.from_here.damage)
        settled = std::max(settled, std::min(single_range, static_cast<int>(ws.way[ws.basic].range)));
    ws.from_here_range = std::min(win_r, ws.stuns ? std::min(settled, stun_range) : settled);
'''+s[b:]
s=s.replace('        // Every movement set contains the origin. Seeing the target from there settles every way within this range.', '        // Every movement set contains the origin. The strongest damage and every possible stun are settled here.')
# The dynamic settled range supersedes the old minimum of all pattern ranges.
s=s.replace('        int from_here_range = win_r;\n','').replace('                    out.from_here_range = std::min(out.from_here_range, range);\n','').replace('    ws.from_here_range = pattern.from_here_range;\n','')
p.write_text(s)
