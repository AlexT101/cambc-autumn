"""Check an exported reply_lean.h against the pickled lean model on held-out rows (native clang++).

    python3 research/reply-model/check_lean.py LEAN.pkl HEADER.h VAL.npz
"""
import os, pickle, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import train  # noqa: E402

m = pickle.load(open(sys.argv[1], "rb"))
z = np.load(sys.argv[3])
X = train.danger_rows(z["D"], z["Dc"])[0][:20000]
X = X.copy()
unused = [i for i in range(X.shape[1]) if i not in m["idx"]]
X[:, unused] = np.nan  # the bot leaves these slots stale: the model must not read them
d = tempfile.mkdtemp()
src = os.path.join(d, "t.cc")
open(src, "w").write(f'''#include <cstdio>
#include "{os.path.abspath(sys.argv[2])}"
int main() {{
    int n, k; float x[64];
    if (scanf("%d %d", &n, &k) != 2) return 1;
    for (int i = 0; i < n; ++i) {{
        for (int j = 0; j < k; ++j) scanf("%a", &x[j]);
        printf("%a\\n", aph::reply::lean::danger(x));
    }}
}}
''')
subprocess.run(["clang++", "-O1", "-std=c++20", src, "-o", os.path.join(d, "t")], check=True)
inp = [f"{len(X)} {X.shape[1]}"] + [" ".join(float(v).hex() for v in row) for row in X]
out = subprocess.run([os.path.join(d, "t")], input="\n".join(inp), capture_output=True, text=True, check=True).stdout.split()
c = np.array([float.fromhex(v) for v in out])
p = np.maximum(m["est"].predict(X[:, m["idx"]]), 0)
print("lean max abs diff", np.abs(c - p).max(), "nan outputs", int(np.isnan(c).sum()))
