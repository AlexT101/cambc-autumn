"""Check an exported reply_model.h against the pickled model on held-out rows (native clang++).

    python3 research/reply-model/check_export.py MODEL.pkl HEADER.h VAL.npz
"""
import os, pickle, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import train  # noqa: E402

m = pickle.load(open(sys.argv[1], "rb"))
z = np.load(sys.argv[3])
Xd = train.danger_rows(z["D"], z["Dc"])[0][:20000]
Xp = train.press_rows(z["P"], z["Pc"])[0][:20000]
d = tempfile.mkdtemp()
src = os.path.join(d, "t.cc")
open(src, "w").write(f'''#include <cstdio>
#include <vector>
#include "{os.path.abspath(sys.argv[2])}"
int main() {{
    int n, k; float x[64];
    for (int s = 0; s < 2; ++s) {{
        if (scanf("%d %d", &n, &k) != 2) return 1;
        for (int i = 0; i < n; ++i) {{
            for (int j = 0; j < k; ++j) scanf("%a", &x[j]);
            if (s == 0) printf("%a\\n", aph::reply::model::danger(x));
            else printf("%a %a\\n", aph::reply::model::press_hit(x), aph::reply::model::press_damage(x));
        }}
    }}
}}
''')
subprocess.run(["clang++", "-O1", "-std=c++20", src, "-o", os.path.join(d, "t")], check=True)
inp = []
for X in (Xd, Xp):
    inp.append(f"{len(X)} {X.shape[1]}")
    inp += [" ".join(float(v).hex() for v in row) for row in X]
out = subprocess.run([os.path.join(d, "t")], input="\n".join(inp), capture_output=True, text=True, check=True).stdout.split("\n")
cd = np.array([float.fromhex(v) for v in out[:len(Xd)]])
cp = np.array([[float.fromhex(v) for v in l.split()] for l in out[len(Xd):len(Xd) + len(Xp)]])
pd = m["danger"][0].predict_proba(Xd)[:, 1] * np.maximum(m["danger"][1].predict(Xd), 0)
ph = m["press"][0].predict_proba(Xp)[:, 1]
pm = np.maximum(m["press"][1].predict(Xp), 0)
print("danger max abs diff", np.abs(cd - pd).max(), "pressure hit", np.abs(cp[:, 0] - ph).max(), "damage", np.abs(cp[:, 1] - pm).max())
