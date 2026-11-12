"""Rule layer (mitere section 3, targeting): Mite's basic attacks take the champion with the lowest absolute health
in reach (0.71 of r7's choices with 2+ in reach). The strike search may then hit only the lowest-health foe open to
an attack at that point of the plan; camps and spells are unchanged.
    py rule_target.py BODY_DIR"""
import sys
from pathlib import Path
f = Path(sys.argv[1]) / 'src/combat/plan.cc'; s = f.read_text()
old = '''    if (s.attack)
        for (int t = 0; t < n; ++t) {
            if (h[t] <= 0 || !open(u[t].legal) || hoisted(s, t)) continue;
'''
new = '''    // Mite body (mitefit rule_target.py): a basic attack takes the lowest-health foe in reach.
    float lowest = 1e30f;
    if (s.attack)
        for (int t = 0; t < n; ++t)
            if (h[t] > 0 && u[t].foe && open(u[t].legal)) lowest = std::min(lowest, h[t]);
    if (s.attack)
        for (int t = 0; t < n; ++t) {
            if (h[t] <= 0 || !open(u[t].legal) || hoisted(s, t) || (u[t].foe && h[t] > lowest + 0.5f)) continue;
'''
assert s.count(old) == 1
f.write_text(s.replace(old, new)); print('patched', f)
