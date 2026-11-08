"""Split bank2's frames by source game: 10% of games (md5 of the game id) held out for validation.

    python3 research/reply-model/split.py BANK.jsonl.gz OUTDIR --train N --val M --seed S
"""
import gzip, hashlib, json, random, sys
from pathlib import Path

def held(game):
    return int(hashlib.md5(game.encode()).hexdigest(), 16) % 10 == 0

def main():
    bank, out = sys.argv[1], Path(sys.argv[2])
    a = sys.argv[3:]
    n_train = int(a[a.index("--train") + 1]); n_val = int(a[a.index("--val") + 1]); seed = int(a[a.index("--seed") + 1])
    out.mkdir(parents=True, exist_ok=True)
    tr, va = [], []
    with gzip.open(bank, "rt") as f:
        for line in f:
            i = line.index('"game":"') + 8
            g = line[i:line.index('"', i)]
            (va if held(g) else tr).append(line)
    rng = random.Random(seed)
    rng.shuffle(tr); rng.shuffle(va)
    print(f"train frames {len(tr)}, held-out frames {len(va)}")
    (out / "train.jsonl").write_text("".join(tr[:n_train]))
    (out / "val.jsonl").write_text("".join(va[:n_val]))

main()
