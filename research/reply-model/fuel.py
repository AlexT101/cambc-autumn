"""Fuel of one team's fighters in `fastrunner scenario --turns` rollouts: turns after the warm start.

    python3 research/reply-model/fuel.py ROLLOUTS.jsonl TEAM [...pairs]
"""
import json
import sys


def main():
    a = sys.argv[1:]
    for k in range(0, len(a), 2):
        path, team = a[k], int(a[k + 1])
        fuel, oof, n = [], 0, 0
        for line in open(path):
            r = json.loads(line)
            if "error" in r:
                continue
            for f in r["fighters"]:
                if f["team"] != team:
                    continue
                for i, t in enumerate(f.get("turn_log", [])):
                    if i == 0 or not t[3]:
                        continue  # the warm start's turn; turns that did not act (dead, stunned)
                    n += 1
                    fuel.append(t[1])
                    oof += t[2] == 1
        fuel.sort()
        mean = sum(fuel) / max(1, n)
        p90 = fuel[int(0.9 * n)] if n else 0
        print(f"{path} team {team}: {n} turns, mean {mean / 1000:.1f}k, p90 {p90 / 1000:.1f}k, out of fuel {100 * oof / max(1, n):.2f}%")


main()
