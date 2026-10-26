import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from proto import find_cuts, rebuild, load, runwidth
mp = json.load(open(sys.argv[1]))
dash = len(sys.argv) > 2 and sys.argv[2] == 'dash'
reps, cuts, (w, h, op, ours) = find_cuts(mp, dash=dash)
pocket, block = rebuild(w, h, op, ours, cuts)
rs = set(reps)
cs = set(cuts)
for y in range(h - 1, -1, -1):
    row = ''
    for x in range(w):
        p = (x, y)
        if not op[y][x]:
            row += '#'
        elif p in cs:
            row += 'C'
        elif p in rs:
            row += 'r'
        elif p in block:
            row += 'X'
        elif p in pocket:
            row += 'p'
        elif p in ours:
            row += 'A'
        else:
            row += '.'
    print(row)
print('cuts', cuts)
